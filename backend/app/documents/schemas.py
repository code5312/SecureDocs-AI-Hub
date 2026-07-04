import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version_number: int
    original_filename: str
    normalized_filename: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    uploaded_by: uuid.UUID
    created_at: datetime
    is_current: bool = False


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None
    owner_id: uuid.UUID
    department_id: uuid.UUID | None
    current_version_id: uuid.UUID | None
    status: DocumentStatus
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    current_version: DocumentVersionRead | None = None
