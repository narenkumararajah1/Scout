"""Analytics (V2 Phase 9).

Covers FR-017's "Analytics: Opportunity trends" and PROJECT_CONTEXT.md's
"Company trends. Opportunity rankings. Historical intelligence." Pure
aggregation over data already produced by earlier phases (Research,
Capability Matching, Opportunity Analysis, Reporting) - no new AI agent,
no new persisted entity. Forecasting, heat maps, and other predictive
analytics are FEATURE_BACKLOG.md's "Predictive Opportunity Intelligence"
and "Analytics & Executive Dashboards" future-version items and are out
of scope here.
"""

from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.repositories.opportunity_repository import list_all_opportunities, list_opportunities
from backend.repositories.report_repository import list_reports
from backend.repositories.research_repository import list_research_sessions


def opportunity_rankings(limit: int = 20) -> list[Opportunity]:
    """Highest-priority opportunities across every company, most relevant first."""
    return list_all_opportunities(limit=limit)


def company_trends(company: Company) -> dict:
    """Historical intelligence summary for one company: research cadence,
    opportunity volume/confidence, and report history.

    Returned as raw data rather than pre-formatted text - rendering
    belongs in the dashboard, not the service (Dashboard Rules).
    """
    sessions = list_research_sessions(company.id)
    opportunities = list_opportunities(company.id)
    reports = list_reports(company.id)

    scored = [o for o in opportunities if o.confidence_score is not None]
    average_confidence = sum(o.confidence_score for o in scored) / len(scored) if scored else None

    return {
        "company_id": company.id,
        "company_name": company.name,
        "research_session_count": len(sessions),
        "opportunity_count": len(opportunities),
        "report_count": len(reports),
        "average_opportunity_confidence": average_confidence,
        "top_opportunities": sorted(
            opportunities, key=lambda o: (o.priority or 0, o.confidence_score or 0), reverse=True
        )[:5],
        "research_sessions": sessions,
        "reports": reports,
    }
