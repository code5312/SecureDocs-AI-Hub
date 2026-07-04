from app.models.document import Document
from app.models.enums import UserRole
from app.models.user import User


def can_view_metadata(user: User, document: Document) -> bool:
    if document.is_deleted:
        return False
    if user.role in {UserRole.SYSTEM_ADMIN, UserRole.DOCUMENT_ADMIN}:
        return True
    if user.role == UserRole.DEPARTMENT_MANAGER:
        return document.owner_id == user.id or (user.department_id is not None and user.department_id == document.department_id)
    return document.owner_id == user.id


def can_download(user: User, document: Document) -> bool:
    if document.is_deleted:
        return False
    if user.role == UserRole.SYSTEM_ADMIN:
        return True
    return document.owner_id == user.id


def can_delete(user: User, document: Document) -> bool:
    if document.is_deleted:
        return False
    if user.role == UserRole.SYSTEM_ADMIN:
        return True
    return document.owner_id == user.id


def can_upload_version(user: User, document: Document) -> bool:
    """Return whether a user may append a new version under the temporary ACL policy."""
    if document.is_deleted:
        return False
    if user.role == UserRole.SYSTEM_ADMIN:
        return True
    return document.owner_id == user.id
