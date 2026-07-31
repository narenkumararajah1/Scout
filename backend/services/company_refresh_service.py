"""Company Refresh Engine (V3 Enhancements Phase 2 -
docs/v3-enhancements/07_COMPANY_REFRESH_ENGINE.md).

Implements that document's workflow on top of the existing analysis
pipeline rather than beside it:

    Run Analysis -> Capture snapshot -> Compare previous snapshot ->
    Detect changes -> Persist -> Present summary

**What this does and does not change.** The document's framing is that
Run Analysis should stop being "generate another report" and start being
"update everything Scout knows about this company". This phase delivers
the second half - a refresh summary that becomes the meaningful output of
a run - without removing the first. Report generation is untouched and
still runs: V2's reports are wired into the scheduler, Report
Distribution and the reports API, and deleting that path would break
working systems for no benefit. What changes is where the user's
attention goes: the summary answers "what changed and what should I do",
and the report remains available for anyone who wants the full document.

Division of responsibility:
  - backend/ai/change_detection.py - deterministic diffing, no LLM
  - this module                    - capture, persist, summarise
  - .../postgres/company_snapshot_repository - the history
  - backend/orchestration/stages.py's CompanyRefreshStage - the wiring

The single LLM call here is confined to narrative and recommended
actions, and its failure is non-fatal: the deterministic changes are
persisted before it runs, so a model outage costs a paragraph, never the
history or the detection.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from typing import Optional

from backend.ai.change_detection import ChangeSet, detect_changes
from backend.ai.llm_gateway import generate_completion, parse_json_object
from backend.ai.prompts.refresh_prompts import (
    build_first_refresh_narrative,
    build_no_change_narrative,
    build_refresh_summary_prompt,
)
from backend.database.models import CompanySnapshot
from backend.repositories.postgres import company_snapshot_repository as repository

logger = logging.getLogger(__name__)

# Cap on how many changes are sent to the model. A refresh that produced
# more than this is dominated by its major changes anyway, and an
# unbounded prompt would grow with the noisiest companies.
MAX_CHANGES_IN_PROMPT = 25

# Cap on recommended actions, matching the prompt's own instruction.
MAX_RECOMMENDED_ACTIONS = 3


def _content_hash(
    signals: list,
    opportunities: list,
    capabilities: list,
    profile: dict,
    executives: Optional[list] = None,
    technologies: Optional[list] = None,
) -> str:
    """Stable hash of a snapshot's comparable content.

    sort_keys makes it independent of dict ordering, and the collections
    are sorted so that the same intelligence arriving in a different order
    hashes identically - otherwise every run would look changed.

    `executives` defaults to None and is omitted from the payload entirely
    when absent, so snapshots taken before V3 Enhancements Phase 4 keep
    hashing to the same value they did. Including an empty list instead
    would change every historical hash and make the first post-upgrade
    refresh of every company report as changed.
    """
    payload = {
        "signals": sorted(
            [f"{item.get('type')}|{item.get('title')}" for item in signals]
        ),
        "opportunities": sorted(
            [f"{item.get('title')}|{item.get('confidence_score')}" for item in opportunities]
        ),
        "capabilities": sorted(capabilities),
        "profile": profile,
    }
    if executives is not None:
        payload["executives"] = sorted(
            [f"{item.get('name')}|{item.get('title')}" for item in executives]
        )
    # Same omit-when-absent rule as executives above: including an empty
    # list would change every pre-Phase-7B hash and make the first refresh
    # after upgrading report as changed.
    if technologies is not None:
        payload["technologies"] = sorted(
            [f"{item.get('name')}|{item.get('category')}" for item in technologies]
        )
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def build_snapshot_content(
    company,
    signals: list,
    opportunities: list,
    capability_matches: list,
    executives: Optional[list] = None,
    technologies: Optional[list] = None,
) -> dict:
    """Shapes the live objects into the snapshot's stored form.

    Kept separate from persistence so it can be unit-tested without a
    database, and so a caller that already has these objects loaded (the
    pipeline stage does) never has to re-query for them.

    `executives` defaults to None rather than an empty list, and that
    distinction is carried all the way to the stored column: None means
    "this run did not look", [] means "this run looked and found nobody".
    Only the second is safe to diff against - see
    change_detection._detect_executive_changes.
    """
    signal_payload = [
        {
            "type": getattr(signal, "type", None),
            "title": getattr(signal, "title", None),
            "description": getattr(signal, "description", None),
        }
        for signal in signals or []
    ]
    opportunity_payload = [
        {
            "title": getattr(opportunity, "title", None),
            "priority": getattr(opportunity, "priority", None),
            "confidence_score": getattr(opportunity, "confidence_score", None),
            "recommended_services": list(getattr(opportunity, "recommended_services", None) or []),
        }
        for opportunity in opportunities or []
    ]
    capability_payload = [
        name
        for name in (getattr(match, "capability_name", None) for match in capability_matches or [])
        if name
    ]
    profile_payload = {
        "industry": getattr(company, "industry", None),
        "headquarters": getattr(company, "headquarters", None),
        "website": getattr(company, "website", None),
        "monitoring_status": getattr(company, "monitoring_status", None),
    }
    technology_payload = (
        None
        if technologies is None
        else [
            {"name": getattr(technology, "name", None), "category": getattr(technology, "category", None)}
            for technology in technologies
        ]
    )
    executive_payload = (
        None
        if executives is None
        else [
            {"name": getattr(executive, "name", None), "title": getattr(executive, "title", None)}
            for executive in executives
        ]
    )
    return {
        "signals": signal_payload,
        "opportunities": opportunity_payload,
        "capabilities": capability_payload,
        "profile": profile_payload,
        "executives": executive_payload,
        "technologies": technology_payload,
    }


async def _generate_narrative(
    company_name: str, change_set: ChangeSet, signal_count: int = 0, opportunity_count: int = 0
) -> tuple:
    """Returns (narrative, recommended_actions).

    Neither the first-refresh nor the no-change case costs a model call -
    see build_first_refresh_narrative and build_no_change_narrative. Any
    failure degrades to a factual, locally-written sentence, because a
    refresh whose detection succeeded is still a useful refresh and must
    not be reported as a failure.
    """
    if change_set.is_first_snapshot:
        return build_first_refresh_narrative(company_name, signal_count, opportunity_count), []

    unchanged_count = len(change_set.unchanged)
    if not change_set.has_changes:
        return build_no_change_narrative(company_name, unchanged_count), []

    prompt = build_refresh_summary_prompt(
        company_name,
        change_set.to_dicts()[:MAX_CHANGES_IN_PROMPT],
        unchanged_count,
    )
    try:
        response = await asyncio.to_thread(generate_completion, prompt)
        parsed = parse_json_object(response, "Company Refresh Service")
    except Exception as exc:
        # Deliberately broad: every provider failure mode (timeout, quota,
        # malformed JSON) has the same correct handling here - keep the
        # verified changes, drop only the prose.
        logger.warning("Refresh narrative generation failed for %s: %s", company_name, exc)
        major = len(change_set.major_changes)
        return (
            f"{len(change_set.changes)} change(s) detected at {company_name}"
            f"{f', {major} significant' if major else ''}. "
            "Narrative summary unavailable for this refresh.",
            [],
        )

    narrative = (parsed.get("narrative") or "").strip() or None
    actions = [
        str(action).strip()
        for action in (parsed.get("recommended_actions") or [])
        if str(action).strip()
    ][:MAX_RECOMMENDED_ACTIONS]
    return narrative, actions


async def refresh_company(
    company,
    *,
    signals: list,
    opportunities: list,
    capability_matches: list,
    executives: Optional[list] = None,
    technologies: Optional[list] = None,
    research_session_id: Optional[str] = None,
) -> dict:
    """Captures a snapshot, diffs it against the previous one, and returns
    the refresh summary.

    The order here is deliberate: the previous snapshot is read *before*
    the new one is written, because the repository's "latest" query would
    otherwise return the row we just inserted and every company would
    appear to have changed nothing.
    """
    content = build_snapshot_content(
        company, signals, opportunities, capability_matches, executives, technologies
    )
    previous = await repository.get_latest_snapshot(company.id)

    snapshot = CompanySnapshot(
        id=str(uuid.uuid4()),
        company_id=company.id,
        research_session_id=research_session_id,
        content_hash=_content_hash(
            content["signals"],
            content["opportunities"],
            content["capabilities"],
            content["profile"],
            content["executives"],
            content["technologies"],
        ),
        signals=content["signals"],
        opportunities=content["opportunities"],
        capabilities=content["capabilities"],
        profile=content["profile"],
        executives=content["executives"],
        technologies=content["technologies"],
        signal_count=len(content["signals"]),
        opportunity_count=len(content["opportunities"]),
    )

    change_set = detect_changes(previous, snapshot)
    snapshot.detected_changes = change_set.to_dicts()
    snapshot.change_count = len(change_set.changes)

    snapshot = await repository.create_snapshot(snapshot)

    narrative, actions = await _generate_narrative(
        company.name, change_set, snapshot.signal_count, snapshot.opportunity_count
    )
    await repository.update_summary(
        snapshot.id, summary_narrative=narrative, recommended_actions=actions
    )

    return {
        "company_id": company.id,
        "snapshot_id": snapshot.id,
        "previous_snapshot_id": previous.id if previous is not None else None,
        "captured_at": snapshot.captured_at,
        "is_first_refresh": change_set.is_first_snapshot,
        "content_unchanged": previous is not None and previous.content_hash == snapshot.content_hash,
        "changes": change_set.to_dicts(),
        "major_change_count": len(change_set.major_changes),
        "unchanged": change_set.unchanged,
        "narrative": narrative,
        "recommended_actions": actions,
        "signal_count": snapshot.signal_count,
        "opportunity_count": snapshot.opportunity_count,
    }


async def get_latest_refresh_summary(company_id: str) -> Optional[dict]:
    """The most recent refresh summary, rebuilt from the stored snapshot.

    Reads persisted detection rather than re-diffing: the summary a user
    saw after a run must not change underneath them just because a later
    run moved the comparison window.
    """
    snapshot = await repository.get_latest_snapshot(company_id)
    if snapshot is None:
        return None
    previous = await repository.get_snapshot_before(company_id, snapshot.id)
    changes = snapshot.detected_changes or []
    return {
        "company_id": company_id,
        "snapshot_id": snapshot.id,
        "previous_snapshot_id": previous.id if previous is not None else None,
        "captured_at": snapshot.captured_at,
        "is_first_refresh": previous is None,
        "content_unchanged": previous is not None and previous.content_hash == snapshot.content_hash,
        "changes": changes,
        "major_change_count": sum(1 for change in changes if change.get("significance") == "major"),
        "unchanged": [],
        "narrative": snapshot.summary_narrative,
        "recommended_actions": snapshot.recommended_actions or [],
        "signal_count": snapshot.signal_count,
        "opportunity_count": snapshot.opportunity_count,
    }


async def list_snapshot_history(company_id: str, limit: Optional[int] = None) -> list:
    """The company's intelligence timeline, newest first."""
    return await repository.list_snapshots(company_id, limit=limit)
