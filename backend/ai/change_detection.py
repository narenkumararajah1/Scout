"""Change detection between two company snapshots (V3 Enhancements
Phase 2 - docs/v3-enhancements/07_COMPANY_REFRESH_ENGINE.md).

**Deliberately contains no LLM call.** 01_VISION.md's principles put
"evidence over assumptions" and "explainability over black-box scoring"
ahead of automation, and asking a model whether two lists differ is both
less reliable and less explainable than comparing them. Detection here is
pure and deterministic: the same two snapshots always yield the same
changes, and every change points at the specific item that produced it.
The narrative layer ("why does it matter", "what should I do next") is a
separate, single model call in
backend/services/company_refresh_service.py, applied *on top of* these
findings rather than in place of them.

Being a pure function of its inputs, this module needs no database and no
network, so it is exercised by ordinary unit tests rather than
Postgres-gated ones.

Noise control is a first-class requirement of that document ("Minor or
duplicate changes should be filtered to reduce noise"), so it is handled
here rather than left to the caller:

  - Titles are normalised, so the same development re-reported with
    different casing or padding is one item, not two.
  - Titles are additionally matched by *similarity*, because the research
    layer rewords the same development between runs - see the note below.
  - An opportunity's score has to move by more than MINIMUM_SCORE_DELTA
    before it counts as strengthened or weakened; small run-to-run drift
    in an LLM-assigned score is not a business change.
  - Every change carries a significance, and callers that only want the
    headline can filter to major without re-deriving the rule.

**Why similarity matching is necessary, and its limits.** Signal and
opportunity titles are written by an LLM and are not stable identifiers.
Verified against two real consecutive analyses of the same company, the
research layer produced pairs like "Sovereign AI Infrastructure
Expansion" / "Sovereign AI and Global Infrastructure Expansion" and
"AI-Ready Data Pipelines for Enterprise NIM & Omniverse Workloads" /
"AI Ready Data Pipelines for Enterprise AI and NIMs Deployment" - the
same facts, reworded. Exact matching reported each pair as one item
appearing and another disappearing, and because a new opportunity is
major, it announced significant new developments where nothing had
changed. Token-overlap matching collapses those pairs into a single
"updated" change instead.

This reduces the problem but cannot eliminate it: a rewording that shares
few words ("Aggressive Workforce Scaling in Engineering and AI" versus
"Aggressive Global Hiring in Silicon Engineering and Software") still
reads as two changes. Lexical similarity is the wrong tool for that, and
the real fix is stable identifiers assigned upstream where a signal is
created rather than inferred downstream here. Recorded in TECH_DEBT.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

# An opportunity's confidence has to move by more than this before the
# movement is reported. Scores are LLM-assigned and vary slightly between
# runs on identical inputs; below this threshold a "change" would be
# describing the model's variance rather than the customer's business.
MINIMUM_SCORE_DELTA = 0.1

# How much of two titles' meaningful vocabulary must overlap before they
# are judged to describe the same thing (Jaccard index over token sets).
#
# 0.45 was chosen against observed real pairs rather than picked for
# roundness. It is above the ~0.22-0.25 scored by genuinely different
# developments that happen to share a leading word, and at or below the
# ~0.45-0.8 scored by the verified rewordings quoted in the module
# docstring. Raising it reintroduces duplicate churn; lowering it starts
# merging distinct developments, which is the worse failure - a merged
# pair hides a real change, while a split pair only adds noise.
TITLE_SIMILARITY_THRESHOLD = 0.45

# Words carrying no distinguishing meaning in these titles. Kept small and
# domain-specific on purpose: stripping too much makes short titles
# collide with each other.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "the",
        "of",
        "for",
        "to",
        "in",
        "on",
        "with",
        "via",
        "into",
        "at",
        "by",
        "or",
        "as",
        "its",
        "their",
    }
)

# Change categories, aligned with 07_COMPANY_REFRESH_ENGINE.md's
# "Change Detection" list. Signal-derived categories reuse the existing
# Signal.type vocabulary (backend/models/research.py) rather than
# inventing a parallel taxonomy.
CATEGORY_LEADERSHIP = "leadership"
CATEGORY_HIRING = "hiring"
CATEGORY_TECHNOLOGY = "technology"
CATEGORY_STRATEGIC = "strategic"
CATEGORY_OPPORTUNITY = "opportunity"
CATEGORY_CAPABILITY = "capability"
CATEGORY_PROFILE = "profile"

# What kind of movement a change describes.
CHANGE_APPEARED = "appeared"
CHANGE_RESOLVED = "resolved"
CHANGE_STRENGTHENED = "strengthened"
CHANGE_WEAKENED = "weakened"
CHANGE_UPDATED = "updated"

SIGNIFICANCE_MAJOR = "major"
SIGNIFICANCE_MINOR = "minor"

# Leadership and strategic developments are the ones a salesperson acts
# on immediately (a new CTO, an acquisition), so a newly appearing signal
# in those categories is major. Hiring and technology signals are usually
# corroborating detail and start as minor - they become interesting in
# aggregate, which the trend view covers, rather than one at a time.
_MAJOR_SIGNAL_CATEGORIES = frozenset({CATEGORY_LEADERSHIP, CATEGORY_STRATEGIC})


@dataclass
class DetectedChange:
    """One meaningful difference between two snapshots.

    `source` is what makes a change explainable rather than asserted: it
    names the snapshot content the change was derived from, so the UI can
    show why Scout believes something changed
    (05_EXTERNAL_INTELLIGENCE.md's source-attribution requirement).
    """

    category: str
    change_type: str
    title: str
    detail: Optional[str] = None
    significance: str = SIGNIFICANCE_MINOR
    source: Optional[str] = None
    previous_value: Optional[str] = None
    current_value: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChangeSet:
    """Everything a diff produced, including what stayed the same.

    07_COMPANY_REFRESH_ENGINE.md asks the refresh summary to report "what
    stayed the same" alongside what changed - a run that confirms nothing
    moved is a real, useful answer, not an empty result.
    """

    changes: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)
    is_first_snapshot: bool = False

    @property
    def has_changes(self) -> bool:
        return bool(self.changes)

    @property
    def major_changes(self) -> list:
        return [change for change in self.changes if change.significance == SIGNIFICANCE_MAJOR]

    def to_dicts(self) -> list:
        return [change.to_dict() for change in self.changes]


def _normalize(text: Optional[str]) -> str:
    """Collapses a title to a comparison key.

    Casing and surrounding whitespace vary between runs because these
    strings come from an LLM; without this, the same development would be
    reported as both resolved and appeared on every single refresh.
    """
    return " ".join((text or "").split()).lower()


def _tokens(text: Optional[str]) -> frozenset:
    """Meaningful word set of a title, for similarity comparison.

    Punctuation is treated as a separator so "AI-Ready" and "AI Ready"
    tokenize identically, and a trailing "s" is trimmed so "NIM" matches
    "NIMs" - both differences were observed between real consecutive runs.
    """
    cleaned = "".join(character if character.isalnum() else " " for character in (text or "").lower())
    words = []
    for word in cleaned.split():
        if word in _STOPWORDS:
            continue
        words.append(word[:-1] if len(word) > 3 and word.endswith("s") else word)
    return frozenset(words)


def _similarity(left: Optional[str], right: Optional[str]) -> float:
    """Jaccard index over the two titles' meaningful tokens, 0.0-1.0."""
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union)


