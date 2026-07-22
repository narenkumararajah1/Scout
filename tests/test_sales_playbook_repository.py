"""Integration tests for backend/repositories/postgres/sales_playbook_repository.py
(V3 Phase 6) against a real PostgreSQL instance. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).
"""

from backend.database.models import Company, SalesPlaybook
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.sales_playbook_repository import (
    create_sales_playbook,
    get_sales_playbook,
    list_sales_playbooks_for_company,
)


async def test_create_sales_playbook_persists_and_is_retrievable(postgres_available):
    await create_company(Company(id="sp-company-1", name="SpCo"))

    created = await create_sales_playbook(
        SalesPlaybook(
            id="sp-1",
            company_id="sp-company-1",
            opportunity_id="opp-1",
            strategy_summary="Lead with platform engineering.",
            talking_points=["Ask about Kubernetes rollout."],
            risks=["Budget constraints"],
        )
    )

    fetched = await get_sales_playbook("sp-1")
    assert fetched is not None
    assert fetched.strategy_summary == "Lead with platform engineering."
    assert fetched.risks == ["Budget constraints"]
    assert created.id == fetched.id


async def test_list_sales_playbooks_for_company_orders_most_recent_first(postgres_available):
    await create_company(Company(id="sp-company-2", name="SpCo2"))
    await create_sales_playbook(SalesPlaybook(id="sp-2", company_id="sp-company-2", strategy_summary="First"))
    await create_sales_playbook(SalesPlaybook(id="sp-3", company_id="sp-company-2", strategy_summary="Second"))

    playbooks = await list_sales_playbooks_for_company("sp-company-2")

    assert [p.strategy_summary for p in playbooks] == ["Second", "First"]


async def test_get_sales_playbook_returns_none_for_an_unknown_id(postgres_available):
    assert await get_sales_playbook("does-not-exist") is None
