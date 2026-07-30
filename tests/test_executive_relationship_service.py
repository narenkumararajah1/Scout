"""Unit tests for backend/services/executive_relationship_service.py and
backend/integrations/linkedin_client.py (V3 Enhancements Phase 4 -
Relationship Intelligence).

Both modules are pure functions over strings and plain objects - no LLM,
no database, no network - so these are ordinary unit tests, matching how
tests/test_change_detection.py covers the other deterministic engine.
"""

from backend.integrations import linkedin_client
from backend.services import executive_relationship_service as service


class FakeExecutive:
    def __init__(self, id, name, title=None, department=None, linkedin_url=None):
        self.id = id
        self.company_id = "company-1"
        self.name = name
        self.title = title
        self.department = department
        self.linkedin_url = linkedin_url
        self.biography = None
        self.responsibilities = None
        self.business_priorities = None
        self.technology_focus = None
        self.confidence_score = None


# --- Seniority ---------------------------------------------------------


def test_seniority_covers_the_common_title_shapes():
    assert service.derive_seniority("Chief Technology Officer") == service.TIER_C_SUITE
    assert service.derive_seniority("VP of Platform Engineering") == service.TIER_EXECUTIVE
    assert service.derive_seniority("Director, Data Science") == service.TIER_DIRECTOR
    assert service.derive_seniority("Engineering Manager") == service.TIER_MANAGER
    assert service.derive_seniority("Senior Software Engineer") == service.TIER_INDIVIDUAL


def test_the_most_senior_marker_in_a_title_wins():
    # A founder who is also CEO is ranked as a founder, not read twice.
    assert service.derive_seniority("Co-Founder & CEO") == service.TIER_FOUNDER


def test_an_unrecognized_or_missing_title_is_unknown_rather_than_guessed():
    assert service.derive_seniority("Ninja Rockstar") == service.TIER_UNKNOWN
    assert service.derive_seniority(None) == service.TIER_UNKNOWN
    assert service.derive_seniority("") == service.TIER_UNKNOWN


def test_markers_match_whole_words_not_substrings():
    # The bug this guards: "vp" inside "VPN", "head" inside "headcount".
    # A substring match would silently misclassify both, and a wrong tier
    # still renders as a perfectly plausible label in the UI.
    assert service.derive_seniority("VPN Support Technician") != service.TIER_EXECUTIVE
    assert service.derive_seniority("Headcount Planning Analyst") != service.TIER_DIRECTOR


# --- Department --------------------------------------------------------


def test_department_is_derived_from_the_title():
    assert service.derive_department("Chief Information Security Officer") == "Security"
    assert service.derive_department("VP of Machine Learning") == "Data & AI"
    assert service.derive_department("Head of Revenue Operations") == "Sales & Marketing"


def test_a_specific_function_beats_general_management():
    # "General Management" is last in the marker list on purpose, so a
    # CTO is Technology rather than being swallowed by the C-suite catch-all.
    assert service.derive_department("Chief Technology Officer") == "Technology"
    assert service.derive_department("Chief Financial Officer") == "Finance"


def test_a_ceo_gets_a_real_department_rather_than_unspecified():
    # Regression: the most senior person at a company used to land in
    # "Unspecified", which reads as a classification failure.
    assert service.derive_department("Chief Executive Officer") == "General Management"


def test_a_stored_department_is_preferred_over_the_derived_one():
    executive = FakeExecutive("1", "Ann Lee", "VP Engineering", department="Corporate Strategy")

    assert service.build_profile(executive).department == "Corporate Strategy"


# --- Org map -----------------------------------------------------------


def test_the_org_map_groups_by_department_most_senior_first():
    grouped = service.build_org_map(
        [
            FakeExecutive("1", "Junior Dev", "Software Engineer"),
            FakeExecutive("2", "Tech Chief", "Chief Technology Officer"),
            FakeExecutive("3", "Money Chief", "Chief Financial Officer"),
        ]
    )

    assert [p.name for p in grouped["Technology"]] == ["Tech Chief", "Junior Dev"]
    assert [p.name for p in grouped["Finance"]] == ["Money Chief"]


def test_unclassifiable_people_sort_last_rather_than_alphabetically():
    grouped = service.build_org_map(
        [FakeExecutive("1", "Odd One", "Ninja"), FakeExecutive("2", "Sec Lead", "Head of Security")]
    )

    assert list(grouped) == ["Security", "Unspecified"]


# --- Path ranking ------------------------------------------------------


def test_seniority_drives_the_ranking_by_default():
    ranked = service.rank_paths(
        [
            FakeExecutive("1", "IC", "Software Engineer"),
            FakeExecutive("2", "Chief", "Chief Technology Officer"),
            FakeExecutive("3", "Dir", "Director of Engineering"),
        ]
    )

    assert [c.profile.name for c in ranked] == ["Chief", "Dir", "IC"]


