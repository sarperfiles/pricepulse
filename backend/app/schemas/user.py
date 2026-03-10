from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class UserUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    is_active: bool
    is_admin: bool
    api_key: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
