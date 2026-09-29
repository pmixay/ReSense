import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, OFFLINE_MESSAGE, api, apiUrl, detailMessage, errorMessage } from './client';

const res = (status: number, body: string, type = 'application/json') => new Response(status === 204 ? null : body, { status, headers: { 'Content-Type': type } });

describe('api client', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('builds urls with queries (skipping null / undefined)', () => {
    expect(apiUrl('/jobs', { status: 'queued,running', x: null, y: undefined })).toBe('/api/jobs?status=queued%2Crunning');
    expect(apiUrl('runs/a b/frames', { from: 0, count: 500 })).toBe('/api/runs/a b/frames?from=0&count=500');
  });

  it('parses JSON and 204', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(res(200, '{"ok":true}')).mockResolvedValueOnce(res(204, ''));
    vi.stubGlobal('fetch', fetch);
    expect(await api.get('/health')).toEqual({ ok: true });
    expect(await api.del('/runs/x')).toBeUndefined();
    expect(fetch.mock.calls[1][1].method).toBe('DELETE');
  });

  it('sends JSON bodies', async () => {
    const fetch = vi.fn().mockResolvedValue(res(201, '{"id":"j1"}'));
    vi.stubGlobal('fetch', fetch);
    await api.post('/jobs', { recording_id: 'r1' });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe('/api/jobs');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(init.body).toBe('{"recording_id":"r1"}');
  });

  it('turns the Russian detail into the error message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res(422, '{"detail":"Не найдено облаков в записи"}')));
    const err = (await api.post('/uploads/x/finalize').catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe('Не найдено облаков в записи');
    expect(err.status).toBe(422);
    expect(err.offline).toBe(false);
  });

  it('reports an unreachable backend as offline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const e1 = (await api.get('/system').catch((e: unknown) => e)) as ApiError;
    expect(e1.offline).toBe(true);
    expect(e1.message).toBe(OFFLINE_MESSAGE);
    // the dev proxy answers a bare 500 when nothing listens on :8000
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res(500, '', 'text/plain')));
    const e2 = (await api.get('/system').catch((e: unknown) => e)) as ApiError;
    expect(e2.offline).toBe(true);
    // our own 500 carries a detail and is not "offline"
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res(500, '{"detail":"Внутренняя ошибка сервера"}')));
    const e3 = (await api.get('/system').catch((e: unknown) => e)) as ApiError;
    expect(e3.offline).toBe(false);
    expect(e3.message).toBe('Внутренняя ошибка сервера');
  });

  it('maps validation lists and unknown errors to Russian', () => {
    expect(detailMessage([{ msg: 'поле обязательно' }], 422)).toBe('Некорректные данные: поле обязательно');
    expect(detailMessage(undefined, 404)).toBe('Не найдено');
    expect(detailMessage(undefined, 418)).toBe('Ошибка сервера (418)');
    expect(errorMessage(new ApiError('x', 400))).toBe('x');
    expect(errorMessage(42)).toBe('Неизвестная ошибка');
  });
});
