// The run page's smaller cards: events, the evaluation against labels, the 3D preview, downloads and
// the preset chip of the header.
import { Suspense, lazy } from 'react';
import { useNavigate } from 'react-router-dom';
import { downloads } from '../../api/hooks';
import type { Decision, EvalSummary, ParamSpec, RunDetail } from '../../api/types';
import { Button, Card, Chip, DecisionChip, EmptyState, Help, Icon } from '../../components';
import { FRAMES, fmtBytes, fmtCount, fmtMeters, fmtNum, fmtPercent, plural } from '../../lib/format';
import { describeEvent, fmtParam, playerUrl } from '../Runs/common/analysis';
import { DecisionTile } from '../Runs/common/Bits';
import styles from './RunDetail.module.css';

// three.js stays out of this page's chunk until the preview mounts
const CloudPreview = lazy(() => import('../../player/CloudPreview'));

// ---------------------------------------------------------------- events

export function EventsCard({
  r,
  posOf,
  labelsInGauge,
  selected,
  onSelect,
}: {
  r: RunDetail;
  posOf: (frame: number) => number;
  labelsInGauge: readonly boolean[] | null;
  selected: number | null;
  onSelect: (pos: number | null) => void;
}) {
  const navigate = useNavigate();
  const lastFrame = r.episodes.length ? r.episodes[r.episodes.length - 1].last_frame : undefined;
  return (
    <Card
      className={styles.ev}
      title="События"
      headGap={6}
      help="Всё, кроме СВОБОДНО: эпизоды СТОП, ВНИМАНИЕ, ошибки датчика и разрывы внутри СТОП. Наведите — 3D-вид покажет кадр, клик откроет его в плеере."
      helpPlacement="bottom"
      actions={<Chip>{fmtNum(r.events.length)}</Chip>}
    >
      {r.events.length === 0 ? (
        <EmptyState icon="check" size="sm" title="Событий нет">
          Все кадры — СВОБОДНО.
        </EmptyState>
      ) : (
        <div className={styles.evList} onMouseLeave={() => onSelect(null)}>
          {r.events.map((ev) => {
            const pos = posOf(ev.first_frame);
            const labelled = !!labelsInGauge && labelsInGauge.slice(pos, pos + ev.n_frames).some(Boolean);
            const info = describeEvent(ev, { lastFrame, labelled });
            return (
              <button
                key={`${ev.first_frame}-${ev.decision}`}
                type="button"
                className={[styles.evr, selected === pos ? styles.on : ''].join(' ')}
                onMouseEnter={() => onSelect(pos)}
                onFocus={() => onSelect(pos)}
                onClick={() => navigate(playerUrl(r.id, pos))}
                aria-label={`${info.title}, ${info.meta}: открыть в плеере`}
              >
                <DecisionTile decision={info.decision} />
                <div className={styles.evtext}>
                  <div className={styles.evt}>{info.title}</div>
                  <div className={styles.evm}>{info.meta}</div>
                </div>
                <span className={styles.evv}>
                  {info.value.num}
                  <small>{info.value.unit}</small>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- evaluation

export function EvalCard({ ev }: { ev: EvalSummary }) {
  const ff = ev.false_stop_frames;
  return (
    <Card
      className={styles.evc}
      title="Оценка по разметке"
      headGap={10}
      help={
        <>
          Детектор против разметки <b>{ev.labels_name}</b>: {fmtCount(ev.frames_labelled, FRAMES)}.
        </>
      }
      helpPlacement="top"
      helpWidth={280}
    >
      <div className={styles.evRows}>
        <div className={styles.evRow}>
          Полнота
          <Help placement="top" width={260}>
            Кадры с объектом в габарите по разметке, где детектор ответил СТОП: <b>{fmtNum(ev.frames_detected)}</b> из{' '}
            <b>{fmtNum(ev.frames_with_object_in_gauge)}</b>
            {ev.recall !== null ? ` (${fmtPercent(ev.recall, 1)})` : ' — объектов в габарите нет'}.
          </Help>
          <span className={styles.sp} />
          <b className={styles.evNum}>{ev.recall !== null ? fmtPercent(ev.recall, 0) : '—'}</b>
          <span className={styles.evSub}>
            {fmtNum(ev.frames_detected)} / {fmtNum(ev.frames_with_object_in_gauge)}
          </span>
        </div>
        <div className={styles.evRow}>
          Ложный СТОП
          <Help placement="top" width={250}>
            Кадры СТОП, где по разметке в габарите пусто, и сколько отдельных эпизодов они образуют.
          </Help>
          <span className={styles.sp} />
          <b className={styles.evNum}>{fmtNum(ev.false_stop_episodes)}</b>
          <span className={styles.evSub}>
            эп. · {fmtNum(ff)} {plural(ff, FRAMES)}
          </span>
        </div>
        <div className={styles.evRow}>
          Первое обнаружение
          <Help placement="top-end" width={250}>
            Самая дальняя дистанция, на которой детектор сопоставил размеченный объект.
          </Help>
          <span className={styles.sp} />
          <b className={styles.evNum}>{fmtMeters(ev.first_detection_distance)}</b>
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------- 3D preview

export function PreviewCard({ r, pos, frame, decision }: { r: RunDetail; pos: number; frame: number; decision: Decision }) {
  return (
    <section className={styles.pv} aria-label="3D-вид кадра">
      {r.has_clouds ? (
        <Suspense fallback={null}>
          <CloudPreview runId={r.id} pos={pos} height="100%" className={styles.pvCanvas} />
        </Suspense>
      ) : (
        <div className={styles.pvEmpty}>
          <span>
            <Icon name="cube" size={22} />
          </span>
          облака точек не сохранены
        </div>
      )}
      <div className={styles.o1}>
        <h2>3D-вид</h2>
        <span className={styles.sp} />
        <span className={styles.glass}>
          кадр {frame} / {fmtNum(r.summary.n_frames)}
        </span>
      </div>
      <div className={styles.o2}>
        <DecisionChip decision={decision} extra={`кадр ${frame}`} />
        <span className={styles.sp} />
        <Button variant="outline" size="sm" icon="play" to={playerUrl(r.id, pos)}>
          Плеер
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- downloads

export function DownloadsCard({ r }: { r: RunDetail }) {
  const jsonl = r.sizes?.results_jsonl ?? null;
  const tiles = [
    { href: downloads.results(r.id), f: 'JSONL', what: 'кадры', b: jsonl !== null ? fmtBytes(jsonl) : fmtCount(r.summary.n_frames, FRAMES) },
    { href: downloads.report(r.id), f: 'JSON', what: 'отчёт', b: 'сводка' },
    { href: downloads.csv(r.id), f: 'CSV', what: 'таблица', b: fmtCount(r.summary.n_frames, ['строка', 'строки', 'строк']) },
  ];
  return (
    <Card className={styles.dl} title="Скачать" headGap={10} help="Результаты по кадрам (как у resense run --out), отчёт с параметрами и сводкой, таблица для Excel." helpPlacement="top-end">
      <div className={styles.dlg}>
        {tiles.map((t) => (
          <a key={t.f} className={styles.dlt} href={t.href} download>
            <span className={styles.dlf}>
              {t.f}
              <Icon name="download" size={16} />
            </span>
            <span className={styles.dls}>
              {t.what}
              <br />
              <b>{t.b}</b>
            </span>
          </a>
        ))}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------- the preset chip

export function PresetChip({ r, schema }: { r: RunDetail; schema: readonly ParamSpec[] | undefined }) {
  const overrides = Object.entries(r.overrides ?? {});
  const spec = new Map((schema ?? []).map((s) => [s.key, s]));
  const o = r.options;
  return (
    <span className={styles.preset}>
      <Chip variant="outline" icon="sliders" className={styles.presetChip} title={r.preset.name}>
        <span className={styles.ell}>{r.preset.name}</span>
      </Chip>
      <Help width={300} placement="bottom">
        <b>{r.preset.name}</b>
        {overrides.length === 0 ? ': параметры детектора по умолчанию.' : ':'}
        {overrides.length > 0 && (
          <ul className={styles.helpList}>
            {overrides.map(([k, v]) => {
              const s = spec.get(k);
              return (
                <li key={k}>
                  {s?.label ?? k}: <b>{fmtParam(v, s?.unit)}</b>
                  {s ? ` (обычно ${fmtParam(s.default, s.unit)})` : ''}
                </li>
              );
            })}
          </ul>
        )}
        {o && (
          <ul className={styles.helpList}>
            <li>
              шаг кадров <b>{o.every}</b>
              {o.start ? ` · с кадра ${o.start}` : ''}
              {o.limit ? ` · не больше ${fmtNum(o.limit)}` : ''}
            </li>
            <li>{o.clouds ? `облака по ${fmtNum(o.cloud_points)} точек` : 'без облаков точек'}</li>
          </ul>
        )}
      </Help>
    </span>
  );
}
