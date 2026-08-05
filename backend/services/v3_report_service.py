"""V3 Report assembly (V3 Phase 6 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 13, docs/v3/09_DATA_MODELS.md's Report entity).

Assembly **plus one synthesis pass**. Every section is read from data
already produced and persisted by an earlier service/phase: Company
Intelligence, Technology Analysis, Executive Intelligence (Phase 5),
Opportunity Analysis, Capability Alignment (V2, read-only), and this
phase's own Sales Playbook, Meeting Brief, and Outreach Drafts. If a
given section doesn't exist yet for this company (e.g. no Sales Playbook
has been generated), it's simply empty in the assembled report - this
service never triggers generation of missing pieces itself.

This was originally pure assembly, which made a "report" a reformatting
of data the reader could already see on other pages, under a summary
that was either copied off a Sales Playbook or the literal sentence
"Intelligence report for <company>." _synthesise() now reads across the
assembled sections once and writes the narrative - see
backend/ai/prompts/report_synthesis_prompts.py.

The distinction that matters: synthesis reads **only** what is already
stored. Generating a report never re-runs research or analysis, so it
stays cheap, does not change the underlying facts, and cannot disagree
with the company page it was generated from.

Named v3_report_service.py (not report_service.py) - that name is
already taken by V2's live backend/services/report_service.py
(Phase 9's SQLite Report read-access, used today by
backend/routers/reports.py), which this phase does not touch. Matches
the v3_reports table name already used in
backend/database/models/report.py.

Not called by any existing agent, service, or router - see TECH_DEBT.md.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from backend.ai.llm_gateway import generate_completion, parse_json_object
from backend.ai.prompts.report_synthesis_prompts import build_report_synthesis_prompt
from backend.database.models import Report
from backend.models.company import Company
from backend.models.report import Report as V2Report
from backend.repositories.capability_match_repository import list_capability_matches
from backend.repositories.opportunity_repository import list_opportunities
from backend.repositories.postgres.meeting_brief_repository import list_meeting_briefs_for_company
from backend.repositories.postgres.outreach_draft_repository import list_outreach_drafts_for_company
from backend.repositories.postgres.report_repository import create_v3_report
from backend.repositories.postgres.sales_playbook_repository import list_sales_playbooks_for_company
from backend.services.company_intelligence_service import build_company_intelligence_profile


logger = logging.getLogger(__name__)


def _serialize_technologies(technologies: list) -> list:
    return [
        {
            "name": t.name,
            "category": t.category,
            "adoption_status": t.adoption_status,
            "business_relevance": t.business_relevance,
        }
        for t in technologies
    ]


def _serialize_executives(executives: list) -> list:
    return [
        {"name": e.name, "title": e.title, "biography": e.biography, "business_priorities": e.business_priorities}
        for e in executives
    ]


def _serialize_opportunities(opportunities: list) -> list:
    return [
        {
            "title": o.title,
            "description": o.description,
            "priority": o.priority,
            "confidence_score": o.confidence_score,
            "recommended_services": o.recommended_services,
        }
        for o in opportunities
    ]


def _serialize_capability_matches(matches: list) -> list:
    return [
        {"capability_name": m.capability_name, "confidence": m.confidence, "reasoning": m.reasoning}
        for m in matches
    ]


def _serialize_sales_playbooks(playbooks: list) -> list:
    return [
        {
            "strategy_summary": p.strategy_summary,
            "talking_points": p.talking_points,
            "recommended_services": p.recommended_services,
            "next_steps": p.next_steps,
            "risks": p.risks,
        }
        for p in playbooks
    ]


def _serialize_meeting_briefs(briefs: list) -> list:
    return [
        {
            "meeting_title": b.meeting_title,
            "meeting_objectives": b.meeting_objectives,
            "talking_points": b.talking_points,
        }
        for b in briefs
    ]


def _serialize_outreach_drafts(drafts: list) -> list:
    return [{"type": d.type, "subject": d.subject, "status": d.status} for d in drafts]


async def build_and_persist_report(company: Company, title: Optional[str] = None) -> Report:
    profile = await build_company_intelligence_profile(company)
    opportunities = list_opportunities(company.id)
    capability_matches = list_capability_matches(company.id)
    sales_playbooks = await list_sales_playbooks_for_company(company.id)
    meeting_briefs = await list_meeting_briefs_for_company(company.id)
    outreach_drafts = await list_outreach_drafts_for_company(company.id)

    content = {
        "company_intelligence": {
            "name": profile.company.name,
            "industry": profile.company.industry,
            "headquarters": profile.company.headquarters,
            "business_initiatives": [bi.name for bi in profile.business_initiatives],
        },
        "technology_landscape": _serialize_technologies(profile.technologies),
        "opportunity_analysis": _serialize_opportunities(opportunities),
        "capability_alignment": _serialize_capability_matches(capability_matches),
        "executive_intelligence": _serialize_executives(profile.executives),
        "sales_playbooks": _serialize_sales_playbooks(sales_playbooks),
        "meeting_briefs": _serialize_meeting_briefs(meeting_briefs),
        "outreach_drafts": _serialize_outreach_drafts(outreach_drafts),
    }

    # Synthesis over the assembled sections: the report reads across the
    # intelligence rather than reformatting it. This deliberately does not
    # re-run analysis - it sees only what is already stored, so generating
    # a report stays cheap and repeatable, and never silently changes the
    # underlying facts.
    synthesis = await _synthesise(company, content)
    content["synthesis"] = synthesis

    report = Report(
        id=str(uuid.uuid4()),
        company_id=company.id,
        title=title or f"{company.name} Intelligence Report",
        executive_summary=synthesis.get("executive_summary") or _fallback_summary(company, sales_playbooks),
        content=content,
    )
    return await create_v3_report(report)


def as_deliverable_report(report: Report) -> V2Report:
    """Presents an intelligence report in the shape the delivery channels
    read, so distribution_service can send it unchanged.

    The email/Teams senders were written against V2's flat Report - six
    text fields. This report keeps its sections in JSON plus a synthesis
    block. Rather than teach every sender a second shape (or copy the
    delivery logic), map one onto the other here. The result is never
    persisted; it exists only for the duration of the send.

    Prefers the synthesised narrative and falls back to rendering the
    stored sections, so a report generated while the LLM was unavailable
    is still deliverable rather than arriving empty.
    """
    content = report.content or {}
    synthesis = content.get("synthesis") or {}

    def _joined(key: str) -> Optional[str]:
        value = synthesis.get(key)
        if isinstance(value, list):
            return "\n".join(f"- {item}" for item in value) or None
        return value or None

    return V2Report(
        id=report.id,
        company_id=report.company_id,
        # V2 reports come from a research session; these do not. The field
        # is required by the model but unread by every sender, so an empty
        # string is honest here - inventing an id would imply a session
        # that does not exist.
        research_session_id="",
        executive_summary=report.executive_summary,
        key_findings=_joined("key_findings"),
        capability_alignment=_joined("capability_alignment")
        or _render_section(content.get("capability_alignment")),
        opportunities_section=_joined("opportunities_section")
        or _render_section(content.get("opportunity_analysis")),
        recommendations=_joined("recommendations"),
        talking_points=_joined("talking_points"),
        created_at=report.created_at,
    )


def _render_section(rows: Optional[list]) -> Optional[str]:
    """Plain-text rendering of an assembled section, for the fallback path
    above. Deliberately dull: this is what a reader gets when synthesis
    was unavailable, and it should read as data rather than pretend to be
    analysis.
    """
    if not rows:
        return None
    lines = []
    for row in rows:
        if isinstance(row, dict):
            label = row.get("title") or row.get("capability_name") or row.get("name") or ""
            detail = row.get("description") or row.get("reasoning") or ""
            lines.append(f"- {label}: {detail}".rstrip(": "))
        else:
            lines.append(f"- {row}")
    return "\n".join(lines)


def _fallback_summary(company: Company, sales_playbooks: list) -> str:
    """What the summary was before synthesis existed. Still reachable when
    the LLM is unavailable - see _synthesise().
    """
    if sales_playbooks and sales_playbooks[0].strategy_summary:
        return sales_playbooks[0].strategy_summary
    return f"Intelligence report for {company.name}."


async def _synthesise(company: Company, content: dict) -> dict:
    """Best-effort by design.

    A report is an assembly of data the user can already see elsewhere;
    the synthesis is the value added on top. If the model is rate limited
    or the response is not parseable, returning the assembled report
    without the narrative is strictly better than failing the request and
    leaving the user with nothing - so this logs and degrades rather than
    raising. The caller falls back to the pre-synthesis summary, and the
    UI renders only the keys that are present.
    """
    prompt = build_report_synthesis_prompt(company.name, content)
    try:
        raw = await asyncio.to_thread(generate_completion, prompt)
        return parse_json_object(raw, "v3_report_service._synthesise")
    except Exception:
        logger.exception(
            "Report synthesis failed for %s (%s); returning the assembled report without it.",
            company.name,
            company.id,
        )
        return {}
