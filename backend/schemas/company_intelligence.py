"""Response schema for GET /api/v1/companies/{company_id}/intelligence
(V3 Phase 7A). Serializes
backend/services/company_intelligence_service.py's
CompanyIntelligenceProfile (built entirely in Phase 5) - this endpoint
adds no new aggregation logic, only a read-only view over it.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CompanyOut(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    monitoring_status: str

    model_config = {"from_attributes": True}


class TechnologyOut(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    adoption_status: Optional[str] = None
    business_relevance: Optional[str] = None
    confidence_score: Optional[float] = None
    source: Optional[str] = None

    model_config = {"from_attributes": True}


class BusinessInitiativeOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    confidence_score: Optional[float] = None

    model_config = {"from_attributes": True}


class ExecutiveOut(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    department: Optional[str] = None
    biography: Optional[str] = None
    linkedin_url: Optional[str] = None
    confidence_score: Optional[float] = None

    model_config = {"from_attributes": True}


class SignalOut(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    date_detected: datetime

    model_config = {"from_attributes": True}


class GleanKnowledgeItemOut(BaseModel):
    source: str
    content: str
    category: Optional[str] = None

    model_config = {"from_attributes": True}


class CompanyIntelligenceResponse(BaseModel):
    company: CompanyOut
    technologies: List[TechnologyOut]
    business_initiatives: List[BusinessInitiativeOut]
    executives: List[ExecutiveOut]
    recent_signals: List[SignalOut]
    glean_knowledge: List[GleanKnowledgeItemOut]
