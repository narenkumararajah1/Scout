"""Outreach draft generation (V3 Phase 6 - docs/v3/06_FEATURE_SPECIFICATIONS.md
Feature 12, docs/v3/04_AI_WORKFLOW.md Stage 13).

Scout never sends customer communications. This module is responsible
ONLY for generating drafts - it contains no delivery capability and no
dependency on SMTP, Outlook, Gmail, SendGrid, SES, or any other
messaging provider. Every draft this module produces is persisted via
backend/repositories/postgres/outreach_draft_repository.py's
create_outreach_draft(), which force-sets status to "Draft" regardless
of what's passed in - there is no code path here, or anywhere in this
module, that changes that status. A human reviewer approving a draft
(backend/repositories/postgres/outreach_draft_repository.py's
mark_draft_approved()) is a separate, explicit action this module never
calls.

Not called by any existing agent, service, or router - see TECH_DEBT.md.
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
    executive_name: str,
    talking_points: list,
    opportunity_id: Optional[str] = None,
    context: str = "",
) -> OutreachDraft:
    if outreach_type not in SUPPORTED_OUTREACH_TYPES:
        raise ValueError(
            f"Unsupported outreach type {outreach_type!r}; expected one of {SUPPORTED_OUTREACH_TYPES}"
        )

    prompt = build_outreach_prompt(company.name, executive_name, outreach_type, talking_points, context)
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
