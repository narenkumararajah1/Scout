"""Prompt for the V2 Executive Reporting service (Phase 8).

Produces the eight-section Report defined in DATA_MODEL.md from a
research cycle's Signals, Capability Matches, and (ranked) Opportunities.
"""

import json


def build_report_prompt(
    company_name: str,
    research_summary: str,
    signals: list[dict],
    capability_matches: list[dict],
    opportunities: list[dict],
) -> str:
    return (
        f'Generate a complete executive intelligence report for "{company_name}" '
        "based on the following research cycle.\n\n"
        f"Research Summary:\n{research_summary}\n\n"
        f"Signals detected:\n{json.dumps(signals)}\n\n"
        f"Innominds capability matches:\n{json.dumps(capability_matches)}\n\n"
        f"Prioritized opportunities (highest priority first):\n{json.dumps(opportunities)}\n\n"
        "Generate eight sections:\n\n"
        "1. executive_summary - a concise, 3-4 sentence overview suitable for a "
        "busy executive.\n"
        "2. company_overview - a short overview of the company based on the research.\n"
        "3. key_findings - the most important signals and what they indicate.\n"
        "4. technology_analysis - the technology adoption and initiatives observed.\n"
        "5. capability_alignment - how Innominds' capabilities align with this "
        "company's needs, referencing each match's confidence score explicitly.\n"
        "6. opportunities_section - the prioritized opportunities, referencing each "
        "one's priority and confidence score explicitly.\n"
        "7. recommendations - a short, numbered action plan synthesizing the "
        "opportunities into next steps for the sales team.\n"
        "8. talking_points - concrete points a salesperson could raise when "
        "engaging this prospect, grounded in the signals and capability matches.\n\n"
        "If the underlying evidence for a section is thin, say so honestly rather "
        "than overstating confidence.\n\n"
        "Respond with ONLY a JSON object, no other text, in this exact format:\n"
        '{"executive_summary": "...", "company_overview": "...", "key_findings": "...", '
        '"technology_analysis": "...", "capability_alignment": "...", '
        '"opportunities_section": "...", "recommendations": "...", "talking_points": "..."}'
    )
