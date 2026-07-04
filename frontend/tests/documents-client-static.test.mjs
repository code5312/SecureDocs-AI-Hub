import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const api = readFileSync(new URL("../lib/documents-api.ts", import.meta.url), "utf8");
const listPage = readFileSync(new URL("../app/documents/page.tsx", import.meta.url), "utf8");
const detailPage = readFileSync(new URL("../app/documents/[id]/page.tsx", import.meta.url), "utf8");

assert(api.includes('new FormData()'), "Document upload must use multipart FormData");
assert(api.includes('apiRequest<DocumentRecord[]>(`/documents'), "Document list must use the protected API client");
assert(api.includes('/download`'), "Document download endpoint must be connected");
assert(!listPage.includes("const documents: DocumentListItem[] = []"), "Document list must not use static placeholder rows");
assert(listPage.includes("uploadDocument") && listPage.includes("listDocuments"), "Document list and upload must call APIs");
assert(detailPage.includes("getDocumentDownloadUrl") && detailPage.includes("deleteDocument"), "Document detail actions must call APIs");
assert(listPage.includes("<ProtectedRoute>") && detailPage.includes("<ProtectedRoute>"), "Document pages must remain protected");
