import { useAuthStore } from "./auth-store";
import { ApiClientError, getApiBaseUrl } from "./api-shared";

export type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
};

type ApiRequestOptions = Omit<RequestInit, "body" | "headers"> & {
  body?: BodyInit | object | null;
  headers?: HeadersInit;
  retryOnUnauthorized?: boolean;
};

let refreshPromise: Promise<boolean> | null = null;

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

function buildHeaders(body: ApiRequestOptions["body"], headers: HeadersInit | undefined): Headers {
  const result = new Headers(headers);
  const token = useAuthStore.getState().accessToken;
  if (token) {
    result.set("Authorization", `Bearer ${token}`);
  }
  if (body && !(body instanceof FormData) && !result.has("Content-Type")) {
    result.set("Content-Type", "application/json");
  }
  return result;
}

function buildBody(body: ApiRequestOptions["body"]): BodyInit | null | undefined {
  if (!body || body instanceof FormData || body instanceof Blob || typeof body === "string") {
    return body as BodyInit | null | undefined;
  }
  return JSON.stringify(body);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  if (!text) {
    return undefined as T;
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiClientError("서버 응답 형식이 올바르지 않습니다.", response.status, "INVALID_RESPONSE");
  }
}

async function toApiError(response: Response): Promise<ApiClientError> {
  let message = "요청 처리 중 오류가 발생했습니다.";
  let code: string | null = null;
  let details: unknown = null;
  try {
    const body = await parseResponse<ApiErrorBody>(response);
    if (body?.error?.message) {
      message = body.error.message;
    }
    code = body?.error?.code ?? null;
    details = body?.error?.details ?? null;
  } catch {
    if (response.status >= 500) {
      message = "서버 오류가 발생했습니다.";
    }
  }
  return new ApiClientError(message, response.status, code, details);
}

async function refreshOnce(): Promise<boolean> {
  if (!refreshPromise) {
    const pendingRefresh = useAuthStore.getState().restoreSession().finally(() => {
      refreshPromise = null;
    });
    refreshPromise = pendingRefresh;
  }
  return refreshPromise ?? Promise.resolve(false);
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, headers, retryOnUnauthorized = true, ...requestOptions } = options;
  const response = await fetch(buildUrl(path), {
    ...requestOptions,
    headers: buildHeaders(body, headers),
    body: buildBody(body),
    credentials: "include",
  });

  const isAuthEndpoint = path.includes("/auth/login") || path.includes("/auth/refresh") || path.includes("/auth/logout");
  if (response.status === 401 && retryOnUnauthorized && !isAuthEndpoint) {
    const refreshed = await refreshOnce();
    if (refreshed) {
      return apiRequest<T>(path, { ...options, retryOnUnauthorized: false });
    }
    useAuthStore.getState().clearSession();
  }

  if (!response.ok) {
    throw await toApiError(response);
  }
  return parseResponse<T>(response);
}

export type DownloadResult = {
  blob: Blob;
  filename: string | null;
};

function headerFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) {
    return null;
  }
  const filenameStar = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (filenameStar?.[1]) {
    try {
      return sanitizeDownloadedFilename(decodeURIComponent(filenameStar[1]));
    } catch {
      return sanitizeDownloadedFilename(filenameStar[1]);
    }
  }
  const filename = contentDisposition.match(/filename="?([^";]+)"?/i);
  return filename?.[1] ? sanitizeDownloadedFilename(filename[1]) : null;
}

export function sanitizeDownloadedFilename(filename: string): string {
  const sanitized = filename.replace(/[\\/\u0000-\u001f\u007f]+/g, "_").replace(/\s+/g, " ").trim().replace(/^\.+$/, "");
  return sanitized || "download";
}

export async function apiDownload(path: string, fallbackFilename = "download", retryOnUnauthorized = true): Promise<DownloadResult> {
  const response = await fetch(buildUrl(path), {
    method: "GET",
    headers: buildHeaders(null, undefined),
    credentials: "include",
  });
  const isAuthEndpoint = path.includes("/auth/");
  if (response.status === 401 && retryOnUnauthorized && !isAuthEndpoint) {
    const refreshed = await refreshOnce();
    if (refreshed) {
      return apiDownload(path, fallbackFilename, false);
    }
    useAuthStore.getState().clearSession();
  }
  if (!response.ok) {
    throw await toApiError(response);
  }
  const blob = await response.blob();
  return { blob, filename: headerFilename(response.headers.get("Content-Disposition")) ?? sanitizeDownloadedFilename(fallbackFilename) };
}
