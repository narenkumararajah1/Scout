"""Unit tests for backend/ai/change_detection.py (V3 Enhancements
Phase 2 - the Company Refresh Engine's diff).

No database and no LLM: detection is a pure function of two snapshots, so
these are ordinary unit tests rather than Postgres-gated ones. A simple
stand-in stands for CompanySnapshot because detect_changes() only reads
the four content attributes.
"""

from types import SimpleNamespace

from backend.ai.change_detection import (
    CATEGORY_CAPABILITY,
    CATEGORY_LEADERSHIP,
    CATEGORY_OPPORTUNITY,
    CATEGORY_PROFILE,
    CHANGE_APPEARED,
    CHANGE_RESOLVED,
    CHANGE_STRENGTHENED,
    CHANGE_UPDATED,
    CHANGE_WEAKENED,
    MINIMUM_SCORE_DELTA,
    SIGNIFICANCE_MAJOR,
    SIGNIFICANCE_MINOR,
    detect_changes,
)


def _snapshot(signals=None, opportunities=None, capabilities=None, profile=None, executives=None):
    # `executives` deliberately keeps its None rather than defaulting to
    # [] like the others: None means "this run did not look at people",
    # which the detector must treat differently from "looked, found none"
    # (V3 Enhancements Phase 4).
    return SimpleNamespace(
        signals=signals or [],
        opportunities=opportunities or [],
        capabilities=capabilities or [],
        profile=profile or {},
        executives=executives,
    )


def _signal(signal_type, title, description=None):
    return {"type": signal_type, "title": title, "description": description}


def _opportunity(title, confidence_score=None, priority=None):
    return {
        "title": title,
        "confidence_score": confidence_score,
        "priority": priority,
        "recommended_services": [],
    }


# --- First refresh -----------------------------------------------------


def test_the_first_snapshot_reports_no_changes():
    # Without this guard a company's very first analysis would announce
    # every signal and opportunity it found as "new".
    current = _snapshot(
        signals=[_signal("leadership", "Appointed a new CTO")],
        opportunities=[_opportunity("Cloud migration", 0.8)],
    )

    result = detect_changes(None, current)

    assert result.is_first_snapshot is True
    assert result.changes == []
    assert result.has_changes is False


# --- Signals -----------------------------------------------------------


def test_a_new_signal_is_detected_and_attributed():
    previous = _snapshot(signals=[_signal("hiring", "Hiring platform engineers")])
    current = _snapshot(
        signals=[
            _signal("hiring", "Hiring platform engineers"),
            _signal("leadership", "Appointed a new CTO", "Former AWS VP joins as CTO."),
        ]
    )

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    change = changes[0]
    assert change.category == CATEGORY_LEADERSHIP
    assert change.change_type == CHANGE_APPEARED
    assert change.title == "Appointed a new CTO"
    assert change.detail == "Former AWS VP joins as CTO."
    assert change.source == "signal:leadership"


def test_leadership_and_strategic_signals_are_major_while_hiring_is_minor():
    previous = _snapshot()
    current = _snapshot(
        signals=[
            _signal("leadership", "New CTO"),
            _signal("strategic", "Acquired a competitor"),
            _signal("hiring", "Hiring cloud engineers"),
            _signal("technology", "Adopted Kubernetes"),
        ]
    )

    by_title = {change.title: change for change in detect_changes(previous, current).changes}

    assert by_title["New CTO"].significance == SIGNIFICANCE_MAJOR
    assert by_title["Acquired a competitor"].significance == SIGNIFICANCE_MAJOR
    assert by_title["Hiring cloud engineers"].significance == SIGNIFICANCE_MINOR
    assert by_title["Adopted Kubernetes"].significance == SIGNIFICANCE_MINOR


def test_the_same_signal_retitled_only_by_case_and_spacing_is_not_a_change():
    # These strings come from an LLM and vary run to run; without
    # normalisation the same development would be reported as both
    # resolved and appeared on every refresh.
    previous = _snapshot(signals=[_signal("technology", "Migrating to AWS")])
    current = _snapshot(signals=[_signal("technology", "  migrating to   aws ")])

    result = detect_changes(previous, current)

    assert result.changes == []
    assert result.unchanged == ["  migrating to   aws "]


