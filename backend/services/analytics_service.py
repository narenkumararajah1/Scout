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
from backend.repositories.capability_match_repository import get_capability_match
from backend.repositories.opportunity_repository import list_all_opportunities, list_opportunities
from backend.repositories.report_repository import list_reports
from backend.repositories.research_repository import list_research_sessions, list_signals_for_session
from backend.services import company_service


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

    # Roadmap Phase 5 (Visual Intelligence) - "Opportunity Trends" and
    # "Timeline of Scout Intelligence" charts. Both are pure
    # re-sortings of data already fetched above - no new AI call, no
    # new query. Opportunity is immutable per analysis run (ADR-018),
    # so every past run's Opportunity rows are still here, giving a
    # real history rather than a single snapshot.
    opportunity_history = [
        {
            "date": opportunity.generated_date,
            "title": opportunity.title,
            "confidence_score": opportunity.confidence_score,
            "priority": opportunity.priority,
        }
        for opportunity in sorted(opportunities, key=lambda o: o.generated_date)
    ]
    timeline = sorted(
        [{"date": session.execution_time, "type": "research", "label": "Research session"} for session in sessions]
        + [
            {"date": opportunity.generated_date, "type": "opportunity", "label": opportunity.title}
            for opportunity in opportunities
        ]
        + [{"date": report.created_at, "type": "report", "label": "Report generated"} for report in reports],
        key=lambda event: event["date"],
    )

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
        "opportunity_history": opportunity_history,
        "timeline": timeline,
    }


def executive_dashboard(limit: int = 50) -> dict:
    """Highest-priority opportunities across every company, grouped by
    company, each with a human-readable explanation of why it scored the
    way it did (roadmap Phase 3 - Executive Intelligence Dashboard).

    Reuses CapabilityMatch.reasoning (already written by the Capability
    Matching stage - backend/orchestration/stages.py) and Signal.type
    counts (already categorized by Research) rather than making any new
    AI call - the explanation was already computed, just never surfaced
    together in one place.
    """
    opportunities = list_all_opportunities(limit=limit)
    companies_by_id = {company.id: company for company in company_service.list_companies()}

    signals_by_session: dict[str, list] = {}

    def _signals_for_session(research_session_id: str) -> list:
        if research_session_id not in signals_by_session:
            signals_by_session[research_session_id] = list_signals_for_session(research_session_id)
        return signals_by_session[research_session_id]

    by_company: dict[str, dict] = {}
    for opportunity in opportunities:
        company = companies_by_id.get(opportunity.company_id)
        if company is None:
            continue  # archived/removed since this opportunity was generated

        matches = [get_capability_match(match_id) for match_id in opportunity.capability_match_ids]
        reasoning = [match.reasoning for match in matches if match is not None]

        session_signals = _signals_for_session(opportunity.research_session_id)
        supporting_signals = [s for s in session_signals if s.id in opportunity.supporting_signal_ids]
        signal_type_counts: dict[str, int] = {}
        for signal in supporting_signals:
            signal_type_counts[signal.type] = signal_type_counts.get(signal.type, 0) + 1

        entry = by_company.setdefault(
            company.id,
            {"company_id": company.id, "company_name": company.name, "opportunities": []},
        )
        entry["opportunities"].append(
            {
                "id": opportunity.id,
                "title": opportunity.title,
                "priority": opportunity.priority,
                "confidence_score": opportunity.confidence_score,
                "recommended_services": opportunity.recommended_services,
                "reasoning": reasoning,
                "signal_type_counts": signal_type_counts,
            }
        )

    dashboard = sorted(by_company.values(), key=lambda entry: len(entry["opportunities"]), reverse=True)
    for entry in dashboard:
        entry["opportunities"].sort(
            key=lambda o: (o["priority"] or 0, o["confidence_score"] or 0), reverse=True
        )

    return {"companies": dashboard}
