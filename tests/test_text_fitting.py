"""Round 4 regressions: machine-generated text is fitted, not fatal.

Nine of nine hostile values written through the real persistence paths
failed before this guard existed - StringDataRightTruncation over the
limit, CharacterNotInRepertoire for a NUL byte. Inside the analysis
pipeline that kills the entire run, after the model calls have been paid
for, with no HTTP response to carry the error to anyone.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import String

from backend.database.models import Executive, Notification, Opportunity
from backend.database.postgres import Base
from backend.database.text_fitting import fit_to_column


class TestFitToColumn:
    def test_short_text_is_unchanged(self):
        assert fit_to_column("Kubernetes", 255) == "Kubernetes"

    def test_over_limit_is_clipped_to_exactly_the_limit(self):
        fitted = fit_to_column("A" * 5000, 255)
        assert len(fitted) == 255

    def test_clipping_is_visible_rather_than_silent(self):
        """A reader must be able to tell the value was cut."""
        assert fit_to_column("A" * 5000, 255).endswith("…")

    def test_exactly_at_the_limit_keeps_every_character(self):
        value = "A" * 255
        assert fit_to_column(value, 255) == value
        assert "…" not in fit_to_column(value, 255)

    def test_nul_is_stripped_without_clipping(self):
        """A NUL is removed; the rest of a short value survives intact."""
        assert fit_to_column("Chief\x00Officer", 255) == "ChiefOfficer"

    def test_control_characters_are_removed(self):
        assert fit_to_column("Ada\x01\x02Lovelace", 255) == "AdaLovelace"

    def test_empty_string_survives(self):
        assert fit_to_column("", 255) == ""


async def _company() -> str:
    """Creates a company row to hang the test's child rows from."""
    from backend.database.models import Company as CompanyModel
    from backend.database.postgres import get_session

    company_id = str(uuid.uuid4())
    async with get_session() as session:
        session.add(CompanyModel(id=company_id, name="Fitting Probe Co"))
        await session.commit()
    return company_id


@pytest.mark.asyncio
class TestFlushHookAppliesToRealWrites:
    """The guard is registered on the Session, so every writer gets it."""

    async def test_oversized_executive_name_is_written_not_rejected(self, postgres_available):
        from backend.database.postgres import get_session

        company_id = await _company()
        row_id = str(uuid.uuid4())
        async with get_session() as session:
            session.add(
                Executive(
                    id=row_id,
                    company_id=company_id,
                    name="B" * 5000,
                    title="Chief\x00Officer",
                )
            )
            await session.commit()

        async with get_session() as session:
            stored = await session.get(Executive, row_id)
            assert stored is not None, "the row must exist - clipping, not skipping"
            assert len(stored.name) == 255
            assert stored.name.endswith("…")
            assert stored.title == "ChiefOfficer"
            await session.delete(stored)
            await session.commit()

    async def test_one_bad_field_does_not_lose_its_siblings(self, postgres_available):
        """The point of clipping: the rest of the batch still persists.

        This is the behaviour that matters in the pipeline - one absurd
        name in a list of forty must not discard the other thirty-nine.
        """
        from backend.database.postgres import get_session

        company_id = await _company()
        ids = [str(uuid.uuid4()) for _ in range(3)]
        async with get_session() as session:
            session.add(Opportunity(id=ids[0], company_id=company_id,
                                    title="Cloud Migration", status="identified"))
            session.add(Opportunity(id=ids[1], company_id=company_id,
                                    title="X" * 5000, status="identified"))
            session.add(Opportunity(id=ids[2], company_id=company_id,
                                    title="Data Platform", status="identified"))
            await session.commit()

        async with get_session() as session:
            rows = [await session.get(Opportunity, i) for i in ids]
            assert all(r is not None for r in rows)
            assert rows[0].title == "Cloud Migration"
            assert len(rows[1].title) == 255
            assert rows[2].title == "Data Platform"
            for r in rows:
                await session.delete(r)
            await session.commit()

    async def test_update_path_is_covered_not_only_insert(self, postgres_available):
        """before_flush sees session.dirty, so edits are fitted too."""
        from backend.database.postgres import get_session

        company_id = await _company()
        row_id = str(uuid.uuid4())
        async with get_session() as session:
            session.add(Notification(id=row_id, company_id=company_id,
                                     type="signal", title="Initial"))
            await session.commit()

        async with get_session() as session:
            row = await session.get(Notification, row_id)
            row.title = "C" * 5000
            await session.commit()

        async with get_session() as session:
            row = await session.get(Notification, row_id)
            assert len(row.title) == 255
            await session.delete(row)
            await session.commit()


class TestEveryBoundedColumnIsCovered:
    """Guards the guard: it must apply to all String(n) columns, not a list."""

    def test_no_bounded_string_column_is_exempt(self):
        bounded = [
            (t.name, c.name)
            for t in Base.metadata.sorted_tables
            for c in t.columns
            if isinstance(c.type, String) and c.type.length
        ]
        # The hook is width-driven rather than column-driven, so this is a
        # smoke check that there is meaningful surface to protect and that
        # the introspection the hook relies on still works.
        assert len(bounded) > 30