def test_the_same_title_under_a_different_signal_type_is_a_change():
    previous = _snapshot(signals=[_signal("hiring", "Expanding the AI team")])
    current = _snapshot(signals=[_signal("strategic", "Expanding the AI team")])

    changes = detect_changes(previous, current).changes

    assert {(change.change_type, change.category) for change in changes} == {
        (CHANGE_APPEARED, "strategic"),
        (CHANGE_RESOLVED, "hiring"),
    }


def test_a_disappearing_signal_is_reported_but_never_as_major():
    # Research coverage varies between runs, so absence is weaker
    # evidence than presence and must not read as "this stopped".
    previous = _snapshot(signals=[_signal("leadership", "New CTO")])
    current = _snapshot()

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].change_type == CHANGE_RESOLVED
    assert changes[0].significance == SIGNIFICANCE_MINOR


# --- Opportunities -----------------------------------------------------


def test_a_new_opportunity_is_major():
    previous = _snapshot(opportunities=[_opportunity("Cloud migration", 0.7)])
    current = _snapshot(
        opportunities=[_opportunity("Cloud migration", 0.7), _opportunity("AI platform build", 0.6)]
    )

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].category == CATEGORY_OPPORTUNITY
    assert changes[0].change_type == CHANGE_APPEARED
    assert changes[0].title == "AI platform build"
    assert changes[0].significance == SIGNIFICANCE_MAJOR


def test_a_strengthened_opportunity_reports_both_scores():
    previous = _snapshot(opportunities=[_opportunity("Cloud migration", 0.5)])
    current = _snapshot(opportunities=[_opportunity("Cloud migration", 0.9)])

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].change_type == CHANGE_STRENGTHENED
    assert changes[0].significance == SIGNIFICANCE_MAJOR
    assert changes[0].previous_value == "0.50"
    assert changes[0].current_value == "0.90"
    assert "0.50" in changes[0].detail and "0.90" in changes[0].detail


def test_a_weakened_opportunity_is_reported_as_minor():
    previous = _snapshot(opportunities=[_opportunity("Cloud migration", 0.9)])
    current = _snapshot(opportunities=[_opportunity("Cloud migration", 0.4)])

    changes = detect_changes(previous, current).changes

    assert changes[0].change_type == CHANGE_WEAKENED
    assert changes[0].significance == SIGNIFICANCE_MINOR


def test_score_drift_at_or_below_the_threshold_is_not_reported():
    # LLM-assigned scores wobble between runs on identical inputs;
    # reporting that would describe the model, not the customer.
    previous = _snapshot(opportunities=[_opportunity("Cloud migration", 0.50)])
    current = _snapshot(opportunities=[_opportunity("Cloud migration", 0.50 + MINIMUM_SCORE_DELTA)])

    assert detect_changes(previous, current).changes == []


def test_score_movement_just_past_the_threshold_is_reported():
    previous = _snapshot(opportunities=[_opportunity("Cloud migration", 0.50)])
    current = _snapshot(opportunities=[_opportunity("Cloud migration", 0.50 + MINIMUM_SCORE_DELTA + 0.01)])

    assert len(detect_changes(previous, current).changes) == 1


def test_a_missing_score_on_either_side_is_skipped_rather_than_guessed():
    previous = _snapshot(opportunities=[_opportunity("Cloud migration", None)])
    current = _snapshot(opportunities=[_opportunity("Cloud migration", 0.9)])

    assert detect_changes(previous, current).changes == []


def test_a_non_numeric_score_does_not_raise():
    previous = _snapshot(opportunities=[{"title": "Cloud migration", "confidence_score": "high"}])
    current = _snapshot(opportunities=[{"title": "Cloud migration", "confidence_score": 0.9}])

    assert detect_changes(previous, current).changes == []


def test_a_dropped_opportunity_is_reported():
    previous = _snapshot(opportunities=[_opportunity("Cloud migration", 0.7)])
    current = _snapshot()

    changes = detect_changes(previous, current).changes

    assert changes[0].change_type == CHANGE_RESOLVED
    assert changes[0].significance == SIGNIFICANCE_MINOR


# --- Capabilities and profile ------------------------------------------


