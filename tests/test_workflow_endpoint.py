import json
from unittest.mock import patch


def test_run_workflow_endpoint_executes_full_workflow(client):
    fake_business_research = "1. Company Research: ...\n2. Company News: ...\n3. Technology Trends: ..."
    fake_social_intelligence = (
        "1. LinkedIn Signals: ...\n2. Hiring Trends: ...\n3. Partnerships: ...\n4. Acquisitions: ..."
    )
    fake_unified_research = "Unified, deduplicated summary of business research and social intelligence."
    fake_opportunities_json = '[{"name": "Cloud Migration", "description": "...", "score": 8}]'
    fake_narrative_json = json.dumps(
        {
            "executive_summary": "Strong opportunity for cloud consulting.",
            "opportunity_summary": "Cloud Migration is the top opportunity.",
            "recommended_next_steps": "1. Propose a cloud infrastructure assessment.",
        }
    )
    fake_linkedin_post = "Curious how companies modernize infrastructure? We can help."
    fake_infographic_prompt = "Section 1: Company snapshot. Section 2: Cloud Migration opportunity."

    with patch(
        "backend.agents.research_agent.generate_completion",
        side_effect=[fake_business_research, fake_social_intelligence, fake_unified_research],
    ), patch(
        "backend.agents.opportunity_agent.generate_completion",
        return_value=fake_opportunities_json,
    ), patch(
        "backend.agents.content_agent.generate_completion",
        side_effect=[fake_narrative_json, fake_linkedin_post, fake_infographic_prompt],
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
    assert body["opportunity_output"]["opportunities"][0]["name"] == "Cloud Migration"
    assert body["content_output"]["executive_summary"] == "Strong opportunity for cloud consulting."
    assert body["content_output"]["linkedin_post"] == fake_linkedin_post
    assert body["content_output"]["infographic_prompt"] == fake_infographic_prompt
