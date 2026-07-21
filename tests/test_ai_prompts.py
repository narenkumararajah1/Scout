"""Tests for backend/ai/prompts/ (V3 Phase 4A) - confirms the re-export
package produces identical output to backend/prompts/, without
physically moving it.
"""

import backend.ai.prompts.capability_matching_prompts as new_capability
import backend.ai.prompts.conversation_prompts as new_conversation
import backend.ai.prompts.opportunity_analysis_prompts as new_opportunity
import backend.ai.prompts.reporting_prompts as new_reporting
import backend.ai.prompts.research_prompts as new_research
import backend.prompts.capability_matching_prompts as old_capability
import backend.prompts.conversation_prompts as old_conversation
import backend.prompts.opportunity_analysis_prompts as old_opportunity
import backend.prompts.reporting_prompts as old_reporting
import backend.prompts.research_prompts as old_research


def test_capability_matching_prompt_is_the_same_function():
    assert new_capability.build_capability_matching_prompt is old_capability.build_capability_matching_prompt


def test_conversation_prompt_is_the_same_function():
    assert new_conversation.build_conversation_prompt is old_conversation.build_conversation_prompt


def test_opportunity_analysis_prompt_is_the_same_function():
    assert new_opportunity.build_opportunity_analysis_prompt is old_opportunity.build_opportunity_analysis_prompt


def test_reporting_prompt_is_the_same_function():
    assert new_reporting.build_report_prompt is old_reporting.build_report_prompt


def test_research_prompts_are_the_same_functions():
    assert new_research.build_company_technology_prompt is old_research.build_company_technology_prompt
    assert new_research.build_merge_prompt is old_research.build_merge_prompt
    assert new_research.build_organizational_strategic_prompt is old_research.build_organizational_strategic_prompt
    assert new_research.build_signal_extraction_prompt is old_research.build_signal_extraction_prompt
