"""Schemas for company-to-company relationships (roadmap Phase 6 -
Relationship Intelligence, basic level).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CompanyRelationshipOut(BaseModel):
    id: str
    company_id: str
    related_company_id: Optional[str] = None
    related_company_name: Optional[str] = None
    relationship_type: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateCompanyRelationshipRequest(BaseModel):
    relationship_type: str = Field(min_length=1)
    related_company_id: Optional[str] = None
    related_company_name: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _require_one_related_field(self) -> "CreateCompanyRelationshipRequest":
        if not self.related_company_id and not self.related_company_name:
            raise ValueError("Provide either related_company_id or related_company_name.")
        return self
