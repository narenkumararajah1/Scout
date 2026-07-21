"""Tests for backend/ai/prompts/ - Prompt Management, physically
relocated here from backend/prompts/ in V3 Phase 4B (see TECH_DEBT.md).
Light smoke tests confirming each prompt builder is importable from its
new home and still produces sensible output; the services that actually
consume these (research_service.py etc.) exercise them more thoroughly
via their own tests.
"""

from backend.ai.prompts.capability_matching_prompts import build_capability_matching_prompt
from backend.ai.prompts.conversation_prompts import build_conversation_prompt
from backend.ai.prompts.opportunity_analysis_prompts import build_opportunity_analysis_prompt
from backend.ai.prompts.reporting_prompts import build_report_prompt
from backend.ai.prompts.research_prompts import (
    build_company_technology_prompt,
    build_merge_prompt,
    build_organizational_strategic_prompt,
    build_signal_extraction_prompt,
)


def test_build_capability_matching_prompt_includes_the_company_name():
    prompt = build_capability_matching_prompt("Acme Corp", [], [], [], [])
    assert "Acme Corp" in prompt


def test_build_conversation_prompt_includes_the_question():
    prompt = build_conversation_prompt("What opportunities exist?", [])
    assert "What opportunities exist?" in prompt


def test_build_opportunity_analysis_prompt_includes_the_company_name():
    prompt = build_opportunity_analysis_prompt("Acme Corp", [])
    assert "Acme Corp" in prompt


def test_build_report_prompt_includes_the_company_name():
    prompt = build_report_prompt("Acme Corp", "summary", [], [], [])
    assert "Acme Corp" in prompt


def test_build_company_technology_prompt_includes_the_company_name():
    assert "Acme Corp" in build_company_technology_prompt("Acme Corp")


def test_build_organizational_strategic_prompt_includes_the_company_name():
    assert "Acme Corp" in build_organizational_strategic_prompt("Acme Corp")


def test_build_merge_prompt_includes_both_research_summaries():
    prompt = build_merge_prompt("Acme Corp", "technology research", "strategic research")
    assert "technology research" in prompt
    assert "strategic research" in prompt


def test_build_signal_extraction_prompt_includes_the_unified_research():
    prompt = build_signal_extraction_prompt("Acme Corp", "unified research summary")
    assert "unified research summary" in prompt
