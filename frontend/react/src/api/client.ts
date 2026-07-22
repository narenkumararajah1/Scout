// Low-level HTTP client (V3 Phase 7A - "API client layer"). The only
// module in the frontend allowed to call fetch() directly; every
// service in ../services/ goes through here instead. Handles auth
// header injection, JSON parsing, and both response shapes the backend
// uses: V3's {"success", "message", "data"} envelope
// (docs/v3/10_API_SPECIFICATION.md, /api/v1/* routes) and V2's raw
// response bodies (unversioned routes, e.g. /companies).

const TOKEN_STORAGE_KEY = "scout_access_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

// Emits "unauthorized" whenever a request comes back 401 - AuthContext
// listens for this so an expired/invalid token clears client-side
// session state immediately, without every call site handling it.
export const authEvents = new EventTarget();

export class ApiError extends Error {
  status: number;
  errors: unknown[];

  constructor(status: number, message: string, errors: unknown[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  // Whether to attach the Authorization header. Defaults to true; only
  // the login call (which has no token yet) passes false.
  auth?: boolean;
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    if (typeof record.message === "string") {
      return record.message;
    }
    if (typeof record.detail === "string") {
      return record.detail;
    }
  }
  return fallback;
}

function extractErrors(payload: unknown): unknown[] {
  if (payload && typeof payload === "object" && Array.isArray((payload as Record<string, unknown>).errors)) {
    return (payload as Record<string, unknown[]>).errors;
  }
  return [];
}

// Returns the raw JSON body, typed as T - callers pick whether that's a
// V2 route's plain body or a V3 envelope (see apiRequestData below).
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = {};

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (auth) {
    const token = getStoredToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Unable to reach the Scout API. Check your connection and try again.");
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json") ? await response.json() : undefined;

  if (!response.ok) {
    if (response.status === 401) {
      authEvents.dispatchEvent(new Event("unauthorized"));
    }
    throw new ApiError(response.status, extractErrorMessage(payload, response.statusText), extractErrors(payload));
  }

  return payload as T;
}

// Unwraps a V3 /api/v1/* envelope's `data` field.
export async function apiRequestData<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const envelope = await apiRequest<Envelope<T>>(path, options);
  return envelope.data;
}
