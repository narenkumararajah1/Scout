import sqlite3

import pytest

from backend.models.company import Company
from backend.models.research import SIGNAL_TYPE_HIRING, SIGNAL_TYPE_TECHNOLOGY, ResearchSession, Signal
from backend.repositories.company_repository import create_company
from backend.repositories.research_repository import (
    create_research_session,
    create_signal,
    get_research_session,
    list_research_sessions,
    list_signals_for_session,
)
from tests.conftest import clear_v2_tables



def _make_company() -> Company:
    return create_company(Company(name="Acme Corp"))


def test_create_and_get_research_session_round_trips_nested_dicts():
    clear_v2_tables()
    company = _make_company()
    session = ResearchSession(
        company_id=company.id,
        research_summary="Acme is expanding into cloud infrastructure.",
        raw_research={"business_research": "...", "social_intelligence": "..."},
        research_sources={"business_research": "...", "social_intelligence": "..."},
        status="completed",
    )

    create_research_session(session)
    fetched = get_research_session(session.id)

    assert fetched is not None
    assert fetched.company_id == company.id
    assert fetched.research_summary == "Acme is expanding into cloud infrastructure."
    assert fetched.raw_research == {"business_research": "...", "social_intelligence": "..."}
    assert fetched.status == "completed"


def test_get_research_session_returns_none_when_not_found():
    clear_v2_tables()
    assert get_research_session("does-not-exist") is None


def test_list_research_sessions_filters_by_company_and_orders_most_recent_first():
    clear_v2_tables()
    company_a = _make_company()
    company_b = create_company(Company(name="Other Co"))

    first = create_research_session(ResearchSession(company_id=company_a.id, status="completed"))
    second = create_research_session(ResearchSession(company_id=company_a.id, status="completed"))
    create_research_session(ResearchSession(company_id=company_b.id, status="completed"))

    sessions = list_research_sessions(company_a.id)

    assert [s.id for s in sessions] == [second.id, first.id]


def test_create_signal_requires_an_existing_research_session():
    """Foreign key enforcement (V2 Phase 2): signals must belong to a real
    research session - PRAGMA foreign_keys is now on for every connection."""
    clear_v2_tables()
    with pytest.raises(sqlite3.IntegrityError):
        create_signal(Signal(research_session_id="does-not-exist", type=SIGNAL_TYPE_TECHNOLOGY, title="Azure adoption"))


def test_list_signals_for_session_returns_only_that_sessions_signals():
    clear_v2_tables()
    company = _make_company()
    session_a = create_research_session(ResearchSession(company_id=company.id, status="completed"))
    session_b = create_research_session(ResearchSession(company_id=company.id, status="completed"))

    create_signal(
        Signal(research_session_id=session_a.id, type=SIGNAL_TYPE_TECHNOLOGY, title="Azure migration", confidence=0.8)
    )
    create_signal(
        Signal(research_session_id=session_a.id, type=SIGNAL_TYPE_HIRING, title="Hiring ML engineers")
    )
    create_signal(
        Signal(research_session_id=session_b.id, type=SIGNAL_TYPE_TECHNOLOGY, title="Unrelated signal")
    )

    signals = list_signals_for_session(session_a.id)

    assert len(signals) == 2
    assert {signal.title for signal in signals} == {"Azure migration", "Hiring ML engineers"}
    assert all(signal.research_session_id == session_a.id for signal in signals)
