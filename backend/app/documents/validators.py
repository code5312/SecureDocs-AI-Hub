import codecs
import hashlib
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from app.config.settings import get_settings
from app.exceptions import ErrorCode, api_error

UPLOAD_CHUNK_SIZE = 1024 * 1024
MAX_ZIP_ENTRIES = 1000
MAX_ZIP_UNCOMPRESSED_SIZE = 200 * 1024 * 1024
MAX_TEXT_BINARY_CONTROL_RATIO = 0.02
TEXT_CONTROL_WHITELIST = {9, 10, 13}

ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
}

OOXML_REQUIRED_ENTRIES = {
    ".docx": {"[Content_Types].xml", "word/document.xml"},
    ".pptx": {"[Content_Types].xml", "ppt/presentation.xml"},
    ".xlsx": {"[Content_Types].xml", "xl/workbook.xml"},
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


def _allowed_extensions() -> set[str]:
    settings = get_settings()
    return {f".{item.strip().lower().lstrip('.')}" for item in settings.document_allowed_extensions.split(",") if item.strip()}


def _validate_extension_and_mime(filename: str, content_type: str | None) -> tuple[str, str, str]:
    normalized = normalize_filename(filename)
    extension = Path(normalized).suffix.lower()
    if extension not in _allowed_extensions() or extension not in ALLOWED_MIME_TYPES:
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_EXTENSION, "지원하지 않는 파일 확장자입니다.")
    mime_type = (content_type or "").split(";")[0].strip().lower()
    if mime_type not in ALLOWED_MIME_TYPES[extension]:
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "파일 MIME 타입이 허용되지 않습니다.")
    return normalized, extension, mime_type


def _scan_stream(file_obj: BinaryIO, max_size: int) -> tuple[int, str, bytes, int, int, bool, bool]:
    checksum = hashlib.sha256()
    total_size = 0
    first_bytes = bytearray()
    control_count = 0
    scanned_text_bytes = 0
    utf8_error = False
    has_nul = False
    utf8_decoder = codecs.getincrementaldecoder("utf-8")()

    while True:
        chunk = file_obj.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise api_error(413, ErrorCode.DOCUMENT_FILE_TOO_LARGE, "파일 크기 제한을 초과했습니다.")
        checksum.update(chunk)
        if len(first_bytes) < 8192:
            first_bytes.extend(chunk[: 8192 - len(first_bytes)])
        if b"\x00" in chunk:
            has_nul = True
        for byte in chunk:
            if byte < 32 and byte not in TEXT_CONTROL_WHITELIST:
                control_count += 1
        scanned_text_bytes += len(chunk)
        try:
            utf8_decoder.decode(chunk)
        except UnicodeDecodeError:
            utf8_error = True

    if total_size == 0:
        raise api_error(422, ErrorCode.DOCUMENT_EMPTY_FILE, "빈 파일은 업로드할 수 없습니다.")
    try:
        utf8_decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        utf8_error = True
    file_obj.seek(0)
    return total_size, checksum.hexdigest(), bytes(first_bytes), control_count, scanned_text_bytes, utf8_error, has_nul


def _validate_pdf(first_bytes: bytes) -> None:
    if not first_bytes.startswith(b"%PDF-"):
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "PDF 파일 서명이 올바르지 않습니다.")


def _validate_text(extension: str, first_bytes: bytes, control_count: int, total_size: int, utf8_error: bool, has_nul: bool) -> None:
    if has_nul or first_bytes.startswith((b"MZ", b"\x7fELF")):
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "바이너리 파일은 텍스트 문서로 업로드할 수 없습니다.")
    if total_size and control_count / total_size > MAX_TEXT_BINARY_CONTROL_RATIO:
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "바이너리 제어문자 비율이 높아 텍스트 문서로 처리할 수 없습니다.")
    if utf8_error:
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, f"{extension.upper()} 파일은 UTF-8 인코딩만 허용합니다.")


def _validate_ooxml(file_obj: BinaryIO, extension: str) -> None:
    try:
        with zipfile.ZipFile(file_obj) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "ZIP entry 수가 허용 범위를 초과했습니다.")
            names = set()
            total_uncompressed = 0
            for info in infos:
                name = info.filename.replace("\\", "/")
                path = PurePosixPath(name)
                if name.startswith("/") or path.is_absolute() or ".." in path.parts:
                    raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "ZIP 경로가 안전하지 않습니다.")
                if info.flag_bits & 0x1:
                    raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "암호화된 ZIP 기반 문서는 허용하지 않습니다.")
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_ZIP_UNCOMPRESSED_SIZE:
                    raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "ZIP 압축 해제 크기가 허용 범위를 초과했습니다.")
                names.add(name)
            if not OOXML_REQUIRED_ENTRIES[extension].issubset(names):
                raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "Office Open XML 필수 구조가 없습니다.")
    except zipfile.BadZipFile as exc:
        raise api_error(422, ErrorCode.DOCUMENT_INVALID_MIME_TYPE, "손상된 ZIP 기반 문서입니다.") from exc
    finally:
        file_obj.seek(0)


def validate_upload_stream(filename: str, content_type: str | None, file_obj: BinaryIO) -> FileValidationResult:
    settings = get_settings()
    max_size = settings.document_max_upload_size_mb * 1024 * 1024
    normalized, extension, mime_type = _validate_extension_and_mime(filename, content_type)
    file_obj.seek(0)
    file_size, checksum_sha256, first_bytes, control_count, scanned_text_bytes, utf8_error, has_nul = _scan_stream(file_obj, max_size)

    if extension == ".pdf":
        _validate_pdf(first_bytes)
    elif extension in OOXML_REQUIRED_ENTRIES:
        _validate_ooxml(file_obj, extension)
    elif extension in {".txt", ".md"}:
        _validate_text(extension, first_bytes, control_count, scanned_text_bytes, utf8_error, has_nul)
    file_obj.seek(0)
    return FileValidationResult(normalized, extension, mime_type, file_size, checksum_sha256)
