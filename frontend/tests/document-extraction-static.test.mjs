import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const actions = readFileSync(new URL("../app/documents/[id]/document-actions.tsx", import.meta.url), "utf8");
const api = readFileSync(new URL("../lib/documents-api.ts", import.meta.url), "utf8");
const types = readFileSync(new URL("../lib/documents.ts", import.meta.url), "utf8");

assert(types.includes('export type ExtractionStatus = "PENDING" | "PROCESSING" | "SUCCEEDED" | "FAILED"'), "ExtractionStatus type must exist");
assert(types.includes("extraction_status: ExtractionStatus"), "DocumentVersion must expose extraction_status");
assert(types.includes("chunk_count: number"), "DocumentVersion must expose chunk_count");
assert(actions.includes("추출 대기") || actions.includes("extractionStatusLabels"), "UI must show extraction status labels");
assert(actions.includes("version.chunk_count"), "UI must show chunk count");
assert(actions.includes('version.extraction_status === "FAILED"'), "Retry button must be limited to FAILED versions");
assert(actions.includes("canRetry"), "Retry button must be hidden without permission");
assert(api.includes("/extraction/retry"), "Retry API helper must be implemented");
