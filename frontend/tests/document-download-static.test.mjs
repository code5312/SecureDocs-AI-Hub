import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const apiClient = readFileSync(new URL("../lib/api-client.ts", import.meta.url), "utf8");
const documentsApi = readFileSync(new URL("../lib/documents-api.ts", import.meta.url), "utf8");
const detailActions = readFileSync(new URL("../app/documents/[id]/document-actions.tsx", import.meta.url), "utf8");

assert(apiClient.includes("apiDownload"), "Blob download helper must be present");
assert(apiClient.includes('credentials: "include"'), "Download requests must include credentials");
assert(apiClient.includes('Authorization", `Bearer ${token}`'), "Download requests must reuse bearer auth headers");
assert(apiClient.includes("response.blob()"), "Successful download responses must be read as Blob");
assert(apiClient.includes("filename\\*="), "RFC 5987 filename* parsing must be supported");
assert(documentsApi.includes("URL.createObjectURL"), "Document download must create an object URL");
assert(documentsApi.includes("URL.revokeObjectURL"), "Document download must revoke the object URL");
assert(!documentsApi.includes("window.location.assign"), "Document download must not navigate to presigned URLs");
assert(!/access_token|Authorization=.*[?&]/i.test(documentsApi), "Access Token must not be placed in a URL");
assert(detailActions.includes("disabled={isDownloading}"), "Download button must prevent duplicate clicks while downloading");
