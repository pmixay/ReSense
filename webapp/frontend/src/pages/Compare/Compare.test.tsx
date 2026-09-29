// @vitest-environment jsdom
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Compare from './index';
import { EVAL, makeDetail, makeRun, makeSeries, renderAt, stubFetch } from '../Runs/common/testing';

afterEach(() => vi.unstubAllGlobals());

const A = makeRun('a', 'GGSSSSSSSS', { name: 'demo_approach' }, { ...EVAL, recall: 0.9, false_stop_episodes: 0, false_stop_frames: 0 });
const B = makeRun('b', 'GSSSSSSSSS', { name: 'demo_approach · Быстрый', preset: { id: 'fast', name: 'Быстрый' } }, { ...EVAL, recall: 0.95, false_stop_episodes: 0, false_stop_frames: 0 });
const C = makeRun('c', 'GGGGGCCGGG', { name: 'demo_clear', recording_id: 'rec2' });
B.summary.first_stop = { frame: 1, t: 0.1, distance: 107.4 };
A.summary.first_stop = { frame: 2, t: 0.2, distance: 105 };

const SCHEMA = [
  { key: 'tracking.confirm_time_s', group: 'Трекинг', label: 'Время подтверждения', help: 'Сколько объект должен продержаться.', type: 'float', default: 0.5, unit: 'с' },
  { key: 'gauge.range_max', group: 'Габарит', label: 'Дальность контроля', help: '', type: 'float', default: 250, unit: 'м' },
];

function api() {
  return stubFetch({
    '/api/runs': [A, B, C],
    '/api/runs/a': makeDetail(A),
    '/api/runs/b': makeDetail(B, { overrides: { 'tracking.confirm_time_s': 0.2, 'gauge.range_max': 250 } }),
    '/api/runs/c': makeDetail(C),
    '/api/runs/a/series': makeSeries(A.summary.decisions),
    '/api/runs/b/series': makeSeries(B.summary.decisions),
    '/api/runs/c/series': makeSeries(C.summary.decisions),
    '/api/presets/schema': SCHEMA,
  });
}

describe('Сравнение', () => {
  it('compares the runs of the URL: KPI table with the best values, strips, what changed', async () => {
    api();
    renderAt(<Compare />, '/compare', '/compare?runs=a,b');
    expect(await screen.findByText('Показатели')).toBeTruthy();
    // the first STOP farther away is best, and the recall
    const firstStop = (await screen.findByRole('rowheader', { name: /Первый СТОП/ })).closest('tr') as HTMLElement;
    await waitFor(() => expect(within(firstStop).getByText(/107,4/).className).toMatch(/best/));
    expect(within(firstStop).getByText(/105,0/).className).not.toMatch(/best/);
    // presets differ on one recording: only the parameter that really differs is listed
    expect(screen.getByText('Что изменилось')).toBeTruthy();
    expect(screen.getByText('Время подтверждения')).toBeTruthy();
    expect(screen.queryByText('Дальность контроля')).toBeNull();
    expect(screen.getByText(/0,2\s*с/)).toBeTruthy();
    // the strips on one axis
    expect(screen.getByRole('img', { name: 'Решения по кадрам: demo_approach' })).toBeTruthy();
  });

  it('removes a run keeping the colour slots in the URL, and asks for more below two', async () => {
    api();
    renderAt(<Compare />, '/compare', '/compare?runs=a,b,c');
    fireEvent.click(await screen.findByRole('button', { name: 'Убрать из сравнения: demo_approach · Быстрый' }));
    // a and c keep their slots; «что изменилось» is gone (different recordings)
    await waitFor(() => expect(screen.queryByText('Что изменилось')).toBeNull());
    fireEvent.click(await screen.findByRole('button', { name: 'Убрать из сравнения: demo_clear' }));
    expect(await screen.findByText('Добавьте ещё прогон')).toBeTruthy();
    // pick another run in the chooser
    fireEvent.click(screen.getByLabelText('Сравнить: demo_clear'));
    expect(await screen.findByText('Показатели')).toBeTruthy();
  });

  it('starts with a chooser', async () => {
    api();
    renderAt(<Compare />, '/compare', '/compare');
    expect(await screen.findByText('Выберите прогоны')).toBeTruthy();
    expect(await screen.findAllByRole('checkbox')).toHaveLength(3);
  });
});
