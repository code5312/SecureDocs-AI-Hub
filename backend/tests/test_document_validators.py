import hashlib
import io
import zipfile
from types import SimpleNamespace

import pytest

from app.documents.validators import normalize_filename, validate_upload_stream
from app.exceptions.errors import ErrorCode


def _stream(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)


def _ooxml(entries: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return output.getvalue()


def _assert_allowed(filename: str, mime_type: str, data: bytes) -> None:
    stream = _stream(data)
    result = validate_upload_stream(filename, mime_type, stream)
    assert result.checksum_sha256 == hashlib.sha256(data).hexdigest()
    assert result.file_size == len(data)
    assert stream.tell() == 0


def test_pdf_allowed() -> None:
    _assert_allowed("a.pdf", "application/pdf", b"%PDF-1.4 data")


def test_invalid_pdf_signature_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.pdf", "application/pdf", _stream(b"not-pdf"))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_docx_allowed() -> None:
    data = _ooxml({"[Content_Types].xml": b"xml", "word/document.xml": b"doc"})
    _assert_allowed("a.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", data)


def test_zip_without_docx_entries_blocked() -> None:
    data = _ooxml({"[Content_Types].xml": b"xml", "xl/workbook.xml": b"wrong"})
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", _stream(data))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_pptx_allowed() -> None:
    data = _ooxml({"[Content_Types].xml": b"xml", "ppt/presentation.xml": b"ppt"})
    _assert_allowed("a.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", data)


def test_xlsx_allowed() -> None:
    data = _ooxml({"[Content_Types].xml": b"xml", "xl/workbook.xml": b"sheet"})
    _assert_allowed("a.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", data)


def test_zip_traversal_entry_blocked() -> None:
    data = _ooxml({"[Content_Types].xml": b"xml", "word/document.xml": b"doc", "../evil.txt": b"bad"})
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", _stream(data))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_zip_excessive_uncompressed_size_blocked(monkeypatch) -> None:
    import app.documents.validators as validators

    monkeypatch.setattr(validators, "MAX_ZIP_UNCOMPRESSED_SIZE", 10)
    data = _ooxml({"[Content_Types].xml": b"xml", "word/document.xml": b"x" * 20})
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", _stream(data))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_encrypted_zip_blocked(monkeypatch) -> None:
    import app.documents.validators as validators

    class FakeInfo:
        filename = "word/document.xml"
        file_size = 1
        flag_bits = 0x1

    class FakeZip:
        def __init__(self, file_obj):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def infolist(self):
            return [FakeInfo()]

    monkeypatch.setattr(validators.zipfile, "ZipFile", FakeZip)
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", _stream(b"zip"))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_txt_allowed() -> None:
    _assert_allowed("a.txt", "text/plain", "hello 한글".encode())


def test_md_allowed() -> None:
    _assert_allowed("a.md", "text/markdown", "# hello".encode())


def test_txt_nul_byte_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.txt", "text/plain", _stream(b"hello\x00"))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_txt_mz_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.txt", "text/plain", _stream(b"MZ executable"))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_txt_elf_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.txt", "text/plain", _stream(b"\x7fELF binary"))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_invalid_extension_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.exe", "application/octet-stream", _stream(b"MZ"))
    assert ErrorCode.DOCUMENT_INVALID_EXTENSION in str(exc_info.value)


def test_mime_mismatch_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.pdf", "text/plain", _stream(b"%PDF-1.4"))
    assert ErrorCode.DOCUMENT_INVALID_MIME_TYPE in str(exc_info.value)


def test_empty_file_blocked() -> None:
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.txt", "text/plain", _stream(b""))
    assert ErrorCode.DOCUMENT_EMPTY_FILE in str(exc_info.value)


def test_dangerous_filename_normalized() -> None:
    assert normalize_filename("../secret/..\\evil.pdf") == "evil.pdf"


def test_checksum_calculated() -> None:
    result = validate_upload_stream("a.txt", "text/plain", _stream(b"checksum"))
    assert result.checksum_sha256 == hashlib.sha256(b"checksum").hexdigest()


def test_max_size_exceeded_blocked(monkeypatch) -> None:
    import app.documents.validators as validators

    monkeypatch.setattr(validators, "get_settings", lambda: SimpleNamespace(document_max_upload_size_mb=0, document_allowed_extensions="txt"))
    with pytest.raises(Exception) as exc_info:
        validate_upload_stream("a.txt", "text/plain", _stream(b"too-large"))
    assert ErrorCode.DOCUMENT_FILE_TOO_LARGE in str(exc_info.value)
