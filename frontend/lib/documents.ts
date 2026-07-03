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

export type DownloadUrlResponse = {
  url: string;
  expires_in: number;
};

export const allowedDocumentExtensions = ["PDF", "DOCX", "PPTX", "XLSX", "TXT", "MD"];

export const documentStatusLabels: Record<DocumentStatus, string> = {
  ACTIVE: "사용 가능",
  PROCESSING: "처리 중",
  FAILED: "처리 실패",
};

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}

export function formatDocumentDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
