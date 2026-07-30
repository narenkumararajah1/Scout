"""Executive Relationship Intelligence (V3 Enhancements Phase 4 -
06_LINKEDIN_INTELLIGENCE.md, roadmap Phase 4).

That roadmap phase's success criterion is that Scout "recommends not only
who to contact, but why they matter and the strongest path into the
organization". This module is the "why they matter" and the ranking; the
people themselves now arrive via
backend/orchestration/stages.py::ExecutivePersistenceStage.

**Deliberately contains no LLM call**, for the same reason
backend/ai/change_detection.py doesn't: 01_VISION.md puts "evidence over
assumptions" and "explainability over black-box scoring" ahead of
automation. A seniority tier derived from the words in a job title can be
shown to a user as the rule that produced it and always yields the same
answer for the same title. A model asked "how senior is this person"
cannot, and would cost a call per executive per analysis.

That matters more here than elsewhere: this ranking tells a salesperson
who to approach first. If Scout cannot say *why* it put someone at the
top, the recommendation is not actionable - the user has to redo the
judgement themselves to trust it.

**Titles are matched on word boundaries, not substrings.** "Director" is
a substring of nothing dangerous, but "CTO" appears inside "CTO Office"
and - the case that actually breaks naive matching - "VP" appears inside
"VPN", "ceo" inside "receovery" typos, and "head" inside "headcount".
Matching tokens avoids a whole class of silent misclassification that
would be invisible in the UI, because a wrong tier still renders as a
perfectly plausible label.

06_LINKEDIN_INTELLIGENCE.md asks for organizational mapping including
"executive hierarchy, business units, key stakeholders, decision makers,
technical influencers". What is honestly derivable from a title is the
*tier* and the *function* - not reporting lines, which no source Scout
has access to actually states. The doc's own Ethical and Technical
Considerations section requires exactly this distinction: "If certain
information cannot be obtained through supported APIs, Scout should
clearly indicate those limitations rather than attempting unsupported
collection methods." So this module derives what titles support and
stops; `is_inferred` is on every result to keep that visible downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from backend.integrations.linkedin_client import resolve_profile_url

# Seniority tiers, most senior first. The rank is what the ranking sorts
# on; the label is what a user reads.
TIER_FOUNDER = "founder"
TIER_C_SUITE = "c_suite"
TIER_EXECUTIVE = "executive"
TIER_DIRECTOR = "director"
TIER_MANAGER = "manager"
TIER_INDIVIDUAL = "individual"
TIER_UNKNOWN = "unknown"

_TIER_RANK = {
    TIER_FOUNDER: 0,
    TIER_C_SUITE: 1,
    TIER_EXECUTIVE: 2,
    TIER_DIRECTOR: 3,
    TIER_MANAGER: 4,
    TIER_INDIVIDUAL: 5,
    TIER_UNKNOWN: 6,
}

_TIER_LABELS = {
    TIER_FOUNDER: "Founder / Owner",
    TIER_C_SUITE: "C-Suite",
    TIER_EXECUTIVE: "Executive (SVP/VP)",
    TIER_DIRECTOR: "Director",
    TIER_MANAGER: "Manager",
    TIER_INDIVIDUAL: "Individual Contributor",
    TIER_UNKNOWN: "Unknown",
}

# Ordered most senior first: the first tier whose markers appear in a
# title wins, so "VP of Engineering, Office of the CTO" reads as C-suite
# only if it genuinely carries a C-suite token.
_TIER_MARKERS = (
    (TIER_FOUNDER, ("founder", "co-founder", "cofounder", "owner", "proprietor")),
    (
        TIER_C_SUITE,
        (
            "ceo", "cto", "cio", "cfo", "coo", "cmo", "ciso", "cdo", "cpo", "chro", "cro",
            "chief", "president", "chairman", "chairwoman", "chairperson", "managing director",
        ),
    ),
    (TIER_EXECUTIVE, ("svp", "evp", "avp", "vp", "vice president", "partner", "principal")),
    (TIER_DIRECTOR, ("director", "head")),
    (TIER_MANAGER, ("manager", "lead", "supervisor", "foreman")),
    (
        TIER_INDIVIDUAL,
        ("engineer", "developer", "architect", "analyst", "scientist", "designer", "consultant", "specialist"),
    ),
)

# Functional areas. 06_LINKEDIN_INTELLIGENCE.md calls these "business
# units"; a title reliably indicates the function even when it says
# nothing about the org chart.
_DEPARTMENT_MARKERS = (
    # The three specific technical areas come before the general
    # "Technology" bucket, because first match wins and Technology's
    # markers ("engineering", "platform") otherwise swallow them: "VP of
    # Data Engineering" belongs in Data & AI, not filed alongside every
    # other engineering leader. That distinction is the whole point of the
    # grouping for a salesperson deciding who owns a data-platform deal.
    ("Data & AI", ("data", "ai", "artificial intelligence", "machine learning", "ml", "analytics",
                   "cdo", "scientist", "science")),
    ("Security", ("security", "ciso", "infosec", "cyber", "risk", "compliance", "privacy")),
    ("Product", ("product", "cpo", "design", "ux", "user experience")),
    ("Technology", ("cto", "cio", "technology", "technical", "engineering", "engineer", "software",
                    "platform", "infrastructure", "architecture", "architect", "devops", "sre")),
    ("Finance", ("finance", "financial", "cfo", "accounting", "treasury", "controller", "audit")),
    ("Sales & Marketing", ("sales", "marketing", "cmo", "revenue", "cro", "growth", "commercial",
                           "business development", "partnerships")),
    ("Operations", ("operations", "operating", "coo", "supply chain", "logistics", "manufacturing")),
    ("People", ("people", "human resources", "hr", "chro", "talent", "recruiting", "culture")),
    ("Legal", ("legal", "counsel", "general counsel", "compliance officer")),
    # Last on purpose. A CEO or COO has a function - running the company -
    # but every specific area above should claim its own leader first, so
    # a CTO maps to Technology rather than here. Without this entry the
    # most senior person at a company lands in "Unspecified", which reads
    # as though Scout failed to classify them.
    (
        "General Management",
        ("ceo", "chief executive", "president", "chairman", "chairwoman", "chairperson",
         "general manager", "managing director", "founder", "owner"),
    ),
)

# Which departments Scout's own offering speaks to. Used only to explain
# a ranking, never to hide anyone: a CFO still appears, just with a
# different stated reason than a VP of Platform Engineering.
_TECHNICAL_DEPARTMENTS = frozenset({"Technology", "Data & AI", "Security", "Product"})

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass
class ExecutiveProfile:
    """One executive, with everything derivable from their title.

    `is_inferred` is always True for tier and department - they are read
    off a job title, not stated by any source - so any surface that
    displays them can say so rather than presenting a guess as a fact.
    """

    executive_id: str
    name: str
    title: Optional[str] = None
    seniority_tier: str = TIER_UNKNOWN
    seniority_label: str = _TIER_LABELS[TIER_UNKNOWN]
    department: Optional[str] = None
    is_decision_maker: bool = False
    is_technical: bool = False
    is_inferred: bool = True
    linkedin_url: Optional[str] = None

    @property
    def rank(self) -> int:
        return _TIER_RANK.get(self.seniority_tier, _TIER_RANK[TIER_UNKNOWN])


@dataclass
class PathCandidate:
    """An executive plus the case for approaching them first."""

    profile: ExecutiveProfile
    score: float = 0.0
    reasons: list = field(default_factory=list)


def _title_tokens(title: Optional[str]) -> frozenset:
    return frozenset(_TOKEN_PATTERN.findall((title or "").lower()))


def _contains_marker(title: Optional[str], marker: str, tokens: frozenset) -> bool:
    """Word-boundary match. Multi-word markers ("vice president") fall back
    to a substring check on the normalised title, since they cannot appear
    accidentally inside a single word the way "vp" can.
    """
    if " " in marker:
        return marker in (title or "").lower()
    return marker in tokens


def derive_seniority(title: Optional[str]) -> str:
    tokens = _title_tokens(title)
    if not tokens:
        return TIER_UNKNOWN
    for tier, markers in _TIER_MARKERS:
        if any(_contains_marker(title, marker, tokens) for marker in markers):
            return tier
    return TIER_UNKNOWN


def derive_department(title: Optional[str]) -> Optional[str]:
    tokens = _title_tokens(title)
    if not tokens:
        return None
    for department, markers in _DEPARTMENT_MARKERS:
        if any(_contains_marker(title, marker, tokens) for marker in markers):
            return department
    return None


def seniority_label(tier: str) -> str:
    return _TIER_LABELS.get(tier, _TIER_LABELS[TIER_UNKNOWN])


def build_profile(executive) -> ExecutiveProfile:
    """Derives everything a title supports for one Executive row."""
    tier = derive_seniority(executive.title)
    department = executive.department or derive_department(executive.title)
    return ExecutiveProfile(
        executive_id=executive.id,
        name=executive.name,
        title=executive.title,
        seniority_tier=tier,
        seniority_label=seniority_label(tier),
        department=department,
        is_decision_maker=tier in (TIER_FOUNDER, TIER_C_SUITE, TIER_EXECUTIVE),
        is_technical=department in _TECHNICAL_DEPARTMENTS,
        linkedin_url=getattr(executive, "linkedin_url", None),
    )


def build_org_map(executives: list) -> dict:
    """Groups executives by department, each ordered most senior first.

    This is 06_LINKEDIN_INTELLIGENCE.md's "organizational mapping" at the
    level a title actually supports: who works in which function and how
    senior they are. It is explicitly *not* a reporting hierarchy - no
    source Scout reads states who reports to whom, and inventing edges
    would be exactly the unsupported inference that document's Ethical and
    Technical Considerations section rules out.
    """
    profiles = [build_profile(executive) for executive in executives]
    grouped: dict = {}
    for profile in profiles:
        grouped.setdefault(profile.department or "Unspecified", []).append(profile)
    for group in grouped.values():
        group.sort(key=lambda profile: (profile.rank, profile.name))
    return dict(sorted(grouped.items(), key=lambda item: (item[0] == "Unspecified", item[0])))


def rank_paths(executives: list, *, focus_departments: Optional[list] = None) -> list:
    """Ranks who to approach first, with the reasons stated.

    Scoring is intentionally small and legible rather than tuned: seniority
    dominates, relevance to the opportunity's subject matter adjusts, and
    every contribution appends the sentence that justifies it. A user can
    read the reasons and disagree, which is the point - 01_VISION.md's
    "explainability over black-box scoring".

    `focus_departments` biases toward the functions an opportunity is
    actually about, so a data-platform opportunity surfaces the CDO ahead
    of the CFO without ever removing the CFO from the list.
    """
    focus = set(focus_departments or [])
    candidates = []

    for executive in executives:
        profile = build_profile(executive)
        score = 0.0
        reasons = []

        if profile.seniority_tier in (TIER_FOUNDER, TIER_C_SUITE):
            score += 3.0
            reasons.append(f"{profile.seniority_label} - typically holds budget authority.")
        elif profile.seniority_tier == TIER_EXECUTIVE:
            score += 2.0
            reasons.append(f"{profile.seniority_label} - usually owns the initiative and its budget line.")
        elif profile.seniority_tier == TIER_DIRECTOR:
            score += 1.0
            reasons.append("Director - close enough to delivery to shape requirements.")
        elif profile.seniority_tier == TIER_MANAGER:
            score += 0.5
            reasons.append("Manager - useful for discovery, rarely the decision maker.")

        if profile.department:
            if profile.department in focus:
                score += 2.0
                reasons.append(f"Owns {profile.department}, which is what this opportunity is about.")
            elif profile.is_technical:
                score += 0.5
                reasons.append(f"Technical leadership ({profile.department}) - likely an evaluator.")

        if not reasons:
            # Split rather than one catch-all sentence: a title can name a
            # function without indicating rank ("General Counsel"), and
            # telling a user Scout found no function when it found Legal
            # would be simply untrue.
            reasons.append(
                f"Works in {profile.department}, but the title does not indicate seniority."
                if profile.department
                else "Title indicates neither seniority nor function; treat as unverified."
            )

        candidates.append(PathCandidate(profile=profile, score=score, reasons=reasons))

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.profile.rank, candidate.profile.name))
    return candidates


def build_executive_overview(
    executives: list, company_name: Optional[str] = None, *, focus_departments: Optional[list] = None
) -> dict:
    """The whole executive picture for one company, in one payload.

    Returns the flat list, the org map and the ranked paths together
    because they are three orderings of the same rows: fetching them
    separately would re-query the same data and let two views drift apart
    if the derivation rules ever changed between requests.
    """
    responses = {executive.id: to_response(executive, company_name) for executive in executives}

    org_map = [
        {"department": department, "executives": [responses[profile.executive_id] for profile in group]}
        for department, group in build_org_map(executives).items()
    ]
    paths = [
        {
            "executive": responses[candidate.profile.executive_id],
            "score": candidate.score,
            "reasons": candidate.reasons,
        }
        for candidate in rank_paths(executives, focus_departments=focus_departments)
    ]

    return {
        "executives": [responses[executive.id] for executive in executives],
        "org_map": org_map,
        "paths": paths,
        "decision_maker_count": sum(1 for r in responses.values() if r["is_decision_maker"]),
    }


def to_response(executive, company_name: Optional[str] = None) -> dict:
    """One Executive as the API shape, including the derived fields.

    Composed here rather than in the router so every surface that returns
    an executive - the company endpoint, the org map, the path ranking -
    produces an identical object. A user comparing the same person across
    two views must not see two different seniority labels.
    """
    profile = build_profile(executive)
    stored_url = (getattr(executive, "linkedin_url", None) or "").strip()
    return {
        "id": executive.id,
        "company_id": executive.company_id,
        "name": executive.name,
        "title": executive.title,
        "department": profile.department,
        "biography": getattr(executive, "biography", None),
        "responsibilities": getattr(executive, "responsibilities", None),
        "business_priorities": getattr(executive, "business_priorities", None),
        "technology_focus": getattr(executive, "technology_focus", None),
        "confidence_score": getattr(executive, "confidence_score", None),
        "seniority_tier": profile.seniority_tier,
        "seniority_label": profile.seniority_label,
        "is_decision_maker": profile.is_decision_maker,
        "is_technical": profile.is_technical,
        "is_inferred": True,
        "linkedin_url": resolve_profile_url(executive, company_name),
        "profile_url_is_search": not stored_url,
    }
