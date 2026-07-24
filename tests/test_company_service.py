import pytest

from backend.models.research import ResearchSession
from backend.repositories import company_repository
from backend.repositories.research_repository import create_research_session
from backend.services import company_service
from tests.conftest import clear_v2_tables


def test_add_company_persists_it():
    clear_v2_tables()
    company = company_service.add_company(name="Acme Corp", industry="Manufacturing")

    fetched = company_repository.get_company(company.id)
    assert fetched is not None
    assert fetched.name == "Acme Corp"
    assert fetched.industry == "Manufacturing"
    assert fetched.monitoring_status == "enabled"


def test_get_company_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        company_service.get_company("does-not-exist")


def test_list_companies_returns_all():
    clear_v2_tables()
    company_service.add_company(name="First Co")
    company_service.add_company(name="Second Co")

    companies = company_service.list_companies()

    assert {c.name for c in companies} == {"First Co", "Second Co"}


def test_list_companies_excludes_archived_by_default():
    clear_v2_tables()
    company_service.add_company(name="Active Co")
    archived = company_service.add_company(name="Archived Co")
    company_service.archive_company(archived.id)

    companies = company_service.list_companies()

    assert {c.name for c in companies} == {"Active Co"}


def test_list_companies_includes_archived_when_requested():
    clear_v2_tables()
    company_service.add_company(name="Active Co")
    archived = company_service.add_company(name="Archived Co")
    company_service.archive_company(archived.id)

    companies = company_service.list_companies(include_archived=True)

    assert {c.name for c in companies} == {"Active Co", "Archived Co"}


def test_archive_company_sets_archived_at():
    clear_v2_tables()
    company = company_service.add_company(name="Acme Corp")
    assert company.archived_at is None

    archived = company_service.archive_company(company.id)

    assert archived.archived_at is not None


def test_archive_company_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        company_service.archive_company("does-not-exist")


def test_restore_company_clears_archived_at():
    clear_v2_tables()
    company = company_service.add_company(name="Acme Corp")
    company_service.archive_company(company.id)

    restored = company_service.restore_company(company.id)

    assert restored.archived_at is None


def test_archive_company_preserves_relationships():
    """Priority 5: "existing relationships should remain recoverable" -
    archiving a company with real historical data must not touch that
    data at all, unlike the old hard-delete path which was blocked by it."""
    clear_v2_tables()
    company = company_service.add_company(name="Acme Corp")
    create_research_session(ResearchSession(company_id=company.id, status="completed"))

    company_service.archive_company(company.id)

    assert company_repository.get_company(company.id) is not None


def test_remove_company_deletes_it_once_archived():
    clear_v2_tables()
    company = company_service.add_company(name="Temporary Co")
    company_service.archive_company(company.id)

    company_service.remove_company(company.id)

    assert company_repository.get_company(company.id) is None


def test_remove_company_raises_if_not_archived_first():
    clear_v2_tables()
    company = company_service.add_company(name="Acme Corp")

    with pytest.raises(ValueError, match="must be archived"):
        company_service.remove_company(company.id)

    assert company_repository.get_company(company.id) is not None


def test_remove_company_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        company_service.remove_company("does-not-exist")


def test_remove_company_raises_meaningful_error_when_blocked_by_history():
    """Data integrity: an archived company with real historical data
    (research sessions, opportunities, reports) must still not be
    permanently deletable - the FK constraint blocks the delete, and the
    service must translate that into a clear error rather than an opaque
    sqlite3.IntegrityError."""
    clear_v2_tables()
    company = company_service.add_company(name="Acme Corp")
    create_research_session(ResearchSession(company_id=company.id, status="completed"))
    company_service.archive_company(company.id)

    with pytest.raises(ValueError, match="cannot be permanently deleted"):
        company_service.remove_company(company.id)

    # The company itself must still exist - the blocked delete must not
    # have partially applied.
    assert company_repository.get_company(company.id) is not None


def test_enable_and_disable_monitoring_updates_status():
    clear_v2_tables()
    company = company_service.add_company(name="Acme Corp")
    assert company.monitoring_status == "enabled"

    disabled = company_service.disable_monitoring(company.id)
    assert disabled.monitoring_status == "disabled"

    enabled = company_service.enable_monitoring(company.id)
    assert enabled.monitoring_status == "enabled"


def test_enable_monitoring_raises_for_unknown_id():
    clear_v2_tables()
    with pytest.raises(ValueError, match="does not exist"):
        company_service.enable_monitoring("does-not-exist")
