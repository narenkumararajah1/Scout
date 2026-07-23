"""Postgres-backed repository for the OutreachDraft entity (V3 Phase 6;
outreach workflow redesign adds update_outreach_draft_content() and
mark_draft_sent()).

create_outreach_draft() force-sets status to "Draft" regardless of what's
passed in, so it is structurally impossible to create an outreach item
in any other status through this repository - not merely a convention
the caller has to honor. mark_draft_approved()/mark_draft_archived()/
mark_draft_sent() are each a human-triggered status transition;
backend/services/outreach_service.py (generation) never calls any of
them, and only backend/services/outreach_delivery_service.py (a real
send, always behind an explicit user action) ever calls
mark_draft_sent().
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import OutreachDraft
from backend.database.postgres import get_session


async def create_outreach_draft(draft: OutreachDraft) -> OutreachDraft:
    draft.status = "Draft"
    async with get_session() as session:
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        return draft


async def get_outreach_draft(draft_id: str) -> Optional[OutreachDraft]:
    async with get_session() as session:
        return await session.get(OutreachDraft, draft_id)


async def list_outreach_drafts_for_company(company_id: str) -> list:
    async with get_session() as session:
        result = await session.execute(
            select(OutreachDraft).where(OutreachDraft.company_id == company_id).order_by(
                OutreachDraft.created_at.desc()
            )
        )
        return list(result.scalars().all())


async def mark_draft_approved(draft_id: str) -> Optional[OutreachDraft]:
    """A human reviewer's action - never called by the generation
    service. A pure status transition, not a send - see
    backend/services/outreach_delivery_service.py for that.
    """
    async with get_session() as session:
        draft = await session.get(OutreachDraft, draft_id)
        if draft is None:
            return None
        draft.status = "Approved"
        await session.commit()
        await session.refresh(draft)
        return draft


async def mark_draft_archived(draft_id: str) -> Optional[OutreachDraft]:
    """A human reviewer's action - never called by the generation service."""
    async with get_session() as session:
        draft = await session.get(OutreachDraft, draft_id)
        if draft is None:
            return None
        draft.status = "Archived"
        await session.commit()
        await session.refresh(draft)
        return draft


async def mark_draft_sent(draft_id: str) -> Optional[OutreachDraft]:
    """Only ever called by backend/services/outreach_delivery_service.py
    after a real send actually succeeded (or was intentionally skipped
    because no channel is configured) - never by generation or by the
    approve/archive review actions.
    """
    async with get_session() as session:
        draft = await session.get(OutreachDraft, draft_id)
        if draft is None:
            return None
        draft.status = "Sent"
        await session.commit()
        await session.refresh(draft)
        return draft


async def update_outreach_draft_content(
    draft_id: str, subject: Optional[str], content: str
) -> Optional[OutreachDraft]:
    """A human reviewer editing a draft before sending (or just to fix a
    typo) - the "Review" step of the outreach workflow redesign. Content
    only; never touches status.
    """
    async with get_session() as session:
        draft = await session.get(OutreachDraft, draft_id)
        if draft is None:
            return None
        draft.subject = subject
        draft.content = content
        await session.commit()
        await session.refresh(draft)
        return draft
