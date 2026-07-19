import json
from unittest.mock import patch

import pytest

from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company
from backend.models.opportunity import Opportunity
from backend.models.research import SIGNAL_TYPE_HIRING, ResearchSession, Signal
from backend.repositories.capability_match_repository import create_capability_match
from backend.repositories.company_repository import create_company
from backend.repositories.opportunity_repository import create_opportunity
from backend.repositories.report_repository import list_reports
from backend.repositories.research_repository import create_research_session, create_signal
from backend.services import reporting_service
from tests.conftest import clear_v2_tables

FAKE_REPORT_RESPONSE = json.dumps(
    {
        "executive_summary": "Strong opportunity for AI/data platform advisory.",
        "company_overview": "Acme Corp is a mid-size data infrastructure company.",
        "key_findings": "Actively hiring ML engineers.",
        "technology_analysis": "Investing in Kubernetes and multi-cloud tooling.",
        "capability_alignment": "AI Ready Data aligns well (confidence 0.85).",
        "opportunities_section": "AI/Data Platform Advisory (priority 8).",
        "recommendations": "1. Schedule a discovery call.",
        "talking_points": "They are actively hiring ML engineers.",
    }
)


def _make_company_and_session():
    company = create_company(Company(name="Acme Corp"))
    session = create_research_session(
        ResearchSession(company_id=company.id, status="completed", research_summary="Acme is hiring ML engineers.")
    )
    return company, session


def _add_signal(session_id: str) -> Signal:
    return create_signal(
        Signal(research_session_id=session_id, type=SIGNAL_TYPE_HIRING, title="ML engineer hiring")
    )


def test_generate_report_raises_without_opportunities():
    clear_v2_tables()
    company, session = _make_company_and_session()

    with pytest.raises(ValueError, match="requires opportunities"):
        reporting_service.generate_report(company, session)


def test_generate_report_creates_and_persists_report():
    clear_v2_tables()
    company, session = _make_company_and_session()
    signal = _add_signal(session.id)
    match = create_capability_match(
        CapabilityMatch(
            company_id=company.id,
            research_session_id=session.id,
            capability_id="capability:cap-1",
            capability_name="AI Ready Data",
            signal_ids=[signal.id],
            confidence=0.85,
            reasoning="ML hiring aligns with AI Ready Data.",
        )
    )
    create_opportunity(
        Opportunity(
            company_id=company.id,
            research_session_id=session.id,
            title="AI/Data Platform Advisory",
            priority=8,
            confidence_score=0.85,
            capability_match_ids=[match.id],
        )
    )

    with patch(
        "backend.services.reporting_service.generate_completion", return_value=FAKE_REPORT_RESPONSE
    ) as mock_completion:
        report = reporting_service.generate_report(company, session)

    assert mock_completion.call_count == 1
    assert report.company_id == company.id
    assert report.research_session_id == session.id
    assert report.executive_summary == "Strong opportunity for AI/data platform advisory."
    assert report.company_overview == "Acme Corp is a mid-size data infrastructure company."
    assert report.key_findings == "Actively hiring ML engineers."
    assert report.technology_analysis == "Investing in Kubernetes and multi-cloud tooling."
    assert report.capability_alignment == "AI Ready Data aligns well (confidence 0.85)."
    assert report.opportunities_section == "AI/Data Platform Advisory (priority 8)."
    assert report.recommendations == "1. Schedule a discovery call."
    assert report.talking_points == "They are actively hiring ML engineers."

    persisted = list_reports(company.id)
    assert len(persisted) == 1
    assert persisted[0].id == report.id


def test_generate_report_raises_clear_error_on_missing_required_fields():
    clear_v2_tables()
    company, session = _make_company_and_session()
    create_opportunity(
        Opportunity(company_id=company.id, research_session_id=session.id, title="Some Opportunity", priority=5)
    )

    incomplete_response = json.dumps({"executive_summary": "Only this field is present."})

    with patch(
        "backend.services.reporting_service.generate_completion", return_value=incomplete_response
    ):
        with pytest.raises(ValueError, match="missing required field"):
            reporting_service.generate_report(company, session)


def test_generate_report_prompt_includes_company_signals_and_opportunities():
    clear_v2_tables()
    company, session = _make_company_and_session()
    _add_signal(session.id)
    create_opportunity(
        Opportunity(company_id=company.id, research_session_id=session.id, title="AI Advisory", priority=8)
    )

    with patch(
        "backend.services.reporting_service.generate_completion", return_value=FAKE_REPORT_RESPONSE
    ) as mock_completion:
        reporting_service.generate_report(company, session)

    prompt = mock_completion.call_args_list[0][0][0]
    assert company.name in prompt
    assert "ML engineer hiring" in prompt
    assert "AI Advisory" in prompt
