"""Knowledge Extraction (V3 Phase 4A - docs/v3/04_AI_WORKFLOW.md Stage 5,
docs/v3/05_KNOWLEDGE_ARCHITECTURE.md's Knowledge Extraction section).

Converts raw research text into structured entities via the LLM Gateway.
Deliberately independent of persistence, per the Stage 4A decision:
returns plain dataclasses only - it never calls a repository or writes
to PostgreSQL. Persisting the entities this returns (e.g. into
backend/database/models.py's Company/Executive tables) is a separate
caller's responsibility, not this module's - see TECH_DEBT.md.

Not called by any existing agent or orchestration path yet - V2's
knowledge_ingestion.py continues to only ingest freeform documents into
ChromaDB, unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.ai.llm_gateway import generate_completion, parse_json_object


@dataclass
class ExtractedTechnology:
    name: str
    category: Optional[str] = None
    context: Optional[str] = None


@dataclass
class ExtractedExecutive:
    name: str
    title: Optional[str] = None
    context: Optional[str] = None


@dataclass
class ExtractedBusinessInitiative:
    name: str
    description: Optional[str] = None
    context: Optional[str] = None


@dataclass
class ExtractedEntities:
    technologies: list = field(default_factory=list)
    executives: list = field(default_factory=list)
    business_initiatives: list = field(default_factory=list)


_EXTRACTION_PROMPT_TEMPLATE = """You are extracting structured business intelligence from raw research \
text about {company_name}.

Read the following research and extract every technology, executive, and business initiative it \
mentions. Respond with a single JSON object with exactly these keys: "technologies", "executives", \
"business_initiatives". Each is a JSON array of objects.

- Each technology object has "name" (required), "category" (optional), "context" (optional - the \
  sentence or phrase that mentioned it).
- Each executive object has "name" (required), "title" (optional), "context" (optional).
- Each business initiative object has "name" (required), "description" (optional), "context" (optional).

If nothing of a given type is mentioned, return an empty array for it. Respond with raw JSON only, \
no markdown fence.

Research:
{raw_text}
"""


def _build_extraction_prompt(raw_text: str, company_name: str) -> str:
    return _EXTRACTION_PROMPT_TEMPLATE.format(company_name=company_name, raw_text=raw_text)


def _to_dataclass(cls, item: dict):
    # Keeps only the keys the dataclass actually declares - a model
    # occasionally adding an extra, unrequested field to its JSON
    # shouldn't break extraction with a TypeError.
    known_fields = {f.name for f in cls.__dataclass_fields__.values()}
    return cls(**{key: value for key, value in item.items() if key in known_fields})


def extract_entities(raw_text: str, company_name: str) -> ExtractedEntities:
    """Extracts structured entities from raw_text via the LLM Gateway.

    Raises ValueError (via parse_json_object) if the model's response
    isn't valid JSON - callers are responsible for handling that, same
    as every other LLM Gateway consumer.
    """
    prompt = _build_extraction_prompt(raw_text, company_name)
    response = generate_completion(prompt)
    parsed = parse_json_object(response, "extract_entities")

    return ExtractedEntities(
        technologies=[_to_dataclass(ExtractedTechnology, item) for item in parsed.get("technologies", [])],
        executives=[_to_dataclass(ExtractedExecutive, item) for item in parsed.get("executives", [])],
        business_initiatives=[
            _to_dataclass(ExtractedBusinessInitiative, item)
            for item in parsed.get("business_initiatives", [])
        ],
    )
