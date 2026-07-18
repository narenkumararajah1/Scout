"""Innominds Intelligence Layer knowledge entities (V2 Phase 5,
docs/V2/DATA_MODEL.md's Knowledge Base section).

This data changes infrequently and is curated manually (DATA_MODEL.md) -
Scout does not generate or infer Innominds' own capabilities/services via
LLM research. Stored exclusively in ChromaDB per ADR-007/ADR-008 and the
Database Rules ("ChromaDB is the source of truth for semantic
knowledge") - no SQLite table exists for these entities.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class Capability(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    practice: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)


class Service(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str


class Industry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None


class Technology(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None


class CaseStudy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer: str
    industry: Optional[str] = None
    challenge: str
    solution: str
    outcome: str


class Partnership(BaseModel):
    # Listed in DATA_MODEL.md's Knowledge Base tree but not given its own
    # attributes section there - modeled minimally, matching Service's/
    # Industry's/Technology's equally thin documentation.
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None


class ProofPoint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    # e.g. "customer_success", "industry_experience", "partnership",
    # "certification" - DATA_MODEL.md's example categories, not a closed
    # enum (same open-category treatment as Signal's SIGNAL_TYPE_*).
    category: Optional[str] = None
