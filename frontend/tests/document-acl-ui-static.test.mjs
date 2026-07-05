import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const actions = readFileSync(new URL("../app/documents/[id]/document-actions.tsx", import.meta.url), "utf8");
const documentsApi = readFileSync(new URL("../lib/documents-api.ts", import.meta.url), "utf8");
const documentsTypes = readFileSync(new URL("../lib/documents.ts", import.meta.url), "utf8");

assert(documentsTypes.includes("export type DocumentPermission"), "DocumentPermission type must exist");
assert(documentsTypes.includes("effective_permissions: DocumentPermission[]"), "Document records must expose effective permissions");
assert(documentsTypes.includes("export type DocumentAclEntry"), "ACL entry type must exist");
assert(actions.includes("READ_CONTENT") && actions.includes("현재 버전 다운로드"), "Download button must be gated by READ_CONTENT");
assert(actions.includes("UPLOAD_VERSION") && actions.includes("새 버전 업로드"), "Version upload form must be gated by UPLOAD_VERSION");
assert(actions.includes("DELETE") && actions.includes("논리 삭제"), "Delete button must be gated by DELETE");
assert(actions.includes("MANAGE_ACL") && actions.includes("공유 및 권한"), "ACL UI must be gated by MANAGE_ACL");
assert(documentsApi.includes("listDocumentAcl") && documentsApi.includes("/acl"), "ACL list helper must be implemented");
assert(documentsApi.includes("searchDocumentAclPrincipals") && documentsApi.includes("/acl/principals?query="), "ACL principal search helper must be implemented");
assert(documentsApi.includes("grantDocumentAcl") && documentsApi.includes("principal_type"), "ACL grant helper must be implemented");
assert(documentsApi.includes("revokeDocumentAcl") && documentsApi.includes('method: "DELETE"'), "ACL revoke helper must be implemented");
assert(!/access_token|Authorization=.*[?&]/i.test(documentsApi), "Access Token must not be placed in a URL");
assert(actions.includes("중복") || actions.includes("disabled={busy}"), "ACL UI must guard against duplicate submissions");
