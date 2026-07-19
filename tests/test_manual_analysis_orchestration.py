import asyncio
from unittest.mock import patch

import pytest

from backend.models.company import Company
from backend.models.report import Report
from backend.models.research import ResearchSession
from backend.orchestration.manual_analysis import run_manual_analysis


def test_run_manual_analysis_calls_pipeline_stages_in_order():
    company = Company(name="Acme Corp")
    session = ResearchSession(company_id=company.id, status="completed")
    expected_report = Report(company_id=company.id, research_session_id=session.id)

    call_order = []

    def fake_research(c):
        call_order.append("research")
        assert c is company
        return session

    def fake_match(c, s):
        call_order.append("match")
        assert c is company and s is session
        return []

    def fake_analyze(c, s):
        call_order.append("analyze")
        assert c is company and s is session
        return []

    def fake_report(c, s):
        call_order.append("report")
        assert c is company and s is session
        return expected_report

    with patch(
        "backend.orchestration.manual_analysis.research_company", side_effect=fake_research
    ), patch(
        "backend.orchestration.manual_analysis.match_capabilities", side_effect=fake_match
    ), patch(
        "backend.orchestration.manual_analysis.analyze_opportunities", side_effect=fake_analyze
    ), patch(
        "backend.orchestration.manual_analysis.generate_report", side_effect=fake_report
    ):
        result = asyncio.run(run_manual_analysis(company))

    assert call_order == ["research", "match", "analyze", "report"]
    assert result is expected_report


def test_run_manual_analysis_propagates_a_stage_failure():
    company = Company(name="Acme Corp")
    session = ResearchSession(company_id=company.id, status="completed")

    with patch(
        "backend.orchestration.manual_analysis.research_company", return_value=session
    ), patch(
        "backend.orchestration.manual_analysis.match_capabilities", return_value=[]
    ), patch(
        "backend.orchestration.manual_analysis.analyze_opportunities", return_value=[]
    ), patch(
        "backend.orchestration.manual_analysis.generate_report",
        side_effect=ValueError("Reporting Service requires opportunities"),
    ):
        with pytest.raises(ValueError, match="requires opportunities"):
            asyncio.run(run_manual_analysis(company))
