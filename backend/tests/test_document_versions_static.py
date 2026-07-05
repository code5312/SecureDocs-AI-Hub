from pathlib import Path


ROUTER = Path("app/documents/router.py").read_text()
SERVICE = Path("app/documents/service.py").read_text()
REPOSITORY = Path("app/documents/repository.py").read_text()
PERMISSIONS = Path("app/documents/permissions.py").read_text()
SCHEMAS = Path("app/documents/schemas.py").read_text()


def test_version_routes_are_registered_without_reading_upload_into_bytes() -> None:
    assert '@router.post("/{document_id}/versions"' in ROUTER
    assert '@router.get("/{document_id}/versions"' in ROUTER
    assert '@router.get("/{document_id}/versions/{version_id}/download"' in ROUTER
    assert "await file.read" not in ROUTER
    assert "file_obj=file.file" in ROUTER


def test_version_number_uses_row_lock_and_max_query_not_len_versions() -> None:
    assert "get_for_update" in SERVICE
    assert "get_max_version_number(document.id) + 1" in SERVICE
    assert "len(document.versions)" not in SERVICE
    assert ".with_for_update()" in REPOSITORY
    assert "func.max(DocumentVersion.version_number)" in REPOSITORY


def test_version_permissions_and_duplicate_checksum_policy_exist() -> None:
    assert "def can_upload_version" in PERMISSIONS
    access = Path("app/documents/access.py").read_text()
    assert "UserRole.SYSTEM_ADMIN" in access
    assert "document.owner_id == user.id" in access
    assert "DOCUMENT_VERSION_DUPLICATE" in SERVICE
    assert "current_version.checksum_sha256 == result.checksum_sha256" in SERVICE


def test_version_response_hides_storage_key_and_marks_current() -> None:
    assert "is_current" in SCHEMAS
    assert "storage_key" not in SCHEMAS


def test_version_audit_actions_and_compensation_exist() -> None:
    assert "DOCUMENT_VERSION_UPLOAD" in SERVICE
    assert "DOCUMENT_VERSION_DOWNLOAD" in SERVICE
    assert "remove_uploaded_object(storage_key)" in SERVICE
    assert "DOCUMENT_VERSION_DOWNLOAD" in Path("app/models/enums.py").read_text()
