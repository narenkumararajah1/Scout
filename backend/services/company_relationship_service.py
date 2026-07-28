"""Company-to-company relationships (roadmap Phase 6 - Relationship
Intelligence, basic level). User-curated, not AI-generated - see
backend/database/models/company_relationship.py's docstring for why.
"""

from __future__ import annotations

import uuid
from typing import Optional

from backend.database.models import CompanyRelationship
from backend.database.models.company_relationship import RELATIONSHIP_TYPES
from backend.repositories.postgres.company_relationship_repository import (
    create_relationship,
    delete_relationship,
    get_relationship,
    list_relationships_for_company,
)
from backend.services import company_service


async def add_relationship(
    company_id: str,
    relationship_type: str,
    related_company_id: Optional[str] = None,
    related_company_name: Optional[str] = None,
    notes: Optional[str] = None,
) -> CompanyRelationship:
    if relationship_type not in RELATIONSHIP_TYPES:
        raise ValueError(f"relationship_type must be one of {RELATIONSHIP_TYPES}, got {relationship_type!r}.")

    if not related_company_id and not related_company_name:
        raise ValueError("Provide either related_company_id or related_company_name.")

    if related_company_id:
        if related_company_id == company_id:
            raise ValueError("A company cannot be related to itself.")
        # Raises ValueError with a clear message if the id doesn't exist -
        # propagated as-is rather than wrapped, same convention as every
        # other company-scoped service function in this codebase.
        company_service.get_company(related_company_id)

    return await create_relationship(
        CompanyRelationship(
            id=str(uuid.uuid4()),
            company_id=company_id,
            related_company_id=related_company_id,
            related_company_name=related_company_name,
            relationship_type=relationship_type,
            notes=notes,
        )
    )


async def list_relationships(company_id: str) -> list:
    return await list_relationships_for_company(company_id)


async def remove_relationship(company_id: str, relationship_id: str) -> None:
    relationship = await get_relationship(relationship_id)
    if relationship is None or relationship.company_id != company_id:
        raise ValueError(f"Relationship {relationship_id} does not exist for this company.")
    await delete_relationship(relationship_id)
