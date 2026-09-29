// @vitest-environment jsdom
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Runs from './index';
import { EVAL, makeRun, renderAt, stubFetch } from './common/testing';

const SYSTEM = { counts: { recordings: 2, runs: 3, jobs_queued: 1, jobs_running: 0 } };

const RUNS = [
  makeRun('crossing', 'GGGCCSSSSGG', { name: 'demo_crossing', created_at: '2026-09-29T10:00:00Z' }, EVAL),
  makeRun('clear', 'GGCCGGGG', { name: 'demo_clear', created_at: '2026-09-29T09:00:00Z', source_kind: 'jsonl' }),
  makeRun('fast', 'GSSSSSSS', { name: 'demo_approach · Быстрый', preset: { id: 'p1', name: 'Быстрый' }, created_at: '2026-09-29T08:00:00Z' }),
];

afterEach(() => vi.unstubAllGlobals());

describe('Прогоны', () => {
  it('lists runs with their facts, filters them and compares a selection', async () => {
    stubFetch({ '/api/runs': RUNS, '/api/system': SYSTEM });
    renderAt(<Runs />, '/runs', '/runs');
    expect(await screen.findByText('demo_crossing')).toBeTruthy();
    expect(screen.getByText('demo_clear')).toBeTruthy();
    // verdict chips, first STOP, queue link
    expect(screen.getByText('ложный СТОП ×1')).toBeTruthy();
    expect(screen.getAllByText('нет разметки')).toHaveLength(2);
    expect(await screen.findByText(/1\s+в очереди/)).toBeTruthy();
    expect(screen.getAllByText('без СТОП')).toHaveLength(1);

    // filter: only runs with a STOP
    fireEvent.click(screen.getByRole('radio', { name: /Со СТОП/ }));
    expect(screen.queryByText('demo_clear')).toBeNull();
    fireEvent.click(screen.getByRole('radio', { name: /Все/ }));

    // search by preset name
    fireEvent.change(screen.getByLabelText('Поиск по названию'), { target: { value: 'быстр' } });
    expect(screen.queryByText('demo_crossing')).toBeNull();
    expect(screen.getByText('demo_approach · Быстрый')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Поиск по названию'), { target: { value: '' } });

    // tick two runs: the floating bar links to /compare
    fireEvent.click(screen.getByLabelText('Выбрать для сравнения: demo_crossing'));
    const bar = screen.getByRole('region', { name: 'Выбранные прогоны' });
    expect(within(bar).getByRole('button', { name: /Сравнить \(1\)/ }).hasAttribute('disabled')).toBe(true);
    fireEvent.click(screen.getByLabelText('Выбрать для сравнения: demo_clear'));
    const link = within(bar).getByRole('link', { name: /Сравнить \(2\)/ });
    expect(link.getAttribute('href')).toBe('/compare?runs=crossing,clear');
  });

  it('renames a run inline and deletes one after confirming', async () => {
    const fetch = stubFetch({
      '/api/runs': RUNS,
      '/api/system': SYSTEM,
      'PATCH /api/runs/clear': (init: RequestInit | undefined) => ({ ...RUNS[1], name: JSON.parse(String(init?.body)).name }),
      'DELETE /api/runs/fast': null,
    });
    renderAt(<Runs />, '/runs', '/runs');
    await screen.findByText('demo_clear');

    fireEvent.click(screen.getByRole('button', { name: 'Действия: demo_clear' }));
    fireEvent.click(await screen.findByRole('menuitem', { name: 'Переименовать' }));
    const input = screen.getByLabelText('Новое название прогона');
    fireEvent.change(input, { target: { value: '  Чистый путь ' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(fetch.mock.calls.some(([u, i]) => String(u).endsWith('/api/runs/clear') && i?.method === 'PATCH')).toBe(true));
    const patch = fetch.mock.calls.find(([, i]) => i?.method === 'PATCH');
    expect(JSON.parse(String(patch?.[1]?.body))).toEqual({ name: 'Чистый путь' });

    fireEvent.click(screen.getByRole('button', { name: 'Действия: demo_approach · Быстрый' }));
    fireEvent.click(await screen.findByRole('menuitem', { name: 'Удалить' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Удалить «demo_approach · Быстрый»?')).toBeTruthy();
    fireEvent.click(within(dialog).getByRole('button', { name: 'Удалить' }));
    await waitFor(() => expect(fetch.mock.calls.some(([u, i]) => String(u).endsWith('/api/runs/fast') && i?.method === 'DELETE')).toBe(true));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });

  it('shows the empty state with a way to upload', async () => {
    stubFetch({ '/api/runs': [], '/api/system': SYSTEM });
    renderAt(<Runs />, '/runs', '/runs');
    expect(await screen.findByText('Прогонов пока нет')).toBeTruthy();
    expect(screen.getByRole('link', { name: /Загрузить запись/ }).getAttribute('href')).toBe('/upload');
  });

  it('shows the backend error', async () => {
    stubFetch({ '/api/system': SYSTEM, '/api/runs': undefined });
    renderAt(<Runs />, '/runs', '/runs');
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText('Не найдено')).toBeTruthy();
  });
});
