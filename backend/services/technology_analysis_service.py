"""Technology Landscape Analysis (V3 Phase 5 -
docs/v3/06_FEATURE_SPECIFICATIONS.md Feature 4).

Enriches an already-persisted Technology record (see
backend/services/company_intelligence_service.py, which persists
Knowledge Extraction's bare name/category output) with adoption status,
business relevance, industry context, and related Innominds services -
reusing the LLM Gateway, ChromaDB semantic search (same technique
capability_matching_service.py already uses), and the Confidence Engine.

Not called by any existing agent, service, or router - see TECH_DEBT.md.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from backend.ai.confidence_engine import EvidenceItem, calculate_confidence
from backend.ai.llm_gateway import generate_completion, parse_json_object
from backend.ai.prompts.technology_analysis_prompts import build_technology_analysis_prompt
from backend.database.models import Technology
from backend.repositories.knowledge_repository import search_knowledge
from backend.repositories.postgres.technology_repository import upsert_technology

MAX_RELATED_SERVICE_RESULTS = 3

_EXPECTED_FIELDS = ["adoption_status", "business_relevance", "industry_context"]


@dataclass
class TechnologyAnalysisResult:
    technology_name: str
    adoption_status: str = ""
    business_relevance: str = ""
    industry_context: str = ""
    related_services: list = field(default_factory=list)
    confidence: object = None  # backend.ai.confidence_engine.ConfidenceResult


async def analyze_technology(technology: Technology, company_name: str) -> TechnologyAnalysisResult:
    related = await asyncio.to_thread(
        search_knowledge, technology.name, MAX_RELATED_SERVICE_RESULTS, "service"
    )

    prompt = build_technology_analysis_prompt(
        company_name, technology.name, technology.category, [r["content"] for r in related]
    )
    response = await asyncio.to_thread(generate_completion, prompt)
    parsed = parse_json_object(response, "Technology Analysis Service")

    evidence_items = [EvidenceItem(source=f"service:{r.get('name', 'unknown')}", reliability=0.7) for r in related]
    present_fields = [name for name in _EXPECTED_FIELDS if parsed.get(name)]
    confidence = calculate_confidence(
        evidence=evidence_items, expected_fields=_EXPECTED_FIELDS, present_fields=present_fields
    )

    return TechnologyAnalysisResult(
        technology_name=technology.name,
        adoption_status=parsed.get("adoption_status", ""),
        business_relevance=parsed.get("business_relevance", ""),
        industry_context=parsed.get("industry_context", ""),
        related_services=[r.get("name") for r in related if r.get("name")],
        confidence=confidence,
    )


async def analyze_and_persist_technology(technology: Technology, company_name: str) -> Technology:
    result = await analyze_technology(technology, company_name)
    technology.adoption_status = result.adoption_status
    technology.business_relevance = result.business_relevance
    technology.confidence_score = result.confidence.score
    return await upsert_technology(technology)
