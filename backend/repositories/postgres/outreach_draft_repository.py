"""Postgres-backed repository for the OutreachDraft entity (V3 Phase 6).

Scout never sends customer communications. create_outreach_draft() force-
sets status to "Draft" regardless of what's passed in, so it is
structurally impossible to create an outreach item in any other status
through this repository - not merely a convention the caller has to
honor. mark_draft_approved()/mark_draft_archived() exist only to
support a future human-reviewer workflow (a person clicking "Approve" in
a UI that doesn't exist yet); backend/services/outreach_service.py (the
generation logic) never calls either of them.
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
    service. Does not send anything; Scout has no delivery capability
    anywhere in this codebase.
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
