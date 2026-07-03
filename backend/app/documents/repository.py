import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentVersion
from app.models.enums import DocumentStatus


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

    def list(self, *, offset: int, limit: int, title: str | None = None, owner_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None, status: DocumentStatus | None = None, include_deleted: bool = False) -> list[Document]:
        stmt = select(Document).options(selectinload(Document.versions)).order_by(Document.created_at.desc()).offset(offset).limit(limit)
        if not include_deleted:
            stmt = stmt.where(Document.is_deleted.is_(False))
        if title:
            stmt = stmt.where(Document.title.ilike(f"%{title.strip()}%"))
        if owner_id:
            stmt = stmt.where(Document.owner_id == owner_id)
        if department_id:
            stmt = stmt.where(Document.department_id == department_id)
        if status:
            stmt = stmt.where(Document.status == status)
        return list(self.db.scalars(stmt))
