"""create document metadata tables

Revision ID: 202607030002
Revises: 202607030001
Create Date: 2026-07-03 00:00:02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202607030002"
down_revision = "202607030001"
branch_labels = None
depends_on = None

document_status = postgresql.ENUM("ACTIVE", "PROCESSING", "FAILED", name="document_status")


def upgrade() -> None:
    for value in ("DOCUMENT_UPLOAD", "DOCUMENT_LIST", "DOCUMENT_VIEW", "DOCUMENT_DOWNLOAD", "DOCUMENT_DELETE", "DOCUMENT_UPLOAD_FAILED"):
        op.execute(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'")
    document_status.create(op.get_bind(), checkfirst=True)
    op.create_table("documents", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False), sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id"), nullable=True), sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("status", document_status, nullable=False), sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_documents_title", "documents", ["title"])
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_department_id", "documents", ["department_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_is_deleted", "documents", ["is_deleted"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])
    op.create_table("document_versions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False), sa.Column("version_number", sa.Integer(), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("normalized_filename", sa.String(255), nullable=False), sa.Column("storage_key", sa.String(1024), nullable=False), sa.Column("mime_type", sa.String(255), nullable=False), sa.Column("file_size", sa.Integer(), nullable=False), sa.Column("checksum_sha256", sa.String(64), nullable=False), sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_document_version"))
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_uploaded_by", "document_versions", ["uploaded_by"])
    op.create_index("ix_document_versions_storage_key", "document_versions", ["storage_key"], unique=True)
    op.create_index("ix_document_versions_checksum", "document_versions", ["checksum_sha256"])
    op.create_foreign_key("fk_documents_current_version_id", "documents", "document_versions", ["current_version_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_documents_current_version_id", "documents", type_="foreignkey")
    op.drop_index("ix_document_versions_checksum", table_name="document_versions")
    op.drop_index("ix_document_versions_storage_key", table_name="document_versions")
    op.drop_index("ix_document_versions_uploaded_by", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_is_deleted", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_department_id", table_name="documents")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_index("ix_documents_title", table_name="documents")
    op.drop_table("documents")
    document_status.drop(op.get_bind(), checkfirst=True)
