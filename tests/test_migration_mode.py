"""Unit tests for backend/migration_mode.py's dispatch logic and
reconciliation metrics - pure logic, no database required, so these run
unconditionally (unlike the Postgres-gated integration tests).
"""

import os

import pytest

from backend.config import get_settings
from backend.migration_mode import (
    MigrationMode,
    ReconciliationMetrics,
    dispatch_read,
    dispatch_write,
    get_migration_mode,
    results_match,
)
from backend.models.company import Company


@pytest.fixture(autouse=True)
def _reset_migration_mode(monkeypatch):
    # get_settings() is lru_cache'd - clear it after each test so one
    # test's monkeypatched MIGRATION_MODE never leaks into the next.
    yield
    monkeypatch.delenv("MIGRATION_MODE", raising=False)
    get_settings.cache_clear()


def _set_mode(monkeypatch, mode: str) -> None:
    monkeypatch.setenv("MIGRATION_MODE", mode)
    get_settings.cache_clear()


def test_get_migration_mode_defaults_to_sqlite():
    assert get_migration_mode() == MigrationMode.SQLITE


def test_dispatch_write_in_sqlite_mode_never_calls_postgres(monkeypatch):
    _set_mode(monkeypatch, "sqlite")
    calls = []

    result = dispatch_write(
        "company", "create_company",
        sqlite_call=lambda: calls.append("sqlite") or "sqlite-result",
        postgres_call=lambda: calls.append("postgres"),
    )

    assert calls == ["sqlite"]
    assert result == "sqlite-result"


def test_dispatch_write_in_dual_write_mode_calls_both(monkeypatch):
    _set_mode(monkeypatch, "dual_write")
    calls = []

    result = dispatch_write(
        "company", "create_company",
        sqlite_call=lambda: calls.append("sqlite") or "sqlite-result",
        postgres_call=lambda: calls.append("postgres"),
    )

    assert calls == ["sqlite", "postgres"]
    assert result == "sqlite-result"


def test_dispatch_write_in_dual_write_mode_swallows_postgres_failures(monkeypatch):
    _set_mode(monkeypatch, "dual_write")

    def _failing_postgres_call():
        raise RuntimeError("Postgres is down")

    result = dispatch_write(
        "company", "create_company",
        sqlite_call=lambda: "sqlite-result",
        postgres_call=_failing_postgres_call,
    )

    assert result == "sqlite-result"


def test_dispatch_write_in_dual_write_mode_still_propagates_sqlite_failures(monkeypatch):
    _set_mode(monkeypatch, "dual_write")

    def _failing_sqlite_call():
        raise RuntimeError("SQLite is down")

    with pytest.raises(RuntimeError, match="SQLite is down"):
        dispatch_write(
            "company", "create_company",
            sqlite_call=_failing_sqlite_call,
            postgres_call=lambda: None,
        )


def test_dispatch_write_in_postgres_mode_only_calls_postgres(monkeypatch):
    _set_mode(monkeypatch, "postgres")
    calls = []

    result = dispatch_write(
        "company", "create_company",
        sqlite_call=lambda: calls.append("sqlite"),
        postgres_call=lambda: calls.append("postgres") or "postgres-result",
    )

    assert calls == ["postgres"]
    assert result == "postgres-result"


def test_dispatch_read_in_sqlite_and_dual_write_modes_only_reads_sqlite(monkeypatch):
    for mode in ("sqlite", "dual_write"):
        _set_mode(monkeypatch, mode)
        calls = []

        result = dispatch_read(
            "company", "get_company",
            sqlite_call=lambda: calls.append("sqlite") or "sqlite-result",
            postgres_call=lambda: calls.append("postgres"),
        )

        assert calls == ["sqlite"], f"mode={mode}"
        assert result == "sqlite-result"


def test_dispatch_read_in_postgres_mode_only_reads_postgres(monkeypatch):
    _set_mode(monkeypatch, "postgres")
    calls = []

    result = dispatch_read(
        "company", "get_company",
        sqlite_call=lambda: calls.append("sqlite"),
        postgres_call=lambda: calls.append("postgres") or "postgres-result",
    )

    assert calls == ["postgres"]
    assert result == "postgres-result"


