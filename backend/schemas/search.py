"""Response schema for GET /api/v1/search (Priority 3 - Global Search).

Reuses backend/schemas/company_intelligence.py's CompanyOut and
ExecutiveOut as-is rather than duplicating them - a search result row
for a company or executive is the same shape as everywhere else those
entities are already returned. Opportunity has no existing response
schema anywhere in the codebase yet, so OpportunitySearchResultOut is
defined here, scoped to only what a search result row needs.
"""

from typing import List, Optional

from pydantic import BaseModel

from backend.schemas.company_intelligence import CompanyOut, ExecutiveOut


class ExecutiveSearchResultOut(ExecutiveOut):
    company_id: str
    company_name: Optional[str] = None


class OpportunitySearchResultOut(BaseModel):
    id: str
    company_id: str
    company_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: Optional[int] = None
    confidence_score: Optional[float] = None

    model_config = {"from_attributes": True}


class SearchResultsOut(BaseModel):
    companies: List[CompanyOut] = []
    executives: List[ExecutiveSearchResultOut] = []
    opportunities: List[OpportunitySearchResultOut] = []
