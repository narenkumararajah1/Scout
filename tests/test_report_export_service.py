"""Unit tests for backend/services/report_export_service.py (V3 Phase 6).

Unconditional - no Postgres or LLM needed, since export_report_to_pdf()
operates on a plain in-memory Report object. Confirms the same seeded
data produces identical rendered text content when exported twice.
"""

import time

from backend.database.models import Report
from backend.services.report_export_service import export_report_to_pdf


def _seeded_report() -> Report:
    return Report(
        id="export-test-1",
        company_id="export-test-company",
        title="Acme Corp Intelligence Report",
        report_type="full_intelligence",
        version=1,
        status="Generated",
        executive_summary="Acme is investing in cloud infrastructure.",
        content={
            "company_intelligence": {
                "industry": "Cloud Infrastructure",
                "headquarters": "San Jose, CA",
                "business_initiatives": ["AI-ready data infrastructure"],
            },
            "technology_landscape": [{"name": "Kubernetes", "business_relevance": "Core to their strategy."}],
            "opportunity_analysis": [{"title": "Cloud Migration", "priority": 1, "confidence_score": 0.8}],
            "capability_alignment": [
                {"capability_name": "Cloud-Native Platform Engineering", "confidence": 0.85, "reasoning": "Aligned."}
            ],
            "executive_intelligence": [{"name": "Jane Doe", "title": "CTO", "biography": "Cloud veteran."}],
            "sales_playbooks": [{"strategy_summary": "Lead with platform engineering."}],
            "meeting_briefs": [{"meeting_title": "Kickoff meeting"}],
            "outreach_drafts": [{"type": "Email", "status": "Draft", "subject": "Following up"}],
        },
    )


def test_export_report_to_pdf_produces_a_valid_pdf():
    pdf_bytes = export_report_to_pdf(_seeded_report())

    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 0


def test_export_report_to_pdf_never_touches_the_llm_gateway():
    import backend.services.report_export_service as module

    assert "generate_completion" not in dir(module)
    assert "llm_gateway" not in [name for name in dir(module) if "llm" in name.lower()]


def test_exporting_the_same_report_twice_is_deterministic():
    """backend/services/report_export_service.py renders with ReportLab's
    own invariant=1 mode, which fixes /CreationDate and the /ID trailer -
    the only two fields that would otherwise vary between two renders of
    identical content. Sleeping across a wall-clock second boundary here
    proves it's actually invariant=1 doing the work, not coincidence.
    """
    report = _seeded_report()

    first_pass = export_report_to_pdf(report)
    time.sleep(1.1)
    second_pass = export_report_to_pdf(report)

    assert first_pass == second_pass
