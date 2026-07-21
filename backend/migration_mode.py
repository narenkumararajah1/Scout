"""Centralized migration-mode dispatch for the SQLite -> PostgreSQL
cutover (V3 Phase 3B).

settings.migration_mode is the single source of truth for which
persistence backend(s) backend/repositories/company_repository.py and
opportunity_repository.py use. Moving forward or back a stage - or
straight to any other stage - is exactly one config change
(MIGRATION_MODE env var), never a code change or deployment rollback.
See TECH_DEBT.md for the full stage-by-stage rollout.

Modes:
    sqlite      - SQLite only. Postgres is never touched. (starting state)
    dual_write  - Writes go to both; SQLite is authoritative (its result
                  is returned, its exceptions propagate) and Postgres is
                  best-effort (a failure is logged, never raised - it can
                  never break a live request). Reads come from SQLite only.
    shadow_read - Same write behavior as dual_write. Reads are served from
                  SQLite (returned to the caller) but also fetched from
                  Postgres purely for comparison - see ReconciliationMetrics.
    postgres    - PostgreSQL only. SQLite is never touched. (fully cut over)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional, TypeVar

from pydantic import BaseModel

from backend.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Datetime fields are allowed to differ by this much between SQLite and
# Postgres before being treated as a real mismatch - the two stores set
# their own created_at/updated_at defaults independently during
# dual-write, at slightly different real wall-clock moments, and exact
# equality would produce mismatch noise unrelated to actual data drift.
_TIMESTAMP_TOLERANCE = timedelta(seconds=5)


class MigrationMode(str, Enum):
    SQLITE = "sqlite"
    DUAL_WRITE = "dual_write"
    SHADOW_READ = "shadow_read"
    POSTGRES = "postgres"


def get_migration_mode() -> MigrationMode:
    return MigrationMode(get_settings().migration_mode)


@dataclass
class ReconciliationMetrics:
    entity_type: str
    total_comparisons: int = 0
    matches: int = 0
    mismatches: int = 0
    mismatch_samples: list = field(default_factory=list)
    sqlite_latency_total: float = 0.0
    postgres_latency_total: float = 0.0

    @property
    def mismatch_percentage(self) -> float:
        if self.total_comparisons == 0:
            return 0.0
        return (self.mismatches / self.total_comparisons) * 100

    @property
    def average_sqlite_latency_ms(self) -> float:
        return (self.sqlite_latency_total / self.total_comparisons * 1000) if self.total_comparisons else 0.0

    @property
    def average_postgres_latency_ms(self) -> float:
        return (self.postgres_latency_total / self.total_comparisons * 1000) if self.total_comparisons else 0.0

    def record(self, operation: str, matched: bool, sqlite_latency: float, postgres_latency: float) -> None:
        self.total_comparisons += 1
        if matched:
            self.matches += 1
        else:
            self.mismatches += 1
            self.mismatch_samples.append(operation)
        self.sqlite_latency_total += sqlite_latency
        self.postgres_latency_total += postgres_latency

    def as_text(self) -> str:
        return (
            f"Shadow-read reconciliation ({self.entity_type}): "
            f"total_comparisons={self.total_comparisons} matches={self.matches} "
            f"mismatches={self.mismatches} mismatch_percentage={self.mismatch_percentage:.2f}% "
            f"avg_latency_ms sqlite={self.average_sqlite_latency_ms:.2f} "
            f"postgres={self.average_postgres_latency_ms:.2f}"
        )


# One set of counters per entity type ("company", "opportunity"),
# accumulating for the process lifetime - summarized via
# get_reconciliation_summary(), not reset per-request.
_metrics: dict = {}


def _get_metrics(entity_type: str) -> ReconciliationMetrics:
    if entity_type not in _metrics:
        _metrics[entity_type] = ReconciliationMetrics(entity_type=entity_type)
    return _metrics[entity_type]


def get_reconciliation_summary(entity_type: Optional[str] = None) -> str:
    if entity_type:
        return _get_metrics(entity_type).as_text()
    if not _metrics:
        return "No shadow-read comparisons recorded yet."
    return "\n".join(metrics.as_text() for metrics in _metrics.values())


def reset_reconciliation_metrics() -> None:
    """Test/tooling hook - production code never needs to call this."""
    _metrics.clear()


def _normalize_datetime(value: datetime) -> datetime:
    # SQLite stores naive UTC (V2's datetime.utcnow()); Postgres's
    # TIMESTAMPTZ columns round-trip as timezone-aware UTC. Both
    # represent the same moment - normalize to naive UTC before
    # subtracting, or comparing an aware and a naive datetime raises
    # TypeError.
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _values_match(a, b) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        return _lists_match(a, b)
    if isinstance(a, BaseModel) and isinstance(b, BaseModel):
        return _models_match(a, b)
    if isinstance(a, datetime) and isinstance(b, datetime):
        return abs(_normalize_datetime(a) - _normalize_datetime(b)) <= _TIMESTAMP_TOLERANCE
    return a == b


def _lists_match(a: list, b: list) -> bool:
    if len(a) != len(b):
        return False
    if a and isinstance(a[0], BaseModel):
        a_by_id = {item.id: item for item in a}
        b_by_id = {item.id: item for item in b}
        if a_by_id.keys() != b_by_id.keys():
            return False
        return all(_models_match(a_by_id[key], b_by_id[key]) for key in a_by_id)
    return a == b


def _models_match(a: BaseModel, b: BaseModel) -> bool:
    if type(a) is not type(b):
        return False
    return all(_values_match(getattr(a, name), getattr(b, name)) for name in type(a).model_fields)


def results_match(a, b) -> bool:
    """Compares two dispatch_read results (a single domain model, a list
    of them, or None) for shadow-read reconciliation, tolerating small
    timestamp differences - see module docstring.
    """
    if a is None or b is None:
        return a is None and b is None
    return _values_match(a, b)


def dispatch_write(
    entity_type: str,
    operation: str,
    sqlite_call: Callable[[], T],
    postgres_call: Callable[[], None],
) -> T:
    """Executes a write per the current migration mode - see module
    docstring for per-mode behavior.
    """
    mode = get_migration_mode()

    if mode == MigrationMode.POSTGRES:
        return postgres_call()

    result = sqlite_call()

    if mode in (MigrationMode.DUAL_WRITE, MigrationMode.SHADOW_READ):
        try:
            postgres_call()
        except Exception:
            logger.exception(
                "Postgres dual-write failed for %s.%s (SQLite write already committed - no data was lost, "
                "but this record needs a backfill/reconciliation pass before cutover)",
                entity_type,
                operation,
            )

    return result


def dispatch_read(
    entity_type: str,
    operation: str,
    sqlite_call: Callable[[], T],
    postgres_call: Callable[[], T],
) -> T:
    """Executes a read per the current migration mode - see module
    docstring for per-mode behavior. In shadow_read mode, records
    reconciliation metrics but always returns SQLite's result.
    """
    mode = get_migration_mode()

    if mode == MigrationMode.POSTGRES:
        return postgres_call()

    if mode != MigrationMode.SHADOW_READ:
        return sqlite_call()

    start = time.perf_counter()
    sqlite_result = sqlite_call()
    sqlite_latency = time.perf_counter() - start

    try:
        start = time.perf_counter()
        postgres_result = postgres_call()
        postgres_latency = time.perf_counter() - start
        matched = results_match(sqlite_result, postgres_result)
        _get_metrics(entity_type).record(operation, matched, sqlite_latency, postgres_latency)
        if not matched:
            logger.warning(
                "Shadow-read mismatch for %s.%s: sqlite=%r postgres=%r",
                entity_type,
                operation,
                sqlite_result,
                postgres_result,
            )
    except Exception:
        logger.exception(
            "Shadow-read Postgres comparison failed for %s.%s (SQLite result still returned to the caller)",
            entity_type,
            operation,
        )

    return sqlite_result
