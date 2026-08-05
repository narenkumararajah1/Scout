"""Prompt for synthesising an intelligence report from what Scout already
knows (V3 - report generation).

The report used to be pure assembly: every section was stored data
reformatted, and the "executive summary" was either a sentence copied off
the newest Sales Playbook or the literal string "Intelligence report for
<company>." That is a document a reader has to synthesise themselves.

This prompt asks the model to do the reading-across that assembly cannot:
connect a hiring signal to a technology to an opportunity, and say what it
means. It is given *only* the intelligence already gathered, never the
live web, so generating a report stays a cheap read over stored state
rather than a second analysis run.
"""

import json

REPORT_SYNTHESIS_PROMPT = """You are a sales strategist writing an intelligence brief on {company_name} for a consulting firm's account team.

Below is everything the firm's research system currently knows about this company. Synthesise it. Do not restate it.

{intelligence}

Write the brief as JSON with exactly these keys:

- "executive_summary": 3-5 sentences. What is happening at this company, why it matters commercially, and what the single most important move is. Lead with the conclusion, not with background.
- "key_findings": an array of 3-6 strings. Each must connect at least two separate pieces of evidence above into an insight that neither shows alone (for example a technology choice plus a hiring pattern plus a stated initiative). Do not list facts that appear verbatim above.
- "capability_alignment": 2-4 sentences on where the firm's proven delivery experience matches what this company appears to need, naming the specific capability matches above. If the matches are weak, say so plainly.
- "opportunities_section": 2-4 sentences prioritising the opportunities above, and saying why that order. Reference confidence where it changes the ranking.
- "recommendations": an array of 2-5 strings, each a concrete next action with a reason.
- "talking_points": an array of 3-5 strings a salesperson could use in a live conversation. Specific to this company; nothing that would be true of any company in its industry.

Rules:
- Ground every claim in the intelligence above. If something is not there, do not assert it.
- Where the evidence is thin, say what is missing rather than filling the gap with plausible-sounding filler. A short honest brief beats a long speculative one.
- No preamble, no markdown fences. Return only the JSON object.
"""


def build_report_synthesis_prompt(company_name: str, content: dict) -> str:
    """`content` is the assembled report body - the same structure that is
    persisted - so the synthesis sees exactly what the reader will see
    underneath it, and cannot cite anything the report does not contain.
    """
    return REPORT_SYNTHESIS_PROMPT.format(
        company_name=company_name,
        # default=str so datetimes and Decimals in the serialised sections
        # cannot turn a report into a 500.
        intelligence=json.dumps(content, indent=2, default=str),
    )
