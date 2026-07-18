"""Scout V2 core data model (docs/V2/DATA_MODEL.md).

Pydantic models for the business entities introduced in V2 Phase 2, the
Innominds Intelligence Layer knowledge entities added in Phase 5, and
the Capability Match entity added in Phase 6. These represent the
canonical entities only - persistence lives in backend/repositories, and
nothing here is wired into the live V1 workflow yet (that begins in
later roadmap phases).
"""

from backend.models.capability_match import CapabilityMatch
from backend.models.company import Company
from backend.models.knowledge import (
    CaseStudy,
    Capability,
    Industry,
    Partnership,
    ProofPoint,
    Service,
    Technology,
)
from backend.models.opportunity import Opportunity
from backend.models.recipient import Delivery, Recipient
from backend.models.report import Report
from backend.models.research import ResearchSession, Signal
from backend.models.schedule import Schedule

__all__ = [
    "Company",
    "ResearchSession",
    "Signal",
    "Opportunity",
    "Report",
    "Recipient",
    "Delivery",
    "Schedule",
    "Capability",
    "Service",
    "Industry",
    "Technology",
    "CaseStudy",
    "Partnership",
    "ProofPoint",
    "CapabilityMatch",
]
