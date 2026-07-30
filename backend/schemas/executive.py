"""Executive response schemas (V3 Enhancements Phase 4 -
06_LINKEDIN_INTELLIGENCE.md).

Everything here beyond the stored columns is *derived* at response time by
backend/services/executive_relationship_service.py rather than persisted.
That is deliberate: seniority and department are read off a job title, so
storing them would freeze an inference the moment the derivation rules
improved, and would need a migration plus a backfill every time the title
vocabulary changed. Derivation is a pure function over a string and costs
nothing to run per request.

`is_inferred` and `profile_url_is_search` exist so a surface can be honest
about what it is showing. Both correspond to things the docs explicitly
require Scout to be careful about: that document's Ethical and Technical
Considerations section demands limitations be indicated rather than papered
over, and 01_VISION.md puts explainability ahead of polish.
"""

from typing import Optional

from pydantic import BaseModel


class ExecutiveOut(BaseModel):
    id: str
    company_id: str
    name: str
    title: Optional[str] = None
    department: Optional[str] = None
    biography: Optional[str] = None
    responsibilities: Optional[list] = None
    business_priorities: Optional[list] = None
    technology_focus: Optional[list] = None
    confidence_score: Optional[float] = None

    # Derived, not stored - see module docstring.
    seniority_tier: str
    seniority_label: str
    is_decision_maker: bool
    is_technical: bool
    # True whenever seniority/department came from the title rather than a
    # source that stated them, which today is always.
    is_inferred: bool = True

    linkedin_url: Optional[str] = None
    # True when linkedin_url is a people-search link Scout constructed
    # rather than a real profile URL it holds, so the UI can label it
    # "Find on LinkedIn" instead of implying a verified match.
    profile_url_is_search: bool = False

    model_config = {"from_attributes": True}


class PathCandidateOut(BaseModel):
    """One ranked route into an organisation, with the case for it.

    `reasons` is not decoration. Roadmap Phase 4's success criterion is
    that Scout says *why* someone matters, and a ranking a user cannot
    interrogate is one they have to redo themselves before trusting it.
    """

    executive: ExecutiveOut
    score: float
    reasons: list


class OrgMapGroupOut(BaseModel):
    """Executives in one functional area, most senior first.

    Explicitly not a reporting hierarchy: no source Scout reads states who
    reports to whom, so the grouping stops at function and seniority.
    """

    department: str
    executives: list
