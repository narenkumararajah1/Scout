"""Postgres-backed repositories (V3 Phase 3A onward).

Namespaced under postgres/ - not merged into backend/repositories/'s top
level - because company_repository.py and opportunity_repository.py
already exist there as V2's live SQLite implementations. Stage B decides
if/how the two namespaces get reconciled; Stage A leaves V2's repositories
completely untouched.
"""
