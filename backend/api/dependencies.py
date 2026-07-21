"""Shared FastAPI dependencies for the /api/v1 surface (V3 Phase 2)."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.user_repository import get_user_by_email
from backend.services.auth_service import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> User:
    if credentials is None:
        raise APIError(401, "Not authenticated.")

    email = decode_access_token(credentials.credentials)
    if email is None:
        raise APIError(401, "Invalid or expired token.")

    user = await get_user_by_email(email)
    if user is None or not user.is_active:
        raise APIError(401, "Invalid or expired token.")

    return user
