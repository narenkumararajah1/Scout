"""Executive Reporting (V2 Phase 8).

Assembles Phase 4's Signals, Phase 6's Capability Matches, and Phase 7's
(ranked) Opportunities for one Research Session into the eight-section
executive Report defined in DATA_MODEL.md, and persists it via Phase 2's
Report repository - which already exists and needed no changes for this
phase.

Implemented as a service, matching every prior V2 intelligence-pipeline
phase (research_service.py, capability_matching_service.py,
opportunity_analysis_service.py): nothing exists yet to sequence this
with in ADK, and the service layer is this codebase's established home
for new business logic.

Report generation only - actual distribution (email/Teams) is Phase 10's
job; ROADMAP.md explicitly separates "Reporting" from "Distribution."
"""

import logging

from backend.llm_client import generate_completion, parse_json_object
from backend.models.company import Company
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.prompts.reporting_prompts import build_report_prompt
from backend.repositories.capability_match_repository import list_capability_matches_for_session
from backend.repositories.opportunity_repository import list_opportunities_for_session
from backend.repositories.report_repository import create_report
from backend.repositories.research_repository import list_signals_for_session

logger = logging.getLogger(__name__)


def _coerce_to_text(value):
    """Normalizes a report section to a single string.

    The prompt's example shows every field as a plain string (e.g.
    "talking_points": "..."), and Claude always complies - but Gemini has
    been observed returning "point-like" fields (talking_points,
    recommendations) as a JSON array of strings instead, which fails
    Report's str-typed fields with a Pydantic ValidationError. Rather
    than fixing this per-provider in the prompt (no wording guarantees
    every model interprets it identically), normalize defensively at the
    boundary where the parsed LLM response becomes a typed Report.
    """
    if isinstance(value, list):
        if len(value) == 1:
            return str(value[0])
        return "\n".join(f"{index}. {item}" for index, item in enumerate(value, start=1))
    return value


REQUIRED_REPORT_FIELDS = (
    "executive_summary",
    "company_overview",
    "key_findings",
    "technology_analysis",
    "capability_alignment",
    "opportunities_section",
    "recommendations",
    "talking_points",
)


def generate_report(company: Company, research_session: ResearchSession) -> Report:
    opportunities = list_opportunities_for_session(research_session.id)
    if not opportunities:
        raise ValueError(
            "Reporting Service requires opportunities from the Opportunity Analysis "
            "Service; none are available for this research session."
        )

    signals = list_signals_for_session(research_session.id)
    matches = list_capability_matches_for_session(research_session.id)

    signal_payload = [
        {"type": signal.type, "title": signal.title, "description": signal.description}
        for signal in signals
    ]
    match_payload = [
        {"capability_name": match.capability_name, "confidence": match.confidence, "reasoning": match.reasoning}
        for match in matches
    ]
    opportunity_payload = [
        {
            "title": opportunity.title,
            "description": opportunity.description,
            "priority": opportunity.priority,
            "confidence_score": opportunity.confidence_score,
            "recommended_services": opportunity.recommended_services,
        }
        for opportunity in opportunities
    ]

    raw_report = parse_json_object(
        generate_completion(
            build_report_prompt(
                company.name,
                research_session.research_summary or "",
                signal_payload,
                match_payload,
                opportunity_payload,
            )
        ),
        caller_name="Reporting Service",
    )

    missing_fields = [field for field in REQUIRED_REPORT_FIELDS if field not in raw_report]
    if missing_fields:
        raise ValueError(
            f"Reporting Service's response was missing required field(s): {', '.join(missing_fields)}"
        )

    report = create_report(
        Report(
            company_id=company.id,
            research_session_id=research_session.id,
            executive_summary=_coerce_to_text(raw_report["executive_summary"]),
            company_overview=_coerce_to_text(raw_report["company_overview"]),
            key_findings=_coerce_to_text(raw_report["key_findings"]),
            technology_analysis=_coerce_to_text(raw_report["technology_analysis"]),
            capability_alignment=_coerce_to_text(raw_report["capability_alignment"]),
            opportunities_section=_coerce_to_text(raw_report["opportunities_section"]),
            recommendations=_coerce_to_text(raw_report["recommendations"]),
            talking_points=_coerce_to_text(raw_report["talking_points"]),
        )
    )
    logger.info("Report created for company %s (%s): report %s.", company.name, company.id, report.id)
    return report
