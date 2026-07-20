"""Conversational Intelligence endpoint (V2 Phase 11, FR-018).

Thin per IMPLEMENTATION_RULES.md's Service Layer rule: validate input,
call backend.services.conversation_service, return responses. No
retrieval or LLM logic lives here.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services import conversation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["conversation"])


class ConversationRequest(BaseModel):
    question: str = Field(min_length=1)


class ConversationResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=ConversationResponse)
def ask(request: ConversationRequest) -> ConversationResponse:
    try:
        answer = conversation_service.answer_question(request.question)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - an upstream (Claude API) failure must return a meaningful message
        logger.exception("Conversational question failed.")
        raise HTTPException(status_code=502, detail=f"Could not answer question: {exc}") from exc
    return ConversationResponse(answer=answer)
