from unittest.mock import patch


def test_run_workflow_endpoint_executes_full_workflow(client):
    fake_business_research = "1. Company Research: ...\n2. Company News: ...\n3. Technology Trends: ..."
    fake_social_intelligence = (
        "1. LinkedIn Signals: ...\n2. Hiring Trends: ...\n3. Partnerships: ...\n4. Acquisitions: ..."
    )
    fake_unified_research = "Unified, deduplicated summary of business research and social intelligence."

    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=[fake_business_research, fake_social_intelligence, fake_unified_research],
    ):
        response = client.post("/workflow/run")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "completed"
    assert body["completed_stages"] == [
        "Planner Agent",
        "Research Agent",
        "Knowledge Agent",
        "Opportunity Analysis Agent",
        "Content Generation Agent",
        "Reporting Agent",
    ]
    assert body["errors"] == []
    assert body["research_output"]["sources"]["business_research"] == fake_business_research
    assert body["research_output"]["sources"]["social_intelligence"] == fake_social_intelligence
    assert body["research_output"]["unified_research"] == fake_unified_research
