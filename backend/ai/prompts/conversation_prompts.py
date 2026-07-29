"""Prompt for the V2 Conversational Intelligence service (Phase 11).

Answers a natural-language question strictly from an already-assembled
snapshot of Scout's intelligence - no tool use, no new research
(ADR-014, FR-018).

Roadmap Phase 2 (Core AI Experience) extends this with optional
conversation history (so a session feels continuous instead of each
question starting cold) and an optional focus company (so a question
asked from a company's page gets that company prioritized in the
answer) - both purely additive to the original single-shot contract.

V3 Enhancements Phase 1 adds retrieved Innominds knowledge
(`knowledge_context`), so answers about Innominds' own services,
expertise and past engagements are grounded in the Company Knowledge
Engine rather than in the LLM's general impressions of the company.
This is the change that makes 02_IMPLEMENTATION_ROADMAP.md's Phase 1
success criterion true: "Scout can answer questions ... using
Innominds-specific knowledge instead of relying solely on the LLM."

Note the deliberate asymmetry in the instructions below: prospect
intelligence stays strictly closed-book (inventing a signal would be
fabricating a fact about a customer), while retrieved knowledge is
supporting evidence the model may reason over and cite. Answering "what
have we done in healthcare?" requires connecting retrieved case studies
to the question, not just quoting them back.
"""

import json
from typing import Optional


def build_conversation_prompt(
    question: str,
    context: list[dict],
    history: Optional[list[dict]] = None,
    focus_company: Optional[str] = None,
    knowledge_context: Optional[str] = None,
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

    knowledge_section = ""
    knowledge_instruction = ""
    if knowledge_context:
        knowledge_section = f"{knowledge_context}\n\n"
        knowledge_instruction = (
            "The Innominds knowledge above is retrieved from Scout's own knowledge base. Use it "
            "whenever the question touches what Innominds does, has delivered, or is positioned "
            "to help with, and cite it by its bracketed number (e.g. [1]) where it supports a "
            "point. Do not claim Innominds capabilities or customer engagements that are not "
            "present in it.\n\n"
        )

    return (
        "You are Scout, an AI Sales Strategist for Innominds. "
        "Answer the user's question using ONLY the data provided below. "
        "Do not invent companies, signals, or opportunities that are not present in this "
        "data, and do not perform new research - you are retrieving from Scout's existing "
        "intelligence, not researching live.\n\n"
        f"Intelligence data (one entry per monitored company):\n{json.dumps(context, default=str)}\n\n"
        f"{knowledge_section}"
        f"{history_section}"
        f"{focus_section}"
        f"Question: {question}\n\n"
        f"{knowledge_instruction}"
        "If the data doesn't contain enough information to answer confidently, say so "
        "honestly rather than guessing. Reference specific companies, signals, or "
        "opportunities from the data to support your answer.\n\n"
        "Format your answer in Markdown: use a short bolded headline or executive summary "
        "line first, then bullet points or a table where that's clearer than prose - never "
        "return a single unbroken paragraph when the content has more than one distinct "
        "point. Keep it concise and written for a sales or leadership audience."
    )
