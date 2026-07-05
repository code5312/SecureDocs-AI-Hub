"""add document extraction pipeline tables

Revision ID: 202607050001
Revises: 202607030004
Create Date: 2026-07-05 00:00:01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202607050001"
down_revision = "202607030004"
branch_labels = None
depends_on = None

extraction_status = postgresql.ENUM("PENDING", "PROCESSING", "SUCCEEDED", "FAILED", name="extraction_status", create_type=False)


def upgrade() -> None:
    extraction_status.create(op.get_bind(), checkfirst=True)
    for value in ("DOCUMENT_EXTRACTION_QUEUED", "DOCUMENT_EXTRACTION_SUCCEEDED", "DOCUMENT_EXTRACTION_FAILED", "DOCUMENT_EXTRACTION_RETRY"):
        op.execute(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column("document_versions", sa.Column("extraction_status", extraction_status, nullable=True))
    op.add_column("document_versions", sa.Column("extraction_error_code", sa.String(length=64), nullable=True))
    op.add_column("document_versions", sa.Column("extraction_error_message", sa.String(length=512), nullable=True))
    op.add_column("document_versions", sa.Column("extraction_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("document_versions", sa.Column("extraction_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("document_versions", sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("document_versions", sa.Column("chunk_count", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.execute("UPDATE document_versions SET extraction_status = 'PENDING' WHERE extraction_status IS NULL")
    op.alter_column("document_versions", "extraction_status", nullable=False, server_default="PENDING")
    op.create_index("ix_document_versions_extraction_status", "document_versions", ["extraction_status"])

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("slide_number", sa.Integer(), nullable=True),
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        sa.Column("row_start", sa.Integer(), nullable=True),
        sa.Column("row_end", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_version_id", "chunk_index", name="uq_document_chunks_version_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_document_version_id", "document_chunks", ["document_version_id"])
    op.create_index("ix_document_chunks_content_sha256", "document_chunks", ["content_sha256"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_content_sha256", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_version_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_document_versions_extraction_status", table_name="document_versions")
    for column in ("chunk_count", "extracted_at", "extraction_started_at", "extraction_attempts", "extraction_error_message", "extraction_error_code", "extraction_status"):
        op.drop_column("document_versions", column)
    extraction_status.drop(op.get_bind(), checkfirst=True)
    # PostgreSQL audit_action enum additions are intentionally not removed on downgrade.
