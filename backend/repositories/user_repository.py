"""Repository for the User entity (V3 Phase 2 - the first Postgres-backed
repository; every other repository in this package still reads/writes
SQLite - see TECH_DEBT.md).
"""

from typing import Optional

from sqlalchemy import select

from backend.database.models import User
from backend.database.postgres import get_session


async def create_user(email: str, hashed_password: str) -> User:
    async with get_session() as session:
        user = User(email=email, hashed_password=hashed_password)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user_by_email(email: str) -> Optional[User]:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


async def get_user_by_id(user_id: int) -> Optional[User]:
    async with get_session() as session:
        return await session.get(User, user_id)
