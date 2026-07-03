import uuid
from pydantic import BaseModel, ConfigDict


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    is_active: bool


class DepartmentCreate(BaseModel):
    name: str
    description: str | None = None
    parent_id: uuid.UUID | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_id: uuid.UUID | None = None
    is_active: bool | None = None
