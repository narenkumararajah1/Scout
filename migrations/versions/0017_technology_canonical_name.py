"""technology canonical names + merge of fragmented duplicates

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-31

The extractor spells one product several ways between runs, so a single
technology accumulated its observation history across several rows and
neither half ever reached the repetition Technology Intelligence needs.
On the live NVIDIA data this affected Omniverse, Riva, NIM, NeMo and
Grace.

This adds the matching key and merges the rows that were already split.

**Merged counts are reconstructed from observation_sources, not summed.**
Summing would overstate: if "Omniverse" was seen in runs 1-2 and "NVIDIA
Omniverse" in runs 2-3, the true observation count is 3, not 4. Each run
stamps every sighting with the same `observed_at`, so counting distinct
timestamps across the merged group recovers the real figure. Where
sources are absent or were trimmed by the retention cap, the maximum of
the group is used instead - understating rather than inflating
confidence, which is the safe direction.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("technologies", sa.Column("canonical_name", sa.String(length=255), nullable=True))
    op.create_index("ix_technologies_canonical_name", "technologies", ["canonical_name"])

    from backend.services.technology_normalization import canonical_name, preferred_display_name

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT t.id, t.company_id, t.name, t.observation_count, t.missed_count,
                   t.consecutive_misses, t.first_seen_at, t.last_seen_at,
                   t.observation_sources, t.category, c.name AS company_name
              FROM technologies t
              JOIN companies c ON c.id = t.company_id
            """
        )
    ).mappings().all()

    groups: dict = {}
    for row in rows:
        key = (row["company_id"], canonical_name(row["name"], row["company_name"]))
        groups.setdefault(key, []).append(row)

    for (company_id, key), members in groups.items():
        survivor = members[0]
        display = survivor["name"]
        category = survivor["category"]
        for member in members[1:]:
            display = preferred_display_name(display, member["name"])
            category = category or member["category"]

        if len(members) > 1:
            # Distinct run timestamps across the group - see the module
            # docstring on why this is not a sum.
            stamps = set()
            for member in members:
                for source in member["observation_sources"] or []:
                    if source.get("observed_at"):
                        stamps.add(source["observed_at"])
            observations = len(stamps) or max(m["observation_count"] or 0 for m in members)
            missed = min(m["missed_count"] or 0 for m in members)
            consecutive = min(m["consecutive_misses"] or 0 for m in members)
            first_seen = min((m["first_seen_at"] for m in members if m["first_seen_at"]), default=None)
            last_seen = max((m["last_seen_at"] for m in members if m["last_seen_at"]), default=None)
            merged_sources = []
            for member in members:
                merged_sources.extend(member["observation_sources"] or [])
            merged_sources = merged_sources[-10:]
        else:
            observations = survivor["observation_count"] or 0
            missed = survivor["missed_count"] or 0
            consecutive = survivor["consecutive_misses"] or 0
            first_seen = survivor["first_seen_at"]
            last_seen = survivor["last_seen_at"]
            merged_sources = survivor["observation_sources"] or []

        looks = observations + missed
        confidence = round(observations / looks, 3) if looks else 0.0

        connection.execute(
            sa.text(
                """
                UPDATE technologies
                   SET canonical_name = :key, name = :name, category = :category,
                       observation_count = :observations, missed_count = :missed,
                       consecutive_misses = :consecutive, first_seen_at = :first_seen,
                       last_seen_at = :last_seen, observation_sources = CAST(:sources AS jsonb),
                       confidence_score = :confidence
                 WHERE id = :id
                """
            ),
            {
                "key": key, "name": display, "category": category,
                "observations": observations, "missed": missed, "consecutive": consecutive,
                "first_seen": first_seen, "last_seen": last_seen,
                "sources": __import__("json").dumps(merged_sources),
                "confidence": confidence, "id": survivor["id"],
            },
        )

        for member in members[1:]:
            connection.execute(
                sa.text("DELETE FROM technologies WHERE id = :id"), {"id": member["id"]}
            )


def downgrade() -> None:
    # The merged rows cannot be un-merged; only the key is reversible.
    op.drop_index("ix_technologies_canonical_name", table_name="technologies")
    op.drop_column("technologies", "canonical_name")
