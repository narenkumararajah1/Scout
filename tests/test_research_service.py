import json
from unittest.mock import patch

import pytest

from backend.models.company import Company
from backend.repositories.company_repository import create_company
from backend.repositories.research_repository import list_signals_for_session
from backend.services import research_service
from tests.conftest import clear_v2_tables

FAKE_COMPANY_TECH = "1. Company Information: ...\n2. Technology Initiatives: ...\n3. Business Trends: ..."
FAKE_ORG_STRATEGIC = (
    "1. Hiring Activity: ...\n2. Leadership Changes: ...\n3. Strategic Initiatives: ...\n4. Public Professional Signals: ..."
)
FAKE_UNIFIED = "Acme Corp is hiring ML engineers and recently appointed a new CTO."
FAKE_SIGNALS_JSON = json.dumps(
    [
        {"type": "hiring", "title": "ML engineer hiring", "description": "Actively hiring ML engineers.", "confidence": 0.8},
        {"type": "leadership", "title": "New CTO", "description": "Recently appointed a new CTO.", "confidence": 0.9},
    ]
)


def _make_company() -> Company:
    return create_company(Company(name="Acme Corp"))


def test_research_company_persists_session_linked_to_company():
    clear_v2_tables()
    company = _make_company()

    with patch(
        "backend.services.research_service.generate_completion",
        side_effect=[FAKE_COMPANY_TECH, FAKE_ORG_STRATEGIC, FAKE_UNIFIED, FAKE_SIGNALS_JSON],
    ):
        session = research_service.research_company(company)

    assert session.company_id == company.id
    assert session.status == "completed"
    assert session.research_summary == FAKE_UNIFIED
    assert session.research_sources == {
        "company_technology": FAKE_COMPANY_TECH,
        "organizational_strategic": FAKE_ORG_STRATEGIC,
    }


def test_research_company_extracts_and_persists_signals():
    clear_v2_tables()
    company = _make_company()

    with patch(
        "backend.services.research_service.generate_completion",
        side_effect=[FAKE_COMPANY_TECH, FAKE_ORG_STRATEGIC, FAKE_UNIFIED, FAKE_SIGNALS_JSON],
    ):
        session = research_service.research_company(company)

    signals = list_signals_for_session(session.id)
    assert len(signals) == 2
    types = {signal.type for signal in signals}
    assert types == {"hiring", "leadership"}
    assert all(signal.source == research_service.SIGNAL_SOURCE for signal in signals)
    assert all(signal.research_session_id == session.id for signal in signals)

    hiring_signal = next(s for s in signals if s.type == "hiring")
    assert hiring_signal.title == "ML engineer hiring"
    assert hiring_signal.confidence == 0.8


def test_research_company_persists_session_with_zero_signals():
    clear_v2_tables()
    company = _make_company()

    with patch(
        "backend.services.research_service.generate_completion",
        side_effect=[FAKE_COMPANY_TECH, FAKE_ORG_STRATEGIC, FAKE_UNIFIED, "[]"],
    ):
        session = research_service.research_company(company)

    assert list_signals_for_session(session.id) == []


def test_research_company_prompts_include_company_name_and_sections():
    clear_v2_tables()
    company = _make_company()

    with patch(
        "backend.services.research_service.generate_completion",
        side_effect=[FAKE_COMPANY_TECH, FAKE_ORG_STRATEGIC, FAKE_UNIFIED, "[]"],
    ) as mock_completion:
        research_service.research_company(company)

    company_tech_prompt = mock_completion.call_args_list[0][0][0]
    assert company.name in company_tech_prompt
    assert "Technology Initiatives" in company_tech_prompt

    org_strategic_prompt = mock_completion.call_args_list[1][0][0]
    assert "Hiring Activity" in org_strategic_prompt
    assert "Leadership Changes" in org_strategic_prompt
    assert "Strategic Initiatives" in org_strategic_prompt

    merge_prompt = mock_completion.call_args_list[2][0][0]
    assert FAKE_COMPANY_TECH in merge_prompt
    assert FAKE_ORG_STRATEGIC in merge_prompt

    extraction_prompt = mock_completion.call_args_list[3][0][0]
    assert FAKE_UNIFIED in extraction_prompt
    assert "technology, hiring, leadership, strategic" in extraction_prompt


def test_research_company_raises_and_persists_nothing_when_a_call_fails():
    clear_v2_tables()
    company = _make_company()

    with patch(
        "backend.services.research_service.generate_completion",
        side_effect=[FAKE_COMPANY_TECH, FAKE_ORG_STRATEGIC, RuntimeError("simulated failure")],
    ):
        with pytest.raises(RuntimeError):
            research_service.research_company(company)

    from backend.repositories.research_repository import list_research_sessions

    assert list_research_sessions(company.id) == []


def test_research_company_raises_clear_error_on_malformed_signal_json():
    clear_v2_tables()
    company = _make_company()

    with patch(
        "backend.services.research_service.generate_completion",
        side_effect=[FAKE_COMPANY_TECH, FAKE_ORG_STRATEGIC, FAKE_UNIFIED, "not actually JSON"],
    ):
        with pytest.raises(ValueError, match="could not parse Claude's response as JSON"):
            research_service.research_company(company)

    from backend.repositories.research_repository import list_research_sessions

    # The research session must not exist either - the whole run is
    # all-or-nothing, matching V1's ResearchAgent precedent.
    assert list_research_sessions(company.id) == []
