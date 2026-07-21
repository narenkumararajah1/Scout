"""Prompts for the Executive Intelligence Service (V3 Phase 5).

Only publicly available information is used, per
docs/v3/04_AI_WORKFLOW.md Stage 10 ("Only publicly available information
is used").
"""


def build_executive_profile_prompt(company_name: str, executive_name: str, title: str, research_summary: str) -> str:
    return (
        f'Based on publicly available information, describe "{executive_name}"'
        f'{f", {title}," if title else ""} at "{company_name}", for a B2B sales prospecting '
        "workflow at Innominds. Use only the research provided below - do not invent details "
        "you cannot support.\n\n"
        "Respond with ONLY a JSON object, no other text, with exactly these keys:\n"
        '{"biography": "one or two sentences", "responsibilities": ["..."], '
        '"business_priorities": ["..."], "technology_focus": ["..."]}\n\n'
        "If the research doesn't support a field, return an empty string or empty array for it "
        "rather than inventing details.\n\n"
        f"Research Summary:\n{research_summary}"
    )


def build_executive_engagement_prompt(company_name: str, executive_name: str, title: str, research_summary: str) -> str:
    return (
        f'Recommend how an Innominds sales team should engage "{executive_name}"'
        f'{f", {title}," if title else ""} at "{company_name}", based only on the research below.\n\n'
        "Respond with ONLY a JSON object, no other text, with exactly these keys:\n"
        '{"why_they_matter": "one or two sentences", "conversation_starters": ["..."], '
        '"discovery_questions": ["..."], "relevant_services": ["..."], '
        '"engagement_strategy": "one or two sentences"}\n\n'
        "If the research doesn't support a field, say so explicitly or return an empty array "
        "rather than inventing details.\n\n"
        f"Research Summary:\n{research_summary}"
    )
