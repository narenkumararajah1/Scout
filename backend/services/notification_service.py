"""Notification generation (V3 Phase 5 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 17, docs/v3/09_DATA_MODELS.md's Notification entity).

No V2 equivalent - backend/notifications.py is a fire-and-forget SMTP
email tied to V1's WorkflowState, not a persisted, queryable entity.
Reuses V2's existing Signal type categories (backend/models/research.py)
as the generation trigger - read-only against SQLite, writes only to the
new Postgres Notification table.

Not called by any existing agent, service, or router - see TECH_DEBT.md.
"""

from __future__ import annotations

import uuid
from typing import Optional

from backend.database.models import Notification
from backend.models.opportunity import Opportunity
from backend.models.research import (
    SIGNAL_TYPE_HIRING,
    SIGNAL_TYPE_LEADERSHIP,
    SIGNAL_TYPE_STRATEGIC,
    SIGNAL_TYPE_TECHNOLOGY,
    Signal,
)
from backend.repositories.postgres.notification_repository import create_notification

# V3's notification types are more granular than V2's four broad Signal
# categories - this mapping is a deliberate simplification, not a 1:1
# correspondence from docs/v3. Technology signals only become a
# notification when they mention AI specifically (see _is_ai_related) -
# not every technology signal (e.g. "adopted Kubernetes") is proactive-
# notification-worthy; V3's "AI Initiative" type is specifically about
# AI investment.
_SIGNAL_TYPE_TO_NOTIFICATION_TYPE = {
    SIGNAL_TYPE_LEADERSHIP: "leadership_change",
    SIGNAL_TYPE_HIRING: "hiring_spike",
    SIGNAL_TYPE_STRATEGIC: "strategic_initiative",
}

_AI_KEYWORDS = ("ai", "artificial intelligence", "machine learning", "genai", "generative ai", "llm")

_RECOMMENDED_ACTIONS = {
    "leadership_change": "Contact executive",
    "hiring_spike": "Review opportunity",
    "strategic_initiative": "Generate report",
    "ai_initiative": "Generate outreach",
    "opportunity_alert": "Review opportunity",
}

# Deliberate, explicit threshold - docs/v3 doesn't specify one for what
# makes an opportunity "significant" enough to alert on.
_OPPORTUNITY_ALERT_CONFIDENCE_THRESHOLD = 0.7


def _is_ai_related(signal: Signal) -> bool:
    text = f"{signal.title} {signal.description or ''}".lower()
    return any(keyword in text for keyword in _AI_KEYWORDS)


def _notification_type_for_signal(signal: Signal) -> Optional[str]:
    if signal.type == SIGNAL_TYPE_TECHNOLOGY:
        return "ai_initiative" if _is_ai_related(signal) else None
    return _SIGNAL_TYPE_TO_NOTIFICATION_TYPE.get(signal.type)


async def generate_notifications_for_signals(company_id: str, signals: list) -> list:
    notifications = []
    for signal in signals:
        notification_type = _notification_type_for_signal(signal)
        if notification_type is None:
            continue

        notification = await create_notification(
            Notification(
                id=str(uuid.uuid4()),
                company_id=company_id,
                type=notification_type,
                title=signal.title,
                summary=signal.description,
                recommended_action=_RECOMMENDED_ACTIONS[notification_type],
            )
        )
        notifications.append(notification)
    return notifications


async def generate_opportunity_alert(opportunity: Opportunity) -> Optional[Notification]:
    if (opportunity.confidence_score or 0) < _OPPORTUNITY_ALERT_CONFIDENCE_THRESHOLD:
        return None

    return await create_notification(
        Notification(
            id=str(uuid.uuid4()),
            company_id=opportunity.company_id,
            type="opportunity_alert",
            title=f"New high-confidence opportunity: {opportunity.title}",
            summary=opportunity.description,
            recommended_action=_RECOMMENDED_ACTIONS["opportunity_alert"],
        )
    )
