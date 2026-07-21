"""Integration tests for backend/services/notification_service.py
(V3 Phase 5) against a real PostgreSQL instance. Skipped automatically
wherever Postgres isn't reachable (see conftest.py's postgres_available
fixture).
"""

from datetime import datetime

from backend.database.models import Company
from backend.models.opportunity import Opportunity
from backend.models.research import Signal
from backend.repositories.postgres.company_repository import create_company
from backend.repositories.postgres.notification_repository import list_notifications_for_company
from backend.services.notification_service import generate_notifications_for_signals, generate_opportunity_alert


async def test_leadership_signal_generates_a_leadership_change_notification(postgres_available):
    await create_company(Company(id="notif-svc-company-1", name="NotifSvcCo"))
    signal = Signal(research_session_id="session-1", type="leadership", title="New CTO appointed")

    notifications = await generate_notifications_for_signals("notif-svc-company-1", [signal])

    assert len(notifications) == 1
    assert notifications[0].type == "leadership_change"
    assert notifications[0].recommended_action == "Contact executive"


async def test_technology_signal_only_generates_a_notification_when_ai_related(postgres_available):
    await create_company(Company(id="notif-svc-company-2", name="NotifSvcCo2"))
    ai_signal = Signal(research_session_id="session-1", type="technology", title="Launched a new GenAI platform")
    generic_signal = Signal(research_session_id="session-1", type="technology", title="Adopted Kubernetes")

    notifications = await generate_notifications_for_signals(
        "notif-svc-company-2", [ai_signal, generic_signal]
    )

    assert len(notifications) == 1
    assert notifications[0].type == "ai_initiative"
    assert notifications[0].title == "Launched a new GenAI platform"


async def test_generate_notifications_for_signals_persists_them(postgres_available):
    await create_company(Company(id="notif-svc-company-3", name="NotifSvcCo3"))
    signal = Signal(research_session_id="session-1", type="hiring", title="Hiring spike in engineering")

    await generate_notifications_for_signals("notif-svc-company-3", [signal])

    persisted = await list_notifications_for_company("notif-svc-company-3")
    assert len(persisted) == 1
    assert persisted[0].type == "hiring_spike"


async def test_generate_opportunity_alert_only_fires_above_the_confidence_threshold(postgres_available):
    await create_company(Company(id="notif-svc-company-4", name="NotifSvcCo4"))
    low_confidence = Opportunity(
        company_id="notif-svc-company-4",
        research_session_id="session-1",
        title="Low confidence opportunity",
        confidence_score=0.4,
    )
    high_confidence = Opportunity(
        company_id="notif-svc-company-4",
        research_session_id="session-1",
        title="High confidence opportunity",
        confidence_score=0.85,
    )

    assert await generate_opportunity_alert(low_confidence) is None
    alert = await generate_opportunity_alert(high_confidence)
    assert alert is not None
    assert alert.type == "opportunity_alert"
    assert "High confidence opportunity" in alert.title
