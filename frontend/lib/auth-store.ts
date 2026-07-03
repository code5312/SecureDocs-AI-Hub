import { create } from "zustand";

import type { AuthenticatedUser, AuthStatus, LoginResponse } from "./auth";
import { ApiClientError, getApiBaseUrl } from "./api-shared";

type AuthState = {
  accessToken: string | null;
  user: AuthenticatedUser | null;
  status: AuthStatus;
  setSession: (session: LoginResponse) => void;
  clearSession: () => void;
  restoreSession: () => Promise<boolean>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

async function parseAuthResponse(response: Response): Promise<LoginResponse> {
  const payload = (await response.json()) as Partial<LoginResponse>;
  if (!payload.access_token || payload.token_type !== "bearer" || !payload.user) {
    throw new ApiClientError("인증 응답 형식이 올바르지 않습니다.", response.status, "INVALID_RESPONSE");
  }
  return payload as LoginResponse;
}

async function requestSession(path: "/auth/login" | "/auth/refresh", body?: object): Promise<LoginResponse> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new ApiClientError(path === "/auth/login" ? "이메일 또는 비밀번호가 올바르지 않습니다." : "인증 세션을 복구할 수 없습니다.", response.status);
  }
  return parseAuthResponse(response);
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  status: "loading",
  setSession: (session) => set({ accessToken: session.access_token, user: session.user, status: "authenticated" }),
  clearSession: () => set({ accessToken: null, user: null, status: "unauthenticated" }),
  restoreSession: async () => {
    set((state) => ({ ...state, status: state.status === "authenticated" ? "authenticated" : "loading" }));
    try {
      const session = await requestSession("/auth/refresh");
      get().setSession(session);
      return true;
    } catch {
      get().clearSession();
      return false;
    }
  },
  login: async (email, password) => {
    const session = await requestSession("/auth/login", { email, password });
    get().setSession(session);
  },
  logout: async () => {
    try {
      await fetch(`${getApiBaseUrl()}/auth/logout`, { method: "POST", credentials: "include" });
    } finally {
      get().clearSession();
    }
  },
}));