def test_a_newly_matched_capability_is_major():
    previous = _snapshot(capabilities=["Cloud-Native Platform Engineering"])
    current = _snapshot(capabilities=["Cloud-Native Platform Engineering", "Applied AI"])

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].category == CATEGORY_CAPABILITY
    assert changes[0].title == "Applied AI"
    assert changes[0].significance == SIGNIFICANCE_MAJOR


def test_profile_edits_are_reported_with_both_values():
    previous = _snapshot(profile={"industry": "Retail", "headquarters": "Austin"})
    current = _snapshot(profile={"industry": "Healthcare", "headquarters": "Austin"})

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].category == CATEGORY_PROFILE
    assert changes[0].change_type == CHANGE_UPDATED
    assert changes[0].previous_value == "Retail"
    assert changes[0].current_value == "Healthcare"


def test_setting_a_previously_empty_profile_field_is_reported_readably():
    previous = _snapshot(profile={"industry": None})
    current = _snapshot(profile={"industry": "Healthcare"})

    changes = detect_changes(previous, current).changes

    assert "not set" in changes[0].detail


def test_untracked_profile_fields_are_ignored():
    previous = _snapshot(profile={"industry": "Retail", "internal_note": "a"})
    current = _snapshot(profile={"industry": "Retail", "internal_note": "b"})

    assert detect_changes(previous, current).changes == []


# --- Ordering and aggregate shape --------------------------------------


def test_major_changes_sort_ahead_of_minor_ones():
    previous = _snapshot()
    current = _snapshot(
        signals=[_signal("hiring", "Hiring engineers"), _signal("leadership", "New CTO")],
        opportunities=[_opportunity("AI platform", 0.8)],
    )

    result = detect_changes(previous, current)

    significances = [change.significance for change in result.changes]
    assert significances == sorted(significances, key=lambda s: 0 if s == SIGNIFICANCE_MAJOR else 1)
    assert result.major_changes and all(c.significance == SIGNIFICANCE_MAJOR for c in result.major_changes)


def test_an_identical_snapshot_reports_nothing_changed_but_lists_what_held():
    signals = [_signal("technology", "Adopted Kubernetes")]
    opportunities = [_opportunity("Cloud migration", 0.7)]
    previous = _snapshot(signals=signals, opportunities=opportunities)
    current = _snapshot(signals=list(signals), opportunities=list(opportunities))

    result = detect_changes(previous, current)

    assert result.changes == []
    assert result.has_changes is False
    assert sorted(result.unchanged) == ["Adopted Kubernetes", "Cloud migration"]


def test_changes_serialize_to_plain_dicts_for_storage():
    previous = _snapshot()
    current = _snapshot(signals=[_signal("leadership", "New CTO")])

    payload = detect_changes(previous, current).to_dicts()

    assert payload[0]["title"] == "New CTO"
    assert payload[0]["significance"] == SIGNIFICANCE_MAJOR
    assert set(payload[0]) == {
        "category",
        "change_type",
        "title",
        "detail",
        "significance",
        "source",
        "previous_value",
        "current_value",
    }


def test_empty_snapshots_on_both_sides_are_handled():
    assert detect_changes(_snapshot(), _snapshot()).changes == []


def test_none_valued_collections_are_treated_as_empty():
    previous = SimpleNamespace(signals=None, opportunities=None, capabilities=None, profile=None)
    current = SimpleNamespace(signals=None, opportunities=None, capabilities=None, profile=None)

    assert detect_changes(previous, current).changes == []


# --- Similarity matching (real rewordings observed between two runs) ----


def test_a_reworded_signal_is_one_update_not_an_appearance_and_a_disappearance():
    # Verbatim from two consecutive real analyses of the same company.
    previous = _snapshot(signals=[_signal("strategic", "Sovereign AI and Global Infrastructure Expansion")])
    current = _snapshot(signals=[_signal("strategic", "Sovereign AI Infrastructure Expansion")])

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].change_type == CHANGE_UPDATED
    # Crucially not major: nothing new actually happened.
    assert changes[0].significance == SIGNIFICANCE_MINOR
    assert changes[0].previous_value == "Sovereign AI and Global Infrastructure Expansion"
    assert changes[0].current_value == "Sovereign AI Infrastructure Expansion"


