import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AclPermission, DocumentStatus, ExtractionStatus


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
    extraction_status: ExtractionStatus
    extraction_error_code: str | None = None
    extraction_error_message: str | None = None
    extraction_attempts: int
    extracted_at: datetime | None = None
    chunk_count: int
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
    effective_permissions: list[AclPermission] = Field(default_factory=list)


class AclUserRead(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    department_id: uuid.UUID | None = None


class AclDepartmentRead(BaseModel):
    id: uuid.UUID
    name: str


class DocumentAclEntryRead(BaseModel):
    id: uuid.UUID
    principal_type: Literal["USER", "DEPARTMENT"]
    user: AclUserRead | None
    department: AclDepartmentRead | None
    permission: AclPermission
    granted_by: uuid.UUID | None
    created_at: datetime


class DocumentAclGrantRequest(BaseModel):
    principal_type: Literal["USER", "DEPARTMENT"]
    principal_id: uuid.UUID
    permissions: list[AclPermission]

    @field_validator("permissions")
    @classmethod
    def permissions_must_not_be_empty(cls, value: list[AclPermission]) -> list[AclPermission]:
        deduped = list(dict.fromkeys(value))
        if not deduped:
            raise ValueError("하나 이상의 권한을 선택해야 합니다.")
        return deduped


class AclPrincipalSearchResponse(BaseModel):
    users: list[AclUserRead]
    departments: list[AclDepartmentRead]
