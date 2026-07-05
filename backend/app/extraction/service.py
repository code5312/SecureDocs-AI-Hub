import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.config.settings import get_settings
from app.documents.storage import DocumentStorage
from app.extraction.chunker import chunk_segments
from app.extraction.errors import ExtractionError, ExtractionErrorCode
from app.extraction.extractors import extract_text
from app.models.document import DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.models.enums import AuditAction, DocumentStatus, ExtractionStatus

logger = logging.getLogger(__name__)


class DocumentExtractionService:
    """Coordinates version-row state transitions, MinIO reads, parsing, and chunk persistence."""

    def __init__(self, db: Session, storage: DocumentStorage | None = None) -> None:
        self.db = db
        self.storage = storage or DocumentStorage()
        self.settings = get_settings()
        self.audit = AuditService(db)

    def process_version(self, version_id: uuid.UUID) -> None:
        version = self._mark_processing(version_id)
        if version is None:
            return
        try:
            max_bytes = self.settings.extraction_max_file_size_mb * 1024 * 1024
            with self.storage.open_original_for_extraction(version.storage_key, max_size_bytes=max_bytes) as stream:
                segments = extract_text(stream, filename=version.normalized_filename, mime_type=version.mime_type, settings=self.settings)
            chunks = chunk_segments(segments, chunk_size=self.settings.extraction_chunk_size, chunk_overlap=self.settings.extraction_chunk_overlap, max_chunks=self.settings.extraction_max_chunks)
            self._mark_succeeded(version.id, chunks)
        except ExtractionError as exc:
            self._mark_failed(version.id, exc.code.value, exc.safe_message)
        except Exception:
            self._mark_failed(version.id, ExtractionErrorCode.INTERNAL_ERROR.value, "문서 추출 중 오류가 발생했습니다.")

    def _locked_version(self, version_id: uuid.UUID) -> DocumentVersion | None:
        return self.db.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id).with_for_update())

    def _mark_processing(self, version_id: uuid.UUID) -> DocumentVersion | None:
        version = self._locked_version(version_id)
        if version is None or version.document.is_deleted or version.document.status == DocumentStatus.FAILED:
            self.db.rollback(); return None
        if version.extraction_status in {ExtractionStatus.SUCCEEDED, ExtractionStatus.PROCESSING}:
            self.db.rollback(); return None
        if version.extraction_attempts >= self.settings.extraction_max_attempts:
            self._mark_failed(version_id, ExtractionErrorCode.INTERNAL_ERROR.value, "최대 추출 시도 횟수를 초과했습니다.")
            return None
        version.extraction_status = ExtractionStatus.PROCESSING
        version.extraction_attempts += 1
        version.extraction_started_at = datetime.now(UTC)
        version.extraction_error_code = None
        version.extraction_error_message = None
        version.extracted_at = None
        self.db.commit()
        self.db.refresh(version)
        logger.info("document extraction processing document_id=%s version_id=%s attempt=%s", version.document_id, version.id, version.extraction_attempts)
        return version

    def _mark_succeeded(self, version_id: uuid.UUID, chunks) -> None:
        version = self._locked_version(version_id)
        if version is None:
            self.db.rollback(); return
        self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_version_id == version.id))
        for chunk in chunks:
            self.db.add(DocumentChunk(document_id=version.document_id, document_version_id=version.id, chunk_index=chunk.chunk_index, content=chunk.content, content_sha256=chunk.content_sha256, character_count=chunk.character_count, page_number=chunk.page_number, slide_number=chunk.slide_number, sheet_name=chunk.sheet_name, row_start=chunk.row_start, row_end=chunk.row_end, section_title=chunk.section_title))
        version.chunk_count = len(chunks)
        version.extraction_status = ExtractionStatus.SUCCEEDED
        version.extracted_at = datetime.now(UTC)
        version.extraction_error_code = None
        version.extraction_error_message = None
        self.audit.record(action=AuditAction.DOCUMENT_EXTRACTION_SUCCEEDED, target_type="Document", target_id=str(version.document_id), details=self._details(version, "SUCCEEDED"))
        self.db.commit()
        logger.info("document extraction succeeded document_id=%s version_id=%s chunk_count=%s", version.document_id, version.id, len(chunks))

    def _mark_failed(self, version_id: uuid.UUID, code: str, message: str) -> None:
        self.db.rollback()
        version = self._locked_version(version_id)
        if version is None:
            self.db.rollback(); return
        version.extraction_status = ExtractionStatus.FAILED
        version.extraction_error_code = code[:64]
        version.extraction_error_message = message[:512]
        self.audit.record(action=AuditAction.DOCUMENT_EXTRACTION_FAILED, target_type="Document", target_id=str(version.document_id), details=self._details(version, "FAILED", code))
        self.db.commit()
        logger.warning("document extraction failed document_id=%s version_id=%s error_code=%s attempt=%s", version.document_id, version.id, code, version.extraction_attempts)

    def _details(self, version: DocumentVersion, status: str, error_code: str | None = None) -> dict:
        data = {"document_id": str(version.document_id), "version_id": str(version.id), "version_number": version.version_number, "status": status, "attempts": version.extraction_attempts, "chunk_count": version.chunk_count}
        if error_code:
            data["error_code"] = error_code
        return data