def _pair_by_similarity(appeared: list, resolved: list, title_of) -> tuple:
    """Greedily pairs appeared items with resolved ones that describe the
    same thing.

    Returns (pairs, unpaired_appeared, unpaired_resolved). Greedy on the
    best available score, and each item can be used once, so a single
    resolved item cannot absorb several genuinely new ones. Scores below
    the threshold are never paired.
    """
    scored = []
    for appeared_index, appeared_item in enumerate(appeared):
        for resolved_index, resolved_item in enumerate(resolved):
            score = _similarity(title_of(appeared_item), title_of(resolved_item))
            if score >= TITLE_SIMILARITY_THRESHOLD:
                scored.append((score, appeared_index, resolved_index))
    # Sort by score descending, then by indices so equal scores pair
    # deterministically rather than depending on dict iteration order.
    scored.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))

    used_appeared, used_resolved, pairs = set(), set(), []
    for score, appeared_index, resolved_index in scored:
        if appeared_index in used_appeared or resolved_index in used_resolved:
            continue
        used_appeared.add(appeared_index)
        used_resolved.add(resolved_index)
        pairs.append((appeared[appeared_index], resolved[resolved_index], score))

    unpaired_appeared = [item for index, item in enumerate(appeared) if index not in used_appeared]
    unpaired_resolved = [item for index, item in enumerate(resolved) if index not in used_resolved]
    return pairs, unpaired_appeared, unpaired_resolved


