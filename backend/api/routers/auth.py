"""Authentication endpoints (V3 Phase 2 - docs/v3/10_API_SPECIFICATION.md).

Login and current-user retrieval only. Logout and refresh-token issuance
are deferred until a full token lifecycle strategy is designed - see
TECH_DEBT.md. This router never imports from backend/services/,
backend/repositories/ (V2's), or backend/routers/ - it depends only on
the V3 Phase 2 auth stack (backend/services/auth_service.py,
backend/repositories/user_repository.py, backend/database/).
"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_current_user
from backend.api.error_handlers import APIError
from backend.database.models import User
from backend.repositories.user_repository import get_user_by_email
from backend.schemas.auth import LoginRequest, LoginResponseData, UserOut
from backend.services.auth_service import create_access_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
async def login(credentials: LoginRequest) -> dict:
    user = await get_user_by_email(credentials.email)
    # Same generic message whether the email doesn't exist or the
    # password is wrong, so the response never discloses which one
    # failed (docs/v3/15_IMPLEMENTATION_GUIDELINES.md Security Guidelines).
    if user is None or not user.is_active or not verify_password(credentials.password, user.hashed_password):
        raise APIError(401, "Invalid email or password.")

    access_token = create_access_token(subject=user.email)
    data = LoginResponseData(access_token=access_token, user=UserOut.model_validate(user))
    return {"success": True, "message": "Login successful.", "data": data.model_dump()}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    data = UserOut.model_validate(current_user)
    return {"success": True, "message": "Current user retrieved successfully.", "data": data.model_dump()}
