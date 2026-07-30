"""Prompts for the Outreach Service (V3 Phase 6; V2->V3 parity pass
loosens executive_name to optional so generation never blocks on
contact information - see backend/services/outreach_service.py's
module docstring).

Generation only - these prompts never ask the model to send anything,
only to draft content for human review.
"""

from typing import Optional

from backend.ai.prompts.enrichment_prompts import grounding_instruction, knowledge_section


def build_outreach_prompt(
    company_name: str,
    executive_name: Optional[str],
    outreach_type: str,
    talking_points: list,
    context: str,
    enrichment_block: Optional[str] = None,
) -> str:
    recipient_description = f'"{executive_name}"' if executive_name else "the most relevant executive contact"
    return (
        f'Draft a {outreach_type} to {recipient_description} at "{company_name}" for an Innominds '
        "sales team, for human review before it is ever sent - do not address it as if it will be "
        "sent automatically."
        + (
            ""
            if executive_name
            else " No specific contact name is known yet, so address it generically (e.g. by role or "
            "team, not a placeholder like \"[Name]\") - write it so a reviewer can drop in a name "
            "later without needing to rewrite the greeting."
        )
        + "\n\n"
        f"Talking points to draw from:\n{talking_points}\n\n"
        f"Additional context:\n{context or 'None provided.'}\n\n"
        f"{knowledge_section(enrichment_block)}"
        "Respond with ONLY a JSON object, no other text, with exactly these keys:\n"
        '{"subject": "a short subject line (empty string if not applicable, e.g. for a LinkedIn '
        'message)", "content": "the drafted message body"}\n\n'
        "Keep it concise and professional. This is a draft for a human to review, edit, and approve - "
        "never a message that will be sent as-is."
        f"{grounding_instruction(enrichment_block)}"
    )
