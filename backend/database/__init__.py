"""Persistence layer: SQLite (active) and PostgreSQL (V3 Phase 1+, see TECH_DEBT.md)."""

from backend.database.sqlite import check_connection, get_connection

__all__ = ["get_connection", "check_connection"]
