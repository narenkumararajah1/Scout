"""Company management business logic (V2 Phase 3, FR-002).

Sits between backend/routers/companies.py and
backend/repositories/company_repository.py: validates and enforces rules
that don't belong in either the API layer (input parsing) or the
repository layer (pure CRUD, no business analysis).

Raises ValueError for "not found" and other business-rule violations;
the router translates these into meaningful HTTP responses rather than
letting them surface as an opaque 500 (IMPLEMENTATION_RULES.md Error
Handling: "avoid silent failures... return meaningful messages").
"""

import sqlite3
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError as SqlAlchemyIntegrityError

from backend.models.company import Company
from backend.repositories import company_repository


def add_company(
    name: str,
    industry: Optional[str] = None,
    headquarters: Optional[str] = None,
    website: Optional[str] = None,
) -> Company:
    company = Company(name=name, industry=industry, headquarters=headquarters, website=website)
    return company_repository.create_company(company)


def get_company(company_id: str) -> Company:
    company = company_repository.get_company(company_id)
    if company is None:
        raise ValueError(f"Company {company_id} does not exist.")
    return company


def list_companies(include_archived: bool = False) -> list[Company]:
    companies = company_repository.list_companies()
    if include_archived:
        return companies
    return [c for c in companies if c.archived_at is None]


def archive_company(company_id: str) -> Company:
    """Soft-delete (Priority 5): hides the company from the default list
    while keeping every relationship (research, opportunities, reports,
    playbooks, briefs, drafts) intact and restorable via restore_company.
    This is now the primary "remove a company" action; permanent deletion
    (remove_company below) is a last resort only available afterward.
    """
    company = get_company(company_id)
    if company.archived_at is None:
        company.archived_at = datetime.utcnow()
    return company_repository.update_company(company)


def restore_company(company_id: str) -> Company:
    company = get_company(company_id)
    company.archived_at = None
    return company_repository.update_company(company)


def remove_company(company_id: str) -> None:
    """Permanent deletion - a last resort, only allowed once a company has
    already been archived (Priority 5: "Delete should become a last-resort
    operation"). Archiving is the recoverable path everyone should use;
    this exists for cases where a record genuinely needs to be gone.
    """
    company = get_company(company_id)  # raises ValueError if not found
    if company.archived_at is None:
        raise ValueError(
            f"Company {company_id} must be archived before it can be permanently deleted."
        )
    try:
        company_repository.delete_company(company_id)
    except (sqlite3.IntegrityError, SqlAlchemyIntegrityError) as exc:
        # Blocked by a foreign key - the company has real historical data
        # (research sessions, opportunities, reports) referencing it.
        # Removing it would orphan or silently lose that history, which
        # Data Integrity rules explicitly forbid, so this must surface as
        # a clear, meaningful error rather than a raw 500.
        raise ValueError(
            f"Company {company_id} cannot be permanently deleted: it has associated "
            "research history that must be preserved."
        ) from exc


def enable_monitoring(company_id: str) -> Company:
    company = get_company(company_id)
    company.monitoring_status = "enabled"
    return company_repository.update_company(company)


def disable_monitoring(company_id: str) -> Company:
    company = get_company(company_id)
    company.monitoring_status = "disabled"
    return company_repository.update_company(company)
