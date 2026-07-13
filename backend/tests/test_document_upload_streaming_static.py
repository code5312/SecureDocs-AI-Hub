from pathlib import Path

from tests.repository_paths import find_repository_root

ROOT = find_repository_root(Path(__file__))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_router_does_not_read_entire_upload_into_bytes() -> None:
    router = read("backend/app/documents/router.py")

    assert "await file.read()" not in router
    assert "file_obj=file.file" in router


def test_storage_upload_uses_stream_and_length() -> None:
    storage = read("backend/app/documents/storage.py")

    assert "put_object(self.bucket, storage_key, stream, length=length" in storage
    assert "BytesIO(data)" not in storage
