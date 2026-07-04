from pathlib import Path


def test_router_does_not_read_entire_upload_into_bytes() -> None:
    router = Path("app/documents/router.py").read_text()

    assert "await file.read()" not in router
    assert "file_obj=file.file" in router


def test_storage_upload_uses_stream_and_length() -> None:
    storage = Path("app/documents/storage.py").read_text()

    assert "put_object(self.bucket, storage_key, stream, length=length" in storage
    assert "BytesIO(data)" not in storage
