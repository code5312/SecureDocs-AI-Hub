from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_acl_model_uses_nullable_fks_check_and_partial_unique_indexes() -> None:
    model = read("backend/app/models/document_acl.py")
    assert "class DocumentAclEntry" in model
    assert "CheckConstraint" in model and "ck_document_acl_one_principal" in model
    assert "user_id IS NOT NULL" in model and "department_id IS NOT NULL" in model
    assert "uq_document_acl_user_permission" in model
    assert "uq_document_acl_department_permission" in model
    assert "storage_key" not in model


def test_acl_migration_creates_enum_table_constraints_and_indexes() -> None:
    migration = read("backend/alembic/versions/202607030004_document_acl.py")
    assert "revision = \"202607030004\"" in migration
    assert "down_revision = \"202607030003\"" in migration
    assert "acl_permission" in migration
    assert "document_acl_entries" in migration
    assert "ck_document_acl_one_principal" in migration
    assert "postgresql_where=sa.text(\"user_id IS NOT NULL\")" in migration
    assert "postgresql_where=sa.text(\"department_id IS NOT NULL\")" in migration
    assert "ondelete=\"CASCADE\"" in migration


def test_acl_permission_scope_is_sql_level_and_rag_reusable() -> None:
    access = read("backend/app/documents/access.py")
    repository = read("backend/app/documents/repository.py")
    service = read("backend/app/documents/service.py")
    assert "def build_document_access_predicate" in access
    assert "exists()" in access and ".where(DocumentAclEntry.document_id == Document.id)" in access
    assert "DocumentAclEntry.user_id == user.id" in access
    assert "DocumentAclEntry.department_id == user.department_id" in access
    assert "accepted = implied_permissions(permission)" in access
    assert "def list_documents" in repository
    assert "def list(self" not in repository
    assert "access_predicate" in repository
    assert ".where(access_predicate)" in repository
    assert "build_document_access_predicate(actor, AclPermission.VIEW_METADATA)" in service
    assert "effective_document_permissions" in service


def test_document_routes_expose_acl_api_and_effective_permissions() -> None:
    router = read("backend/app/documents/router.py")
    schemas = read("backend/app/documents/schemas.py")
    assert "@router.get(\"/{document_id}/acl/principals\"" in router
    assert "@router.get(\"/{document_id}/acl\"" in router
    assert "@router.post(\"/{document_id}/acl\"" in router
    assert "@router.delete(\"/{document_id}/acl/{acl_entry_id}\"" in router
    assert "payload.effective_permissions = service.effective_permissions" in router
    assert "class DocumentAclGrantRequest" in schemas
    assert "class DocumentAclEntryRead" in schemas
    assert "effective_permissions" in schemas


def test_acl_audit_actions_and_sensitive_data_rules() -> None:
    enums = read("backend/app/models/enums.py")
    service = read("backend/app/documents/service.py")
    assert "DOCUMENT_ACL_GRANT" in enums
    assert "DOCUMENT_ACL_REVOKE" in enums
    assert "AuditAction.DOCUMENT_ACL_GRANT" in service
    assert "AuditAction.DOCUMENT_ACL_REVOKE" in service
    acl_sections = "\n".join(line for line in service.splitlines() if "DOCUMENT_ACL" in line or "acl_entry" in line or "principal" in line)
    assert "storage_key" not in acl_sections
    assert "password" not in acl_sections.lower()
