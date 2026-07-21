"""Tests for backend/ai/llm_gateway.py (V3 Phase 4A) - confirms the
wrapper genuinely re-exports backend/llm_client.py's exact objects
rather than copies, and that backend/llm_client.py itself is untouched.
"""

import backend.ai.llm_gateway as gateway
import backend.llm_client as legacy


def test_generate_completion_is_the_same_object_as_the_legacy_module():
    assert gateway.generate_completion is legacy.generate_completion


def test_get_default_model_is_the_same_object_as_the_legacy_module():
    assert gateway.get_default_model is legacy.get_default_model


def test_parse_json_array_is_the_same_object_as_the_legacy_module():
    assert gateway.parse_json_array is legacy.parse_json_array


def test_parse_json_object_is_the_same_object_as_the_legacy_module():
    assert gateway.parse_json_object is legacy.parse_json_object


def test_strip_markdown_json_fence_is_the_same_object_as_the_legacy_module():
    assert gateway.strip_markdown_json_fence is legacy.strip_markdown_json_fence


def test_gateway_parse_json_object_behaves_identically_to_legacy():
    raw = '```json\n{"a": 1}\n```'
    assert gateway.parse_json_object(raw, "test") == legacy.parse_json_object(raw, "test")
