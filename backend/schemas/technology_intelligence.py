"""Technology Intelligence response schema.

Mirrors backend/services/technology_intelligence_service.py::describe().

Every field beyond the identity is *evidence*, not decoration. The
lifecycle label alone would ask a user to trust a verdict; the counters
and the evidence sentence let them check it, which matters more here than
elsewhere because this replaced a feature that was confidently wrong.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TechnologyObservation(BaseModel):
    source: str
    observed_at: str
    research_session_id: Optional[str] = None


class TechnologyIntelligenceOut(BaseModel):
    id: str
    company_id: str
    name: str
    category: Optional[str] = None

    lifecycle: str
    lifecycle_label: str
    # Carried in the payload rather than mapped in the frontend so the
    # careful wording - particularly that "not observed recently" is not
    # evidence of removal - cannot be lost in translation to a surface
    # that never read the service.
    lifecycle_description: str

    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    observation_count: int
    missed_count: int
    consecutive_misses: int
    # The observation rate, not a tuned score: observations / times looked.
    confidence: float
    evidence_summary: str
    observation_sources: list = []