def test_dispatch_read_in_shadow_read_mode_reads_both_but_returns_sqlite(monkeypatch):
    _set_mode(monkeypatch, "shadow_read")
    calls = []

    result = dispatch_read(
        "company", "get_company",
        sqlite_call=lambda: calls.append("sqlite") or "sqlite-result",
        postgres_call=lambda: calls.append("postgres") or "postgres-result",
    )

    assert calls == ["sqlite", "postgres"]
    assert result == "sqlite-result"


def test_dispatch_read_in_shadow_read_mode_records_a_match(monkeypatch):
    _set_mode(monkeypatch, "shadow_read")

    from backend.migration_mode import _get_metrics, reset_reconciliation_metrics

    reset_reconciliation_metrics()
    dispatch_read(
        "company", "get_company",
        sqlite_call=lambda: "same-value",
        postgres_call=lambda: "same-value",
    )

    metrics = _get_metrics("company")
    assert metrics.total_comparisons == 1
    assert metrics.matches == 1
    assert metrics.mismatches == 0


def test_dispatch_read_in_shadow_read_mode_records_a_mismatch_without_raising(monkeypatch):
    _set_mode(monkeypatch, "shadow_read")

    from backend.migration_mode import _get_metrics, reset_reconciliation_metrics

    reset_reconciliation_metrics()
    result = dispatch_read(
        "company", "get_company",
        sqlite_call=lambda: "sqlite-value",
        postgres_call=lambda: "different-postgres-value",
    )

    assert result == "sqlite-value"
    metrics = _get_metrics("company")
    assert metrics.total_comparisons == 1
    assert metrics.mismatches == 1
    assert metrics.mismatch_percentage == 100.0


def test_dispatch_read_in_shadow_read_mode_survives_a_failing_postgres_comparison(monkeypatch):
    _set_mode(monkeypatch, "shadow_read")

    def _failing_postgres_call():
        raise RuntimeError("Postgres is down")

    result = dispatch_read(
        "company", "get_company",
        sqlite_call=lambda: "sqlite-value",
        postgres_call=_failing_postgres_call,
    )

    assert result == "sqlite-value"


def test_results_match_treats_none_as_equal_only_to_none():
    assert results_match(None, None) is True
    assert results_match(None, "something") is False
    assert results_match("something", None) is False


def test_results_match_compares_pydantic_models_field_by_field():
    company_a = Company(id="c1", name="Acme", industry="Software")
    company_b = Company(id="c1", name="Acme", industry="Software", created_at=company_a.created_at, updated_at=company_a.updated_at)
    company_c = Company(id="c1", name="Different Name", industry="Software", created_at=company_a.created_at, updated_at=company_a.updated_at)

    assert results_match(company_a, company_b) is True
    assert results_match(company_a, company_c) is False


def test_results_match_tolerates_small_timestamp_differences():
    from datetime import timedelta

    company_a = Company(id="c1", name="Acme")
    company_b = company_a.model_copy(update={"updated_at": company_a.updated_at + timedelta(seconds=1)})

    assert results_match(company_a, company_b) is True


def test_results_match_rejects_large_timestamp_differences():
    from datetime import timedelta

    company_a = Company(id="c1", name="Acme")
    company_b = company_a.model_copy(update={"updated_at": company_a.updated_at + timedelta(hours=1)})

    assert results_match(company_a, company_b) is False


def test_results_match_compares_lists_of_models_order_independently():
    company_a = Company(id="c1", name="Acme")
    company_b = Company(id="c2", name="Beta")

    assert results_match([company_a, company_b], [company_b, company_a]) is True
    assert results_match([company_a], [company_a, company_b]) is False


def test_reconciliation_metrics_as_text_reports_percentage_and_latency():
    metrics = ReconciliationMetrics(entity_type="company")
    metrics.record("get_company", True, 0.01, 0.02)
    metrics.record("get_company", False, 0.01, 0.02)

    text = metrics.as_text()

    assert "total_comparisons=2" in text
    assert "matches=1" in text
    assert "mismatches=1" in text
    assert "mismatch_percentage=50.00%" in text
