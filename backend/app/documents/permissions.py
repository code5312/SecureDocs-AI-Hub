from collections.abc import Iterable

from app.documents.access import has_document_permission
from app.models.document import Document
from app.models.enums import AclPermission
from app.models.user import User


def can_view_metadata(user: User, document: Document, permissions: Iterable[AclPermission] = ()) -> bool:
    return has_document_permission(user, document, permissions, AclPermission.VIEW_METADATA)


def can_download(user: User, document: Document, permissions: Iterable[AclPermission] = ()) -> bool:
    return has_document_permission(user, document, permissions, AclPermission.READ_CONTENT)


def can_delete(user: User, document: Document, permissions: Iterable[AclPermission] = ()) -> bool:
    return has_document_permission(user, document, permissions, AclPermission.DELETE)


def can_upload_version(user: User, document: Document, permissions: Iterable[AclPermission] = ()) -> bool:
    """Return whether a user may append a new version under ACL-aware policy."""
    return has_document_permission(user, document, permissions, AclPermission.UPLOAD_VERSION)


def can_manage_acl(user: User, document: Document, permissions: Iterable[AclPermission] = ()) -> bool:
    return has_document_permission(user, document, permissions, AclPermission.MANAGE_ACL)
