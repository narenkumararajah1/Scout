"""Request/response validation models for the /api/v1/auth endpoints
(V3 Phase 2). Distinct from backend/database/models.py (ORM entities) and
backend/models/ (V2 domain dataclasses) per the API/Data/Business layering
in docs/v3/03_SYSTEM_ARCHITECTURE.md.
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    is_active: bool

    model_config = {"from_attributes": True}


class LoginResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
