"""Unit tests for backend/ai/knowledge_fusion.py (V3 Phase 4A) - a pure
transformation, no database or LLM required.
"""

from backend.ai.knowledge_fusion import KnowledgeItem, fuse_knowledge


def test_fuse_knowledge_combines_all_three_sources():
    result = fuse_knowledge(
        company_name="Acme Corp",
        research=[KnowledgeItem(source="TechCrunch", content="Acme raised $50M")],
        semantic_search_results=[KnowledgeItem(source="ChromaDB", content="Similar case study: Beta Inc")],
        structured_knowledge=[KnowledgeItem(source="Postgres", content="Acme industry: SaaS")],
    )

    assert result.company_name == "Acme Corp"
    assert len(result.items) == 3
    assert result.duplicate_count == 0


def test_fuse_knowledge_deduplicates_identical_content_across_sources():
    result = fuse_knowledge(
        company_name="Acme Corp",
        research=[KnowledgeItem(source="TechCrunch", content="Acme raised $50M Series C")],
        semantic_search_results=[KnowledgeItem(source="ChromaDB", content="Acme raised $50M Series C")],
        structured_knowledge=[],
    )

    assert len(result.items) == 1
    assert result.duplicate_count == 1
    # The first (highest-priority - research) source's version is kept.
    assert result.items[0].source == "TechCrunch"


def test_fuse_knowledge_deduplication_is_whitespace_and_case_insensitive():
    result = fuse_knowledge(
        company_name="Acme Corp",
        research=[KnowledgeItem(source="A", content="Acme   raised $50M")],
        semantic_search_results=[KnowledgeItem(source="B", content="acme raised $50m")],
        structured_knowledge=[],
    )

    assert len(result.items) == 1
    assert result.duplicate_count == 1


def test_fuse_knowledge_sources_list_is_deduplicated_and_sorted():
    result = fuse_knowledge(
        company_name="Acme Corp",
        research=[KnowledgeItem(source="TechCrunch", content="Fact 1"), KnowledgeItem(source="TechCrunch", content="Fact 2")],
        semantic_search_results=[],
        structured_knowledge=[KnowledgeItem(source="Postgres", content="Fact 3")],
    )

    assert result.sources == ["Postgres", "TechCrunch"]


def test_fuse_knowledge_handles_all_empty_inputs():
    result = fuse_knowledge(company_name="Acme Corp", research=[], semantic_search_results=[], structured_knowledge=[])

    assert result.items == []
    assert result.sources == []
    assert result.duplicate_count == 0


def test_knowledge_fusion_never_imports_a_repository_or_orchestrator_module():
    import ast

    import backend.ai.knowledge_fusion as module

    with open(module.__file__) as f:
        tree = ast.parse(f.read())

    imported_modules = [
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    ] + [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]

    assert not any("repositor" in name.lower() for name in imported_modules)
    assert not any("orchestrat" in name.lower() for name in imported_modules)
    assert not any("postgres" in name.lower() for name in imported_modules)
