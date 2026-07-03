import uuid

from app.documents.permissions import can_delete, can_download, can_view_metadata
from app.models.document import Document
from app.models.enums import DocumentStatus, UserRole
from app.models.user import User


def _user(role: UserRole, department_id=None):
    return User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.com", password_hash="hash", name="User", role=role, department_id=department_id, is_active=True)


def _document(owner_id, department_id=None, is_deleted=False):
    return Document(id=uuid.uuid4(), title="Doc", owner_id=owner_id, department_id=department_id, status=DocumentStatus.ACTIVE, is_deleted=is_deleted)


def test_user_only_sees_own_document() -> None:
    user = _user(UserRole.USER)
    other = _user(UserRole.USER)
    assert can_view_metadata(user, _document(user.id))
    assert not can_view_metadata(user, _document(other.id))


def test_department_manager_sees_same_department_metadata_but_cannot_download_others() -> None:
    department_id = uuid.uuid4()
    manager = _user(UserRole.DEPARTMENT_MANAGER, department_id)
    other = _user(UserRole.USER, department_id)
    document = _document(other.id, department_id)
    assert can_view_metadata(manager, document)
    assert not can_download(manager, document)


def test_document_admin_sees_metadata_but_only_downloads_own_document() -> None:
    admin = _user(UserRole.DOCUMENT_ADMIN)
    other = _user(UserRole.USER)
    assert can_view_metadata(admin, _document(other.id))
    assert not can_download(admin, _document(other.id))
    assert can_download(admin, _document(admin.id))


def test_system_admin_has_full_access() -> None:
    admin = _user(UserRole.SYSTEM_ADMIN)
    other = _user(UserRole.USER)
    document = _document(other.id)
    assert can_view_metadata(admin, document)
    assert can_download(admin, document)
    assert can_delete(admin, document)


def test_deleted_document_hidden() -> None:
    admin = _user(UserRole.SYSTEM_ADMIN)
    assert not can_view_metadata(admin, _document(admin.id, is_deleted=True))