def test_focus_departments_lift_the_relevant_owner():
    executives = [
        FakeExecutive("1", "Finance VP", "VP of Finance"),
        FakeExecutive("2", "Data VP", "VP of Data Engineering"),
    ]

    unfocused = service.rank_paths(executives)
    focused = service.rank_paths(executives, focus_departments=["Data & AI"])

    # Equal seniority, so the default ordering is a tie broken by name;
    # the focus is what makes the relevant one first.
    assert unfocused[0].profile.name == "Data VP" or unfocused[0].score == unfocused[1].score
    assert focused[0].profile.name == "Data VP"
    assert focused[0].score > focused[1].score


def test_focus_never_removes_anyone_from_the_ranking():
    # A CFO still has to be reachable on a data-platform deal - the
    # ranking reorders, it does not filter.
    ranked = service.rank_paths(
        [FakeExecutive("1", "Money", "Chief Financial Officer"), FakeExecutive("2", "Data", "VP of Data")],
        focus_departments=["Data & AI"],
    )

    assert {c.profile.name for c in ranked} == {"Money", "Data"}


def test_every_candidate_carries_a_stated_reason():
    # The phase's success criterion is that Scout says *why* someone
    # matters. A ranking with no reason is one a user has to redo.
    ranked = service.rank_paths([FakeExecutive("1", "Nobody", "Ninja Rockstar")])

    assert ranked[0].reasons
    assert "unverified" in ranked[0].reasons[0]


def test_a_known_function_without_a_known_rank_says_so_accurately():
    # Regression: this used to claim the title indicated no function, when
    # it had in fact identified Legal.
    ranked = service.rank_paths([FakeExecutive("1", "Counsel", "General Counsel")])

    assert "Legal" in ranked[0].reasons[0]


def test_the_ranking_is_deterministic_for_equal_scores():
    executives = [FakeExecutive("1", "Zoe", "Director"), FakeExecutive("2", "Abe", "Director")]

    assert [c.profile.name for c in service.rank_paths(executives)] == ["Abe", "Zoe"]


# --- Overview payload --------------------------------------------------


def test_the_overview_returns_the_same_object_in_every_view():
    executives = [FakeExecutive("1", "Chief", "Chief Technology Officer")]

    overview = service.build_executive_overview(executives, "Acme")

    flat = overview["executives"][0]
    from_map = overview["org_map"][0]["executives"][0]
    from_path = overview["paths"][0]["executive"]
    # Identity, not just equality: a user comparing the same person across
    # two views must never see two different seniority labels.
    assert flat is from_map is from_path


def test_decision_makers_are_counted():
    overview = service.build_executive_overview(
        [
            FakeExecutive("1", "Chief", "Chief Technology Officer"),
            FakeExecutive("2", "IC", "Software Engineer"),
        ]
    )

    assert overview["decision_maker_count"] == 1


def test_derived_fields_are_flagged_as_inferred():
    overview = service.build_executive_overview([FakeExecutive("1", "Chief", "CTO")])

    assert overview["executives"][0]["is_inferred"] is True


def test_an_empty_company_produces_an_empty_but_valid_payload():
    overview = service.build_executive_overview([])

    assert overview == {"executives": [], "org_map": [], "paths": [], "decision_maker_count": 0}


# --- LinkedIn client ---------------------------------------------------


def test_a_search_url_is_built_when_no_profile_is_stored():
    executive = FakeExecutive("1", "Jensen Huang", "CEO")

    response = service.to_response(executive, "NVIDIA")

    assert response["profile_url_is_search"] is True
    assert "Jensen+Huang" in response["linkedin_url"]
    assert "NVIDIA" in response["linkedin_url"]


def test_a_stored_profile_url_wins_and_is_not_flagged_as_a_search():
    executive = FakeExecutive("1", "Jensen Huang", "CEO", linkedin_url="https://linkedin.com/in/real")

    response = service.to_response(executive, "NVIDIA")

    assert response["linkedin_url"] == "https://linkedin.com/in/real"
    assert response["profile_url_is_search"] is False


def test_no_name_means_no_url_rather_than_a_broken_search():
    assert linkedin_client.profile_url("", "NVIDIA") is None
    assert linkedin_client.profile_url("   ") is None


async def test_the_null_client_returns_nothing_and_admits_it_is_not_live():
    # The shipped default. An empty result must mean "Scout has no
    # connection data", never "broken" - and is_live() is what lets a
    # surface say that rather than implying nobody is known.
    client = linkedin_client.NullLinkedInClient()

    assert await client.find_connections_at("NVIDIA") == []
    assert client.is_live() is False
