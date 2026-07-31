"""Round 3 regressions: request text that overflows its target column.

The pattern behind every case here: a request model accepted an
unbounded `str`, the value reached a `String(n)` column, and Postgres
raised StringDataRightTruncation. Where that happened inside a
background generation job it was worse than a 500 - the endpoint
answered "generation started", the job then failed asynchronously
*after* spending an LLM call on each retry, and the user was never told.

Each test names the column bound it is defending, so a future migration
that widens or narrows a column has an obvious place to update.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.api.routers.meeting_briefs import GenerateMeetingBriefRequest
from backend.api.routers.outreach_drafts import (
    GenerateOutreachDraftRequest,
    UpdateOutreachDraftRequest,
)
from backend.api.routers.reports import GenerateV3ReportRequest
from backend.schemas.company_relationship import CreateCompanyRelationshipRequest
from backend.schemas.knowledge_document import (
    IngestWebsiteRequest,
    UpdateKnowledgeMetadataRequest,
)

COMPANY = "11111111-1111-1111-1111-111111111111"


class TestOversizedTextIsRejectedAtTheBoundary:
    """422 at submit, rather than a failed job nobody sees."""

    @pytest.mark.parametrize(
        "model, payload, field, limit",
        [
            # v3_reports.title
            (GenerateV3ReportRequest, {"company_id": COMPANY, "title": "A" * 256}, "title", 255),
            # meeting_briefs.meeting_title
            (
                GenerateMeetingBriefRequest,
                {"company_id": COMPANY, "meeting_title": "A" * 256},
                "meeting_title",
                255,
            ),
            # company_relationships.related_company_name
            (
                CreateCompanyRelationshipRequest,
                {"relationship_type": "competitor", "related_company_name": "A" * 256},
                "related_company_name",
                255,
            ),
            # outreach_drafts.subject
            (
                UpdateOutreachDraftRequest,
                {"subject": "A" * 501, "content": "body"},
                "subject",
                500,
            ),
            # outreach_drafts.type
            (
                GenerateOutreachDraftRequest,
                {"company_id": COMPANY, "outreach_type": "A" * 51},
                "outreach_type",
                50,
            ),
            # knowledge_documents.title
            (
                UpdateKnowledgeMetadataRequest,
                {"title": "A" * 501},
                "title",
                500,
            ),
            # knowledge_documents.author
            (
                UpdateKnowledgeMetadataRequest,
                {"author": "A" * 256},
                "author",
                255,
            ),
        ],
    )
    def test_rejects_over_limit(self, model, payload, field, limit):
        with pytest.raises(ValidationError) as exc:
            model(**payload)
        message = str(exc.value)
        assert field in message
        assert str(limit) in message

    def test_category_is_guarded_by_its_vocabulary_not_its_length(self):
        """knowledge_documents.category is String(40), but the binding
        constraint is the closed category vocabulary, which is far
        stricter than any length bound. The length type on the field is
        only a backstop, so this asserts the guard that actually governs.
        """
        from backend.services.knowledge_ingestion_service import _validate_category, IngestionError

        with pytest.raises(IngestionError):
            _validate_category("A" * 41)
        assert _validate_category("case_studies") == "case_studies"

    def test_exactly_at_the_limit_is_accepted(self):
        """Off-by-one guard: the limit is inclusive."""
        request = GenerateV3ReportRequest(company_id=COMPANY, title="A" * 255)
        assert len(request.title) == 255


class TestTextIsSanitisedNotRejected:
    """Control characters are stripped; the request still succeeds.

    A NUL byte cannot reach Postgres, but a title containing one is a
    paste artifact rather than an attack - silently cleaning it is the
    behaviour that does not lose the user's work.
    """

    def test_nul_is_stripped_from_a_title(self):
        assert GenerateV3ReportRequest(company_id=COMPANY, title="Q3 \x00Review").title == "Q3 Review"

    def test_whitespace_is_collapsed(self):
        request = GenerateMeetingBriefRequest(company_id=COMPANY, meeting_title="  Board   sync  ")
        assert request.meeting_title == "Board sync"

    def test_blank_optional_becomes_none(self):
        """"   " is not a title; storing it would render as an empty heading."""
        assert GenerateV3ReportRequest(company_id=COMPANY, title="   ").title is None

    def test_none_stays_none(self):
        assert GenerateV3ReportRequest(company_id=COMPANY, title=None).title is None


class TestResponseModelsAreNotConstrained:
    """The bound belongs on input, not on what is read back.

    An earlier version of this fix landed the validator on
    CompanyRelationshipOut - the response model - instead of the request
    model, because both declare a related_company_name. Rows already in
    the database must still be readable whatever their length.
    """

    def test_response_model_accepts_a_long_existing_value(self):
        from backend.schemas.company_relationship import CompanyRelationshipOut

        out = CompanyRelationshipOut(
            id="r1",
            company_id=COMPANY,
            relationship_type="competitor",
            related_company_name="A" * 400,
            created_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
        )
        assert len(out.related_company_name) == 400
