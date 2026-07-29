"""Prompt for the Company Refresh Engine's summary narrative (V3
Enhancements Phase 2 - docs/v3-enhancements/07_COMPANY_REFRESH_ENGINE.md).

One consolidated call per refresh. The model is deliberately given the
already-detected changes rather than the raw snapshots: detection is
deterministic (backend/ai/change_detection.py) and must stay that way, so
this call answers only the two questions that genuinely need judgement -
"why does it matter" and "what should I do next" - and is explicitly told
not to introduce developments of its own.
"""

import json


def build_refresh_summary_prompt(company_name: str, changes: list, unchanged_count: int) -> str:
    return (
        f'You are an Innominds account strategist reviewing what has changed at "{company_name}" '
        "since the last time Scout analysed it.\n\n"
        f"Detected changes (already verified - do not add to this list):\n{json.dumps(changes, indent=2)}\n\n"
        f"Items confirmed unchanged since the previous refresh: {unchanged_count}\n\n"
        "Respond with ONLY a JSON object with these exact keys, no other text:\n"
        '{"narrative": "...", "recommended_actions": ["..."]}\n\n'
        "narrative: two or three sentences explaining why these changes matter commercially for an "
        "Innominds sales pursuit. Lead with the most consequential change. Reference only the changes "
        "listed above - do not invent developments, numbers, names or dates that are not there.\n"
        "recommended_actions: up to three specific next steps for the sales team, each a short "
        "imperative phrase. If the changes do not justify an action, return an empty array rather "
        "than inventing busywork."
    )


def build_no_change_narrative(company_name: str, unchanged_count: int) -> str:
    """The no-change summary, written here rather than by the model.

    A refresh that found nothing new needs no judgement, so it costs no
    LLM call - and 07_COMPANY_REFRESH_ENGINE.md's performance section asks
    exactly this ("minimize unnecessary AI calls"). Saying so plainly is
    also more trustworthy than a generated paragraph padding out the fact
    that nothing happened.
    """
    if unchanged_count:
        return (
            f"No meaningful changes at {company_name} since the last refresh. "
            f"{unchanged_count} previously known item(s) were reconfirmed."
        )
    return f"No meaningful changes at {company_name} since the last refresh."


def build_first_refresh_narrative(company_name: str, signal_count: int, opportunity_count: int) -> str:
    """The first-refresh summary.

    Distinct from the no-change wording above, which would otherwise claim
    "no changes since the last refresh" when there was no previous refresh
    to compare against - technically true of the empty change list, but
    misleading about why it is empty. A first analysis is a baseline being
    established, and saying so sets the right expectation for what the
    next run will show.
    """
    return (
        f"First analysis of {company_name}. Captured {signal_count} signal(s) and "
        f"{opportunity_count} opportunity(ies) as the baseline - the next analysis will "
        "report what has changed against it."
    )
