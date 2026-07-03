import { apiDownload, apiRequest, sanitizeDownloadedFilename } from "./api-client";
import type { DocumentListItem } from "./documents";

export async function getDocument(documentId: string): Promise<DocumentListItem> {
  return apiRequest<DocumentListItem>(`/documents/${documentId}`);
}

export async function downloadDocument(documentId: string, fallbackFilename?: string): Promise<void> {
  const { blob, filename } = await apiDownload(`/documents/${documentId}/download`, fallbackFilename ?? "document");
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
