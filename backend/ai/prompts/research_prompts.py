"""Re-exports backend/prompts/research_prompts.py unchanged - see backend/ai/prompts/__init__.py."""

from backend.prompts.research_prompts import (
    build_company_technology_prompt,
    build_merge_prompt,
    build_organizational_strategic_prompt,
    build_signal_extraction_prompt,
)

__all__ = [
    "build_company_technology_prompt",
    "build_merge_prompt",
    "build_organizational_strategic_prompt",
    "build_signal_extraction_prompt",
]
