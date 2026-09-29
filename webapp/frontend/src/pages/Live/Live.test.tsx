// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Run } from '../../api/types';
import { Beacon, fmtAge, stateLabel } from './Beacon';
import type { FeedSnapshot } from './feed';
import type { DecisionLetter } from '../../lib/decisions';
import { HealthCard, NodeCard } from './Panels';
import { TimelineCard } from './TimelineCard';
import { ViewCard, webglAvailable } from './ViewCard';
import type { StatusMessage } from './timeline';

const STOP: StatusMessage = {
  decision: 'STOP',
  snapshot_kind: 'frame',
  nearest_distance: 55.24,
  clear_distance: 55.24,
  health: { level: 'ok', visibility: 185, rail_lock: 1 },
  mount: { status: 'ok' },
} as unknown as StatusMessage;

function snap(over: Partial<FeedSnapshot>): FeedSnapshot {
  return {
    link: 'open',
    view: 'live',
    error: null,
    msg: STOP,
    age: 40,
    count: 12,
    samples: [],
    timeNow: 0,
    paused: false,
    reconnecting: false,
    source: { kind: 'ros', url: 'ws://node:9090' },
    ...over,
  };
}

const text = (el: HTMLElement) => (el.textContent ?? '').replace(/[  ]/g, ' ');

/** Elements with exactly this text outside the (always mounted, hidden) tooltips. */
const shown = (t: string) => screen.queryAllByText(t).filter((el) => !el.closest('[role="tooltip"]'));

describe('Beacon', () => {
  it('shows a live STOP with the obstacle distance and the freshness', () => {
    const { container } = render(<Beacon snap={snap({})} kind="ros" />);
    expect(shown('СТОП')).toHaveLength(1);
    expect(screen.getByText('До препятствия')).toBeTruthy();
    expect(text(container)).toContain('55,2м');
    expect(text(container)).toContain('0,04 с');
    expect(container.querySelector('[class*="fill"]')).not.toBeNull(); // the monitored distance, in green
  });

  it('never shows the last decision or a distance when the data is stale', () => {
    const { container } = render(<Beacon snap={snap({ view: 'stale', age: 1600 })} kind="ros" />);
    expect(shown('ДАННЫЕ УСТАРЕЛИ')).toHaveLength(1);
    expect(shown('СТОП')).toHaveLength(0);
    expect(text(container)).not.toContain('55,2');
    expect(text(container)).toContain('1,6 с');
  });

  it('names the idle state after the source, and keeps a paused frame inspectable', () => {
    render(<Beacon snap={snap({ view: 'idle', link: 'idle', msg: null, age: null })} kind="sim" />);
    expect(screen.getByText('ЭФИР НЕ ЗАПУЩЕН')).toBeTruthy();
    render(<Beacon snap={snap({ view: 'paused', paused: true })} kind="sim" />);
    expect(screen.getByText('ПАУЗА')).toBeTruthy();
    expect(screen.getByTitle('Решение кадра на паузе')).toBeTruthy();
  });

  it('shows no monitored (green) distance on ОШИБКА, even when the frame carries one', () => {
    const fault = { ...STOP, decision: 'FAULT', nearest_distance: null, clear_distance: 150 } as unknown as StatusMessage;
    const { container } = render(<Beacon snap={snap({ msg: fault })} kind="ros" />);
    expect(shown('ОШИБКА')).toHaveLength(1);
    expect(screen.getByText('Путь не контролируется')).toBeTruthy();
    expect(text(container)).not.toContain('150');
    expect(container.querySelector('[class*="fill"]')).toBeNull();
  });

  it('shows no freshness age once the record has ended', () => {
    const { container } = render(<Beacon snap={snap({ view: 'ended', link: 'ended', age: 3 })} kind="sim" />);
    expect(shown('КОНЕЦ ЗАПИСИ')).toHaveLength(1);
    expect(text(container)).not.toContain('0,00 с');
  });

  it('labels states and ages', () => {
    expect(stateLabel('idle', 'ros')).toBe('НЕ ПОДКЛЮЧЕНО');
    expect(stateLabel('error', 'sim')).toBe('НЕТ СВЯЗИ');
    expect(fmtAge(null)).toBe('—');
    expect(fmtAge(80)).toBe('0,08 с');
    expect(fmtAge(2340)).toBe('2,3 с');
    expect(fmtAge(12_400)).toBe('12 с');
  });
});

