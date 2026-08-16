import type { ApiErrorBody } from "@/types/api";

/**
 * Browser calls go through the Next.js same-origin rewrite (`/backend/*` → FastAPI).
 * Override with NEXT_PUBLIC_API_BASE_URL when pointing at a remote backend.
 */
export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "/backend";
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

async function parseError(response: Response): Promise<ApiError> {
  let code = `http_${response.status}`;
  let message = response.statusText || "Request failed";
  let details: unknown;

  try {
    const body = (await response.json()) as ApiErrorBody | Record<string, unknown>;
    if (
      body &&
      typeof body === "object" &&
      "error" in body &&
      body.error &&
      typeof body.error === "object"
    ) {
      const err = body.error as ApiErrorBody["error"];
      code = err.code || code;
      message = err.message || message;
      details = err.details;
    } else if (body && typeof body === "object" && "detail" in body) {
      message = String(body.detail);
    }
  } catch {
    // Non-JSON error bodies are fine; keep status text.
  }

  return new ApiError(response.status, code, message, details);
}

export type RequestOptions = {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  headers?: HeadersInit;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = new Headers(options.headers);
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? (options.body !== undefined ? "POST" : "GET"),
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(0, "network_error", "Network failure or backend unavailable");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/** Absolute URL for MJPEG <img src>. Uses same base as the API client. */
export function cameraPreviewUrl(cameraId: string): string {
  const base = getApiBaseUrl();
  if (base.startsWith("http://") || base.startsWith("https://")) {
    return `${base}/api/cameras/${encodeURIComponent(cameraId)}/preview`;
  }
  // Relative same-origin path (proxy).
  return `${base}/api/cameras/${encodeURIComponent(cameraId)}/preview`;
}
