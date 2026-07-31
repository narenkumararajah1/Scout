"""Tests for EntityPersistenceStage (V3 Enhancements Phase 4, renamed
in Phase 7B).

This stage is why Scout knows any people at all. Before it existed,
Knowledge Extraction returned executives and `persist_extracted_entities`
could store them, but nothing connected the two - the dev database held
five analysed companies and zero executive rows.

Postgres-gated, because the whole point of the stage is that rows land in
the database; asserting against a mocked repository would pass while the
original bug was still present.
"""

import uuid
from unittest.mock import patch

import pytest

from backend.ai.knowledge_extraction import ExtractedEntities, ExtractedExecutive
from backend.database.models import Company as CompanyModel
from backend.models.company import Company
from backend.orchestration.pipeline import OrchestrationMode, PipelineContext, StageMetrics
from backend.orchestration.stages import EntityPersistenceStage
from backend.repositories.postgres.executive_repository import list_executives_for_company

pytestmark = pytest.mark.usefixtures("postgres_available")


async def _company_row(name="Acme Corp"):
    """A real companies row, since executives.company_id is a real FK."""
    from backend.database.postgres import get_session

    company_id = str(uuid.uuid4())
    async with get_session() as session:
        session.add(CompanyModel(id=company_id, name=name))
        await session.commit()
    return company_id


def _context(company_id, *, research_summary="Acme's CTO is Ann Lee.", extracted=None):
    company = Company(name="Acme Corp")
    company.id = company_id
    context = PipelineContext(company=company, mode=OrchestrationMode.LEGACY)
    context.research_session = type("Session", (), {"id": "session-1", "research_summary": research_summary})()
    context.extracted_entities = extracted
    context.metrics = {"executive_persistence": StageMetrics(stage_name="executive_persistence")}
    return context


def _extracted(*people):
    return ExtractedEntities(
        technologies=[],
        executives=[ExtractedExecutive(name=name, title=title) for name, title in people],
        business_initiatives=[],
    )


async def test_executives_from_the_extraction_stage_are_persisted():
    company_id = await _company_row()
    context = _context(company_id, extracted=_extracted(("Ann Lee", "CTO"), ("Bo Chen", "CFO")))

    await EntityPersistenceStage().run(context)

    stored = await list_executives_for_company(company_id)
    assert {e.name for e in stored} == {"Ann Lee", "Bo Chen"}
    assert {e.name for e in context.persisted_executives} == {"Ann Lee", "Bo Chen"}


async def test_legacy_mode_extracts_for_itself_when_the_extraction_stage_did_not_run():
    # KnowledgeExtractionStage is disabled in legacy, which is the default
    # mode - so without this fallback the phase would deliver nothing in
    # the configuration the product actually ships with.
    company_id = await _company_row()
    context = _context(company_id, extracted=None)

    with patch(
        "backend.ai.knowledge_extraction.extract_entities", return_value=_extracted(("Ann Lee", "CTO"))
    ) as extract:
        await EntityPersistenceStage().run(context)

    assert extract.called
    assert [e.name for e in await list_executives_for_company(company_id)] == ["Ann Lee"]


async def test_an_existing_extraction_result_is_reused_rather_than_re_extracted():
    company_id = await _company_row()
    context = _context(company_id, extracted=_extracted(("Ann Lee", "CTO")))

    with patch("backend.ai.knowledge_extraction.extract_entities") as extract:
        await EntityPersistenceStage().run(context)

    assert not extract.called


async def test_re_running_updates_rather_than_duplicating_a_person():
    company_id = await _company_row()

    await EntityPersistenceStage().run(_context(company_id, extracted=_extracted(("Ann Lee", "VP Finance"))))
    await EntityPersistenceStage().run(_context(company_id, extracted=_extracted(("Ann Lee", "CFO"))))

    stored = await list_executives_for_company(company_id)
    assert len(stored) == 1
    assert stored[0].title == "CFO"


async def test_no_research_summary_means_no_extraction_and_no_crash():
    company_id = await _company_row()
    context = _context(company_id, research_summary="", extracted=None)

    with patch("backend.ai.knowledge_extraction.extract_entities") as extract:
        await EntityPersistenceStage().run(context)

    assert not extract.called
    assert context.persisted_executives is None


async def test_a_persistence_failure_is_swallowed_and_leaves_executives_unset():
    # Best-effort: by this point the report exists and the run has
    # succeeded. Losing the people must not fail the analysis - and
    # persisted_executives must stay None rather than becoming [], or the
    # refresh snapshot would report every known executive as departed.
    company_id = await _company_row()
    context = _context(company_id, extracted=_extracted(("Ann Lee", "CTO")))

    with patch(
        "backend.services.company_intelligence_service.persist_extracted_entities",
        side_effect=RuntimeError("database is down"),
    ):
        await EntityPersistenceStage().run(context)

    assert context.persisted_executives is None


async def test_the_stage_runs_in_every_orchestration_mode():
    # Unlike the Phase 4B AI stages, this one is additive - nothing else
    # identifies people - so opting out of any mode would lose data.
    stage = EntityPersistenceStage()

    assert all(stage.is_enabled(mode) for mode in OrchestrationMode)


async def test_the_stage_passes_the_company_name_for_name_normalisation():
    """Regression for a wiring bug that reached the live database.

    A patch added `company_name` to the wrong call site - the refresh
    stage, which does not accept it - so two things broke at once: the
    refresh raised TypeError into a best-effort handler and silently
    stopped producing summaries, while technology normalisation never
    received the company name and every vendor-prefixed variant forked a
    duplicate row.

    Asserting on the keyword directly is what a test can catch here; the
    forking itself only shows up against a real extractor.
    """
    from unittest.mock import AsyncMock, patch

    company_id = await _company_row(name="NVIDIA")
    context = _context(company_id, extracted=_extracted(("Ann Lee", "CTO")))
    context.company.name = "NVIDIA"

    with patch(
        "backend.services.company_intelligence_service.persist_extracted_entities",
        new=AsyncMock(return_value=([], [], [])),
    ) as persist:
        await EntityPersistenceStage().run(context)

    assert persist.await_args.kwargs["company_name"] == "NVIDIA"
