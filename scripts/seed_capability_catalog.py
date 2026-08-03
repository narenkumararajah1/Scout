"""Loads Innominds' capability catalog into the vector store.

Capability matching searches the knowledge collection for
entity_type="capability" and turns the hits into the opportunities every
downstream artifact is built from. Before this script the catalog was
six records that existed only in one developer's local Chroma directory:
three generic capability blurbs, two proof points, and a case study for
an invented customer called "Global Fleet Logistics Co.". Nothing
recreated them, so a fresh deployment ran the pipeline against an empty
catalog, matched nothing, produced no opportunities, and failed the
whole analysis with "Reporting Service requires opportunities" - which
reads like a bug in the reporting stage rather than missing seed data.

The catalog now lives in seeds/capability_catalog.json, derived from the
81 case studies actually in the Knowledge Library, so a match means "we
have done this before" and the proof points quote real engagements.
Regenerating it needs an LLM and human review; loading it must work on
any machine with no API key, so the two are separate.

Safe to re-run: ids are derived from entity names, so a second run
updates records in place instead of duplicating them. That also makes it
safe to call from a container entrypoint.

    python -m scripts.seed_capability_catalog
    python -m scripts.seed_capability_catalog --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from backend.models.knowledge import (
    Capability,
    Industry,
    ProofPoint,
    Technology,
)
from backend.repositories.knowledge_repository import (
    index_capability,
    index_industry,
    index_proof_point,
    index_technology,
)

CATALOG_PATH = Path(__file__).parent / "seeds" / "capability_catalog.json"


def stable_id(kind: str, name: str) -> str:
    """A deterministic id, so re-seeding upserts rather than duplicates.

    Chroma keys on the composite "<entity_type>:<id>", and a uuid4 per
    run would leave the old copy behind on every seed - the catalog
    would silently grow and matching would return the same capability
    several times.
    """
    digest = hashlib.sha256(f"{kind}:{name}".encode("utf-8")).hexdigest()
    return digest[:32]


def load_catalog(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Catalog not found at {path}")
    return json.loads(path.read_text())


def seed(catalog: dict, dry_run: bool = False) -> dict:
    counts = {}

    capabilities = [
        Capability(
            id=stable_id("capability", item["name"]),
            name=item["name"],
            description=item["description"],
            practice=item.get("practice"),
            keywords=item.get("keywords", []),
        )
        for item in catalog.get("capabilities", [])
    ]
    industries = [
        Industry(
            id=stable_id("industry", item["name"]),
            name=item["name"],
            description=item.get("description"),
        )
        for item in catalog.get("industries", [])
    ]
    technologies = [
        Technology(
            id=stable_id("technology", item["name"]),
            name=item["name"],
            description=item.get("description"),
        )
        for item in catalog.get("technologies", [])
    ]
    proof_points = [
        ProofPoint(
            id=stable_id("proof_point", item["description"]),
            description=item["description"],
            category=item.get("category"),
        )
        for item in catalog.get("proof_points", [])
    ]

    counts = {
        "capabilities": len(capabilities),
        "industries": len(industries),
        "technologies": len(technologies),
        "proof_points": len(proof_points),
    }
    if dry_run:
        return counts

    for capability in capabilities:
        index_capability(capability)
    for industry in industries:
        index_industry(industry)
    for technology in technologies:
        index_technology(technology)
    for proof_point in proof_points:
        index_proof_point(proof_point)

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, default=CATALOG_PATH, help="Path to the catalog JSON."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate the catalog without writing to the vector store.",
    )
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    counts = seed(catalog, dry_run=args.dry_run)

    verb = "Would index" if args.dry_run else "Indexed"
    for kind, count in counts.items():
        print(f"  {verb} {count} {kind}")
    if not args.dry_run:
        print("Capability catalog seeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
