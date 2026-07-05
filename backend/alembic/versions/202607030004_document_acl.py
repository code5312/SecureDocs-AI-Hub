"""add document ACL entries

Revision ID: 202607030004
Revises: 202607030003
Create Date: 2026-07-03 00:00:04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "202607030004"
down_revision = "202607030003"
branch_labels = None
depends_on = None

acl_permission = postgresql.ENUM("VIEW_METADATA", "READ_CONTENT", "UPLOAD_VERSION", "DELETE", "MANAGE_ACL", name="acl_permission")


def upgrade() -> None:
    for value in ("DOCUMENT_ACL_GRANT", "DOCUMENT_ACL_REVOKE"):
        op.execute(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'")
    acl_permission.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "document_acl_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("permission", acl_permission, nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("(user_id IS NOT NULL AND department_id IS NULL) OR (user_id IS NULL AND department_id IS NOT NULL)", name="ck_document_acl_one_principal"),
    )
    op.create_index("ix_document_acl_entries_document_id", "document_acl_entries", ["document_id"])
    op.create_index("ix_document_acl_entries_user_id", "document_acl_entries", ["user_id"])
    op.create_index("ix_document_acl_entries_department_id", "document_acl_entries", ["department_id"])
    op.create_index("ix_document_acl_entries_permission", "document_acl_entries", ["permission"])
    op.create_index("ix_document_acl_document_permission", "document_acl_entries", ["document_id", "permission"])
    op.create_index("uq_document_acl_user_permission", "document_acl_entries", ["document_id", "user_id", "permission"], unique=True, postgresql_where=sa.text("user_id IS NOT NULL"))
    op.create_index("uq_document_acl_department_permission", "document_acl_entries", ["document_id", "department_id", "permission"], unique=True, postgresql_where=sa.text("department_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("uq_document_acl_department_permission", table_name="document_acl_entries")
    op.drop_index("uq_document_acl_user_permission", table_name="document_acl_entries")
    op.drop_index("ix_document_acl_document_permission", table_name="document_acl_entries")
    op.drop_index("ix_document_acl_entries_permission", table_name="document_acl_entries")
    op.drop_index("ix_document_acl_entries_department_id", table_name="document_acl_entries")
    op.drop_index("ix_document_acl_entries_user_id", table_name="document_acl_entries")
    op.drop_index("ix_document_acl_entries_document_id", table_name="document_acl_entries")
    op.drop_table("document_acl_entries")
    acl_permission.drop(op.get_bind(), checkfirst=True)
