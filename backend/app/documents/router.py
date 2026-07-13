import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user, request_ip
from app.documents.downloads import content_disposition
from app.documents.schemas import (
    AclDepartmentRead,
    AclPrincipalSearchResponse,
    AclUserRead,
    DocumentAclEntryRead,
    DocumentAclGrantRequest,
    DocumentRead,
    DocumentVersionRead,
)
from app.documents.service import DocumentService
from app.models.document import Document, DocumentVersion
from app.models.document_acl import DocumentAclEntry
from app.models.enums import DocumentStatus
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["documents"])


def _version_read(version: DocumentVersion | None, current_version_id: uuid.UUID | None) -> DocumentVersionRead | None:
    if version is None:
        return None
    payload = DocumentVersionRead.model_validate(version)
    payload.is_current = version.id == current_version_id
    return payload


def _read_document(document: Document, service: DocumentService, actor: User) -> DocumentRead:
    version = next((item for item in document.versions if item.id == document.current_version_id), None)
    payload = DocumentRead.model_validate(document)
    payload.current_version = _version_read(version, document.current_version_id)
    payload.effective_permissions = service.effective_permissions(actor, document)
    return payload


def _acl_entry_read(entry: DocumentAclEntry) -> DocumentAclEntryRead:
    return DocumentAclEntryRead(
        id=entry.id,
        principal_type="USER" if entry.user_id else "DEPARTMENT",
        user=AclUserRead(id=entry.user.id, name=entry.user.name, email=entry.user.email, department_id=entry.user.department_id) if entry.user else None,
        department=AclDepartmentRead(id=entry.department.id, name=entry.department.name) if entry.department else None,
        permission=entry.permission,
        granted_by=entry.granted_by,
        created_at=entry.created_at,
    )


def _streaming_response(download) -> StreamingResponse:
    headers = {
        "Content-Disposition": content_disposition(download.filename),
        "Content-Length": str(download.content_length),
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(download.stream, media_type=download.content_type, headers=headers)


@router.post("", response_model=DocumentRead, status_code=201)
async def upload_document(request: Request, title: str = Form(...), description: str | None = Form(None), file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentRead:
    try:
        service = DocumentService(db)
        document = service.upload(title=title, description=description, filename=file.filename or "upload", content_type=file.content_type, file_obj=file.file, actor=current_user, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
        return _read_document(document, service, current_user)
    finally:
        await file.close()


@router.get("", response_model=list[DocumentRead])
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), title: str | None = None, owner_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None, status: DocumentStatus | None = None) -> list[DocumentRead]:
    service = DocumentService(db)
    documents = service.list_documents(current_user, offset=offset, limit=limit, title=title, owner_id=owner_id, department_id=department_id, status=status)
    return [_read_document(document, service, current_user) for document in documents]


@router.post("/{document_id}/versions", response_model=DocumentRead, status_code=201)
async def upload_document_version(document_id: uuid.UUID, request: Request, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentRead:
    try:
        service = DocumentService(db)
        document = service.upload_version(document_id=document_id, filename=file.filename or "upload", content_type=file.content_type, file_obj=file.file, actor=current_user, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
        return _read_document(document, service, current_user)
    finally:
        await file.close()


@router.get("/{document_id}/versions", response_model=list[DocumentVersionRead])
def list_document_versions(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DocumentVersionRead]:
    service = DocumentService(db)
    document = service.get_document(current_user, document_id)
    versions = service.list_versions(current_user, document_id)
    return [item for item in (_version_read(version, document.current_version_id) for version in versions) if item is not None]



@router.post("/{document_id}/versions/{version_id}/extraction/retry", response_model=DocumentVersionRead)
def retry_document_version_extraction(document_id: uuid.UUID, version_id: uuid.UUID, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentVersionRead:
    service = DocumentService(db)
    version = service.retry_extraction(current_user, document_id, version_id, request_ip(request), request.headers.get("user-agent"))
    document = service.get_document(current_user, document_id)
    return _version_read(version, document.current_version_id)

@router.get("/{document_id}/versions/{version_id}/download", response_class=StreamingResponse)
def download_document_version(document_id: uuid.UUID, version_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> StreamingResponse:
    download = DocumentService(db).download_version(current_user, document_id, version_id)
    return _streaming_response(download)


@router.get("/{document_id}/acl/principals", response_model=AclPrincipalSearchResponse)
def search_document_acl_principals(document_id: uuid.UUID, query: str = Query(..., min_length=2), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AclPrincipalSearchResponse:
    users, departments = DocumentService(db).search_acl_principals(current_user, document_id, query)
    return AclPrincipalSearchResponse(users=[AclUserRead(id=user.id, name=user.name, email=user.email, department_id=user.department_id) for user in users], departments=[AclDepartmentRead(id=department.id, name=department.name) for department in departments])


@router.get("/{document_id}/acl", response_model=list[DocumentAclEntryRead])
def list_document_acl(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DocumentAclEntryRead]:
    entries = DocumentService(db).list_acl_entries(current_user, document_id)
    return [_acl_entry_read(entry) for entry in entries]


@router.post("/{document_id}/acl", response_model=list[DocumentAclEntryRead], status_code=201)
def grant_document_acl(document_id: uuid.UUID, payload: DocumentAclGrantRequest, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DocumentAclEntryRead]:
    entries = DocumentService(db).grant_acl(actor=current_user, document_id=document_id, principal_type=payload.principal_type, principal_id=payload.principal_id, permissions=payload.permissions, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    return [_acl_entry_read(entry) for entry in entries]


@router.delete("/{document_id}/acl/{acl_entry_id}", status_code=204)
def revoke_document_acl(document_id: uuid.UUID, acl_entry_id: uuid.UUID, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    DocumentService(db).revoke_acl(actor=current_user, document_id=document_id, acl_entry_id=acl_entry_id, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentRead:
    service = DocumentService(db)
    return _read_document(service.get_document(current_user, document_id), service, current_user)


@router.get("/{document_id}/download", response_class=StreamingResponse)
def download_document(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> StreamingResponse:
    download = DocumentService(db).download(current_user, document_id)
    return _streaming_response(download)


@router.delete("/{document_id}", response_model=DocumentRead)
def delete_document(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentRead:
    service = DocumentService(db)
    return _read_document(service.delete(current_user, document_id), service, current_user)
