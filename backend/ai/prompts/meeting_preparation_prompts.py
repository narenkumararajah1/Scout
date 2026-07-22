"""Prompts for the Meeting Preparation Service (V3 Phase 6).

Only the meeting-objectives prompt lives here - executive engagement
content (conversation starters, discovery questions, talking points) is
reused from backend/services/executive_intelligence_service.py (Phase 5)
rather than duplicated, per the Phase 6 requirement.
"""

import json


def build_meeting_objectives_prompt(company_name: str, meeting_title: str, business_priorities: list) -> str:
    return (
        f'Define clear objectives for an upcoming meeting titled "{meeting_title}" with "{company_name}", '
        "for an Innominds sales team.\n\n"
        f"Known business priorities:\n{json.dumps(business_priorities)}\n\n"
        "Respond with ONLY a JSON array of short objective strings, no other text, e.g.:\n"
        '["Confirm the timeline for their cloud migration initiative.", "..."]\n\n'
        "If there isn't enough information to define objectives, return an empty array rather than "
        "inventing details."
    )
