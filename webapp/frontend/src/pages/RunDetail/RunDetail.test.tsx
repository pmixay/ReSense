// @vitest-environment jsdom
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import RunDetail from './index';
import { stripMarkers } from './Timeline';
import { EVAL, NO_LABELS, makeDetail, makeRun, makeSeries, renderAt, stubFetch } from '../Runs/common/testing';

vi.mock('../../player/CloudPreview', () => ({ default: ({ pos }: { pos?: number }) => <div data-testid="cloud">{pos}</div> }));

afterEach(() => vi.unstubAllGlobals());

//            0         1
//            01234567890123456789
const DEC = 'GGGCCSSSSGSSSSGGGSSG';
const LABELS = DEC.split('').map((_, i) => i >= 3 && i <= 13);

function api(detail = makeDetail(makeRun('r1', DEC, { name: 'demo_crossing · Быстрый', preset: { id: 'p1', name: 'Быстрый' } }, EVAL), { overrides: { 'tracking.confirm_time_s': 0.2 } })) {
  return stubFetch({
    '/api/runs/r1': detail,
    '/api/runs/r1/series': makeSeries(DEC, LABELS),
    '/api/runs/r1/labels': { ...NO_LABELS, available: true, labels_name: 'gt', in_gauge: LABELS, near: LABELS.map((x) => (x ? 55.27 : null)), far: LABELS.map((x) => (x ? 55.67 : null)) },
    '/api/runs': [detail, makeRun('r2', 'GGSS', { name: 'demo_crossing' })],
    '/api/presets/schema': [{ key: 'tracking.confirm_time_s', group: 'Трекинг', label: 'Время подтверждения', help: '', type: 'float', default: 0.5, unit: 'с' }],
    'DELETE /api/runs/r1': null,
  });
}

describe('Прогон', () => {
  it('shows the verdict, KPIs, events, evaluation and downloads of a run', async () => {
    api();
    renderAt(<RunDetail />, '/runs/:id', '/runs/r1');
    // the title drops the preset suffix (the preset chip says it)
    expect(await screen.findByRole('heading', { level: 1, name: 'demo_crossing' })).toBeTruthy();
    expect(screen.getByText(/с кадра 5 · 55,2\s*м/)).toBeTruthy();
    expect(screen.getAllByText('Быстрый').length).toBeGreaterThan(0);
    // KPIs: 3 STOP episodes, misses against labels (frames 3, 4, 9: 3 frames), 1 false alarm episode
    expect(screen.getByText('СТОП-эпизоды').closest('div')?.parentElement?.textContent).toMatch(/3первый: кадры 5–8/);
    await waitFor(() => expect(screen.getByText('Пропуски').closest('div')?.parentElement?.textContent).toMatch(/3\s*кадра/));
    expect(screen.getByText('Ложные тревоги').closest('div')?.parentElement?.textContent).toMatch(/1\s*эпизод/);
    // events: CAUTION, 2 STOP episodes, the GO gap inside (labelled → a false «free»)
    expect(screen.getByText('Ложное «свободно»')).toBeTruthy();
    expect(screen.getAllByRole('button', { name: /открыть в плеере/ }).length).toBeGreaterThanOrEqual(4);
    // evaluation
    expect(screen.getByText('Оценка по разметке')).toBeTruthy();
    expect(screen.getByText(/83\s*%/)).toBeTruthy();
    // downloads
    expect(screen.getByText('JSONL').closest('a')?.getAttribute('href')).toBe('/api/runs/r1/download/results.jsonl');
    expect(screen.getByText('CSV').closest('a')?.getAttribute('href')).toBe('/api/runs/r1/download/frames.csv');
    // actions: compare with the other run of the recording, player
    expect(screen.getByRole('link', { name: /Сравнить/ }).getAttribute('href')).toBe('/compare?runs=r1,r2');
    expect(screen.getByRole('link', { name: /Открыть в плеере/ }).getAttribute('href')).toBe('/player/r1');
  });

  it('opens the player at an event', async () => {
    api();
    renderAt(<RunDetail />, '/runs/:id', '/runs/r1');
    fireEvent.click(await screen.findByRole('button', { name: /Ложное «свободно».*открыть в плеере/ }));
    expect((await screen.findByTestId('elsewhere')).textContent).toBe('/player/r1?pos=9');
  });

  it('deletes the run from the menu and returns to the list', async () => {
    const fetch = api();
    renderAt(<RunDetail />, '/runs/:id', '/runs/r1');
    fireEvent.click(await screen.findByRole('button', { name: 'Действия с прогоном' }));
    fireEvent.click(await screen.findByRole('menuitem', { name: 'Удалить' }));
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Удалить' }));
    expect((await screen.findByTestId('elsewhere')).textContent).toBe('/runs');
    expect(fetch.mock.calls.some(([u, i]) => String(u).endsWith('/api/runs/r1') && i?.method === 'DELETE')).toBe(true);
  });

  it('says so when the run does not exist', async () => {
    stubFetch({ '/api/runs': [], '/api/presets/schema': [] });
    renderAt(<RunDetail />, '/runs/:id', '/runs/nope');
    expect(await screen.findByText('Возможно, его удалили')).toBeTruthy();
  });
});

describe('stripMarkers', () => {
  it('keeps the first STOP and thins out the others', () => {
    const r = makeDetail(makeRun('r1', DEC));
    const m = stripMarkers(r, DEC.length, (f) => f);
    expect(m[0]).toMatchObject({ pos: 3, tone: 'caution' });
    const first = m.find((x) => x.tone === 'stop' && String(x.label).includes('СТОП'));
    expect(first).toMatchObject({ pos: 5, label: 'кадр 5 · СТОП' });
    expect(m.map((x) => x.pos)).toEqual([...m.map((x) => x.pos)].sort((a, b) => a - b));
  });
});
