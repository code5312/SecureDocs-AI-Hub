import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.documents.downloads import DocumentDownload
from app.documents.permissions import can_delete, can_download, can_view_metadata
from app.documents.repository import DocumentRepository
from app.documents.storage import DocumentStorage
from app.documents.validators import validate_title, validate_upload_bytes
from app.exceptions import ErrorCode, api_error
from app.models.document import Document, DocumentVersion
from app.models.enums import AuditAction, DocumentStatus, UserRole
from app.models.user import User


class DocumentService:
    """Document metadata and first-version upload service.

    This uses a temporary role/ownership policy until document ACLs are implemented.
    """

    def __init__(self, db: Session, storage: DocumentStorage | None = None) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.storage = storage or DocumentStorage()
        self.audit = AuditService(db)

    def upload(self, *, title: str, description: str | None, filename: str, content_type: str | None, data: bytes, actor: User, ip_address: str | None, user_agent: str | None) -> Document:
        cleaned_title = validate_title(title)
        result = validate_upload_bytes(filename, content_type, data)
        document_id = uuid.uuid4()
        version_id = uuid.uuid4()
        storage_key = f"documents/{actor.id}/{document_id}/{version_id}/{uuid.uuid4()}{result.extension}"
        document = Document(id=document_id, title=cleaned_title, description=description, owner_id=actor.id, department_id=actor.department_id, status=DocumentStatus.PROCESSING)
        try:
            self.documents.create_document(document)
            version = DocumentVersion(id=version_id, document_id=document.id, version_number=1, original_filename=filename[:255], normalized_filename=result.normalized_filename, storage_key=storage_key, mime_type=result.mime_type, file_size=result.file_size, checksum_sha256=result.checksum_sha256, uploaded_by=actor.id)
            self.documents.create_version(version)
            self.storage.upload(storage_key, data, result.mime_type)
            document.current_version_id = version.id
            document.status = DocumentStatus.ACTIVE
            self.audit.record(action=AuditAction.DOCUMENT_UPLOAD, actor_id=actor.id, target_type="Document", target_id=str(document.id), ip_address=ip_address, user_agent=user_agent, details={"document_id": str(document.id), "version_id": str(version.id), "filename": result.normalized_filename, "file_size": result.file_size, "mime_type": result.mime_type, "checksum": result.checksum_sha256, "result": "success"})
            self.db.commit()
            self.db.refresh(document)
            return document
        except Exception:
            self.db.rollback()
            if storage_key:
                self.storage.remove_uploaded_object(storage_key)
            self.audit.record(action=AuditAction.DOCUMENT_UPLOAD_FAILED, actor_id=actor.id, target_type="Document", ip_address=ip_address, user_agent=user_agent, details={"filename": filename[:255], "result": "failed"})
            self.db.commit()
            raise

    def list_documents(self, actor: User, *, offset: int, limit: int, title: str | None, owner_id: uuid.UUID | None, department_id: uuid.UUID | None, status: DocumentStatus | None) -> list[Document]:
        scoped_owner = owner_id
        scoped_department = department_id
        if actor.role == UserRole.USER:
            scoped_owner = actor.id
        elif actor.role == UserRole.DEPARTMENT_MANAGER:
            scoped_department = actor.department_id
        docs = self.documents.list(offset=offset, limit=limit, title=title, owner_id=scoped_owner, department_id=scoped_department, status=status, include_deleted=False)
        return [doc for doc in docs if can_view_metadata(actor, doc)]

    def get_document(self, actor: User, document_id: uuid.UUID) -> Document:
        document = self.documents.get(document_id)
        if document is None or not can_view_metadata(actor, document):
            raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서를 찾을 수 없습니다.")
        self.audit.record(action=AuditAction.DOCUMENT_VIEW, actor_id=actor.id, target_type="Document", target_id=str(document.id))
        self.db.commit()
        return document

    def download(self, actor: User, document_id: uuid.UUID) -> DocumentDownload:
        document = self.documents.get(document_id)
        if document is None or document.is_deleted:
            self._record_download_failure(actor, None, None, ErrorCode.DOCUMENT_NOT_FOUND)
            raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서를 찾을 수 없습니다.")
        if not can_download(actor, document):
            self._record_download_failure(actor, document, None, ErrorCode.DOCUMENT_DOWNLOAD_DENIED)
            raise api_error(403, ErrorCode.DOCUMENT_DOWNLOAD_DENIED, "다운로드 권한이 없습니다.")
        version = self._current_version(document)
        try:
            stat = self.storage.stat_object(version.storage_key)
            stream = self.storage.open_download_stream(version.storage_key)
        except HTTPException as exc:
            error_code = exc.detail.get("error", {}).get("code") if isinstance(exc.detail, dict) else ErrorCode.DOCUMENT_DOWNLOAD_FAILED
            self._record_download_failure(actor, document, version, error_code)
            raise
        except Exception:
            self._record_download_failure(actor, document, version, ErrorCode.DOCUMENT_DOWNLOAD_FAILED)
            raise
        self.audit.record(action=AuditAction.DOCUMENT_DOWNLOAD, actor_id=actor.id, target_type="Document", target_id=str(document.id), details={"document_id": str(document.id), "version_id": str(version.id), "filename": version.normalized_filename, "file_size": version.file_size, "mime_type": version.mime_type, "checksum": version.checksum_sha256, "result": "success"})
        self.db.commit()
        return DocumentDownload(filename=version.original_filename or version.normalized_filename, content_type=version.mime_type or stat.content_type or "application/octet-stream", content_length=stat.size or version.file_size, stream=stream.iterator)

    def _record_download_failure(self, actor: User, document: Document | None, version: DocumentVersion | None, error_code: str) -> None:
        details = {"result": "failed", "error_code": error_code}
        if document is not None:
            details["document_id"] = str(document.id)
        if version is not None:
            details.update({"version_id": str(version.id), "filename": version.normalized_filename})
        self.audit.record(action=AuditAction.DOCUMENT_DOWNLOAD, actor_id=actor.id, target_type="Document", target_id=str(document.id) if document else None, details=details)
        self.db.commit()

    def delete(self, actor: User, document_id: uuid.UUID) -> Document:
        document = self.documents.get(document_id)
        if document is None:
            raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서를 찾을 수 없습니다.")
        if document.is_deleted:
            raise api_error(409, ErrorCode.DOCUMENT_ALREADY_DELETED, "이미 삭제된 문서입니다.")
        if not can_delete(actor, document):
            raise api_error(403, ErrorCode.DOCUMENT_ACCESS_DENIED, "문서 삭제 권한이 없습니다.")
        document.is_deleted = True
        document.deleted_at = datetime.now(UTC)
        self.audit.record(action=AuditAction.DOCUMENT_DELETE, actor_id=actor.id, target_type="Document", target_id=str(document.id), details={"document_id": str(document.id), "result": "success"})
        self.db.commit()
        self.db.refresh(document)
        return document

    def _current_version(self, document: Document) -> DocumentVersion:
        version = next((item for item in document.versions if item.id == document.current_version_id), None)
        if version is None:
            raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서 버전을 찾을 수 없습니다.")
        return version
