"""Prompt Management (V3 Phase 4B).

Physically relocated here from backend/prompts/ in V3 Phase 4B, after
Phase 4A's re-export wrapper (which briefly lived at this path) and
every test kept passing - see TECH_DEBT.md. Every service that used to
import backend.prompts.* now imports from here instead; behavior is
unchanged.
"""