def _signal_key(signal: dict) -> tuple:
    return (signal.get("type") or "", _normalize(signal.get("title")))


def _opportunity_key(opportunity: dict) -> str:
    return _normalize(opportunity.get("title"))


def _score_of(opportunity: dict) -> Optional[float]:
    raw = opportunity.get("confidence_score")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _signal_significance(signal_type: str) -> str:
    return SIGNIFICANCE_MAJOR if signal_type in _MAJOR_SIGNAL_CATEGORIES else SIGNIFICANCE_MINOR


def _detect_signal_changes(previous: list, current: list) -> tuple:
    """New and no-longer-present signals, plus the ones still standing."""
    previous_by_key = {_signal_key(signal): signal for signal in previous}
    current_by_key = {_signal_key(signal): signal for signal in current}

    appeared = [signal for key, signal in current_by_key.items() if key not in previous_by_key]
    resolved = [signal for key, signal in previous_by_key.items() if key not in current_by_key]

    # Only pair within the same signal type: a hiring signal and a
    # strategic one describing similar words are still a genuine
    # recategorisation, which is itself worth reporting.
    changes = []
    remaining_appeared, remaining_resolved = [], list(resolved)
    for signal in appeared:
        signal_type = signal.get("type") or CATEGORY_STRATEGIC
        same_type = [other for other in remaining_resolved if (other.get("type") or CATEGORY_STRATEGIC) == signal_type]
        pairs, unpaired, _ = _pair_by_similarity([signal], same_type, lambda item: item.get("title"))
        if not pairs:
            remaining_appeared.append(signal)
            continue
        _, matched, score = pairs[0]
        remaining_resolved.remove(matched)
        # The same development, reworded by the research layer. Reported as
        # an update rather than silently dropped: the wording did change,
        # and hiding that would make the history look artificially static.
        changes.append(
            DetectedChange(
                category=signal_type,
                change_type=CHANGE_UPDATED,
                title=signal.get("title") or "Signal restated",
                detail=(
                    "Restated in the latest research (previously "
                    f'"{matched.get("title")}"). Treated as the same development.'
                ),
                significance=SIGNIFICANCE_MINOR,
                source=f"signal:{signal_type}",
                previous_value=matched.get("title"),
                current_value=signal.get("title"),
            )
        )

    for signal in remaining_appeared:
        signal_type = signal.get("type") or CATEGORY_STRATEGIC
        changes.append(
            DetectedChange(
                category=signal_type,
                change_type=CHANGE_APPEARED,
                title=signal.get("title") or "New signal",
                detail=signal.get("description"),
                significance=_signal_significance(signal_type),
                source=f"signal:{signal_type}",
            )
        )

    # A signal disappearing is reported, but never as major: research
    # coverage varies between runs, so absence is weaker evidence than
    # presence and should not read as "this stopped being true".
    for signal in remaining_resolved:
        signal_type = signal.get("type") or CATEGORY_STRATEGIC
        changes.append(
            DetectedChange(
                category=signal_type,
                change_type=CHANGE_RESOLVED,
                title=signal.get("title") or "Signal no longer reported",
                detail="No longer appearing in the latest research.",
                significance=SIGNIFICANCE_MINOR,
                source=f"signal:{signal_type}",
            )
        )

    unchanged = [
        current_by_key[key].get("title") or "" for key in current_by_key.keys() & previous_by_key.keys()
    ]
    return changes, [title for title in unchanged if title]


