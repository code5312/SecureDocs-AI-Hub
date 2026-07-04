import uuid
from pydantic import BaseModel, ConfigDict, field_validator

from app.auth.security import normalize_email
from app.models.enums import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    department_id: uuid.UUID | None
    is_active: bool


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: UserRole = UserRole.USER
    department_id: uuid.UUID | None = None

    @field_validator("email")
    @classmethod
    def normalize(cls, value: str) -> str:
        return normalize_email(value)


class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    department_id: uuid.UUID | None = None
    is_active: bool | None = None
