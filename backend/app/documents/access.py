from collections.abc import Iterable

from sqlalchemy import and_, exists, false, or_, true
from sqlalchemy.sql.elements import ColumnElement

from app.models.department import Department
from app.models.document import Document
from app.models.document_acl import DocumentAclEntry
from app.models.enums import AclPermission, UserRole
from app.models.user import User

ALL_DOCUMENT_PERMISSIONS = frozenset({AclPermission.VIEW_METADATA, AclPermission.READ_CONTENT, AclPermission.UPLOAD_VERSION, AclPermission.DELETE, AclPermission.MANAGE_ACL})


def implied_permissions(permission: AclPermission) -> set[AclPermission]:
    """Return ACL permissions that satisfy a requested permission."""
    if permission == AclPermission.VIEW_METADATA:
        return set(ALL_DOCUMENT_PERMISSIONS)
    return {permission}


def has_document_permission(user: User, document: Document, granted_permissions: Iterable[AclPermission], permission: AclPermission) -> bool:
    """Evaluate document access with implicit owner/role grants and explicit ACL rows."""
    if not user.is_active or document.is_deleted:
        return False
    if user.role == UserRole.SYSTEM_ADMIN or document.owner_id == user.id:
        return True
    if permission == AclPermission.VIEW_METADATA:
        if user.role == UserRole.DOCUMENT_ADMIN:
            return True
        if user.role == UserRole.DEPARTMENT_MANAGER and user.department_id is not None and user.department_id == document.department_id:
            return True
    return bool(set(granted_permissions).intersection(implied_permissions(permission)))


def effective_document_permissions(user: User, document: Document, granted_permissions: Iterable[AclPermission]) -> list[AclPermission]:
    """Return effective permissions sorted in stable declaration order for API/UI use."""
    return [permission for permission in AclPermission if has_document_permission(user, document, granted_permissions, permission)]


def build_document_access_predicate(user: User, permission: AclPermission) -> ColumnElement[bool]:
    """Build a SQL predicate reusable by document listing and future RAG filtering."""
    if not user.is_active:
        return false()
    if user.role == UserRole.SYSTEM_ADMIN:
        return Document.is_deleted.is_(False)

    clauses: list[ColumnElement[bool]] = [Document.owner_id == user.id]
    if permission == AclPermission.VIEW_METADATA:
        if user.role == UserRole.DOCUMENT_ADMIN:
            clauses.append(true())
        if user.role == UserRole.DEPARTMENT_MANAGER and user.department_id is not None:
            clauses.append(Document.department_id == user.department_id)

    accepted = implied_permissions(permission)
    clauses.append(
        exists()
        .where(DocumentAclEntry.document_id == Document.id)
        .where(DocumentAclEntry.user_id == user.id)
        .where(DocumentAclEntry.permission.in_(accepted))
    )
    if user.department_id is not None:
        clauses.append(
            exists()
            .where(DocumentAclEntry.document_id == Document.id)
            .where(DocumentAclEntry.department_id == user.department_id)
            .where(DocumentAclEntry.permission.in_(accepted))
            .where(exists().where(Department.id == DocumentAclEntry.department_id).where(Department.is_active.is_(True)))
        )
    return and_(Document.is_deleted.is_(False), or_(*clauses))
