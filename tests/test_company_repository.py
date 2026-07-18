from backend.models.company import Company
from backend.repositories.company_repository import (
    create_company,
    delete_company,
    get_company,
    list_companies,
    update_company,
)
from tests.conftest import clear_v2_tables



def test_create_and_get_company_round_trips_all_fields():
    clear_v2_tables()
    company = Company(
        name="Acme Corp",
        industry="Manufacturing",
        headquarters="Chicago, IL",
        website="https://acme.example.com",
    )

    create_company(company)
    fetched = get_company(company.id)

    assert fetched is not None
    assert fetched.id == company.id
    assert fetched.name == "Acme Corp"
    assert fetched.industry == "Manufacturing"
    assert fetched.headquarters == "Chicago, IL"
    assert fetched.website == "https://acme.example.com"
    assert fetched.monitoring_status == "enabled"


def test_get_company_returns_none_when_not_found():
    clear_v2_tables()
    assert get_company("does-not-exist") is None


def test_list_companies_returns_most_recent_first():
    clear_v2_tables()
    first = create_company(Company(name="First Co"))
    second = create_company(Company(name="Second Co"))

    companies = list_companies()

    assert [c.id for c in companies] == [second.id, first.id]


def test_update_company_persists_changes_and_bumps_updated_at():
    clear_v2_tables()
    company = create_company(Company(name="Original Name", monitoring_status="enabled"))
    original_updated_at = company.updated_at

    company.name = "Renamed Co"
    company.monitoring_status = "disabled"
    updated = update_company(company)

    assert updated.updated_at >= original_updated_at
    fetched = get_company(company.id)
    assert fetched.name == "Renamed Co"
    assert fetched.monitoring_status == "disabled"


def test_delete_company_removes_it():
    clear_v2_tables()
    company = create_company(Company(name="Temporary Co"))

    delete_company(company.id)

    assert get_company(company.id) is None
