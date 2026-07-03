import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from app.config.settings import get_settings
from app.exceptions import ErrorCode, api_error

ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
}

MAGIC_SIGNATURES = {
    ".pdf": (b"%PDF",),
    ".docx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
}

@dataclass(frozen=True)
class FileValidationResult:
    normalized_filename: str
    extension: str
    mime_type: str
    file_size: int
    checksum_sha256: str


def normalize_filename(filename: str) -> str:
    name = Path(filename or "upload").name.replace("\\", "")
    name = re.sub(r"[\x00-\x1f\x7f/]+", "", name).strip().strip(".")
    return (name or "upload")[:255]


def validate_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_TITLE, "문서 제목은 필수입니다.")
    return cleaned[:255]


def validate_upload_bytes(filename: str, content_type: str | None, data: bytes) -> FileValidationResult:
    settings = get_settings()
    max_size = settings.document_max_upload_size_mb * 1024 * 1024
    if not data:
        raise api_error(422, ErrorCode.DOCUMENT_EMPTY_FILE, "빈 파일은 업로드할 수 없습니다.")
    if len(data) > max_size:
        raise api_error(413, ErrorCode.DOCUMENT_FILE_TOO_LARGE, "파일 크기 제한을 초과했습니다.")
    normalized = normalize_filename(filename)
    extension = Path(normalized).suffix.lower()
    allowed_extensions = {f".{item.strip().lower().lstrip('.')}" for item in settings.document_allowed_extensions.split(",") if item.strip()}
    if extension not in allowed_extensions or extension not in ALLOWED_MIME_TYPES:
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_EXTENSION, "지원하지 않는 파일 확장자입니다.")
    mime_type = (content_type or "").split(";")[0].strip().lower()
    if mime_type not in ALLOWED_MIME_TYPES[extension]:
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "파일 MIME 타입이 허용되지 않습니다.")
    signatures = MAGIC_SIGNATURES.get(extension)
    if signatures and not any(data.startswith(signature) for signature in signatures):
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "파일 서명이 확장자와 일치하지 않습니다.")
    if extension in {".txt", ".md"} and data.startswith(b"MZ"):
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "실행 파일은 업로드할 수 없습니다.")
    return FileValidationResult(normalized, extension, mime_type, len(data), hashlib.sha256(data).hexdigest())
