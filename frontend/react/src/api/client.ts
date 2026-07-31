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
  // Whether to attach the Authorization header. Defaults to true, and
  // the default is almost always right - see PUBLIC_ENDPOINTS below
  // before passing false.
  auth?: boolean;
}

// The only endpoints that are reachable without credentials. Mirrors the
// backend's public list (tests/test_route_authentication.py); everything
// else answers 401 without a token.
//
// This is enforced rather than documented because getting it wrong is
// silent and looks like something else entirely: systemService and
// workflowService both passed `auth: false`, correctly, back when those
// V2 routes were unauthenticated. Once every route required a token they
// started returning 401, the 401 handler below cleared the session, and
// the visible symptom was "clicking Settings logs me out" - a bug that
// points nowhere near its cause.
const PUBLIC_ENDPOINTS = ["/api/v1/auth/login", "/health"];

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

  if (!auth && !PUBLIC_ENDPOINTS.some((endpoint) => path.startsWith(endpoint))) {
    throw new Error(
      `${path} is not a public endpoint, so it must be called with a token. ` +
        "Remove `auth: false`, or add the path to PUBLIC_ENDPOINTS if the " +
        "backend really does serve it anonymously.",
    );
  }

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

  // 204 No Content never has a body even when the server's content-type
  // header still says application/json (FastAPI does this) - calling
  // response.json() on that empty body throws "Unexpected end of JSON
  // input" instead of returning undefined, so every DELETE endpoint
  // (removeRecipient, removeCompany, deleteSchedule, ...) must be
  // excluded from the parse attempt here.
  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown =
    response.status !== 204 && contentType.includes("application/json") ? await response.json() : undefined;

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

// Multipart upload (V3 Enhancements Phase 1B - the Knowledge Library's
// file upload). Separate from apiRequest because that function always
// JSON.stringify()s its body and sets Content-Type: application/json,
// which a file upload cannot use.
//
// Content-Type is deliberately NOT set here: the browser has to generate
// it itself so it can append the multipart boundary token. Setting it
// manually produces a header with no boundary and the server rejects the
// body as malformed.
//
// Returns the unwrapped `data` of a V3 envelope, matching apiRequestData.
export async function apiUploadData<T>(path: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getStoredToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(path, { method: "POST", headers, body: formData });
  } catch {
    throw new ApiError(0, "Unable to reach the Scout API. Check your connection and try again.");
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown =
    response.status !== 204 && contentType.includes("application/json") ? await response.json() : undefined;

  if (!response.ok) {
    if (response.status === 401) {
      authEvents.dispatchEvent(new Event("unauthorized"));
    }
    throw new ApiError(response.status, extractErrorMessage(payload, response.statusText), extractErrors(payload));
  }

  return (payload as Envelope<T>).data;
}
