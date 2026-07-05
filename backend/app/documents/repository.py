import uuid

from sqlalchemy import ColumnElement, and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.department import Department
from app.models.document import Document, DocumentVersion
from app.models.document_acl import DocumentAclEntry
from app.models.enums import AclPermission, DocumentStatus
from app.models.user import User


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_document(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def create_version(self, version: DocumentVersion) -> DocumentVersion:
        self.db.add(version)
        self.db.flush()
        return version

    def get(self, document_id: uuid.UUID) -> Document | None:
        return self.db.scalar(select(Document).options(selectinload(Document.versions)).where(Document.id == document_id))

    def get_for_update(self, document_id: uuid.UUID) -> Document | None:
        """Lock a document row while calculating the next version number."""
        return self.db.scalar(select(Document).options(selectinload(Document.versions)).where(Document.id == document_id).with_for_update())

    def get_version(self, document_id: uuid.UUID, version_id: uuid.UUID) -> DocumentVersion | None:
        return self.db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document_id, DocumentVersion.id == version_id))

    def list_versions(self, document_id: uuid.UUID) -> list[DocumentVersion]:
        stmt = select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_number.desc())
        return list(self.db.scalars(stmt))

    def get_max_version_number(self, document_id: uuid.UUID) -> int:
        return int(self.db.scalar(select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(DocumentVersion.document_id == document_id)) or 0)

    def granted_permissions(self, document_id: uuid.UUID, user: User) -> set[AclPermission]:
        stmt = select(DocumentAclEntry.permission).where(DocumentAclEntry.document_id == document_id)
        if user.department_id is None:
            stmt = stmt.where(DocumentAclEntry.user_id == user.id)
        else:
            active_department_acl = and_(
                DocumentAclEntry.department_id == user.department_id,
                exists().where(Department.id == DocumentAclEntry.department_id).where(Department.is_active.is_(True)),
            )
            stmt = stmt.where(or_(DocumentAclEntry.user_id == user.id, active_department_acl))
        return set(self.db.scalars(stmt))

    def list(self, *, offset: int, limit: int, access_predicate: ColumnElement[bool], title: str | None = None, owner_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None, status: DocumentStatus | None = None) -> list[Document]:
        stmt = select(Document).options(selectinload(Document.versions)).where(access_predicate).order_by(Document.created_at.desc()).offset(offset).limit(limit)
        if title:
            stmt = stmt.where(Document.title.ilike(f"%{title.strip()}%"))
        if owner_id:
            stmt = stmt.where(Document.owner_id == owner_id)
        if department_id:
            stmt = stmt.where(Document.department_id == department_id)
        if status:
            stmt = stmt.where(Document.status == status)
        return list(self.db.scalars(stmt).unique())

    def list_acl_entries(self, document_id: uuid.UUID) -> list[DocumentAclEntry]:
        stmt = select(DocumentAclEntry).options(selectinload(DocumentAclEntry.user), selectinload(DocumentAclEntry.department)).where(DocumentAclEntry.document_id == document_id).order_by(DocumentAclEntry.created_at.desc())
        return list(self.db.scalars(stmt))

    def get_acl_entry(self, document_id: uuid.UUID, entry_id: uuid.UUID) -> DocumentAclEntry | None:
        stmt = select(DocumentAclEntry).options(selectinload(DocumentAclEntry.user), selectinload(DocumentAclEntry.department)).where(DocumentAclEntry.document_id == document_id, DocumentAclEntry.id == entry_id)
        return self.db.scalar(stmt)

    def find_acl_entry(self, *, document_id: uuid.UUID, permission: AclPermission, user_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None) -> DocumentAclEntry | None:
        stmt = select(DocumentAclEntry).where(DocumentAclEntry.document_id == document_id, DocumentAclEntry.permission == permission)
        if user_id is not None:
            stmt = stmt.where(DocumentAclEntry.user_id == user_id)
        if department_id is not None:
            stmt = stmt.where(DocumentAclEntry.department_id == department_id)
        return self.db.scalar(stmt)

    def create_acl_entry(self, entry: DocumentAclEntry) -> DocumentAclEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def delete_acl_entry(self, entry: DocumentAclEntry) -> None:
        self.db.delete(entry)
        self.db.flush()

    def get_active_user(self, user_id: uuid.UUID) -> User | None:
        return self.db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))

    def get_active_department(self, department_id: uuid.UUID) -> Department | None:
        return self.db.scalar(select(Department).where(Department.id == department_id, Department.is_active.is_(True)))

    def search_acl_users(self, query: str, limit: int = 20) -> list[User]:
        pattern = self._search_pattern(query)
        stmt = select(User).where(User.is_active.is_(True), or_(User.email.ilike(pattern, escape="\\"), User.name.ilike(pattern, escape="\\"))).order_by(User.name.asc()).limit(limit)
        return list(self.db.scalars(stmt))

    def search_acl_departments(self, query: str, limit: int = 20) -> list[Department]:
        pattern = self._search_pattern(query)
        stmt = select(Department).where(Department.is_active.is_(True), Department.name.ilike(pattern, escape="\\")).order_by(Department.name.asc()).limit(limit)
        return list(self.db.scalars(stmt))

    def _search_pattern(self, query: str) -> str:
        escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return f"%{escaped}%"
