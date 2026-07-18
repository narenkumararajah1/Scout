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
from typing import Optional

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


def list_companies() -> list[Company]:
    return company_repository.list_companies()


def remove_company(company_id: str) -> None:
    get_company(company_id)  # raises ValueError if not found
    try:
        company_repository.delete_company(company_id)
    except sqlite3.IntegrityError as exc:
        # Blocked by a foreign key - the company has real historical data
        # (research sessions, opportunities, reports) referencing it.
        # Removing it would orphan or silently lose that history, which
        # Data Integrity rules explicitly forbid, so this must surface as
        # a clear, meaningful error rather than a raw 500.
        raise ValueError(
            f"Company {company_id} cannot be removed: it has associated "
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
