"""Company Intelligence (V3 Phase 5 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 3).

Two responsibilities:

1. Persist Knowledge Extraction's output (backend/ai/knowledge_extraction.py,
   Phase 4A) into Postgres - the "separate caller" Phase 4A's docstring
   said would eventually do this. Knowledge Extraction itself still
   never touches persistence; this is that separate caller.
2. Aggregate Company + Technologies + Business Initiatives + Executives
   + recent Signals (+ Glean, if configured) into one profile - read-only,
   no new AI reasoning of its own.

Not called by any existing agent, service, or router - see TECH_DEBT.md.
Executive persistence reuses Phase 3A's existing
backend/repositories/postgres/executive_repository.py functions
unchanged (create/list/update) - it has no upsert primitive of its own,
so the check-then-create-or-update logic lives here, in this new
caller, rather than modifying that already-completed phase's file.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional

from backend.ai.knowledge_extraction import ExtractedEntities
from backend.database.models import BusinessInitiative, Executive
from backend.integrations.glean_client import get_glean_client
from backend.models.company import Company
from backend.repositories.postgres.business_initiative_repository import (
    list_business_initiatives_for_company,
    upsert_business_initiative,
)
from backend.repositories.postgres.executive_repository import (
    create_executive,
    list_executives_for_company,
    update_executive,
)
from backend.repositories.postgres.technology_repository import list_technologies_for_company
from backend.services.technology_intelligence_service import record_observations
from backend.repositories.research_repository import list_signals_for_session


@dataclass
class CompanyIntelligenceProfile:
    company: Company
    technologies: list = field(default_factory=list)
    business_initiatives: list = field(default_factory=list)
    executives: list = field(default_factory=list)
    recent_signals: list = field(default_factory=list)
    glean_knowledge: list = field(default_factory=list)


async def persist_extracted_entities(
    company_id: str,
    extracted: ExtractedEntities,
    research_session_id: Optional[str] = None,
    company_name: Optional[str] = None,
) -> tuple:
    """Persists Knowledge Extraction's technologies/business initiatives/
    executives for one company. Idempotent: business initiatives upsert by
    (company_id, name); executives check for an existing name first and
    update rather than duplicate, since the same company is re-researched
    across cycles.

    **Technologies go through the observation recorder, not
    `upsert_technology`.** That upsert overwrites `confidence_score` and
    `source` on every call, which would erase the accumulated observation
    history on the first re-analysis - and that history is the whole basis
    on which Technology Intelligence distinguishes a company's real stack
    from a one-off mention. The recorder also does something an upsert
    structurally cannot: it marks the technologies this run did *not* see,
    which is what keeps confidence honest rather than monotonically
    rising.
    """
    technologies = await record_observations(
        company_id,
        extracted.technologies,
        company_name=company_name,
        research_session_id=research_session_id,
    )

    business_initiatives = [
        await upsert_business_initiative(
            BusinessInitiative(
                id=str(uuid.uuid4()),
                company_id=company_id,
                name=initiative.name,
                description=initiative.description,
            )
        )
        for initiative in extracted.business_initiatives
    ]

    existing_executives_by_name = {
        executive.name: executive for executive in await list_executives_for_company(company_id)
    }
    executives = []
    for extracted_executive in extracted.executives:
        existing = existing_executives_by_name.get(extracted_executive.name)
        if existing is not None:
            existing.title = extracted_executive.title or existing.title
            executives.append(await update_executive(existing))
        else:
            executives.append(
                await create_executive(
                    Executive(
                        id=str(uuid.uuid4()),
                        company_id=company_id,
                        name=extracted_executive.name,
                        title=extracted_executive.title,
                    )
                )
            )

    return technologies, business_initiatives, executives


async def build_company_intelligence_profile(
    company: Company, research_session: Optional[object] = None
) -> CompanyIntelligenceProfile:
    """Read-only aggregation - does not call Knowledge Extraction or
    persist anything itself; call persist_extracted_entities() first if
    fresh extraction results need saving before building this profile.
    """
    technologies = await list_technologies_for_company(company.id)
    business_initiatives = await list_business_initiatives_for_company(company.id)
    executives = await list_executives_for_company(company.id)

    recent_signals = []
    if research_session is not None:
        recent_signals = await asyncio.to_thread(list_signals_for_session, research_session.id)

    glean_client = get_glean_client()
    glean_knowledge = await glean_client.search(company.name)

    return CompanyIntelligenceProfile(
        company=company,
        technologies=technologies,
        business_initiatives=business_initiatives,
        executives=executives,
        recent_signals=recent_signals,
        glean_knowledge=glean_knowledge,
    )
