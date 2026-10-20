// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { SystemInfo } from '../../api/types';
import { FEATURES, LINKS, RESULTS, ROS_COMMANDS, STATIONS, TEAM, fmtVersion } from './content';
import About from './index';
import { copyText } from './useCopy';

const SYSTEM: SystemInfo = {
  version: '0.1.0',
  detector_version: '1.0.0',
  uptime_s: 120,
  cpu_count: 4,
  load_1m: 0.4,
  cpu_cores_busy: 0.4,
  disk_free_bytes: 10 * 1024 ** 3,
  data_dir: '/data/web',
  server_root: '/data',
  server_root_exists: true,
  features: { rosbags: true, open3d: false, native_kernels: true, clouds: true },
  counts: { recordings: 3, runs: 3, jobs_queued: 0, jobs_running: 0 },
};

function stubSystem(reply: () => Promise<Response>) {
  const fn = vi.fn(reply);
  vi.stubGlobal('fetch', fn);
  return fn;
}
const ok = () => Promise.resolve(new Response(JSON.stringify(SYSTEM), { status: 200, headers: { 'Content-Type': 'application/json' } }));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <About />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const shown = (t: string | RegExp) => screen.queryAllByText(t).filter(el => !el.closest('details:not([open])'));
function expand(label: string) {
  const summary = screen.getByText(label, { selector: 'summary' });
  fireEvent.click(summary);
  expect(summary.parentElement!.hasAttribute('open')).toBe(true);
  return summary.parentElement!;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('О системе', () => {
  it('keeps the overview concise and exposes the full pipeline on demand', () => {
    stubSystem(ok);
    renderPage();
    const line = screen.getByRole('list', { name: 'Обработка кадра' });
    expect(within(line).getAllByRole('listitem')).toHaveLength(STATIONS.length);
    expect(STATIONS.map((s) => s.name)).toEqual(['декодирование', 'калибровка', 'модель пути', 'габарит', 'кластеризация', 'трекинг', 'решение']);
    expect(shown('0,5 с')).toHaveLength(0);
    expect(screen.queryByRole('button', { name: /Этап/ })).toBeNull();
    const details = expand('Подробнее об обработке');
    expect(details.textContent).toContain('1,05 м в каждую сторону');
    expect(details.textContent).toContain('0,5 с');
    fireEvent.click(screen.getByText('Подробнее об обработке', { selector: 'summary' }));
    expect(details.hasAttribute('open')).toBe(false);
  });

  it('shows the four decisions as signals with their rule', () => {
    stubSystem(ok);
    renderPage();
    const list = screen.getByRole('list', { name: 'Решения' });
    const decisions = within(list).getAllByRole('listitem');
    expect(decisions).toHaveLength(4);
    expect(decisions[0].textContent).toContain('Препятствие не обнаружено');
    expect(decisions[2].textContent).toContain('подтверждённое препятствие в габарите 2,1 × 3,0 м');
    expect(decisions[3].textContent).toContain('0,5 с');
    expect(within(list).queryByRole('button')).toBeNull();
  });

  it('puts the measurements and their complete conditions in one disclosure', () => {
    stubSystem(ok);
    renderPage();
    expect(screen.getByRole('list', { name: 'Результаты в выборке' }).closest('details')!.hasAttribute('open')).toBe(false);
    expand('Результаты в выборке');
    const results = screen.getByRole('list', { name: 'Результаты в выборке' });
    const text = results.textContent ?? '';
    for (const v of ['55,5–56,6', '2,3', '8 из 8', '81', '10', '≈ 210']) expect(text).toContain(v);
    expect(RESULTS.every((r) => /в выборке|Синтетика|ВМ|кадр/i.test(r.help))).toBe(true);
    expect(RESULTS.find((r) => r.key === 'obstacle')?.help).toContain('В выборке');
    for (const result of RESULTS) expect(results.textContent).toContain(result.help);
  });

  it('lists the five ROS commands and copies one', async () => {
    stubSystem(ok);
    const writeText = vi.fn(() => Promise.resolve());
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    renderPage();
    expand('Как проверить — ROS 2');
    expand('Как проверить — веб');
    for (const c of ROS_COMMANDS) expect(shown(c.cmd)).toHaveLength(1);
    expect(ROS_COMMANDS[2].cmd).toContain('--read-ahead-queue-size 10');
    const copies = screen.getAllByRole('button', { name: 'Скопировать' });
    expect(copies).toHaveLength(ROS_COMMANDS.length + 2); // UDP prerequisite + web command
    await act(async () => {
      fireEvent.click(copies[2]);
    });
    expect(writeText).toHaveBeenCalledWith('docker run --rm -it --net=host --ipc=host resense');
    expect(screen.getAllByRole('button', { name: 'Скопировано' })).toHaveLength(1);
    expect(screen.getByText('Команда скопирована')).toBeTruthy();
  });

  it('shows this stand from /api/system: versions and features', async () => {
    stubSystem(ok);
    renderPage();
    await waitFor(() => expect(shown('детектор v1.0.0')).toHaveLength(1));
    expect(shown('детектор v1.0.0')).toHaveLength(1); // the header chip
    expand('Как проверить — веб');
    expect(shown('v0.1.0')).toHaveLength(1);
    for (const f of FEATURES) expect(shown(f.label)).toHaveLength(1);
    expect(screen.getByText(': нет')).toBeTruthy(); // open3d is missing on this stand
  });

  it('keeps the page usable when the backend is down', async () => {
    stubSystem(() => Promise.reject(new TypeError('Failed to fetch')));
    renderPage();
    expand('Как проверить — веб');
    expect(await screen.findByText('Нет связи с бэкендом')).toBeTruthy();
    expect(screen.getByRole('alert').textContent).toContain('переподключится сама');
    expect(shown(/детектор v/)).toHaveLength(0);
    expect(screen.getByRole('list', { name: 'Обработка кадра' })).toBeTruthy();
  });

  it('links the documentation and names the team', () => {
    stubSystem(ok);
    renderPage();
    expand('Команда «Молоток»');
    const links = screen.getByRole('list', { name: 'Ссылки на документацию' });
    for (const l of LINKS) {
      const a = within(links).getByRole('link', { name: new RegExp(l.label) });
      expect(a.getAttribute('href')).toBe(l.href);
      expect(a.getAttribute('target')).toBe('_blank');
    }
    expect(LINKS[0].href).toBe('https://resense.gitbook.io/resense-docs/');
    expect(TEAM.map((m) => m.id)).toEqual(['P1', 'P2', 'P3', 'P4']);
    expect(within(screen.getByRole('list', { name: 'Роли в команде' })).getAllByRole('listitem')).toHaveLength(4);
    expect(shown('капитан')).toHaveLength(1);
    expect(screen.getByRole('link', { name: /Попробовать на демо/ }).getAttribute('href')).toBe('/upload?source=demo');
  });
});

describe('helpers', () => {
  it('formats versions', () => {
    expect(fmtVersion('1.0.0')).toBe('v1.0.0');
    expect(fmtVersion('v2')).toBe('v2');
    expect(fmtVersion('')).toBe('—');
    expect(fmtVersion(null)).toBe('—');
  });

  it('copies without the Clipboard API (plain http on a LAN address)', async () => {
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true });
    const exec = vi.fn(() => true);
    Object.defineProperty(document, 'execCommand', { value: exec, configurable: true });
    expect(await copyText('scripts/run_webapp.sh')).toBe(true);
    expect(exec).toHaveBeenCalledWith('copy');
    expect(document.querySelector('textarea')).toBeNull();
  });
});