def _detect_opportunity_changes(previous: list, current: list) -> tuple:
    """New, gone, strengthened and weakened opportunities.

    07_COMPANY_REFRESH_ENGINE.md's "Opportunity Refresh" asks for exactly
    these four transitions, and for Scout to explain why a recommendation
    changed - hence previous_value/current_value on score movements.
    """
    previous_by_key = {_opportunity_key(item): item for item in previous}
    current_by_key = {_opportunity_key(item): item for item in current}

    # Titles that appear on only one side may still be the same
    # opportunity reworded. Pairing those first matters more here than for
    # signals: a new opportunity is reported as major, so an unmatched
    # rewording would announce a significant new pursuit that does not
    # exist.
    appeared_only = [item for key, item in current_by_key.items() if key not in previous_by_key]
    resolved_only = [item for key, item in previous_by_key.items() if key not in current_by_key]
    reworded_pairs, genuinely_new, genuinely_gone = _pair_by_similarity(
        appeared_only, resolved_only, lambda item: item.get("title")
    )

    changes = []
    for current_item, previous_item, _score in reworded_pairs:
        title = current_item.get("title") or "Untitled opportunity"
        old_score, new_score = _score_of(previous_item), _score_of(current_item)
        detail = (
            "Restated in the latest analysis (previously "
            f'"{previous_item.get("title")}"). Treated as the same opportunity.'
        )
        change_type = CHANGE_UPDATED
        significance = SIGNIFICANCE_MINOR
        # previous_value/current_value describe whatever actually moved, so
        # a pure rewording shows the two titles rather than two identical
        # scores - which would read as a score change that did not happen.
        previous_value, current_value = previous_item.get("title"), title
        # A rewording can also carry a real score move; report the move,
        # since that is the part with commercial meaning.
        if old_score is not None and new_score is not None and abs(new_score - old_score) > MINIMUM_SCORE_DELTA:
            strengthened = new_score > old_score
            change_type = CHANGE_STRENGTHENED if strengthened else CHANGE_WEAKENED
            significance = SIGNIFICANCE_MAJOR if strengthened else SIGNIFICANCE_MINOR
            detail = (
                f"Confidence {'rose' if strengthened else 'fell'} from {old_score:.2f} to "
                f"{new_score:.2f}. Restated from \"{previous_item.get('title')}\"."
            )
            previous_value, current_value = f"{old_score:.2f}", f"{new_score:.2f}"
        changes.append(
            DetectedChange(
                category=CATEGORY_OPPORTUNITY,
                change_type=change_type,
                title=title,
                detail=detail,
                significance=significance,
                source="opportunity",
                previous_value=previous_value,
                current_value=current_value,
            )
        )

    for opportunity in genuinely_new:
        changes.append(
            DetectedChange(
                category=CATEGORY_OPPORTUNITY,
                change_type=CHANGE_APPEARED,
                title=opportunity.get("title") or "Untitled opportunity",
                detail="New opportunity identified in this refresh.",
                significance=SIGNIFICANCE_MAJOR,
                source="opportunity",
            )
        )

    for key, opportunity in current_by_key.items():
        title = opportunity.get("title") or "Untitled opportunity"
        if key not in previous_by_key:
            continue

        old_score = _score_of(previous_by_key[key])
        new_score = _score_of(opportunity)
        if old_score is None or new_score is None:
            continue
        delta = new_score - old_score
        if abs(delta) <= MINIMUM_SCORE_DELTA:
            continue
        strengthened = delta > 0
        changes.append(
            DetectedChange(
                category=CATEGORY_OPPORTUNITY,
                change_type=CHANGE_STRENGTHENED if strengthened else CHANGE_WEAKENED,
                title=title,
                detail=(
                    f"Confidence {'rose' if strengthened else 'fell'} "
                    f"from {old_score:.2f} to {new_score:.2f}."
                ),
                significance=SIGNIFICANCE_MAJOR if strengthened else SIGNIFICANCE_MINOR,
                source="opportunity",
                previous_value=f"{old_score:.2f}",
                current_value=f"{new_score:.2f}",
            )
        )

    for opportunity in genuinely_gone:
        changes.append(
            DetectedChange(
                category=CATEGORY_OPPORTUNITY,
                change_type=CHANGE_RESOLVED,
                title=opportunity.get("title") or "Untitled opportunity",
                detail="No longer surfaced by the latest analysis.",
                significance=SIGNIFICANCE_MINOR,
                source="opportunity",
            )
        )

    unchanged = [
        current_by_key[key].get("title") or ""
        for key in current_by_key.keys() & previous_by_key.keys()
    ]
    return changes, [title for title in unchanged if title]


