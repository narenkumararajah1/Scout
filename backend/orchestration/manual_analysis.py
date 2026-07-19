"""Manual Company Analysis orchestration (V2 Phase 9, FR-003).

Coordinates one on-demand run of the V2 intelligence pipeline for a
single company - Research (Phase 4) -> Capability Matching (Phase 6) ->
Opportunity Analysis (Phase 7) -> Reporting (Phase 8) - and returns the
resulting Report. Knowledge retrieval (Phase 5) happens inside Capability
Matching via semantic search, matching how that service already works;
there is no separate Knowledge stage to call here.

This is the Workflow Layer (ARCHITECTURE.md): it sequences execution but
performs no business analysis itself. It does not use Google ADK, unlike
V1's orchestration (backend/orchestration/workflow.py) - none of the V2
services are ADK agents (see each service's module docstring), so there
is nothing for the ADK Runner to orchestrate here. A thin async function
that calls the four services in order fulfills the same "Workflow
Manager coordinates execution" role for this pipeline.

ADR-012: manual analysis reuses the exact same service functions
scheduled monitoring would use, so both paths stay behaviorally
identical. ADR-020: manual analysis always persists - see that decision
for why no non-persisting/preview mode exists.
"""

import asyncio
import logging

from backend.models.company import Company
from backend.models.report import Report
from backend.services.capability_matching_service import match_capabilities
from backend.services.opportunity_analysis_service import analyze_opportunities
from backend.services.reporting_service import generate_report
from backend.services.research_service import research_company

logger = logging.getLogger(__name__)


async def run_manual_analysis(company: Company) -> Report:
    """Runs Research -> Capability Matching -> Opportunity Analysis ->
    Reporting for one company and returns the persisted Report.

    Each stage is blocking, network-bound work (Claude calls via
    litellm.completion); offloaded to a worker thread per ADR-017 so this
    coroutine doesn't block the FastAPI event loop for the run's
    duration. Any stage raising (e.g. Reporting Service's ValueError when
    no opportunities were generated) propagates to the caller - a single
    manual analysis request failing outright is the correct behavior
    here, unlike scheduled monitoring's per-company fault isolation.
    """
    logger.info("Manual analysis starting for company %s (%s).", company.name, company.id)

    session = await asyncio.to_thread(research_company, company)
    await asyncio.to_thread(match_capabilities, company, session)
    await asyncio.to_thread(analyze_opportunities, company, session)
    report = await asyncio.to_thread(generate_report, company, session)

    logger.info("Manual analysis completed for company %s (%s).", company.name, company.id)
    return report
