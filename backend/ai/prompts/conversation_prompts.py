"""Prompt for the V2 Conversational Intelligence service (Phase 11).

Answers a natural-language question strictly from an already-assembled
snapshot of Scout's intelligence - no tool use, no new research
(ADR-014, FR-018).

Roadmap Phase 2 (Core AI Experience) extends this with optional
conversation history (so a session feels continuous instead of each
question starting cold) and an optional focus company (so a question
asked from a company's page gets that company prioritized in the
answer) - both purely additive to the original single-shot contract.
"""

import json
from typing import Optional


def build_conversation_prompt(
    question: str,
    context: list[dict],
    history: Optional[list[dict]] = None,
    focus_company: Optional[str] = None,
) -> str:
    history_section = ""
    if history:
        turns = "\n".join(f"Q: {turn['question']}\nA: {turn['answer']}" for turn in history)
        history_section = f"Prior conversation in this session (for context only, don't repeat it):\n{turns}\n\n"

    focus_section = ""
    if focus_company:
        focus_section = (
            f"The user is currently viewing {focus_company}'s page in Scout - prioritize and lead with "
            f"information about {focus_company} unless the question is clearly about something else.\n\n"
        )

    return (
        "You are Scout, an AI Sales Strategist for Innominds. "
        "Answer the user's question using ONLY the intelligence data provided below. "
        "Do not invent companies, signals, or opportunities that are not present in this "
        "data, and do not perform new research - you are retrieving from Scout's existing "
        "intelligence, not researching live.\n\n"
        f"Intelligence data (one entry per monitored company):\n{json.dumps(context, default=str)}\n\n"
        f"{history_section}"
        f"{focus_section}"
        f"Question: {question}\n\n"
        "If the data doesn't contain enough information to answer confidently, say so "
        "honestly rather than guessing. Reference specific companies, signals, or "
        "opportunities from the data to support your answer.\n\n"
        "Format your answer in Markdown: use a short bolded headline or executive summary "
        "line first, then bullet points or a table where that's clearer than prose - never "
        "return a single unbroken paragraph when the content has more than one distinct "
        "point. Keep it concise and written for a sales or leadership audience."
    )
