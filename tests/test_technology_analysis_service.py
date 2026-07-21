"""Integration tests for backend/services/technology_analysis_service.py
(V3 Phase 5). Postgres-gated (persistence) with the LLM call mocked, so
these run without real provider credentials.
"""

import json
from unittest.mock import patch

from backend.database.models import Company, Technology
from backend.repositories.postgres.company_repository import create_company
from backend.services.technology_analysis_service import analyze_and_persist_technology, analyze_technology


def _mock_response(**fields) -> str:
    return json.dumps(
        {
            "adoption_status": fields.get("adoption_status", "Established"),
            "business_relevance": fields.get("business_relevance", "Supports scaling."),
            "industry_context": fields.get("industry_context", "Widely adopted in this sector."),
        }
    )


async def test_analyze_technology_returns_a_result_with_confidence(postgres_available):
    technology = Technology(id="ta-1", company_id="ta-company-1", name="Kubernetes", category="infrastructure")

    with patch(
        "backend.services.technology_analysis_service.generate_completion", return_value=_mock_response()
    ):
        result = await analyze_technology(technology, "Acme Corp")

    assert result.technology_name == "Kubernetes"
    assert result.adoption_status == "Established"
    assert result.confidence is not None
    assert result.confidence.completeness == 1.0


async def test_analyze_and_persist_technology_updates_the_stored_row(postgres_available):
    await create_company(Company(id="ta-company-2", name="TaCo2"))
    technology = Technology(id="ta-2", company_id="ta-company-2", name="Snowflake")

    with patch(
        "backend.services.technology_analysis_service.generate_completion",
        return_value=_mock_response(business_relevance="Central to their data strategy."),
    ):
        updated = await analyze_and_persist_technology(technology, "Acme Corp")

    assert updated.business_relevance == "Central to their data strategy."
    assert updated.confidence_score is not None
