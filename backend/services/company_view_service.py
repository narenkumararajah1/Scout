"""'What Changed Since Last Visit' (roadmap Phase 3, item 8).

Diffs against a company's own already-persisted intelligence - creates
no new data itself, just compares existing notifications/opportunities/
reports against a check-in timestamp
(backend/repositories/postgres/company_view_repository.py). Users never
need to figure out what changed themselves.
"""

from datetime import datetime, timezone

from backend.repositories.opportunity_repository import list_opportunities
from backend.repositories.postgres.company_view_repository import check_in_and_get_previous_visit
from backend.repositories.postgres.notification_repository import list_notifications_for_company
from backend.repositories.postgres.report_repository import list_v3_reports_for_company
from backend.repositories.report_repository import list_reports


def _as_utc(value: datetime) -> datetime:
    # Mirrors backend/repositories/postgres/sync_facade.py's _as_utc -
    # V2's SQLite-backed models store naive datetimes that are already
    # UTC wall-clock values but don't say so; comparing a naive and an
    # aware datetime raises, so this makes the comparison unambiguous.
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


async def get_changes_since_last_visit(company_id: str) -> dict:
    """Records a visit to `company_id` right now and returns what
    changed since the *previous* visit (never touches new data, only
    compares timestamps against what's already persisted).

    Returns {"first_visit": True, ...} with no changes computed on a
    company's very first recorded visit - there's nothing to diff
    against yet.
    """
    previous_visit = await check_in_and_get_previous_visit(company_id)
    if previous_visit is None:
        return {
            "first_visit": True,
            "since": None,
            "new_notifications": [],
            "new_opportunity_count": 0,
            "new_report_count": 0,
        }

    notifications = await list_notifications_for_company(company_id)
    new_notifications = [n for n in notifications if _as_utc(n.created_at) > previous_visit]

    opportunities = list_opportunities(company_id)
    new_opportunity_count = sum(1 for o in opportunities if _as_utc(o.generated_date) > previous_visit)

    v2_reports = list_reports(company_id)
    v3_reports = await list_v3_reports_for_company(company_id)
    new_report_count = sum(1 for r in v2_reports if _as_utc(r.created_at) > previous_visit) + sum(
        1 for r in v3_reports if _as_utc(r.created_at) > previous_visit
    )

    return {
        "first_visit": False,
        "since": previous_visit,
        "new_notifications": [
            {"id": n.id, "title": n.title, "type": n.type, "recommended_action": n.recommended_action}
            for n in new_notifications
        ],
        "new_opportunity_count": new_opportunity_count,
        "new_report_count": new_report_count,
    }


async def list_recently_viewed(limit: int = 8) -> list:
    """Recently opened companies, newest first (V3 Enhancements Phase 6 -
    10_NAVIGATION_IMPROVEMENTS.md's "Recently viewed companies").

    **Resolves each view against the live company store rather than
    trusting the view row.** `company_views` holds only an id and a
    timestamp, and a company can be archived or deleted after being
    viewed - `company_service.get_company()` raises for those, and a
    switcher offering a dead link is worse than a shorter list. Archived
    companies are dropped for the same reason: the point of this list is
    somewhere to go next, and an archived account is not that.

    Reads rows the visit endpoint has been writing since roadmap Phase 3.
    No new persistence, and nothing needs to start recording anything.
    """
    from backend.repositories.postgres.company_view_repository import list_recent_views
    from backend.services import company_service

    # Over-fetch, because resolution can drop rows and a list that
    # silently shrinks to two entries is a worse switcher than one that
    # holds its size.
    views = await list_recent_views(limit=limit * 2)

    recent = []
    for view in views:
        try:
            company = company_service.get_company(view.company_id)
        except ValueError:
            continue
        if getattr(company, "archived_at", None) is not None:
            continue
        recent.append(
            {
                "company_id": company.id,
                "company_name": company.name,
                "industry": company.industry,
                "last_viewed_at": view.last_viewed_at,
            }
        )
        if len(recent) >= limit:
            break
    return recent
