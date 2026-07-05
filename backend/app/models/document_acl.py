import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AclPermission


class DocumentAclEntry(Base):
    __tablename__ = "document_acl_entries"
    __table_args__ = (
        CheckConstraint("(user_id IS NOT NULL AND department_id IS NULL) OR (user_id IS NULL AND department_id IS NOT NULL)", name="ck_document_acl_one_principal"),
        Index("ix_document_acl_document_permission", "document_id", "permission"),
        Index("uq_document_acl_user_permission", "document_id", "user_id", "permission", unique=True, postgresql_where=text("user_id IS NOT NULL")),
        Index("uq_document_acl_department_permission", "document_id", "department_id", "permission", unique=True, postgresql_where=text("department_id IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True, index=True)
    permission: Mapped[AclPermission] = mapped_column(Enum(AclPermission, name="acl_permission"), nullable=False, index=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("Document")
    user = relationship("User", foreign_keys=[user_id])
    department = relationship("Department")
    grantor = relationship("User", foreign_keys=[granted_by])
