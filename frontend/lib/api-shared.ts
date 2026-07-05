export class ApiClientError extends Error {
  status: number;
  code: string | null;
  details: unknown;

  constructor(message: string, status: number, code: string | null = null, details: unknown = null) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";
}
