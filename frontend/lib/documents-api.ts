import { apiDownload, apiRequest, sanitizeDownloadedFilename } from "./api-client";
import type { DocumentListParams, DocumentRecord, DocumentVersion } from "./documents";

function queryString(params: DocumentListParams = {}): string {
  const query = new URLSearchParams();
  if (params.title?.trim()) {
    query.set("title", params.title.trim());
  }
  if (params.status) {
    query.set("status", params.status);
  }
  query.set("offset", String(params.offset ?? 0));
  query.set("limit", String(params.limit ?? 50));
  return query.toString();
}

export async function listDocuments(params: DocumentListParams = {}): Promise<DocumentRecord[]> {
  const query = queryString(params);
  return apiRequest<DocumentRecord[]>(`/documents?${query}`);
}

export async function uploadDocument(input: { title: string; description?: string; file: File }): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("title", input.title);
  if (input.description) {
    form.append("description", input.description);
  }
  form.append("file", input.file);
  return apiRequest<DocumentRecord>("/documents", { method: "POST", body: form });
}

export async function getDocument(documentId: string): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(`/documents/${documentId}`);
}

export async function deleteDocument(documentId: string): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(`/documents/${documentId}`, { method: "DELETE" });
}

export async function listDocumentVersions(documentId: string): Promise<DocumentVersion[]> {
  return apiRequest<DocumentVersion[]>(`/documents/${documentId}/versions`);
}

export async function uploadDocumentVersion(documentId: string, file: File): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<DocumentRecord>(`/documents/${documentId}/versions`, { method: "POST", body: form });
}

async function saveBlob(path: string, fallbackFilename?: string): Promise<void> {
  const { blob, filename } = await apiDownload(path, fallbackFilename ?? "document");
  const objectUrl = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = sanitizeDownloadedFilename(filename ?? fallbackFilename ?? "document");
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export async function downloadDocument(documentId: string, fallbackFilename?: string): Promise<void> {
  return saveBlob(`/documents/${documentId}/download`, fallbackFilename);
}

export async function downloadDocumentVersion(documentId: string, versionId: string, fallbackFilename?: string): Promise<void> {
  return saveBlob(`/documents/${documentId}/versions/${versionId}/download`, fallbackFilename);
}
