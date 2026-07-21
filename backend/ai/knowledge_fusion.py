"""Knowledge Fusion (V3 Phase 4A - docs/v3/04_AI_WORKFLOW.md Stage 4,
docs/v3/05_KNOWLEDGE_ARCHITECTURE.md's Knowledge Fusion section - "the
core of Scout V3").

A pure transformation service, per the Stage 4A decision: takes research,
semantic search results, and structured knowledge as plain inputs and
returns a unified context - no repository calls, no orchestrator calls,
no side effects. Not called by any existing agent or orchestration path
yet - see TECH_DEBT.md.

Deduplicates by exact (normalized) content match rather than an LLM call,
so this stays deterministic and cheaply unit-testable without mocking a
model - conflict *resolution* beyond simple deduplication is left to a
later phase's AI Reasoning stage, which operates on this stage's output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KnowledgeItem:
    source: str
    content: str
    category: Optional[str] = None


@dataclass
class UnifiedKnowledgeContext:
    company_name: str
    items: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    duplicate_count: int = 0


def _normalize(content: str) -> str:
    return " ".join(content.strip().lower().split())


def fuse_knowledge(
    company_name: str,
    research: list,
    semantic_search_results: list,
    structured_knowledge: list,
) -> UnifiedKnowledgeContext:
    """Merges research, semantic_search_results, and structured_knowledge
    (each a list[KnowledgeItem]) into one deduplicated, source-attributed
    context, in that priority order (research first, then semantic
    search, then structured knowledge) - later duplicates of an earlier
    item are dropped, so the first (highest-priority) source's version
    of any given fact is what's kept.
    """
    combined = list(research) + list(semantic_search_results) + list(structured_knowledge)

    seen_content = set()
    unified_items = []
    duplicate_count = 0

    for item in combined:
        normalized = _normalize(item.content)
        if normalized in seen_content:
            duplicate_count += 1
            continue
        seen_content.add(normalized)
        unified_items.append(item)

    sources = sorted({item.source for item in unified_items})

    return UnifiedKnowledgeContext(
        company_name=company_name,
        items=unified_items,
        sources=sources,
        duplicate_count=duplicate_count,
    )
