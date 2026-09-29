// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Preset } from '../../api/types';
import Presets from './index';
import { SPECS, STANDARD } from './testing';

type Reply = { status: number; body: unknown };

/** A tiny in-memory presets backend behind a stubbed fetch. */
function backend(onPost?: (body: Record<string, unknown>) => Reply | null) {
  const presets: Preset[] = [STANDARD];
  const calls: { method: string; path: string; body: unknown }[] = [];
  const json = (status: number, body: unknown) =>
    new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, 'http://test');
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path: url.pathname, body });
    if (method === 'GET' && url.pathname === '/api/presets') return json(200, presets);
    if (method === 'GET' && url.pathname === '/api/presets/schema') return json(200, SPECS);
    if (method === 'POST' && url.pathname === '/api/presets') {
      const forced = onPost?.(body);
      if (forced) return json(forced.status, forced.body);
      const p: Preset = { id: `p${presets.length}`, builtin: false, created_at: '2026-09-29T11:00:00Z', ...body };
      presets.push(p);
      return json(201, p);
    }
    const m = /^\/api\/presets\/(\w+)$/.exec(url.pathname);
    if (m && method === 'DELETE') {
      const i = presets.findIndex((p) => p.id === m[1]);
      presets.splice(i, 1);
      return json(204, null);
    }
    if (url.pathname === '/api/system') return json(200, {});
    return json(404, { detail: 'Не найдено' });
  });
  vi.stubGlobal('fetch', fn);
  return { presets, calls };
}

function Where() {
  const loc = useLocation();
  return <output data-testid="where">{loc.pathname + loc.search}</output>;
}

function renderPage(path = '/presets') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route
            path="/presets"
            element={
              <>
                <Presets />
                <Where />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** Text outside the (always mounted, hidden) tooltips. */
const shown = (t: string | RegExp) => screen.queryAllByText(t).filter((el) => !el.closest('[role="tooltip"]'));

afterEach(() => vi.unstubAllGlobals());

describe('Presets page', () => {
  it('shows the sealed built-in read-only, grouped by the schema', async () => {
    backend();
    renderPage();
    await waitFor(() => expect(shown('Кластеризация')).toHaveLength(1));
    expect(shown('опечатан').length).toBeGreaterThan(0);
    expect(screen.queryByRole('spinbutton')).toBeNull(); // no editable controls on the built-in
    expect(screen.queryByRole('button', { name: /Сохранить/ })).toBeNull();
    expect(shown('Габарит')).toHaveLength(1);
    expect(shown('Низкие объекты')).toHaveLength(1);
    const run = screen.getByRole('link', { name: /Обработать с этим пресетом/ });
    expect(run.getAttribute('href')).toBe('/upload?preset=standard');
  });

  it('duplicates the built-in, counts the changes and creates the preset with only the overrides', async () => {
    const { calls } = backend();
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Дублировать/ }));

    const name = (await screen.findByRole('textbox', { name: 'Название пресета' })) as HTMLInputElement;
    expect(name.value).toBe('Стандарт 1.0 (копия)');
    expect((screen.getByRole('textbox', { name: 'Описание пресета' }) as HTMLInputElement).value).toBe('На основе «Стандарт 1.0»');

    fireEvent.click(screen.getByRole('button', { name: 'Минимум точек объекта: больше' }));
    fireEvent.click(screen.getByRole('switch', { name: 'Поиск низких предметов' }));
    expect(shown('изменено 2').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: /Поиск низких предметов: сбросить/ })).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /Создать/ }));
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    const post = calls.find((c) => c.method === 'POST');
    expect(post?.body).toEqual({
      name: 'Стандарт 1.0 (копия)',
      description: 'На основе «Стандарт 1.0»',
      overrides: { 'cluster.min_points': 6, 'lowobj.enabled': false },
    });
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/presets?id=p1'));
    expect(screen.getByRole('link', { name: /Обработать с этим пресетом/ }).getAttribute('href')).toBe('/upload?preset=p1');
  });

  it('turns a link to a preset that is gone, or to a draft lost on reload, into the address of what is shown', async () => {
    backend();
    renderPage('/presets?id=gone');
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/presets'));
    expect(shown('Стандарт 1.0').length).toBeGreaterThan(0);
  });

  it('forgets a draft id that has no draft (a reload)', async () => {
    backend();
    renderPage('/presets?id=__new__');
    await waitFor(() => expect(screen.getByTestId('where').textContent).toBe('/presets'));
  });

  it('shows the backend’s message at the name field on a conflict', async () => {
    backend(() => ({ status: 409, body: { detail: 'Пресет с таким названием уже есть' } }));
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Новый пресет/ }));
    fireEvent.change(await screen.findByRole('textbox', { name: 'Название пресета' }), { target: { value: 'Стандарт 1.0' } });
    fireEvent.click(screen.getByRole('button', { name: /Создать/ }));
    expect(await screen.findByText('Пресет с таким названием уже есть')).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Название пресета' }).getAttribute('aria-invalid')).toBe('true');
  });

  it('shows a validation error at the parameter it names', async () => {
    backend(() => ({ status: 422, body: { detail: '«Радиус объединения точек» (cluster.eps): значение 5 вне диапазона 0,1…1 м' } }));
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: /Новый пресет/ }));
    fireEvent.click(await screen.findByRole('button', { name: /Создать/ }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('вне диапазона');
    expect(alert.closest('[class*="rowWrap"]')?.querySelector('[data-param="cluster.eps"]')).toBeTruthy();
  });

  it('shows the error with a retry when the backend is down', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))));
    renderPage();
    expect(await screen.findByText('Бэкенд недоступен')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Повторить/ })).toBeTruthy();
  });
});

