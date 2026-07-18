"""Repository for the Recipient and Delivery entities (V2 Phase 2).

Recipient supports full CRUD - it's a managed configuration entity
(FR-016: add, remove, enable, disable, delivery preferences). Delivery is
create + read only: each row is an immutable record of one delivery
attempt, an audit trail rather than a mutable entity.
"""

from datetime import datetime
from typing import Optional

from backend.database import get_connection
from backend.models.recipient import Delivery, Recipient
from backend.repositories._json_list import dump_list, load_list


def init_recipients_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS recipients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                delivery_status TEXT,
                preferred_frequency TEXT,
                preferred_company_ids TEXT NOT NULL,
                preferred_channels TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def init_delivery_history_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS delivery_history (
                id TEXT PRIMARY KEY,
                recipient_id TEXT NOT NULL,
                report_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                delivery_time TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (recipient_id) REFERENCES recipients (id),
                FOREIGN KEY (report_id) REFERENCES research_reports (id)
            )
            """
        )
        connection.commit()


def create_recipient(recipient: Recipient) -> Recipient:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO recipients
                (id, name, email, delivery_status, preferred_frequency,
                 preferred_company_ids, preferred_channels, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipient.id,
                recipient.name,
                recipient.email,
                recipient.delivery_status,
                recipient.preferred_frequency,
                dump_list(recipient.preferred_company_ids),
                dump_list(recipient.preferred_channels),
                recipient.created_at.isoformat(),
            ),
        )
        connection.commit()
    return recipient


def get_recipient(recipient_id: str) -> Optional[Recipient]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM recipients WHERE id = ?", (recipient_id,)
        ).fetchone()
    return _row_to_recipient(row) if row else None


def list_recipients() -> list[Recipient]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM recipients ORDER BY created_at DESC").fetchall()
    return [_row_to_recipient(row) for row in rows]


def update_recipient(recipient: Recipient) -> Recipient:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE recipients
            SET name = ?, email = ?, delivery_status = ?, preferred_frequency = ?,
                preferred_company_ids = ?, preferred_channels = ?
            WHERE id = ?
            """,
            (
                recipient.name,
                recipient.email,
                recipient.delivery_status,
                recipient.preferred_frequency,
                dump_list(recipient.preferred_company_ids),
                dump_list(recipient.preferred_channels),
                recipient.id,
            ),
        )
        connection.commit()
    return recipient


def delete_recipient(recipient_id: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM recipients WHERE id = ?", (recipient_id,))
        connection.commit()


def create_delivery(delivery: Delivery) -> Delivery:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO delivery_history
                (id, recipient_id, report_id, channel, delivery_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                delivery.id,
                delivery.recipient_id,
                delivery.report_id,
                delivery.channel,
                delivery.delivery_time.isoformat(),
                delivery.status,
            ),
        )
        connection.commit()
    return delivery


def list_deliveries_for_recipient(recipient_id: str) -> list[Delivery]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM delivery_history WHERE recipient_id = ? ORDER BY delivery_time DESC",
            (recipient_id,),
        ).fetchall()
    return [_row_to_delivery(row) for row in rows]


def list_deliveries_for_report(report_id: str) -> list[Delivery]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM delivery_history WHERE report_id = ? ORDER BY delivery_time DESC",
            (report_id,),
        ).fetchall()
    return [_row_to_delivery(row) for row in rows]


def _row_to_recipient(row) -> Recipient:
    return Recipient(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        delivery_status=row["delivery_status"],
        preferred_frequency=row["preferred_frequency"],
        preferred_company_ids=load_list(row["preferred_company_ids"]),
        preferred_channels=load_list(row["preferred_channels"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_delivery(row) -> Delivery:
    return Delivery(
        id=row["id"],
        recipient_id=row["recipient_id"],
        report_id=row["report_id"],
        channel=row["channel"],
        delivery_time=datetime.fromisoformat(row["delivery_time"]),
        status=row["status"],
    )
