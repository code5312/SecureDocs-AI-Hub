"""add document version audit actions

Revision ID: 202607030003
Revises: 202607030002
Create Date: 2026-07-03 00:00:03
"""
from alembic import op

revision = "202607030003"
down_revision = "202607030002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for value in ("DOCUMENT_VERSION_UPLOAD", "DOCUMENT_VERSION_DOWNLOAD"):
        op.execute(f"ALTER TYPE audit_action ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed without recreating the enum safely.
    pass
