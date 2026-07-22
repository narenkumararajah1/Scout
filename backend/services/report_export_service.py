"""PDF export for the V3 Report (V3 Phase 6 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 13).

Renders only persisted data (a backend.database.models.Report row) via
ReportLab - never invokes the LLM Gateway or any AI service. Given the
same Report row, exporting it twice produces identical rendered text
content; ReportLab's PDF byte stream itself may still differ between
calls (e.g. an embedded creation-date in the PDF's own binary metadata),
which is the "optional metadata such as timestamps" exception this
phase's requirements explicitly allow for.
"""

from __future__ import annotations

import io

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from backend.database.models import Report

_styles = getSampleStyleSheet()


def _section(story: list, heading: str, lines: list) -> None:
    if not lines:
        return
    story.append(Paragraph(heading, _styles["Heading2"]))
    for line in lines:
        story.append(Paragraph(line, _styles["Normal"]))
    story.append(Spacer(1, 8))


def export_report_to_pdf(report: Report) -> bytes:
    buffer = io.BytesIO()
    # invariant=1 is ReportLab's own built-in reproducible-output mode:
    # it fixes the /CreationDate and /ID trailer fields that would
    # otherwise vary between two renders of identical content, rather
    # than leaving that to be worked around after the fact.
    doc = SimpleDocTemplate(buffer, pagesize=letter, invariant=1)
    content = report.content or {}
    story = []

    story.append(Paragraph(report.title or "Intelligence Report", _styles["Title"]))
    story.append(Paragraph(f"Report Type: {report.report_type} | Version: {report.version} | Status: {report.status}", _styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Executive Summary", _styles["Heading2"]))
    story.append(Paragraph(report.executive_summary or "Not available.", _styles["Normal"]))
    story.append(Spacer(1, 8))

    company_intelligence = content.get("company_intelligence") or {}
    if company_intelligence:
        lines = [
            f"Industry: {company_intelligence.get('industry') or 'Unknown'}",
            f"Headquarters: {company_intelligence.get('headquarters') or 'Unknown'}",
        ]
        lines.extend(f"Initiative: {name}" for name in company_intelligence.get("business_initiatives", []))
        _section(story, "Company Intelligence", lines)

    _section(
        story,
        "Technology Landscape",
        [
            f"{tech.get('name')}: {tech.get('business_relevance') or 'No analysis yet.'}"
            for tech in content.get("technology_landscape", [])
        ],
    )

    _section(
        story,
        "Opportunity Analysis",
        [
            f"{opp.get('title')} (priority {opp.get('priority')}, confidence {opp.get('confidence_score')})"
            for opp in content.get("opportunity_analysis", [])
        ],
    )

    _section(
        story,
        "Capability Alignment",
        [
            f"{match.get('capability_name')} (confidence {match.get('confidence')}): {match.get('reasoning')}"
            for match in content.get("capability_alignment", [])
        ],
    )

    _section(
        story,
        "Executive Intelligence",
        [
            f"{exec_.get('name')}, {exec_.get('title') or 'Unknown title'}: {exec_.get('biography') or 'No profile yet.'}"
            for exec_ in content.get("executive_intelligence", [])
        ],
    )

    _section(
        story,
        "Sales Playbooks",
        [playbook.get("strategy_summary") or "No strategy summary." for playbook in content.get("sales_playbooks", [])],
    )

    _section(
        story,
        "Meeting Briefs",
        [brief.get("meeting_title") or "Untitled meeting" for brief in content.get("meeting_briefs", [])],
    )

    _section(
        story,
        "Outreach Drafts",
        [
            f"{draft.get('type')} - {draft.get('status')}: {draft.get('subject') or '(no subject)'}"
            for draft in content.get("outreach_drafts", [])
        ],
    )

    doc.build(story)
    return buffer.getvalue()
