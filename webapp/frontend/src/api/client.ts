// Thin fetch wrapper for /api: JSON in and out, errors become ApiError with the backend's Russian
// `detail` (webapp/API.md: {"detail": "<short Russian message>"}).

export const API_BASE = '/api';

export class ApiError extends Error {
  readonly status: number; // 0 = the request never reached the server
  readonly detail: unknown;
  /** The backend could not be reached (network error, or a proxy answering for it). */
  readonly offline: boolean;

  constructor(message: string, status: number, detail?: unknown, offline?: boolean) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.offline = offline ?? status === 0;
  }
}

const STATUS_TEXT: Record<number, string> = {
  400: 'Некорректный запрос',
  403: 'Действие запрещено',
  404: 'Не найдено',
  409: 'Конфликт: данные изменились',
  413: 'Слишком большой файл',
  422: 'Некорректные данные',
  429: 'Слишком много запросов',
  500: 'Внутренняя ошибка сервера',
  502: 'Бэкенд недоступен',
  503: 'Бэкенд недоступен',
  504: 'Бэкенд не отвечает',
};

export const OFFLINE_MESSAGE = 'Бэкенд недоступен — проверьте, что сервер запущен';

/** The user-facing message of an error body (FastAPI validation lists included). */
export function detailMessage(detail: unknown, status: number): string {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    const msgs = detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : ''))
      .filter(Boolean);
    return msgs.length ? `${STATUS_TEXT[422]}: ${msgs.join('; ')}` : STATUS_TEXT[422];
  }
  return STATUS_TEXT[status] ?? `Ошибка сервера (${status})`;
}

/** Builds an ApiError from a non-OK response (body read as JSON when possible). */
export async function errorFromResponse(res: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    const text = await res.text();
    try {
      detail = (JSON.parse(text) as { detail?: unknown }).detail;
    } catch {
      detail = undefined; // a proxy's HTML page, not our JSON
    }
  } catch {
    detail = undefined;
  }
  // our backend always answers errors with JSON {"detail"}; a bare 5xx comes from a proxy (the Vite
  // dev / preview proxy answers 500 when nothing listens on :8000)
  if (detail === undefined && res.status >= 500) {
    return new ApiError(OFFLINE_MESSAGE, res.status, undefined, true);
  }
  return new ApiError(detailMessage(detail, res.status), res.status, detail);
}

/** Russian message of any thrown value (for banners / toasts). */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof DOMException && err.name === 'AbortError') return 'Запрос отменён';
  if (err instanceof Error && err.message) return err.message;
  return 'Неизвестная ошибка';
}

export type Query = Record<string, string | number | boolean | null | undefined>;

export function apiUrl(path: string, query?: Query): string {
  const url = API_BASE + (path.startsWith('/') ? path : '/' + path);
  if (!query) return url;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null) qs.set(k, String(v));
  const s = qs.toString();
  return s ? `${url}?${s}` : url;
}

interface RequestOptions {
  query?: Query;
  body?: unknown; // JSON-encoded unless BodyInit (Blob, ArrayBuffer, string…)
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

async function send(method: string, path: string, opts: RequestOptions = {}): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json', ...opts.headers };
  let body: BodyInit | undefined;
  if (opts.body !== undefined) {
    const raw = opts.body;
    if (typeof raw === 'string' || raw instanceof Blob || raw instanceof ArrayBuffer || ArrayBuffer.isView(raw)) {
      body = raw as BodyInit;
      headers['Content-Type'] ??= 'application/octet-stream';
    } else {
      body = JSON.stringify(raw);
      headers['Content-Type'] = 'application/json';
    }
  }
  let res: Response;
  try {
    res = await fetch(apiUrl(path, opts.query), { method, headers, body, signal: opts.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError(OFFLINE_MESSAGE, 0);
  }
  if (!res.ok) throw await errorFromResponse(res);
  return res;
}

async function json<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError('Сервер вернул некорректный ответ', res.status);
  }
}

export const api = {
  get: async <T>(path: string, opts?: RequestOptions): Promise<T> => json<T>(await send('GET', path, opts)),
  post: async <T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> =>
    json<T>(await send('POST', path, { ...opts, body })),
  put: async <T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> =>
    json<T>(await send('PUT', path, { ...opts, body })),
  patch: async <T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> =>
    json<T>(await send('PATCH', path, { ...opts, body })),
  /** DELETE; most endpoints answer 204 (→ undefined), a few return the changed entity. */
  del: async <T = void>(path: string, opts?: RequestOptions): Promise<T> => json<T>(await send('DELETE', path, opts)),
  text: async (path: string, opts?: RequestOptions): Promise<string> =>
    (await send('GET', path, { ...opts, headers: { Accept: 'text/plain', ...opts?.headers } })).text(),
  binary: async (path: string, opts?: RequestOptions): Promise<ArrayBuffer> =>
    (await send('GET', path, { ...opts, headers: { Accept: 'application/octet-stream', ...opts?.headers } })).arrayBuffer(),
};
