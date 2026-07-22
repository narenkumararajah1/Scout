"""V3 Report assembly (V3 Phase 6 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 13, docs/v3/09_DATA_MODELS.md's Report entity).

Pure assembly - no new AI generation happens here. Every section is
read from data already produced and persisted by an earlier
service/phase: Company Intelligence, Technology Analysis, Executive
Intelligence (Phase 5), Opportunity Analysis, Capability Alignment (V2,
read-only), and this phase's own Sales Playbook, Meeting Brief, and
Outreach Drafts. If a given section doesn't exist yet for this company
(e.g. no Sales Playbook has been generated), it's simply empty in the
assembled report - this service never triggers generation of missing
pieces itself.

Named v3_report_service.py (not report_service.py) - that name is
already taken by V2's live backend/services/report_service.py
(Phase 9's SQLite Report read-access, used today by
backend/routers/reports.py), which this phase does not touch. Matches
the v3_reports table name already used in
backend/database/models/report.py.

Not called by any existing agent, service, or router - see TECH_DEBT.md.
"""

from __future__ import annotations

import uuid
from typing import Optional

from backend.database.models import Report
from backend.models.company import Company
from backend.repositories.capability_match_repository import list_capability_matches
from backend.repositories.opportunity_repository import list_opportunities
from backend.repositories.postgres.meeting_brief_repository import list_meeting_briefs_for_company
from backend.repositories.postgres.outreach_draft_repository import list_outreach_drafts_for_company
from backend.repositories.postgres.report_repository import create_v3_report
from backend.repositories.postgres.sales_playbook_repository import list_sales_playbooks_for_company
from backend.services.company_intelligence_service import build_company_intelligence_profile


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

    # Deterministic, no LLM call - assembly only. Prefers the most
    # recent Sales Playbook's strategy summary if one exists.
    executive_summary = (
        sales_playbooks[0].strategy_summary
        if sales_playbooks and sales_playbooks[0].strategy_summary
        else f"Intelligence report for {company.name}."
    )

    report = Report(
        id=str(uuid.uuid4()),
        company_id=company.id,
        title=title or f"{company.name} Intelligence Report",
        executive_summary=executive_summary,
        content=content,
    )
    return await create_v3_report(report)
