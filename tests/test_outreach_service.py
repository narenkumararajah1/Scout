"""Integration tests for backend/services/outreach_service.py (V3 Phase 6).

Postgres-gated (persistence) with the LLM call mocked. Includes the
Phase 6 safety-invariant tests: generated drafts can only ever be
"Draft" status, and the module has no send-capable functionality and no
dependency on any messaging provider.
"""

import ast
import json
from unittest.mock import patch

import pytest

from backend.database.models import Company
from backend.repositories.postgres.company_repository import create_company
from backend.services.outreach_service import SUPPORTED_OUTREACH_TYPES, generate_outreach_draft


def _mock_response() -> str:
    return json.dumps({"subject": "Following up on our conversation", "content": "Hi Jane, ..."})


async def test_generate_outreach_draft_persists_as_draft_status(postgres_available):
    await create_company(Company(id="out-svc-company-1", name="OutSvcCo"))

    with patch("backend.services.outreach_service.generate_completion", return_value=_mock_response()):
        draft = await generate_outreach_draft(
            Company(id="out-svc-company-1", name="OutSvcCo"),
            outreach_type="Email",
            executive_name="Jane Doe",
            talking_points=["Kubernetes rollout"],
        )

    assert draft.status == "Draft"
    assert draft.subject == "Following up on our conversation"
    assert draft.type == "Email"


async def test_generate_outreach_draft_rejects_an_unsupported_type():
    # No Postgres or LLM call involved - the type check happens first.
    with pytest.raises(ValueError, match="Unsupported outreach type"):
        await generate_outreach_draft(
            Company(id="out-svc-company-2", name="OutSvcCo2"),
            outreach_type="Cold Call",
            executive_name="Jane Doe",
            talking_points=[],
        )


def test_all_supported_types_match_the_documented_data_model():
    assert set(SUPPORTED_OUTREACH_TYPES) == {"Email", "Follow-up", "Meeting Request", "LinkedIn Message"}


def test_outreach_service_never_imports_a_messaging_provider_dependency():
    """Static check, not just behavioral: the module must have no
    dependency on SMTP, Outlook, Gmail, SendGrid, SES, or any other
    messaging provider - checked at the import-statement level, same
    technique used for Knowledge Extraction/Fusion in Phase 4A.
    """
    import backend.services.outreach_service as module

    with open(module.__file__) as f:
        tree = ast.parse(f.read())

    imported_modules = [
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    ] + [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]

    forbidden_terms = ("smtplib", "smtp", "outlook", "gmail", "sendgrid", "ses", "boto3", "requests", "httpx")
    for name in imported_modules:
        assert not any(term in name.lower() for term in forbidden_terms), f"forbidden import found: {name}"


def test_outreach_service_has_no_send_capable_function():
    """No function anywhere in the module has a name suggesting it sends,
    delivers, or dispatches anything - only generation and drafting.
    """
    import backend.services.outreach_service as module

    with open(module.__file__) as f:
        tree = ast.parse(f.read())

    function_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef)]

    forbidden_name_fragments = ("send", "deliver", "dispatch", "email_out", "transmit")
    for name in function_names:
        assert not any(fragment in name.lower() for fragment in forbidden_name_fragments), (
            f"function name suggests send capability: {name}"
        )
