import hashlib

import pytest

from app.documents.validators import normalize_filename, validate_upload_bytes
from app.exceptions.errors import ErrorCode


def _assert_allowed(filename: str, mime_type: str, data: bytes) -> None:
    result = validate_upload_bytes(filename, mime_type, data)
    assert result.checksum_sha256 == hashlib.sha256(data).hexdigest()
    assert result.file_size == len(data)


def test_pdf_allowed() -> None:
    _assert_allowed("a.pdf", "application/pdf", b"%PDF-1.4 data")


def test_docx_allowed() -> None:
    _assert_allowed("a.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04data")


def test_pptx_allowed() -> None:
    _assert_allowed("a.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", b"PK\x03\x04data")


def test_xlsx_allowed() -> None:
    _assert_allowed("a.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK\x03\x04data")


def test_txt_allowed() -> None:
    _assert_allowed("a.txt", "text/plain", b"hello")


def test_md_allowed() -> None:
    _assert_allowed("a.md", "text/markdown", b"# hello")


def test_invalid_extension_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_bytes("a.exe", "application/octet-stream", b"MZ")
    assert ErrorCode.DOCUMENT_INVALID_EXTENSION in str(exc_info.value)


def test_mime_mismatch_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_bytes("a.pdf", "text/plain", b"%PDF-1.4")
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_empty_file_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_bytes("a.txt", "text/plain", b"")
    assert ErrorCode.DOCUMENT_EMPTY_FILE in str(exc_info.value)


def test_dangerous_filename_normalized() -> None:
    assert normalize_filename("../secret/..\\evil.pdf") == "evil.pdf"


def test_checksum_calculated() -> None:
    result = validate_upload_bytes("a.txt", "text/plain", b"checksum")
    assert result.checksum_sha256 == hashlib.sha256(b"checksum").hexdigest()


def test_max_size_exceeded_blocked(monkeypatch) -> None:
    from types import SimpleNamespace
    import app.documents.validators as validators

    monkeypatch.setattr(validators, "get_settings", lambda: SimpleNamespace(document_max_upload_size_mb=0, document_allowed_extensions="txt"))
    with pytest.raises(Exception) as exc_info:
        validate_upload_bytes("a.txt", "text/plain", b"too-large")
    assert ErrorCode.DOCUMENT_FILE_TOO_LARGE in str(exc_info.value)
