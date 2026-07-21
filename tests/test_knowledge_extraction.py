"""Unit tests for backend/ai/knowledge_extraction.py (V3 Phase 4A) - the
LLM call is mocked, so these run without a real provider or database.
Confirms it never touches persistence, per the Stage 4A decision.
"""

import json
from unittest.mock import patch

import pytest

from backend.ai.knowledge_extraction import (
    ExtractedBusinessInitiative,
    ExtractedExecutive,
    ExtractedTechnology,
    extract_entities,
)


def _mock_response(technologies=None, executives=None, business_initiatives=None) -> str:
    return json.dumps(
        {
            "technologies": technologies or [],
            "executives": executives or [],
            "business_initiatives": business_initiatives or [],
        }
    )


def test_extract_entities_parses_all_three_entity_types():
    response = _mock_response(
        technologies=[{"name": "Kubernetes", "category": "infrastructure"}],
        executives=[{"name": "Jane Doe", "title": "CTO"}],
        business_initiatives=[{"name": "Cloud Migration", "description": "Moving to AWS"}],
    )

    with patch("backend.ai.knowledge_extraction.generate_completion", return_value=response):
        result = extract_entities("some research text", "Acme Corp")

    assert result.technologies == [ExtractedTechnology(name="Kubernetes", category="infrastructure", context=None)]
    assert result.executives == [ExtractedExecutive(name="Jane Doe", title="CTO", context=None)]
    assert result.business_initiatives == [
        ExtractedBusinessInitiative(name="Cloud Migration", description="Moving to AWS", context=None)
    ]


def test_extract_entities_handles_no_entities_found():
    with patch("backend.ai.knowledge_extraction.generate_completion", return_value=_mock_response()):
        result = extract_entities("irrelevant text", "Acme Corp")

    assert result.technologies == []
    assert result.executives == []
    assert result.business_initiatives == []


def test_extract_entities_ignores_unexpected_extra_fields():
    response = _mock_response(technologies=[{"name": "Kubernetes", "unexpected_field": "should be dropped"}])

    with patch("backend.ai.knowledge_extraction.generate_completion", return_value=response):
        result = extract_entities("some research text", "Acme Corp")

    assert result.technologies == [ExtractedTechnology(name="Kubernetes", category=None, context=None)]


def test_extract_entities_raises_on_invalid_json():
    with patch("backend.ai.knowledge_extraction.generate_completion", return_value="not valid json"):
        with pytest.raises(ValueError):
            extract_entities("some research text", "Acme Corp")


def test_extract_entities_never_imports_a_repository_or_persistence_module():
    import ast

    import backend.ai.knowledge_extraction as module

    with open(module.__file__) as f:
        tree = ast.parse(f.read())

    imported_modules = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ] + [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]

    assert not any("repositor" in name.lower() for name in imported_modules)
    assert not any("postgres" in name.lower() for name in imported_modules)
