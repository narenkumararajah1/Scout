"""Integration tests for backend/services/v3_report_service.py
(V3 Phase 6). Postgres-gated. Confirms it purely assembles already-
persisted data - no LLM call happens during assembly.
"""

from unittest.mock import patch

from backend.database.models import Company as OrmCompany
from backend.database.models import Technology
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.technology_repository import upsert_technology
from backend.services.v3_report_service import build_and_persist_report


async def test_build_and_persist_report_assembles_without_any_llm_call(postgres_available):
    company = OrmCompany(id="v3rs-company-1", name="V3RsCo")
    await create_company(company)
    await upsert_technology(Technology(id="v3rs-tech-1", company_id="v3rs-company-1", name="Kubernetes"))

    with patch("backend.ai.llm_gateway.generate_completion") as mock_generate:
        report = await build_and_persist_report(company)

    mock_generate.assert_not_called()
    assert report.title == "V3RsCo Intelligence Report"
    assert report.content["technology_landscape"][0]["name"] == "Kubernetes"
    assert report.executive_summary == "Intelligence report for V3RsCo."


async def test_build_and_persist_report_uses_a_sales_playbook_summary_when_one_exists(postgres_available):
    from backend.database.models import SalesPlaybook
    from backend.repositories.postgres.sales_playbook_repository import create_sales_playbook

    company = OrmCompany(id="v3rs-company-2", name="V3RsCo2")
    await create_company(company)
    await create_sales_playbook(
        SalesPlaybook(id="v3rs-sp-1", company_id="v3rs-company-2", strategy_summary="Lead with case studies.")
    )

    report = await build_and_persist_report(company)

    assert report.executive_summary == "Lead with case studies."
