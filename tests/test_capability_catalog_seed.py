"""The catalog capability matching runs against must be reproducible.

It used to be six records that existed only in one developer's local
Chroma directory - three generic capability descriptions, two proof
points, and a case study for an invented customer. Nothing recreated
them, so the containerised stack ran the pipeline against an empty
catalog and Run Analysis failed with "Reporting Service requires
opportunities from the Opportunity Analysis Service" - an error that
points at the reporting stage rather than at the missing seed data three
stages earlier.

The entrypoint now seeds on every boot, which makes idempotency a
correctness requirement rather than a nicety: uuid4 ids would leave the
previous copy behind on each restart, and matching would start returning
the same capability several times.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts import seed_capability_catalog as seeder


@pytest.fixture
def catalog():
    return json.loads(seeder.CATALOG_PATH.read_text())


class TestTheShippedCatalog:
    def test_it_is_present_and_parses(self, catalog):
        """A fresh clone must be able to seed with no LLM and no key."""
        assert catalog["capabilities"], "no capabilities in the shipped catalog"

    def test_capabilities_carry_what_retrieval_needs(self, catalog):
        """index_capability builds its document from these fields.

        Keywords matter most: they are the prospect-vocabulary terms that
        decide whether a company's situation matches this capability at
        all, so a capability without them is close to unreachable.
        """
        for item in catalog["capabilities"]:
            assert item["name"].strip()
            assert len(item["description"]) > 40, f"{item['name']} has a stub description"
            assert item.get("keywords"), f"{item['name']} has no keywords"

    def test_the_invented_customer_is_gone(self, catalog):
        """The placeholder case study must not come back with the catalog."""
        blob = json.dumps(catalog).lower()
        assert "global fleet logistics" not in blob


class TestSeedingIsRepeatable:
    def test_ids_are_derived_from_names_not_random(self):
        first = seeder.stable_id("capability", "Cloud Migration and Modernization")
        second = seeder.stable_id("capability", "Cloud Migration and Modernization")
        assert first == second

    def test_different_entities_get_different_ids(self):
        assert seeder.stable_id("capability", "A") != seeder.stable_id("capability", "B")

    def test_the_same_name_in_two_kinds_does_not_collide(self):
        """Chroma keys on "<entity_type>:<id>", but a shared id across
        kinds would still make the catalog confusing to inspect."""
        assert seeder.stable_id("capability", "Security") != seeder.stable_id(
            "technology", "Security"
        )

    def test_two_runs_write_the_same_ids(self, catalog):
        """The property the entrypoint depends on: re-seeding upserts."""
        seen = []

        def capture(entity):
            seen.append(entity.id)

        for _ in range(2):
            with patch.object(seeder, "index_capability", capture), patch.object(
                seeder, "index_industry", capture
            ), patch.object(seeder, "index_technology", capture), patch.object(
                seeder, "index_proof_point", capture
            ):
                seeder.seed(catalog)

        half = len(seen) // 2
        assert seen[:half] == seen[half:], "a second seed produced different ids"
        assert len(set(seen)) == half, "ids are not unique within one run"

    def test_dry_run_writes_nothing(self, catalog):
        with patch.object(seeder, "index_capability") as index:
            counts = seeder.seed(catalog, dry_run=True)
        index.assert_not_called()
        assert counts["capabilities"] == len(catalog["capabilities"])