def test_a_reworded_opportunity_is_not_announced_as_a_new_one():
    # Also verbatim. A false "new opportunity" is the most damaging
    # possible error here, because new opportunities are reported as major.
    previous = _snapshot(
        opportunities=[_opportunity("AI Ready Data Pipelines for Enterprise AI and NIMs Deployment", 0.7)]
    )
    current = _snapshot(
        opportunities=[_opportunity("AI-Ready Data Pipelines for Enterprise NIM & Omniverse Workloads", 0.7)]
    )

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].change_type == CHANGE_UPDATED
    assert changes[0].significance == SIGNIFICANCE_MINOR


def test_a_reworded_opportunity_still_reports_a_real_score_move():
    previous = _snapshot(
        opportunities=[_opportunity("AI Ready Data Pipelines for Enterprise AI and NIMs Deployment", 0.4)]
    )
    current = _snapshot(
        opportunities=[_opportunity("AI-Ready Data Pipelines for Enterprise NIM & Omniverse Workloads", 0.9)]
    )

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].change_type == CHANGE_STRENGTHENED
    assert changes[0].significance == SIGNIFICANCE_MAJOR
    assert "0.40" in changes[0].detail and "0.90" in changes[0].detail


def test_genuinely_different_developments_are_not_merged():
    # These two share a leading word but describe different things; merging
    # them would hide a real change, which is worse than reporting noise.
    previous = _snapshot(signals=[_signal("strategic", "Supply Chain Diversification")])
    current = _snapshot(signals=[_signal("strategic", "Industrial Digitalization via Omniverse")])

    changes = detect_changes(previous, current).changes

    assert {change.change_type for change in changes} == {CHANGE_APPEARED, CHANGE_RESOLVED}


def test_punctuation_and_plural_differences_alone_do_not_read_as_change():
    previous = _snapshot(signals=[_signal("technology", "NVIDIA Inference Microservices (NIMs)")])
    current = _snapshot(signals=[_signal("technology", "NVIDIA Inference Microservice - NIM")])

    changes = detect_changes(previous, current).changes

    assert len(changes) == 1
    assert changes[0].change_type == CHANGE_UPDATED


def test_signals_are_only_paired_within_the_same_type():
    # A development being recategorised is itself worth reporting, so
    # similar titles under different types must stay two changes.
    previous = _snapshot(signals=[_signal("hiring", "Expanding the global AI engineering team")])
    current = _snapshot(signals=[_signal("strategic", "Expanding the global AI engineering team")])

    changes = detect_changes(previous, current).changes

    assert {change.change_type for change in changes} == {CHANGE_APPEARED, CHANGE_RESOLVED}


def test_one_disappearing_item_cannot_absorb_two_new_ones():
    previous = _snapshot(opportunities=[_opportunity("Cloud migration programme", 0.5)])
    current = _snapshot(
        opportunities=[
            _opportunity("Cloud migration programme phase one", 0.5),
            _opportunity("Cloud migration programme phase two", 0.5),
        ]
    )

    changes = detect_changes(previous, current).changes

    # One pairs as a rewording; the other must remain a genuine new
    # opportunity rather than being silently dropped.
    assert sum(1 for c in changes if c.change_type == CHANGE_APPEARED) == 1
    assert sum(1 for c in changes if c.change_type == CHANGE_UPDATED) == 1


def test_similarity_pairing_is_deterministic_across_repeated_runs():
    previous = _snapshot(
        signals=[
            _signal("technology", "Blackwell Architecture and Advanced Liquid Cooling"),
            _signal("technology", "NVIDIA Inference Microservices and AI Software Stack"),
        ]
    )
    current = _snapshot(
        signals=[
            _signal("technology", "Blackwell Architecture and GB200 Superchips Rollout"),
            _signal("technology", "Expansion of NVIDIA AI Enterprise and NIM Microservices"),
        ]
    )

    first = [(c.change_type, c.title) for c in detect_changes(previous, current).changes]
    second = [(c.change_type, c.title) for c in detect_changes(previous, current).changes]

    assert first == second


def test_a_pure_rewording_shows_the_two_titles_not_two_identical_scores():
    # Showing previous_value/current_value as the same score would read as
    # a score change that did not happen; the title is what moved.
    previous = _snapshot(
        opportunities=[_opportunity("AI Ready Data Pipelines for Enterprise AI and NIMs Deployment", 0.8)]
    )
    current = _snapshot(
        opportunities=[_opportunity("AI-Ready Data Pipelines for Enterprise NIM & Omniverse Workloads", 0.8)]
    )

    change = detect_changes(previous, current).changes[0]

    assert change.change_type == CHANGE_UPDATED
    assert change.previous_value == "AI Ready Data Pipelines for Enterprise AI and NIMs Deployment"
    assert change.current_value == "AI-Ready Data Pipelines for Enterprise NIM & Omniverse Workloads"


