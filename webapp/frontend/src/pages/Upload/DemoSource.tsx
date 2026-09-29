// «Демо-запись»: a synthetic rosbag2 bag made on the server (three scenes, 5–60 s) with its ground
// truth, so the whole chain can be shown without real data. Generation is synchronous; progress
// comes from the server while the request runs.
import { useState, type KeyboardEvent } from 'react';
import { useSystem } from '../../api/hooks';
import type { DemoScenario, Recording } from '../../api/types';
import { Button, Chip, ErrorBanner, Help, ProgressBar, Stepper } from '../../components';
import { fmtBytes, fmtClock, fmtDuration, fmtPercent } from '../../lib/format';
import { demoBytes, demoSeconds } from './estimate';
import { RecordingCard } from './RecordingCard';
import { SCENARIO_LABEL, type useDemoGenerator } from './useDemo';
import styles from './DemoSource.module.css';

const SCENARIOS: { id: DemoScenario; line: string; help: string }[] = [
  {
    id: 'approach',
    line: 'человек на пути, поезд тормозит',
    help: 'Поезд идёт по тоннелю и останавливается примерно в 25 м перед человеком на пути. Ожидается СТОП с дальней дистанции.',
  },
  {
    id: 'crossing',
    line: 'человек переходит путь',
    help: 'Поезд стоит, человек пересекает путь примерно в 55 м. Ожидается: свободно → внимание → СТОП → свободно.',
  },
  {
    id: 'clear',
    line: 'оборудование у пути, препятствий нет',
    help: 'Шкафы и столбики рядом с габаритом, на пути никого. Ожидается: без СТОП, «внимание» у оборудования.',
  },
];

/** Small line drawings of the three scenes: converging rails, a person, trackside cabinets. */
function SceneGlyph({ id }: { id: DemoScenario }) {
  return (
    <svg viewBox="0 0 96 56" className={styles.glyph} aria-hidden>
      <path d="M22 56 L44 8 M74 56 L52 8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
      <path d="M30 44h36M35 32h26M39 22h18M42 14h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity=".35" />
      {id === 'approach' && (
        <g>
          <circle cx="48" cy="9" r="3.2" fill="currentColor" />
          <rect x="45.4" y="13" width="5.2" height="11" rx="2.4" fill="currentColor" />
          <path d="M48 53 V35 M42.5 40.5 L48 35 L53.5 40.5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </g>
      )}
      {id === 'crossing' && (
        <g>
          <circle cx="62" cy="13" r="3.2" fill="currentColor" />
          <rect x="59.4" y="17" width="5.2" height="11" rx="2.4" fill="currentColor" />
          <path d="M28 26 H52 M47 21 l5 5 -5 5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </g>
      )}
      {id === 'clear' && (
        <g fill="currentColor">
          <rect x="6" y="26" width="9" height="16" rx="2.5" />
          <rect x="80" y="18" width="8" height="14" rx="2.5" />
          <rect x="68" y="30" width="3" height="12" rx="1.5" />
        </g>
      )}
    </svg>
  );
}

export interface DemoSourceProps {
  demo: ReturnType<typeof useDemoGenerator>;
  current: Recording | null;
  onClear: () => void;
}

export function DemoSource({ demo, current, onClear }: DemoSourceProps) {
  const [scenario, setScenario] = useState<DemoScenario>('approach');
  const [seconds, setSeconds] = useState(15);
  const sys = useSystem();
  const free = sys.isError ? undefined : sys.data?.disk_free_bytes;
  const bytes = demoBytes(seconds);
  const noSpace = free !== undefined && bytes > free;
  const busy = demo.active !== null;

  // radio group keyboard: arrows move the choice (and the focus) between the three scenes
  const onArrows = (e: KeyboardEvent<HTMLDivElement>) => {
    const step = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
    if (!step || busy) return;
    e.preventDefault();
    const i = SCENARIOS.findIndex((s) => s.id === scenario);
    const next = SCENARIOS[(i + step + SCENARIOS.length) % SCENARIOS.length].id;
    setScenario(next);
    e.currentTarget.querySelector<HTMLButtonElement>(`[data-scenario="${next}"]`)?.focus();
  };

  // the page picks the result up (useDemoGenerator.take), also after a trip to another page
  const go = () => {
    demo.dismissError();
    void demo.generate({ scenario, seconds });
  };

  return (
    <div className={styles.wrap}>
      {current && !busy && <RecordingCard rec={current} onClear={onClear} />}
      <div className={styles.cards} role="radiogroup" aria-label="Сценарий демо-записи" onKeyDown={onArrows}>
        {SCENARIOS.map((s) => {
          const on = s.id === scenario;
          return (
            <div key={s.id} className={[styles.sc, on ? styles.on : ''].join(' ')}>
              <button
                type="button"
                role="radio"
                aria-checked={on}
                tabIndex={on ? 0 : -1}
                data-scenario={s.id}
                className={styles.pick}
                disabled={busy}
                onClick={() => setScenario(s.id)}
              >
                <span className={styles.glyphBox}>
                  <SceneGlyph id={s.id} />
                </span>
                <span className={styles.scT}>{SCENARIO_LABEL[s.id]}</span>
                <span className={styles.scL}>{s.line}</span>
              </button>
              <Help placement="bottom" className={styles.scHelp} tone={on ? 'light' : 'dark'}>
                {s.help}
              </Help>
            </div>
          );
        })}
      </div>

      <div className={styles.controls}>
        <div className={styles.field}>
          <span className={styles.fl}>Длительность</span>
          <Stepper value={seconds} onChange={setSeconds} min={5} max={60} step={5} unit="с" label="Длительность демо-записи" disabled={busy} />
        </div>
        <div className={styles.facts}>
          <Chip icon="database" title="Размер на диске">
            ≈ {fmtBytes(bytes)}
          </Chip>
          <Chip icon="clock" title="Время создания на сервере" className={styles.time}>
            ≈ {fmtDuration(Math.max(1, Math.round(demoSeconds(seconds))))}
          </Chip>
          <Chip variant="ink" icon="sparkle">
            синтетическая
          </Chip>
          <Help placement="top" width={280}>
            Настоящий bag rosbag2 (10 Гц, /lidar_points), но кадры смоделированы: тоннель, путь и человек. Эталонная разметка создаётся вместе с записью, поэтому
            прогон сразу оценивается. Около <b>33 МБ</b> на секунду записи.
          </Help>
        </div>
        <span className={styles.sp} />
        <Button variant="dark" icon="sparkle" onClick={go} loading={busy} disabled={noSpace}>
          Создать демо
        </Button>
      </div>

      {busy && (
        <div className={styles.progress} aria-live="polite">
          <div className={styles.progLine}>
            <b>Создаём «{SCENARIO_LABEL[demo.active?.scenario ?? scenario]}»</b>
            <span>{fmtPercent(demo.fraction)}</span>
            <span>осталось ≈ {fmtClock(demo.etaS)}</span>
          </div>
          <ProgressBar value={demo.fraction} height={12} label="Создание демо-записи" />
        </div>
      )}
      {noSpace && !busy && <ErrorBanner error={`Нужно ≈ ${fmtBytes(bytes)}, свободно ${fmtBytes(free)}`} title="Мало места на диске" compact />}
      {demo.error && !busy && <ErrorBanner error={demo.error} title="Демо-запись не создана" onRetry={go} compact />}
    </div>
  );
}
