export type DocumentStatus = "ACTIVE" | "PROCESSING" | "FAILED";

export type DocumentVersion = {
  id: string;
  version_number: number;
  original_filename: string;
  normalized_filename: string;
  mime_type: string;
  file_size: number;
  checksum_sha256: string;
  uploaded_by: string;
  created_at: string;
  is_current: boolean;
};

export type DocumentRecord = {
  id: string;
  title: string;
  description: string | null;
  owner_id: string;
  department_id: string | null;
  current_version_id: string | null;
  status: DocumentStatus;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  current_version: DocumentVersion | null;
};

export type DocumentListItem = DocumentRecord;

export type DocumentListParams = {
  title?: string;
  status?: DocumentStatus | "";
  offset?: number;
  limit?: number;
};

export const allowedDocumentExtensions = ["PDF", "DOCX", "PPTX", "XLSX", "TXT", "MD"];

export function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function shortChecksum(checksum: string): string {
  return checksum.length > 16 ? `${checksum.slice(0, 16)}…` : checksum;
}
