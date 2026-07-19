import json
from unittest.mock import patch

from backend.models.company import Company
from backend.models.knowledge import CaseStudy, Capability, ProofPoint
from backend.repositories.company_repository import create_company
from backend.repositories.knowledge_repository import (
    delete_knowledge_entry,
    index_capability,
    index_case_study,
    index_proof_point,
)
from tests.conftest import clear_v2_tables

FAKE_COMPANY_TECH = "1. Company Information: ...\n2. Technology Initiatives: Kubernetes investment.\n3. Business Trends: ..."
FAKE_ORG_STRATEGIC = "1. Hiring Activity: Hiring ML engineers.\n2. Leadership Changes: ...\n3. Strategic Initiatives: ...\n4. Public Professional Signals: ..."
FAKE_UNIFIED = "Acme Corp is hiring ML engineers and investing in Kubernetes."
FAKE_SIGNALS = json.dumps(
    [{"type": "hiring", "title": "ML engineer hiring", "description": "Hiring ML engineers.", "confidence": 0.8}]
)


def test_analyze_company_endpoint_returns_404_for_unknown_company(client):
    clear_v2_tables()
    response = client.post("/companies/does-not-exist/analyze")

    assert response.status_code == 404


def test_analyze_company_endpoint_returns_422_when_pipeline_has_no_evidence(client):
    """No knowledge is indexed, so Capability Matching finds nothing to
    match against (its documented honest-empty behavior), which cascades
    to Opportunity Analysis and finally Reporting Service's ValueError."""
    clear_v2_tables()
    company = create_company(Company(name="Acme Corp"))

    with patch(
        "backend.services.research_service.generate_completion",
        side_effect=[FAKE_COMPANY_TECH, FAKE_ORG_STRATEGIC, FAKE_UNIFIED, FAKE_SIGNALS],
    ):
        response = client.post(f"/companies/{company.id}/analyze")

    assert response.status_code == 422
    assert "opportunities" in response.json()["detail"]


def test_analyze_company_endpoint_runs_the_full_pipeline_and_persists_a_report(client):
    clear_v2_tables()
    company = create_company(Company(name="Acme Corp"))

    capability = Capability(name="AI Ready Data", description="Data platform readiness.", practice="Data Engineering")
    case_study = CaseStudy(
        customer="Example Co", industry="Logistics", challenge="Legacy warehouse.",
        solution="Cloud migration.", outcome="Faster reporting.",
    )
    proof_point = ProofPoint(description="AWS Advanced Partner.", category="certification")
    index_capability(capability)
    index_case_study(case_study)
    index_proof_point(proof_point)

    fake_match_response = json.dumps(
        [
            {
                "capability_id": f"capability:{capability.id}",
                "confidence": 0.85,
                "reasoning": "ML hiring aligns with AI Ready Data.",
                "case_study_ids": [f"case_study:{case_study.id}"],
                "proof_point_ids": [f"proof_point:{proof_point.id}"],
            }
        ]
    )
    fake_opportunity_response = json.dumps(
        [
            {
                "title": "AI/Data Platform Advisory",
                "priority": 8,
                "confidence_score": 0.85,
                "recommended_services": ["AI Ready Data"],
            }
        ]
    )
    fake_report_response = json.dumps(
        {
            "executive_summary": "Strong opportunity.",
            "company_overview": "Acme Corp overview.",
            "key_findings": "Hiring ML engineers.",
            "technology_analysis": "Kubernetes investment.",
            "capability_alignment": "AI Ready Data aligns well.",
            "opportunities_section": "AI/Data Platform Advisory.",
            "recommendations": "1. Schedule a call.",
            "talking_points": "They are hiring ML engineers.",
        }
    )

    try:
        with patch(
            "backend.services.research_service.generate_completion",
            side_effect=[FAKE_COMPANY_TECH, FAKE_ORG_STRATEGIC, FAKE_UNIFIED, FAKE_SIGNALS],
        ), patch(
            "backend.services.capability_matching_service.generate_completion",
            return_value=fake_match_response,
        ), patch(
            "backend.services.opportunity_analysis_service.generate_completion",
            return_value=fake_opportunity_response,
        ), patch(
            "backend.services.reporting_service.generate_completion",
            return_value=fake_report_response,
        ):
            response = client.post(f"/companies/{company.id}/analyze")
    finally:
        delete_knowledge_entry("capability", capability.id)
        delete_knowledge_entry("case_study", case_study.id)
        delete_knowledge_entry("proof_point", proof_point.id)

    assert response.status_code == 201
    body = response.json()
    assert body["company_id"] == company.id
    assert body["executive_summary"] == "Strong opportunity."

    reports_response = client.get(f"/companies/{company.id}/reports")
    assert len(reports_response.json()) == 1
