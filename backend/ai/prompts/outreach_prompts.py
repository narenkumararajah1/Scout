"""Prompts for the Outreach Service (V3 Phase 6).

Generation only - see backend/services/outreach_service.py's module
docstring. These prompts never ask the model to send anything, only to
draft content for human review.
"""


def build_outreach_prompt(
    company_name: str, executive_name: str, outreach_type: str, talking_points: list, context: str
) -> str:
    return (
        f'Draft a {outreach_type} to "{executive_name}" at "{company_name}" for an Innominds sales '
        "team, for human review before it is ever sent - do not address it as if it will be sent "
        "automatically.\n\n"
        f"Talking points to draw from:\n{talking_points}\n\n"
        f"Additional context:\n{context or 'None provided.'}\n\n"
        "Respond with ONLY a JSON object, no other text, with exactly these keys:\n"
        '{"subject": "a short subject line (empty string if not applicable, e.g. for a LinkedIn '
        'message)", "content": "the drafted message body"}\n\n'
        "Keep it concise and professional. This is a draft for a human to review, edit, and approve - "
        "never a message that will be sent as-is."
    )
