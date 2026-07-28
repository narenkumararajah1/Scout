"""PostgreSQL ORM entities (SQLAlchemy declarative models).

Deliberately separate from backend/models/, which holds V2's plain
dataclasses returned by the SQLite repositories - those are domain/business
objects, not persistence entities, and V3 keeps the two apart rather than
mixing ORM classes into that package.
"""

from backend.database.models.business_initiative import BusinessInitiative
from backend.database.models.company import Company
from backend.database.models.company_relationship import CompanyRelationship
from backend.database.models.company_view import CompanyView
from backend.database.models.evidence import Evidence
from backend.database.models.executive import Executive
from backend.database.models.generation_feedback import GenerationFeedback
from backend.database.models.generation_job import GenerationJob
from backend.database.models.meeting_brief import MeetingBrief
from backend.database.models.notification import Notification
from backend.database.models.opportunity import Opportunity
from backend.database.models.outreach_draft import OutreachDraft
from backend.database.models.report import Report
from backend.database.models.sales_playbook import SalesPlaybook
from backend.database.models.technology import Technology
from backend.database.models.user import User
from backend.database.postgres import Base

__all__ = [
    "Base",
    "User",
    "Company",
    "Executive",
    "Opportunity",
    "Evidence",
    "Technology",
    "BusinessInitiative",
    "Notification",
    "SalesPlaybook",
    "MeetingBrief",
    "OutreachDraft",
    "Report",
    "GenerationJob",
    "GenerationFeedback",
    "CompanyView",
    "CompanyRelationship",
]
