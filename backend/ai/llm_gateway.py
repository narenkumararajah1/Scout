"""LLM Gateway (V3 Phase 4A - ADR-016).

Wraps backend/llm_client.py rather than relocating it - per the Stage 4A
decision, the old module stays intact and is what every existing V2
agent still imports from, completely unchanged, until Stage 4B actually
cuts orchestration over (see TECH_DEBT.md). This gives new Phase 4A AI
components (Confidence Engine, Knowledge Extraction, Knowledge Fusion) a
stable backend/ai/ import path without touching anything V2 currently
uses.
"""

from backend.llm_client import (
    generate_completion,
    get_default_model,
    parse_json_array,
    parse_json_object,
    strip_markdown_json_fence,
)

__all__ = [
    "generate_completion",
    "get_default_model",
    "parse_json_array",
    "parse_json_object",
    "strip_markdown_json_fence",
]
