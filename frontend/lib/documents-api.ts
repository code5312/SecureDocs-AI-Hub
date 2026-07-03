import { apiRequest } from "./api-client";
import type { DocumentRecord, DocumentStatus, DownloadUrlResponse } from "./documents";

export type DocumentListQuery = {
  offset?: number;
  limit?: number;
  title?: string;
  ownerId?: string;
  departmentId?: string;
  status?: DocumentStatus | "";
};

function buildDocumentQuery(query: DocumentListQuery): string {
  const params = new URLSearchParams();
  if (query.offset !== undefined) params.set("offset", String(query.offset));
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  if (query.title?.trim()) params.set("title", query.title.trim());
  if (query.ownerId) params.set("owner_id", query.ownerId);
  if (query.departmentId) params.set("department_id", query.departmentId);
  if (query.status) params.set("status", query.status);
  const value = params.toString();
  return value ? `?${value}` : "";
}

export function listDocuments(query: DocumentListQuery = {}): Promise<DocumentRecord[]> {
  return apiRequest<DocumentRecord[]>(`/documents${buildDocumentQuery(query)}`);
}

export function getDocument(documentId: string): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(`/documents/${encodeURIComponent(documentId)}`);
}

export function uploadDocument(input: { title: string; description?: string; file: File }): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.set("title", input.title.trim());
  if (input.description?.trim()) formData.set("description", input.description.trim());
  formData.set("file", input.file);
  return apiRequest<DocumentRecord>("/documents", { method: "POST", body: formData });
}

export function getDocumentDownloadUrl(documentId: string): Promise<DownloadUrlResponse> {
  return apiRequest<DownloadUrlResponse>(`/documents/${encodeURIComponent(documentId)}/download`);
}

export function deleteDocument(documentId: string): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(`/documents/${encodeURIComponent(documentId)}`, { method: "DELETE" });
}
