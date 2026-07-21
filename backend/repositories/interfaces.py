"""Repository contracts for Company and Opportunity (V3 Phase 3B).

Both backend/repositories/sqlite/ and backend/repositories/postgres/sync_facade.py
implement these interfaces, so backend/repositories/company_repository.py
and opportunity_repository.py (the public API every caller already
imports from) can dispatch between them by migration mode alone - see
backend/migration_mode.py and TECH_DEBT.md.

Both implementations speak the same "business" type - backend/models/'s
plain domain dataclasses - regardless of backing store, so a caller (or
a reconciliation comparison) never needs to know which store answered.

OpportunityRepositoryInterface deliberately has no update/delete: V2's
existing opportunity_repository.py is create+read only (opportunities are
generated fresh each research cycle, never mutated in place - see its
docstring), and this interface mirrors that real contract exactly rather
than inventing operations neither implementation is asked to support.
"""

from abc import ABC, abstractmethod
from typing import Optional

from backend.models.company import Company
from backend.models.opportunity import Opportunity


class CompanyRepositoryInterface(ABC):
    @abstractmethod
    def create_company(self, company: Company) -> Company:
        ...

    @abstractmethod
    def get_company(self, company_id: str) -> Optional[Company]:
        ...

    @abstractmethod
    def list_companies(self) -> list[Company]:
        ...

    @abstractmethod
    def update_company(self, company: Company) -> Company:
        ...

    @abstractmethod
    def delete_company(self, company_id: str) -> None:
        ...


class OpportunityRepositoryInterface(ABC):
    @abstractmethod
    def create_opportunity(self, opportunity: Opportunity) -> Opportunity:
        ...

    @abstractmethod
    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        ...

    @abstractmethod
    def list_opportunities(self, company_id: str) -> list[Opportunity]:
        ...

    @abstractmethod
    def list_all_opportunities(self, limit: Optional[int] = None) -> list[Opportunity]:
        ...

    @abstractmethod
    def list_opportunities_for_session(self, research_session_id: str) -> list[Opportunity]:
        ...