def _detect_capability_changes(previous: list, current: list) -> list:
    """Capabilities newly aligned with, or no longer aligned with.

    A shift here is a shift in *why* Innominds is relevant to this
    company, which is why a new alignment is treated as major.
    """
    previous_set = {_normalize(name) for name in previous}
    current_names = {_normalize(name): name for name in current}

    changes = []
    for key, name in current_names.items():
        if key not in previous_set:
            changes.append(
                DetectedChange(
                    category=CATEGORY_CAPABILITY,
                    change_type=CHANGE_APPEARED,
                    title=name,
                    detail="Newly aligned Innominds capability.",
                    significance=SIGNIFICANCE_MAJOR,
                    source="capability_match",
                )
            )
    for name in previous:
        if _normalize(name) not in current_names:
            changes.append(
                DetectedChange(
                    category=CATEGORY_CAPABILITY,
                    change_type=CHANGE_RESOLVED,
                    title=name,
                    detail="No longer among the matched capabilities.",
                    significance=SIGNIFICANCE_MINOR,
                    source="capability_match",
                )
            )
    return changes


def _detect_executive_changes(previous: Optional[list], current: Optional[list]) -> list:
    """People joining, leaving, and changing title (V3 Enhancements Phase 4).

    Leadership movement is among the strongest buying signals a company
    emits - a new CTO reorganises priorities, and a departure stalls
    whatever the previous one sponsored - so an arrival or departure at
    any level is major, matching how CATEGORY_LEADERSHIP signals are
    already treated.

    **Matched on name, not title.** Unlike signals and opportunities,
    whose titles are LLM prose and need the similarity machinery above, a
    person's name is close to a stable identifier across runs. Applying
    similarity matching here would be actively wrong: "David Chen" and
    "Daniel Chen" share most of their tokens and are two people.

    **A NULL previous list means "unknown", not "nobody".** Snapshots
    captured before this phase have no executives column, and reporting
    every executive as newly arrived on the first post-upgrade run would
    manufacture a wave of leadership changes that never happened.
    """
    if previous is None or current is None:
        return []

    def by_name(entries):
        return {
            _normalize(entry.get("name")): entry
            for entry in entries or []
            if _normalize(entry.get("name"))
        }

    previous_by_name = by_name(previous)
    current_by_name = by_name(current)

    changes = []
    for key, entry in current_by_name.items():
        if key not in previous_by_name:
            title = entry.get("title")
            changes.append(
                DetectedChange(
                    category=CATEGORY_LEADERSHIP,
                    change_type=CHANGE_APPEARED,
                    title=entry.get("name"),
                    detail=f"Newly identified{f' as {title}' if title else ''}.",
                    significance=SIGNIFICANCE_MAJOR,
                    source="executive",
                    current_value=title,
                )
            )
            continue

        old_title = previous_by_name[key].get("title")
        new_title = entry.get("title")
        if _normalize(old_title) != _normalize(new_title):
            changes.append(
                DetectedChange(
                    category=CATEGORY_LEADERSHIP,
                    change_type=CHANGE_UPDATED,
                    title=entry.get("name"),
                    detail=f"Title changed from '{old_title or 'not recorded'}' to '{new_title or 'not recorded'}'.",
                    significance=SIGNIFICANCE_MAJOR,
                    source="executive",
                    previous_value=old_title,
                    current_value=new_title,
                )
            )

    for key, entry in previous_by_name.items():
        if key not in current_by_name:
            changes.append(
                DetectedChange(
                    category=CATEGORY_LEADERSHIP,
                    change_type=CHANGE_RESOLVED,
                    title=entry.get("name"),
                    # Deliberately not "has left the company". Research not
                    # mentioning someone this run is weak evidence of a
                    # departure, and stating it as fact is the kind of claim
                    # a salesperson could repeat to a customer.
                    detail="No longer appearing in research for this company.",
                    significance=SIGNIFICANCE_MAJOR,
                    source="executive",
                    previous_value=entry.get("title"),
                )
            )

    return changes


