import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const listPage = readFileSync(new URL("../app/documents/documents-page-client.tsx", import.meta.url), "utf8");
const detailPage = readFileSync(new URL("../app/documents/[id]/document-detail-client.tsx", import.meta.url), "utf8");
const actions = readFileSync(new URL("../app/documents/[id]/document-actions.tsx", import.meta.url), "utf8");
const documentsApi = readFileSync(new URL("../lib/documents-api.ts", import.meta.url), "utf8");
const documentsTypes = readFileSync(new URL("../lib/documents.ts", import.meta.url), "utf8");

assert(!listPage.includes("const documents = []"), "Documents page must not use a static placeholder array");
assert(listPage.includes("listDocuments"), "Documents page must call listDocuments");
assert(listPage.includes("uploadDocument"), "Documents page must upload with API helper");
assert(listPage.includes("FormData") || documentsApi.includes("new FormData"), "Uploads must use FormData");
assert(detailPage.includes("getDocument") && detailPage.includes("listDocumentVersions"), "Detail page must load document and versions");
assert(actions.includes("uploadDocumentVersion"), "Detail actions must support new version uploads");
assert(actions.includes("downloadDocumentVersion"), "Detail actions must support historical version downloads");
assert(actions.includes('user.role === "SYSTEM_ADMIN"') && actions.includes("user.id === document.owner_id"), "Only SYSTEM_ADMIN or owner should see version upload UI");
assert(documentsApi.includes("/versions/${versionId}/download"), "Version download API path must be implemented");
assert(documentsApi.includes("URL.revokeObjectURL"), "Blob object URL must be revoked after downloads");
assert(!/access_token|Authorization=.*[?&]/i.test(documentsApi), "Access Token must not be placed in a URL");
assert(documentsTypes.includes("is_current: boolean"), "DocumentVersion type must expose is_current");
