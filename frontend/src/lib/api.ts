// Typed fetch layer over the FastAPI backend. Base is the relative "/api" prefix so the
// same code works in dev (Vite proxies /api → :8001) and behind a single origin in prod.
const BASE = "/api";

// Fields are declared, not constructor parameter properties: tsconfig sets
// erasableSyntaxOnly, which rejects `constructor(readonly status: number)`.
export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    const detail = body && typeof body === "object" && "detail" in body ? (body as { detail?: unknown }).detail : undefined;
    const message = typeof detail === "string" ? detail : detail && typeof detail === "object" && "message" in detail ? String((detail as { message?: unknown }).message) : `Request failed with ${status}`;
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

type JsonBody = unknown;

async function request<T>(method: string, path: string, body?: JsonBody): Promise<T> {
  // Auth rides the httpOnly session cookie automatically — never add auth headers here.
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "include",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  // FastAPI reports request-validation failures as 422 with a {detail: [...]} body.
  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new ApiError(res.status, errBody);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// The response type is yours to declare: nothing infers across the Python boundary, so a
// TS interface here mirrors the endpoint's Pydantic model by hand — keep the two in sync.
export const apiGet = <T>(path: string) => request<T>("GET", path);
export const apiPost = <T>(path: string, body?: JsonBody) => request<T>("POST", path, body);
export const apiPut = <T>(path: string, body?: JsonBody) => request<T>("PUT", path, body);
export const apiPatch = <T>(path: string, body?: JsonBody) =>
  request<T>("PATCH", path, body);
export const apiDelete = <T>(path: string) => request<T>("DELETE", path);

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", credentials: "include", body: form });
  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new ApiError(res.status, errBody);
  }
  return (await res.json()) as T;
}

export async function apiPostStream<T>(path: string, body: unknown, onDelta: (content: string) => void): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "Accept": "text/event-stream" }, body: JSON.stringify(body) });
  if (!res.ok) {
    const errBody = await res.json().catch(() => null);
    throw new ApiError(res.status, errBody);
  }
  if (!res.body) throw new ApiError(502, { detail: "The AI Engine returned an empty stream" });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed: T | undefined;
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const lines = block.split("\n");
      const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
      const raw = lines.find((line) => line.startsWith("data:"))?.slice(5).trim();
      if (!raw) continue;
      const data = JSON.parse(raw) as { content?: string } | T;
      if (event === "delta" && "content" in (data as { content?: string })) onDelta((data as { content: string }).content);
      if (event === "complete") completed = data as T;
    }
    if (done) break;
  }
  if (!completed) throw new ApiError(502, { detail: "The AI Engine stream ended before completion" });
  return completed;
}