describe('HealthCard', () => {
  it('lights the lamps while fresh and says what the level is', () => {
    const { container } = render(<HealthCard snap={snap({})} fresh minVisibility={60} />);
    expect(shown('норма')).toHaveLength(2); // the level chip and the calibration value
    expect(shown('да')).toHaveLength(1);
    expect(container.querySelectorAll('[class*="l-ok"]')).toHaveLength(4);
  });

  it('marks stale data as not fresh, hides the level and darkens the lamps', () => {
    const { container } = render(<HealthCard snap={snap({ view: 'stale', age: 900 })} fresh={false} minVisibility={60} />);
    expect(shown('норма')).toHaveLength(1); // only the calibration value, no level chip
    expect(shown('нет')).toHaveLength(1);
    expect(container.querySelectorAll('[class*="l-ok"]')).toHaveLength(0);
    expect(container.querySelectorAll('[class*="l-off"]')).toHaveLength(3);
  });
});

describe('freshness after a deliberate stop', () => {
  it('is dark, not a fault, once the replay is stopped or the node disconnected', () => {
    const idle = snap({ view: 'idle', link: 'idle', age: 5000 });
    const { container } = render(<HealthCard snap={idle} fresh={false} minVisibility={60} />);
    expect(container.querySelectorAll('[class*="l-error"]')).toHaveLength(0);
    expect(shown('нет')).toHaveLength(0);
    const beacon = render(<Beacon snap={idle} kind="ros" />);
    expect(beacon.container.querySelector('[class*="lampBad"]')).toBeNull();
  });

  it('is a violet «нет» while the data is late or the link broke', () => {
    const { container } = render(<HealthCard snap={snap({ view: 'error', link: 'error', age: 5000 })} fresh={false} minVisibility={60} />);
    expect(container.querySelectorAll('[class*="l-error"]')).toHaveLength(1);
    expect(shown('нет')).toHaveLength(1);
  });
});

describe('NodeCard', () => {
  it('shows the latency only for the frame on screen (live or paused), never after a stop', () => {
    const msg = { ...STOP, node: { fps: 10, latency_ms: 42, frames: 12, dropped_frames: 0 } } as unknown as StatusMessage;
    const live = render(<NodeCard snap={snap({ msg })} kind="ros" latency={[]} latencyBudget={100} />);
    expect(text(live.container)).toContain('42мс');
    live.unmount();
    const stopped = render(<NodeCard snap={snap({ msg, view: 'idle', link: 'idle' })} kind="ros" latency={[]} latencyBudget={100} />);
    expect(text(stopped.container)).not.toContain('42');
    expect(text(stopped.container)).toContain('12'); // the frames of that connection stay
  });
});

describe('TimelineCard', () => {
  it('draws the last 30 s as blocks (STOP hatched, a gap where no message came), not a canvas redrawn every tick', () => {
    const letters: (DecisionLetter | null)[] = [
      ...Array<null>(100).fill(null),
      ...Array<DecisionLetter>(50).fill('G'),
      ...Array<DecisionLetter>(10).fill('S'),
      ...Array<null>(40).fill(null),
      ...Array<DecisionLetter>(100).fill('C'),
    ];
    const slots = { letters, free: letters.map((l) => (l ? 120 : null)), latency: letters.map(() => null) };
    const { container } = render(<TimelineCard slots={slots} live />);
    const pieces = container.querySelectorAll<HTMLElement>('[class*="piece"]');
    expect(pieces).toHaveLength(2);
    expect(parseFloat(pieces[0].style.left)).toBeCloseTo(33.333, 2);
    expect(parseFloat(pieces[0].style.width)).toBeCloseTo(20, 2);
    expect(pieces[0].querySelectorAll('i')).toHaveLength(2);
    expect(container.querySelectorAll('[class*="seg-stop"]')).toHaveLength(1);
    expect(container.querySelector('canvas')).toBeNull();
    expect(shown('нет данных')).toHaveLength(0);
  });
});

describe('ViewCard', () => {
  const run = {
    id: 'r1',
    has_clouds: true,
    summary: { n_frames: 100 },
  } as unknown as Run;

  it('draws the scheme for the real node', () => {
    render(<ViewCard snap={snap({})} kind="ros" run={undefined} fresh />);
    expect(shown('Схема пути')).toHaveLength(1);
    expect(screen.getByRole('img', { name: /Схема пути сверху/ })).toBeTruthy();
  });

  it('falls back to the scheme for a replay when the browser has no WebGL', () => {
    expect(webglAvailable()).toBe(false); // jsdom: getContext returns null
    render(
      <ViewCard
        snap={snap({
          source: { kind: 'sim', runId: 'r1', speed: 1, loop: true },
        })}
        kind="sim"
        run={run}
        fresh
      />,
    );
    expect(shown('Схема пути')).toHaveLength(1);
    expect(screen.queryByRole('radiogroup', { name: 'Вид' })).toBeNull();
  });
});