def _detect_technology_changes(previous: Optional[list], current: Optional[list]) -> list:
    """Technologies newly adopted, or no longer detected (V3 Enhancements
    Phase 7B).

    **A newly adopted technology is a buying signal, which is why an
    arrival is major.** A company standing up Kubernetes between two runs
    has just created work Innominds does; before this phase Scout stored
    technologies but only ever as a current-state list, so the moment of
    adoption - the part with sales value - was invisible.

    Matched on name like executives, and for the same reason: technology
    names are proper nouns, not LLM prose, so the similarity machinery
    that signals and opportunities need would only introduce errors here.
    "Kubernetes" and "Kubeflow" share tokens and are different products.

    Disappearance is minor, not major. Research coverage varies between
    runs, so a technology dropping out is much weaker evidence than one
    appearing - the same asymmetry already applied to signals.

    NULL means "this run did not look", exactly as for executives: the
    first refresh after upgrading must not report a company's entire
    stack as newly adopted.
    """
    if previous is None or current is None:
        return []

    def by_name(entries):
        return {
            _normalize(entry.get("name")): entry
            for entry in entries or []
            if _normalize(entry.get("name"))
        }

    previous_by_name = by_name(previous)
    current_by_name = by_name(current)

    changes = []
    for key, entry in current_by_name.items():
        if key not in previous_by_name:
            category = entry.get("category")
            changes.append(
                DetectedChange(
                    category=CATEGORY_TECHNOLOGY,
                    change_type=CHANGE_APPEARED,
                    title=entry.get("name"),
                    detail=f"Newly detected in this company's stack{f' ({category})' if category else ''}.",
                    significance=SIGNIFICANCE_MAJOR,
                    source="technology",
                    current_value=category,
                )
            )

    for key, entry in previous_by_name.items():
        if key not in current_by_name:
            changes.append(
                DetectedChange(
                    category=CATEGORY_TECHNOLOGY,
                    change_type=CHANGE_RESOLVED,
                    title=entry.get("name"),
                    # Not "no longer used": research not mentioning a
                    # technology this run is weak evidence it was dropped.
                    detail="No longer appearing in research for this company.",
                    significance=SIGNIFICANCE_MINOR,
                    source="technology",
                    previous_value=entry.get("category"),
                )
            )

    return changes


# Profile fields worth reporting, with the labels used in the summary.
# monitoring_status is included because pausing monitoring changes what
# Scout will tell you next, which is exactly the kind of thing a user
# forgets they did.
_PROFILE_FIELDS = (
    ("industry", "Industry"),
    ("headquarters", "Headquarters"),
    ("website", "Website"),
    ("monitoring_status", "Monitoring status"),
)


def _detect_profile_changes(previous: dict, current: dict) -> list:
    changes = []
    for field_name, label in _PROFILE_FIELDS:
        old = (previous or {}).get(field_name)
        new = (current or {}).get(field_name)
        if _normalize(old) == _normalize(new):
            continue
        changes.append(
            DetectedChange(
                category=CATEGORY_PROFILE,
                change_type=CHANGE_UPDATED,
                title=f"{label} updated",
                detail=f"{label} changed from '{old or 'not set'}' to '{new or 'not set'}'.",
                significance=SIGNIFICANCE_MINOR,
                source="company_profile",
                previous_value=old,
                current_value=new,
            )
        )
    return changes


def detect_changes(previous: Optional[object], current: object) -> ChangeSet:
    """Diffs two CompanySnapshot rows and returns the meaningful changes.

    `previous` may be None, which is the first-refresh case: there is no
    baseline, so nothing is reported as new. This matters - without the
    guard, a company's first analysis would announce every single signal
    and opportunity as a change, which is noise precisely when the user
    has the least context to filter it.

    Ordering is major-first, then by category, so a caller that renders
    the list unmodified leads with what matters. Within a significance
    band the order is stable, so the same diff always renders the same
    way.
    """
    if previous is None:
        return ChangeSet(changes=[], unchanged=[], is_first_snapshot=True)

    signal_changes, signals_unchanged = _detect_signal_changes(
        previous.signals or [], current.signals or []
    )
    opportunity_changes, opportunities_unchanged = _detect_opportunity_changes(
        previous.opportunities or [], current.opportunities or []
    )
    capability_changes = _detect_capability_changes(
        previous.capabilities or [], current.capabilities or []
    )
    profile_changes = _detect_profile_changes(previous.profile or {}, current.profile or {})
    # Passed through without the `or []` the others use: None and [] mean
    # different things for executives - see _detect_executive_changes.
    executive_changes = _detect_executive_changes(
        getattr(previous, "executives", None), getattr(current, "executives", None)
    )
    technology_changes = _detect_technology_changes(
        getattr(previous, "technologies", None), getattr(current, "technologies", None)
    )

    changes = (
        signal_changes
        + opportunity_changes
        + capability_changes
        + profile_changes
        + executive_changes
        + technology_changes
    )
    changes.sort(key=lambda change: (0 if change.significance == SIGNIFICANCE_MAJOR else 1, change.category))

    return ChangeSet(
        changes=changes,
        unchanged=signals_unchanged + opportunities_unchanged,
        is_first_snapshot=False,
    )
