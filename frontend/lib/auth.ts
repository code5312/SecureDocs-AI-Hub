export type Role = "SYSTEM_ADMIN" | "DOCUMENT_ADMIN" | "DEPARTMENT_MANAGER" | "USER";

export type UserSummary = {
  id: string;
  email: string;
  name: string;
  role: Role;
  department_id: string | null;
  is_active: boolean;
};

export const roleLabels: Record<Role, string> = {
  SYSTEM_ADMIN: "시스템 관리자",
  DOCUMENT_ADMIN: "문서 관리자",
  DEPARTMENT_MANAGER: "부서 관리자",
  USER: "사용자",
};
