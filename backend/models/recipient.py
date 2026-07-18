"""Recipient and Delivery entities (docs/V2/DATA_MODEL.md).

A Recipient is a configured destination for report distribution. A
Delivery is one immutable record of a report being sent to a recipient
through a channel - the audit trail behind DATA_MODEL.md's "Recipient
Many -> Many Reports" relationship.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Recipient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    delivery_status: Optional[str] = None
    preferred_frequency: Optional[str] = None
    preferred_company_ids: list[str] = Field(default_factory=list)
    preferred_channels: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Delivery(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recipient_id: str
    report_id: str
    channel: str
    delivery_time: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"
