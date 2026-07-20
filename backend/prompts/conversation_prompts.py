"""Prompt for the V2 Conversational Intelligence service (Phase 11).

Answers a natural-language question strictly from an already-assembled
snapshot of Scout's intelligence - no tool use, no new research
(ADR-014, FR-018).
"""

import json


def build_conversation_prompt(question: str, context: list[dict]) -> str:
    return (
        "You are Scout, an AI Sales Intelligence Platform for Innominds. "
        "Answer the user's question using ONLY the intelligence data provided below. "
        "Do not invent companies, signals, or opportunities that are not present in this "
        "data, and do not perform new research - you are retrieving from Scout's existing "
        "intelligence, not researching live.\n\n"
        f"Intelligence data (one entry per monitored company):\n{json.dumps(context, default=str)}\n\n"
        f"Question: {question}\n\n"
        "If the data doesn't contain enough information to answer confidently, say so "
        "honestly rather than guessing. Reference specific companies, signals, or "
        "opportunities from the data to support your answer. Respond in clear business "
        "language suitable for a sales or leadership audience."
    )