# --- Executive movement (V3 Enhancements Phase 4) ----------------------


def _executive(name, title=None):
    return {"name": name, "title": title}


def test_a_newly_identified_executive_is_a_major_leadership_change():
    changes = detect_changes(
        _snapshot(executives=[_executive("Ann Lee", "CFO")]),
        _snapshot(executives=[_executive("Ann Lee", "CFO"), _executive("Bo Chen", "CTO")]),
    ).changes

    arrival = [c for c in changes if c.title == "Bo Chen"]
    assert len(arrival) == 1
    assert arrival[0].category == CATEGORY_LEADERSHIP
    assert arrival[0].change_type == CHANGE_APPEARED
    assert arrival[0].significance == SIGNIFICANCE_MAJOR
    assert "CTO" in arrival[0].detail


def test_a_title_change_is_reported_with_both_titles():
    changes = detect_changes(
        _snapshot(executives=[_executive("Ann Lee", "VP Finance")]),
        _snapshot(executives=[_executive("Ann Lee", "Chief Financial Officer")]),
    ).changes

    assert len(changes) == 1
    assert changes[0].change_type == CHANGE_UPDATED
    assert changes[0].previous_value == "VP Finance"
    assert changes[0].current_value == "Chief Financial Officer"


def test_a_departure_is_worded_as_absence_from_research_not_as_a_departure():
    # Research failing to mention someone is weak evidence they left, and
    # stating it as fact is a claim a salesperson could repeat to a
    # customer.
    changes = detect_changes(
        _snapshot(executives=[_executive("Ann Lee", "CFO")]),
        _snapshot(executives=[]),
    ).changes

    assert changes[0].change_type == CHANGE_RESOLVED
    assert "No longer appearing in research" in changes[0].detail
    assert "left" not in changes[0].detail.lower()


def test_an_unchanged_roster_reports_nothing():
    roster = [_executive("Ann Lee", "CFO"), _executive("Bo Chen", "CTO")]

    assert detect_changes(_snapshot(executives=roster), _snapshot(executives=list(roster))).changes == []


def test_names_are_matched_case_and_whitespace_insensitively():
    changes = detect_changes(
        _snapshot(executives=[_executive("ann lee", "CFO")]),
        _snapshot(executives=[_executive("  Ann Lee  ", "CFO")]),
    ).changes

    assert changes == []


def test_similar_names_are_two_people_not_one_reworded_person():
    # Unlike signal titles, names must NOT go through similarity matching:
    # "David Chen" and "Daniel Chen" share most of their tokens and are
    # two different people.
    changes = detect_changes(
        _snapshot(executives=[_executive("David Chen", "CTO")]),
        _snapshot(executives=[_executive("Daniel Chen", "CTO")]),
    ).changes

    assert {c.change_type for c in changes} == {CHANGE_APPEARED, CHANGE_RESOLVED}


def test_a_snapshot_that_never_looked_at_people_reports_no_movement():
    # The upgrade case: snapshots captured before Phase 4 have a NULL
    # executives column. Diffing against it would announce every executive
    # as newly arrived on the first post-upgrade run.
    changes = detect_changes(
        _snapshot(executives=None),
        _snapshot(executives=[_executive("Ann Lee", "CFO")]),
    ).changes

    assert changes == []


def test_a_failed_persistence_run_does_not_report_everyone_as_departed():
    # The inverse: the pipeline stage is best-effort, so a failure leaves
    # executives as None rather than [].
    changes = detect_changes(
        _snapshot(executives=[_executive("Ann Lee", "CFO")]),
        _snapshot(executives=None),
    ).changes

    assert changes == []


def test_an_unnamed_executive_entry_is_skipped_rather_than_crashing():
    changes = detect_changes(
        _snapshot(executives=[]),
        _snapshot(executives=[_executive(None, "CTO"), _executive("  ", "CFO")]),
    ).changes

    assert changes == []
