"""Outreach draft generation (V3 Phase 6 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 12, docs/v3/04_AI_WORKFLOW.md Stage 13).

This module generates content only - it has no dependency on SMTP,
Outlook, Gmail, SendGrid, SES, or any other messaging provider, and
never calls anything in backend/services/outreach_delivery_service.py
or backend/distribution/. Every draft this module produces is persisted
via backend/repositories/postgres/outreach_draft_repository.py's
create_outreach_draft(), which force-sets status to "Draft" regardless
of what's passed in - there is no code path here that changes that
status. A human reviewer approving/archiving a draft, or sending it
through outreach_delivery_service.py, are separate, explicit actions
this module never calls - generation and delivery are deliberately
decoupled (V2->V3 parity pass, "outreach workflow redesign") so
generating a draft never requires - or triggers - a send.

executive_name is optional by the same redesign: a user should be able
to generate a complete draft immediately from company/opportunity/
meeting-brief context alone, before deciding who it's for. When no
executive is known, build_outreach_prompt() asks the model to address
the draft generically rather than blocking generation on contact
lookup.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from backend.ai.llm_gateway import generate_completion, parse_json_object
from backend.ai.prompts.outreach_prompts import build_outreach_prompt
from backend.database.models import OutreachDraft
from backend.models.company import Company
from backend.repositories.postgres.outreach_draft_repository import create_outreach_draft

SUPPORTED_OUTREACH_TYPES = ("Email", "Follow-up", "Meeting Request", "LinkedIn Message")


async def generate_outreach_draft(
    company: Company,
    outreach_type: str,
    executive_name: Optional[str] = None,
    talking_points: Optional[list] = None,
    opportunity_id: Optional[str] = None,
    context: str = "",
) -> OutreachDraft:
    if outreach_type not in SUPPORTED_OUTREACH_TYPES:
        raise ValueError(
            f"Unsupported outreach type {outreach_type!r}; expected one of {SUPPORTED_OUTREACH_TYPES}"
        )

    prompt = build_outreach_prompt(company.name, executive_name, outreach_type, talking_points or [], context)
    response = await asyncio.to_thread(generate_completion, prompt)
    parsed = parse_json_object(response, "Outreach Service")

    draft = OutreachDraft(
        id=str(uuid.uuid4()),
        company_id=company.id,
        opportunity_id=opportunity_id,
        type=outreach_type,
        subject=parsed.get("subject") or None,
        content=parsed.get("content", ""),
    )
    return await create_outreach_draft(draft)
