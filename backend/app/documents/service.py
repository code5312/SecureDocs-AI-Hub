import logging
import uuid
from datetime import UTC, datetime
from typing import BinaryIO, Iterator

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.database.session import SessionLocal
from app.documents.downloads import DocumentDownload
from app.documents.permissions import can_delete, can_download, can_upload_version, can_view_metadata
from app.documents.repository import DocumentRepository
from app.documents.storage import DocumentStorage
from app.documents.validators import FileValidationResult, validate_title, validate_upload_stream
from app.exceptions import ErrorCode, api_error
from app.models.document import Document, DocumentVersion
from app.models.enums import AuditAction, DocumentStatus, UserRole
from app.models.user import User

logger = logging.getLogger(__name__)


class DocumentService:
    """Document metadata, first-version upload, and version management service.

    This uses a temporary role/ownership policy until document ACLs are implemented.
    """

    def __init__(self, db: Session, storage: DocumentStorage | None = None) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.storage = storage or DocumentStorage()
        self.audit = AuditService(db)

    def upload(self, *, title: str, description: str | None, filename: str, content_type: str | None, file_obj: BinaryIO, actor: User, ip_address: str | None, user_agent: str | None) -> Document:
        cleaned_title = validate_title(title)
        result = validate_upload_stream(filename, content_type, file_obj)
        document_id = uuid.uuid4()
        version_id = uuid.uuid4()
        storage_key = self._storage_key(actor.id, document_id, version_id, result.extension)
        document = Document(id=document_id, title=cleaned_title, description=description, owner_id=actor.id, department_id=actor.department_id, status=DocumentStatus.PROCESSING)
        uploaded = False
        try:
            self.documents.create_document(document)
            version = self._build_version(version_id, document.id, 1, filename, storage_key, result, actor)
            self.documents.create_version(version)
            self.storage.upload(storage_key, file_obj, result.file_size, result.mime_type)
            uploaded = True
            document.current_version_id = version.id
            document.status = DocumentStatus.ACTIVE
            self.audit.record(action=AuditAction.DOCUMENT_UPLOAD, actor_id=actor.id, target_type="Document", target_id=str(document.id), ip_address=ip_address, user_agent=user_agent, details=self._version_audit_details(document, version, result.normalized_filename, result, "success"))
            self.db.commit()
            self.db.refresh(document)
            return document
        except Exception:
            self.db.rollback()
            if uploaded:
                self.storage.remove_uploaded_object(storage_key)
            self.audit.record(action=AuditAction.DOCUMENT_UPLOAD_FAILED, actor_id=actor.id, target_type="Document", ip_address=ip_address, user_agent=user_agent, details={"filename": filename[:255], "result": "failed"})
            self.db.commit()
            raise

    def upload_version(self, *, document_id: uuid.UUID, filename: str, content_type: str | None, file_obj: BinaryIO, actor: User, ip_address: str | None, user_agent: str | None) -> Document:
        result = validate_upload_stream(filename, content_type, file_obj)
        version_id = uuid.uuid4()
        storage_key: str | None = None
        uploaded = False
        try:
            document = self.documents.get_for_update(document_id)
            if document is None or document.is_deleted:
                raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서를 찾을 수 없습니다.")
            if not can_upload_version(actor, document):
                raise api_error(403, ErrorCode.DOCUMENT_ACCESS_DENIED, "문서 버전 업로드 권한이 없습니다.")
            current_version = self._current_version(document)
            if current_version.checksum_sha256 == result.checksum_sha256:
                raise api_error(409, ErrorCode.DOCUMENT_VERSION_DUPLICATE, "현재 버전과 동일한 파일은 새 버전으로 업로드할 수 없습니다.")
            next_version_number = self.documents.get_max_version_number(document.id) + 1
            storage_key = self._storage_key(document.owner_id, document.id, version_id, result.extension)
            version = self._build_version(version_id, document.id, next_version_number, filename, storage_key, result, actor)
            self.documents.create_version(version)
            self.storage.upload(storage_key, file_obj, result.file_size, result.mime_type)
            uploaded = True
            document.current_version_id = version.id
            document.status = DocumentStatus.ACTIVE
            self.audit.record(action=AuditAction.DOCUMENT_VERSION_UPLOAD, actor_id=actor.id, target_type="Document", target_id=str(document.id), ip_address=ip_address, user_agent=user_agent, details=self._version_audit_details(document, version, result.normalized_filename, result, "success"))
            self.db.commit()
            self.db.refresh(document)
            return document
        except IntegrityError as exc:
            self.db.rollback()
            if uploaded and storage_key:
                self.storage.remove_uploaded_object(storage_key)
            self._record_version_upload_failure(actor, document_id, filename, ip_address, user_agent, ErrorCode.DOCUMENT_UPLOAD_FAILED)
            raise api_error(409, ErrorCode.DOCUMENT_UPLOAD_FAILED, "문서 버전 번호 충돌이 발생했습니다. 다시 시도하세요.") from exc
        except Exception as exc:
            self.db.rollback()
            if uploaded and storage_key:
                self.storage.remove_uploaded_object(storage_key)
            self._record_version_upload_failure(actor, document_id, filename, ip_address, user_agent, self._error_code(exc))
            raise

    def list_versions(self, actor: User, document_id: uuid.UUID) -> list[DocumentVersion]:
        document = self.documents.get(document_id)
        if document is None or not can_view_metadata(actor, document):
            raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서를 찾을 수 없습니다.")
        return self.documents.list_versions(document.id)

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
            self._record_download_failure(actor, None, None, ErrorCode.DOCUMENT_NOT_FOUND, AuditAction.DOCUMENT_DOWNLOAD)
            raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서를 찾을 수 없습니다.")
        if not can_download(actor, document):
            self._record_download_failure(actor, document, None, ErrorCode.DOCUMENT_DOWNLOAD_DENIED, AuditAction.DOCUMENT_DOWNLOAD)
            raise api_error(403, ErrorCode.DOCUMENT_DOWNLOAD_DENIED, "다운로드 권한이 없습니다.")
        return self._download_version(actor, document, self._current_version(document), AuditAction.DOCUMENT_DOWNLOAD)

    def download_version(self, actor: User, document_id: uuid.UUID, version_id: uuid.UUID) -> DocumentDownload:
        document = self.documents.get(document_id)
        if document is None or document.is_deleted:
            self._record_download_failure(actor, None, None, ErrorCode.DOCUMENT_NOT_FOUND, AuditAction.DOCUMENT_VERSION_DOWNLOAD)
            raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서를 찾을 수 없습니다.")
        if not can_download(actor, document):
            self._record_download_failure(actor, document, None, ErrorCode.DOCUMENT_DOWNLOAD_DENIED, AuditAction.DOCUMENT_VERSION_DOWNLOAD)
            raise api_error(403, ErrorCode.DOCUMENT_DOWNLOAD_DENIED, "다운로드 권한이 없습니다.")
        version = self.documents.get_version(document.id, version_id)
        if version is None:
            self._record_download_failure(actor, document, None, ErrorCode.DOCUMENT_NOT_FOUND, AuditAction.DOCUMENT_VERSION_DOWNLOAD)
            raise api_error(404, ErrorCode.DOCUMENT_NOT_FOUND, "문서 버전을 찾을 수 없습니다.")
        return self._download_version(actor, document, version, AuditAction.DOCUMENT_VERSION_DOWNLOAD)

    def _download_version(self, actor: User, document: Document, version: DocumentVersion, action: AuditAction) -> DocumentDownload:
        try:
            stat = self.storage.stat_object(version.storage_key)
            stream = self.storage.open_download_stream(version.storage_key)
        except HTTPException as exc:
            error_code = exc.detail.get("error", {}).get("code") if isinstance(exc.detail, dict) else ErrorCode.DOCUMENT_DOWNLOAD_FAILED
            self._record_download_failure(actor, document, version, error_code, action)
            raise
        except Exception:
            self._record_download_failure(actor, document, version, ErrorCode.DOCUMENT_DOWNLOAD_FAILED, action)
            raise
        audit_details = self._download_audit_details(document, version, "started")
        self.audit.record(action=action, actor_id=actor.id, target_type="Document", target_id=str(document.id), details=audit_details)
        self.db.commit()
        return DocumentDownload(filename=version.original_filename or version.normalized_filename, content_type=version.mime_type or stat.content_type or "application/octet-stream", content_length=stat.size or version.file_size, stream=self._audit_download_stream(stream.iterator, actor.id, str(document.id), action, {key: value for key, value in audit_details.items() if key != "result"}))

    def _audit_download_stream(self, source: Iterator[bytes], actor_id: uuid.UUID, document_id: str, action: AuditAction, audit_details: dict) -> Iterator[bytes]:
        """Yield a MinIO stream and record post-response download state in a short DB session."""
        completed = False
        try:
            for chunk in source:
                yield chunk
            completed = True
        finally:
            result = "completed" if completed else "interrupted"
            try:
                with SessionLocal() as db:
                    AuditService(db).record(action=action, actor_id=actor_id, target_type="Document", target_id=document_id, details={**audit_details, "result": result})
                    db.commit()
            except Exception as exc:  # pragma: no cover - download bytes must not be corrupted by audit persistence failure
                logger.warning("download audit finalization failed for document_id=%s result=%s", document_id, result, exc_info=exc)

    def _record_download_failure(self, actor: User, document: Document | None, version: DocumentVersion | None, error_code: str, action: AuditAction) -> None:
        details = {"result": "failed", "error_code": error_code}
        if document is not None:
            details["document_id"] = str(document.id)
        if version is not None:
            details.update({"version_id": str(version.id), "version_number": version.version_number, "filename": version.normalized_filename})
        self.audit.record(action=action, actor_id=actor.id, target_type="Document", target_id=str(document.id) if document else None, details=details)
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

    def _storage_key(self, owner_id: uuid.UUID, document_id: uuid.UUID, version_id: uuid.UUID, extension: str) -> str:
        return f"documents/{owner_id}/{document_id}/{version_id}/{uuid.uuid4()}{extension}"

    def _build_version(self, version_id: uuid.UUID, document_id: uuid.UUID, version_number: int, filename: str, storage_key: str, result: FileValidationResult, actor: User) -> DocumentVersion:
        return DocumentVersion(id=version_id, document_id=document_id, version_number=version_number, original_filename=filename[:255], normalized_filename=result.normalized_filename, storage_key=storage_key, mime_type=result.mime_type, file_size=result.file_size, checksum_sha256=result.checksum_sha256, uploaded_by=actor.id)

    def _version_audit_details(self, document: Document, version: DocumentVersion, filename: str, result: FileValidationResult, audit_result: str) -> dict:
        return {"document_id": str(document.id), "version_id": str(version.id), "version_number": version.version_number, "filename": filename, "file_size": result.file_size, "mime_type": result.mime_type, "checksum": result.checksum_sha256, "result": audit_result}

    def _download_audit_details(self, document: Document, version: DocumentVersion, result: str) -> dict:
        return {"document_id": str(document.id), "version_id": str(version.id), "version_number": version.version_number, "filename": version.normalized_filename, "file_size": version.file_size, "mime_type": version.mime_type, "checksum": version.checksum_sha256, "result": result}

    def _record_version_upload_failure(self, actor: User, document_id: uuid.UUID, filename: str, ip_address: str | None, user_agent: str | None, error_code: str) -> None:
        try:
            self.audit.record(action=AuditAction.DOCUMENT_VERSION_UPLOAD, actor_id=actor.id, target_type="Document", target_id=str(document_id), ip_address=ip_address, user_agent=user_agent, details={"document_id": str(document_id), "filename": filename[:255], "result": "failed", "error_code": error_code})
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _error_code(self, exc: Exception) -> str:
        if isinstance(exc, HTTPException) and isinstance(exc.detail, dict):
            code = exc.detail.get("error", {}).get("code")
            if isinstance(code, str):
                return code
        return ErrorCode.DOCUMENT_UPLOAD_FAILED
