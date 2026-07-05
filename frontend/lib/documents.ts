export type DocumentStatus = "ACTIVE" | "PROCESSING" | "FAILED";
export type ExtractionStatus = "PENDING" | "PROCESSING" | "SUCCEEDED" | "FAILED";

export type DocumentPermission = "VIEW_METADATA" | "READ_CONTENT" | "UPLOAD_VERSION" | "DELETE" | "MANAGE_ACL";

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
  extraction_status: ExtractionStatus;
  extraction_error_code: string | null;
  extraction_error_message: string | null;
  extraction_attempts: number;
  extracted_at: string | null;
  chunk_count: number;
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
  effective_permissions: DocumentPermission[];
};

export type DocumentAclEntry = {
  id: string;
  principal_type: "USER" | "DEPARTMENT";
  user: { id: string; name: string; email: string; department_id: string | null } | null;
  department: { id: string; name: string } | null;
  permission: DocumentPermission;
  granted_by: string | null;
  created_at: string;
};

export type DocumentAclPrincipalSearch = {
  users: Array<{ id: string; name: string; email: string; department_id: string | null }>;
  departments: Array<{ id: string; name: string }>;
};

export type DocumentListItem = DocumentRecord;

export type DocumentListParams = {
  title?: string;
  status?: DocumentStatus | "";
  offset?: number;
  limit?: number;
};

export const allowedDocumentExtensions = ["PDF", "DOCX", "PPTX", "XLSX", "TXT", "MD"];

export const documentPermissionLabels: Record<DocumentPermission, string> = {
  VIEW_METADATA: "문서 정보 보기",
  READ_CONTENT: "문서 내용 읽기 및 다운로드",
  UPLOAD_VERSION: "새 버전 업로드",
  DELETE: "문서 삭제",
  MANAGE_ACL: "공유 및 권한 관리",
};

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

export const extractionStatusLabels: Record<ExtractionStatus, string> = { PENDING: "추출 대기", PROCESSING: "처리 중", SUCCEEDED: "추출 완료", FAILED: "추출 실패" };
