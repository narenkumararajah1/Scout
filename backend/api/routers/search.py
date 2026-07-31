"""Global Search endpoint (Priority 3).

Searches companies, executives, and opportunities in one call so the
frontend's single search box never has to fan out to three different
endpoints. Reuses existing repositories throughout - no new
aggregation logic beyond filtering and shaping the response:

- Companies: backend/repositories/company_repository.list_companies()
  (the existing V2/V3 dispatcher - same source CompaniesPage already
  lists from), filtered in Python since the result set is small.
- Executives: backend/repositories/postgres/executive_repository's new
  search_executives(), a straightforward ILIKE query.
- Opportunities: backend/repositories/opportunity_repository
  .list_all_opportunities() (the existing dispatcher), filtered in
  Python for the same reason as companies.
"""

import asyncio

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user
from backend.database.models import User
from backend.repositories.company_repository import list_companies
from backend.repositories.opportunity_repository import list_all_opportunities
from backend.repositories.postgres.executive_repository import search_executives
from backend.schemas.search import ExecutiveSearchResultOut, OpportunitySearchResultOut, SearchResultsOut
from backend.schemas.company_intelligence import CompanyOut
from backend.utils.text import clean_search_text

router = APIRouter(prefix="/api/v1/search", tags=["search"])

_MAX_RESULTS_PER_TYPE = 5


@router.get("")
async def search(q: str = Query(default="", max_length=200), current_user: User = Depends(get_current_user)) -> dict:
    # Sanitised rather than rejected: a NUL byte here reached Postgres
    # through the executives ILIKE and returned a 500, and someone pasting
    # a fragment of a document into a search box wants results, not a
    # validation error (see backend/utils/text.py).
    query = clean_search_text(q).lower()
    if not query:
        empty = SearchResultsOut()
        return {"success": True, "message": "Search results retrieved.", "data": empty.model_dump()}

    companies = await asyncio.to_thread(list_companies)
    matched_companies = [
        c for c in companies if query in c.name.lower() or (c.industry and query in c.industry.lower())
    ][:_MAX_RESULTS_PER_TYPE]
    company_names_by_id = {c.id: c.name for c in companies}

    executives = await search_executives(query, limit=_MAX_RESULTS_PER_TYPE)

    all_opportunities = await asyncio.to_thread(list_all_opportunities)
    matched_opportunities = [o for o in all_opportunities if query in o.title.lower()][:_MAX_RESULTS_PER_TYPE]

    data = SearchResultsOut(
        companies=[CompanyOut.model_validate(c, from_attributes=True) for c in matched_companies],
        executives=[
            ExecutiveSearchResultOut.model_validate(e, from_attributes=True).model_copy(
                update={"company_name": company_names_by_id.get(e.company_id)}
            )
            for e in executives
        ],
        opportunities=[
            OpportunitySearchResultOut(
                id=o.id,
                company_id=o.company_id,
                company_name=company_names_by_id.get(o.company_id),
                title=o.title,
                description=o.description,
                priority=o.priority,
                confidence_score=o.confidence_score,
            )
            for o in matched_opportunities
        ],
    )
    return {"success": True, "message": "Search results retrieved.", "data": data.model_dump()}
