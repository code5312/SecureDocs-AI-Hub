export type DocumentStatus = "ACTIVE" | "PROCESSING" | "FAILED";

export type DocumentListItem = {
  id: string;
  title: string;
  description: string | null;
  owner_id: string;
  department_id: string | null;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  current_version: {
    normalized_filename: string;
    mime_type: string;
    file_size: number;
    checksum_sha256: string;
  } | null;
};

export const allowedDocumentExtensions = ["PDF", "DOCX", "PPTX", "XLSX", "TXT", "MD"];
