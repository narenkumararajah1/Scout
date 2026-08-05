"""Refresh Intelligence: refreshing what Scout knows, without publishing
a report.

Each test names the defect it prevents. The defect these exist for is
specific: "Refresh Intelligence" ran V2's analyze pipeline, whose final
stage publishes a Report - so the button's visible output was a new
report rather than updated intelligence, and every refresh silently grew
the company's report list.
"""

import pytest

from backend.orchestration import manual_analysis
from tests.conftest import clear_v2_tables


def _stage_names(pipeline) -> list:
    return [stage.name for stage in pipeline.stages]


def test_reporting_stage_is_the_only_stage_dropped():
    """The refresh must skip publishing and change nothing else.

    Dropping a stage is a blunt instrument: if the exclusion were written
    as a filter or an index it could silently take a neighbour with it,
    and the loss (no executives persisted, no snapshot written) would show
    up as "the refresh does nothing" long after the change.
    """
    with_reporting = _stage_names(manual_analysis._build_pipeline(include_reporting=True))
    without = _stage_names(manual_analysis._build_pipeline(include_reporting=False))

    assert "reporting" in with_reporting
    assert "reporting" not in without
    assert [name for name in with_reporting if name != "reporting"] == without


def test_refresh_keeps_the_stages_the_intelligence_sections_depend_on():
    """Named explicitly rather than by count.

    The refresh exists to update signals, key people, technologies and the
    "what changed" summary. A future edit that reorders or removes any of
    these would still satisfy a "same length minus one" assertion, and the
    UI would quietly stop updating the section it fed.
    """
    without = _stage_names(manual_analysis._build_pipeline(include_reporting=False))

    for required in (
        "research",
        "capability_matching",
        "opportunity_analysis",
        "executive_persistence",
        "company_refresh",
    ):
        assert required in without, f"{required} is required for the intelligence sections"


def test_default_pipeline_still_publishes_a_report():
    """The V2 contract is unchanged.

    POST /companies/{id}/analyze and the scheduler both rely on a report
    coming out of the default pipeline. Making reporting optional must not
    have made it opt-in.
    """
    assert "reporting" in _stage_names(manual_analysis._build_pipeline())


@pytest.mark.asyncio
async def test_refresh_company_intelligence_runs_without_reporting(monkeypatch):
    """The public entrypoint must pass the flag through.

    A wrapper that forgets its one argument is an easy mistake and an
    invisible one: the refresh would work, return a summary, and still
    publish the report it was written to avoid.
    """
    captured = {}

    async def fake_pipeline(company, include_reporting=True):
        captured["include_reporting"] = include_reporting

        class _Result:
            refresh_summary = None

        return _Result()

    monkeypatch.setattr(manual_analysis, "run_manual_analysis_pipeline", fake_pipeline)

    class _Company:
        id = "c1"
        name = "Acme"

    await manual_analysis.refresh_company_intelligence(_Company())

    assert captured["include_reporting"] is False


def test_refresh_endpoint_returns_404_for_unknown_company(client):
    clear_v2_tables()
    response = client.post("/api/v1/companies/does-not-exist/refresh")

    assert response.status_code == 404


def test_refresh_endpoint_does_not_create_a_report(client, monkeypatch):
    """The user-visible promise, asserted end to end.

    This is the actual bug report - "it generates a report instead of
    refreshing" - so it is asserted against the company's report list
    rather than against the pipeline internals the tests above cover.
    """
    clear_v2_tables()
    company = client.post("/companies", json={"name": "Acme Corp"}).json()

    async def fake_refresh(company_arg):
        class _Result:
            refresh_summary = None

        return _Result()

    # Patched where it is used, not where it is defined - the router
    # imported the name at module load.
    monkeypatch.setattr("backend.api.routers.companies.refresh_company_intelligence", fake_refresh)

    # The company's report list lives at /companies/{id}/reports. Reading
    # it through a guessed query-string route instead returned 404, which
    # made an earlier version of this assertion skip itself and pass
    # having checked nothing - so the status is asserted first, and the
    # comparison is unconditional.
    before = client.get(f"/companies/{company['id']}/reports")
    assert before.status_code == 200, "report list endpoint moved; this test would assert nothing"
    count_before = len(before.json())

    response = client.post(f"/api/v1/companies/{company['id']}/refresh")

    assert response.status_code == 200
    assert response.json()["success"] is True

    after = client.get(f"/companies/{company['id']}/reports")
    assert after.status_code == 200
    assert len(after.json()) == count_before, "refresh must not publish a report"


def test_refresh_endpoint_reports_upstream_failure_as_502(client, monkeypatch):
    """A failed refresh must say so.

    The stage that writes the summary is best-effort and swallows its own
    errors; that must not extend to the whole run reporting success after
    the research itself failed.
    """
    clear_v2_tables()
    company = client.post("/companies", json={"name": "Acme Corp"}).json()

    async def boom(company_arg):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr("backend.api.routers.companies.refresh_company_intelligence", boom)

    response = client.post(f"/api/v1/companies/{company['id']}/refresh")

    assert response.status_code == 502
