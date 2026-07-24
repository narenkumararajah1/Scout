"""Synchronous facade over PostgreSQL for Company and Opportunity
(V3 Phase 3B).

Deliberately NOT built on backend/repositories/postgres/company_repository.py
or opportunity_repository.py's async functions (Stage 3A) - the point of
"sync facade, no full async refactor" (approved for Stage 3B) is a true
synchronous call path compatible with V2's existing synchronous
repository interface, not a sync-wrapped-async bridge running under
uvicorn's already-active event loop (fragile, can deadlock). This uses a
dedicated sync engine (backend/database/postgres_sync.py) against the
exact same ORM models Stage 3A already defined
(backend/database/models/) - those classes are just table mappings, not
tied to sync or async execution.

Converts between the ORM entities and V2's domain dataclasses
(backend/models/) so both implementations of
CompanyRepositoryInterface/OpportunityRepositoryInterface speak the same
type regardless of backing store - see backend/repositories/interfaces.py.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from backend.database.models import Company as OrmCompany
from backend.database.models import Opportunity as OrmOpportunity
from backend.database.postgres_sync import get_sync_session
from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.repositories.interfaces import CompanyRepositoryInterface, OpportunityRepositoryInterface


def _as_utc(value: datetime) -> datetime:
    # V2's domain dataclasses store naive datetimes (datetime.utcnow()),
    # which are already UTC wall-clock values but don't say so. Handing
    # a naive datetime to a TIMESTAMPTZ column lets the driver/session
    # interpret it in the *session's local timezone* instead of UTC -
    # silently shifting the stored value by whatever that offset is.
    # Tagging it explicitly as UTC before the write removes the ambiguity.
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _orm_to_company(row: OrmCompany) -> Company:
    return Company(
        id=row.id,
        name=row.name,
        industry=row.industry,
        headquarters=row.headquarters,
        website=row.website,
        monitoring_status=row.status,
        archived_at=row.archived_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _orm_to_opportunity(row: OrmOpportunity) -> Opportunity:
    return Opportunity(
        id=row.id,
        company_id=row.company_id,
        research_session_id=row.research_session_id or "",
        title=row.title,
        description=row.description,
        priority=row.priority,
        confidence_score=row.confidence_score,
        supporting_signal_ids=row.supporting_signal_ids or [],
        capability_match_ids=row.capability_match_ids or [],
        recommended_services=row.recommended_services or [],
        recommended_case_studies=row.recommended_case_studies or [],
        generated_date=row.created_at,
    )


class PostgresCompanyRepository(CompanyRepositoryInterface):
    def create_company(self, company: Company) -> Company:
        with get_sync_session() as session:
            orm_company = OrmCompany(
                id=company.id,
                name=company.name,
                industry=company.industry,
                headquarters=company.headquarters,
                website=company.website,
                status=company.monitoring_status,
                archived_at=_as_utc(company.archived_at) if company.archived_at else None,
                created_at=_as_utc(company.created_at),
                updated_at=_as_utc(company.updated_at),
            )
            session.add(orm_company)
            session.commit()
            session.refresh(orm_company)
            return _orm_to_company(orm_company)

    def get_company(self, company_id: str) -> Optional[Company]:
        with get_sync_session() as session:
            row = session.get(OrmCompany, company_id)
            return _orm_to_company(row) if row else None

    def list_companies(self) -> list[Company]:
        with get_sync_session() as session:
            rows = session.execute(select(OrmCompany).order_by(OrmCompany.created_at.desc())).scalars().all()
            return [_orm_to_company(row) for row in rows]

    def update_company(self, company: Company) -> Company:
        company.updated_at = datetime.utcnow()
        with get_sync_session() as session:
            orm_company = session.get(OrmCompany, company.id)
            if orm_company is None:
                raise ValueError(f"Company {company.id} not found in PostgreSQL")
            orm_company.name = company.name
            orm_company.industry = company.industry
            orm_company.headquarters = company.headquarters
            orm_company.website = company.website
            orm_company.status = company.monitoring_status
            orm_company.archived_at = _as_utc(company.archived_at) if company.archived_at else None
            orm_company.updated_at = _as_utc(company.updated_at)
            session.commit()
            session.refresh(orm_company)
            return _orm_to_company(orm_company)

    def delete_company(self, company_id: str) -> None:
        with get_sync_session() as session:
            orm_company = session.get(OrmCompany, company_id)
            if orm_company is not None:
                session.delete(orm_company)
                session.commit()


class PostgresOpportunityRepository(OpportunityRepositoryInterface):
    def create_opportunity(self, opportunity: Opportunity) -> Opportunity:
        with get_sync_session() as session:
            orm_opportunity = OrmOpportunity(
                id=opportunity.id,
                company_id=opportunity.company_id,
                research_session_id=opportunity.research_session_id,
                title=opportunity.title,
                description=opportunity.description,
                priority=opportunity.priority,
                confidence_score=opportunity.confidence_score,
                supporting_signal_ids=opportunity.supporting_signal_ids,
                capability_match_ids=opportunity.capability_match_ids,
                recommended_services=opportunity.recommended_services,
                recommended_case_studies=opportunity.recommended_case_studies,
                created_at=_as_utc(opportunity.generated_date),
            )
            session.add(orm_opportunity)
            session.commit()
            session.refresh(orm_opportunity)
            return _orm_to_opportunity(orm_opportunity)

    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        with get_sync_session() as session:
            row = session.get(OrmOpportunity, opportunity_id)
            return _orm_to_opportunity(row) if row else None

    def list_opportunities(self, company_id: str) -> list[Opportunity]:
        with get_sync_session() as session:
            rows = (
                session.execute(
                    select(OrmOpportunity)
                    .where(OrmOpportunity.company_id == company_id)
                    .order_by(OrmOpportunity.created_at.desc())
                )
                .scalars()
                .all()
            )
            return [_orm_to_opportunity(row) for row in rows]

    def list_all_opportunities(self, limit: Optional[int] = None) -> list[Opportunity]:
        with get_sync_session() as session:
            query = select(OrmOpportunity).order_by(
                OrmOpportunity.priority.desc(), OrmOpportunity.confidence_score.desc()
            )
            if limit is not None:
                query = query.limit(limit)
            rows = session.execute(query).scalars().all()
            return [_orm_to_opportunity(row) for row in rows]

    def list_opportunities_for_session(self, research_session_id: str) -> list[Opportunity]:
        with get_sync_session() as session:
            rows = (
                session.execute(
                    select(OrmOpportunity)
                    .where(OrmOpportunity.research_session_id == research_session_id)
                    .order_by(OrmOpportunity.priority.desc())
                )
                .scalars()
                .all()
            )
            return [_orm_to_opportunity(row) for row in rows]
