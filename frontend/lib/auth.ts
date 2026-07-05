export type Role = "SYSTEM_ADMIN" | "DOCUMENT_ADMIN" | "DEPARTMENT_MANAGER" | "USER";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export type AuthenticatedUser = {
  id: string;
  email: string;
  name: string;
  role: Role;
  department_id: string | null;
  is_active: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthenticatedUser;
};

export type UserSummary = AuthenticatedUser;

export const roleLabels: Record<Role, string> = {
  SYSTEM_ADMIN: "시스템 관리자",
  DOCUMENT_ADMIN: "문서 관리자",
  DEPARTMENT_MANAGER: "부서 관리자",
  USER: "사용자",
};

export const adminRoles: Role[] = ["SYSTEM_ADMIN"];

export function isSystemAdmin(user: AuthenticatedUser | null): boolean {
  return user?.role === "SYSTEM_ADMIN";
}
