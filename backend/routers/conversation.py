"""Conversational Intelligence endpoint (V2 Phase 11, FR-018).

Thin per IMPLEMENTATION_RULES.md's Service Layer rule: validate input,
call backend.services.conversation_service, return responses. No
retrieval or LLM logic lives here.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services import conversation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["conversation"])


class ConversationTurn(BaseModel):
    question: str
    answer: str


class ConversationRequest(BaseModel):
    question: str = Field(min_length=1)
    # Roadmap Phase 2 (Scout Copilot): both optional and purely additive
    # to the original single-shot contract - existing callers that omit
    # them keep working exactly as before.
    company_id: Optional[str] = None
    history: list[ConversationTurn] = Field(default_factory=list)


class RelatedCompany(BaseModel):
    id: str
    name: str


class SuggestedAction(BaseModel):
    label: str
    action_type: str
    company_id: str


class ConversationResponse(BaseModel):
    answer: str
    related_companies: list[RelatedCompany] = Field(default_factory=list)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)


@router.post("/ask", response_model=ConversationResponse)
def ask(request: ConversationRequest) -> ConversationResponse:
    try:
        result = conversation_service.answer_question(
            request.question,
            company_id=request.company_id,
            history=[turn.model_dump() for turn in request.history],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - an upstream (Claude API) failure must return a meaningful message
        logger.exception("Conversational question failed.")
        raise HTTPException(status_code=502, detail=f"Could not answer question: {exc}") from exc
    return ConversationResponse(**result)
