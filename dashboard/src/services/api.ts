export type Row = Record<string, any>;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

/** Readable text for an error body: plain `detail`, or the messages of a validation error list. */
function message(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const texts = detail.map(d => String(d?.msg ?? '').replace(/^Value error, /, '')).filter(Boolean);
    if (texts.length) return [...new Set(texts)].join(' · ');
  }
  return JSON.stringify(detail);
}

let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (handler: () => void) => { onUnauthorized = handler; };

/** Multipart upload (the browser sets the boundary header itself). */
export async function upload<T = any>(route: string, file: File, field = 'file'): Promise<T> {
  const body = new FormData();
  body.append(field, file);
  const response = await fetch('/api/' + route, {method: 'POST', credentials: 'include', body});
  if (!response.ok) {
    if (response.status === 401) onUnauthorized();
    const payload = await response.json().catch(() => ({detail: `HTTP ${response.status}`}));
    throw new ApiError(response.status, message(payload.detail));
  }
  return response.json();
}

/** Same-origin JSON API; the session is an HttpOnly cookie, never stored in JS. */
export async function api<T = any>(route: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch('/api/' + route, {
    method, credentials: 'include', headers: {'Content-Type': 'application/json'},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    if (response.status === 401 && route !== 'auth/login') onUnauthorized();
    const payload = await response.json().catch(() => ({detail: `HTTP ${response.status}`}));
    throw new ApiError(response.status, message(payload.detail));
  }
  return response.json();
}
