// Choosing runs to compare: the «+ Прогон» popover of the header and the full chooser shown while
// fewer than two runs are picked (runs of the same recording as the first pick come first).
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import type { Run } from '../../api/types';
import { Button, DecisionStrip, TextInput } from '../../components';
import { fmtDuration, fmtFrames, fmtRelDate } from '../../lib/format';
import { MAX_COMPARE } from '../Runs/common/analysis';
import { Check, EvalChip } from '../Runs/common/Bits';
import styles from './Compare.module.css';

function rank(runs: readonly Run[], chosen: readonly string[]): Run[] {
  const recs = new Set(runs.filter((r) => chosen.includes(r.id)).map((r) => r.recording_id));
  return [...runs].sort((a, b) => Number(recs.has(b.recording_id) && !!b.recording_id) - Number(recs.has(a.recording_id) && !!a.recording_id));
}

const matches = (r: Run, q: string) => !q || `${r.name} ${r.preset.name}`.toLocaleLowerCase('ru').includes(q.trim().toLocaleLowerCase('ru'));

/** The header's «+ Прогон» button with a searchable list of the runs not compared yet. */
export function AddRun({ runs, chosen, onAdd }: { runs: readonly Run[]; chosen: readonly string[]; onAdd: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const anchor = useRef<HTMLSpanElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  const list = useMemo(() => rank(runs, chosen).filter((r) => !chosen.includes(r.id) && matches(r, q)), [runs, chosen, q]);
  const full = chosen.length >= MAX_COMPARE;

  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const r = anchor.current?.getBoundingClientRect();
      if (r) setPos({ top: r.bottom + 8, left: Math.min(r.left, window.innerWidth - 400) });
    };
    place();
    window.addEventListener('resize', place);
    return () => window.removeEventListener('resize', place);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!anchor.current?.contains(t) && !pop.current?.contains(t)) setOpen(false);
    };
    document.addEventListener('pointerdown', onDown, true);
    return () => document.removeEventListener('pointerdown', onDown, true);
  }, [open]);

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      setOpen(false);
      anchor.current?.querySelector('button')?.focus();
    }
  };

  return (
    <span ref={anchor} className={styles.addWrap}>
      <Button variant="outline" size="sm" icon="plus" disabled={full} onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="dialog">
        Прогон
      </Button>
      {open &&
        createPortal(
          <div
            ref={pop}
            className={styles.pop}
            role="dialog"
            aria-label="Добавить прогон к сравнению"
            style={{ top: pos?.top ?? -9999, left: pos?.left ?? -9999, visibility: pos ? 'visible' : 'hidden' }}
            onKeyDown={onKey}
          >
            <TextInput autoFocus icon="search" placeholder="Название или пресет" aria-label="Поиск прогона" value={q} onChange={(e) => setQ(e.target.value)} />
            <div className={styles.popList}>
              {list.length === 0 ? (
                <div className={styles.popEmpty}>{runs.length ? 'Нет подходящих прогонов' : 'Прогонов пока нет'}</div>
              ) : (
                list.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    className={styles.popItem}
                    onClick={() => {
                      onAdd(r.id);
                      setOpen(false);
                      setQ('');
                    }}
                  >
                    <span className={styles.popName}>{r.name}</span>
                    <span className={styles.popMeta}>
                      {fmtFrames(r.summary.n_frames)} · {fmtDuration(r.summary.duration_s)} · {fmtRelDate(r.created_at)}
                    </span>
                    <DecisionStrip decisions={r.summary.decisions} height={10} radius={4} />
                  </button>
                ))
              )}
            </div>
          </div>,
          document.body,
        )}
    </span>
  );
}

/** Tiles of every run to tick (while fewer than two are compared). */
export function Chooser({ runs, chosen, onToggle }: { runs: readonly Run[]; chosen: readonly string[]; onToggle: (id: string) => void }) {
  const [q, setQ] = useState('');
  const list = useMemo(() => rank(runs, chosen).filter((r) => matches(r, q)), [runs, chosen, q]);
  const full = chosen.length >= MAX_COMPARE;
  return (
    <div className={styles.chooser}>
      <TextInput icon="search" placeholder="Название или пресет" aria-label="Поиск прогона" value={q} onChange={(e) => setQ(e.target.value)} className={styles.chooserSearch} />
      <div className={styles.tiles}>
        {list.map((r) => {
          const on = chosen.includes(r.id);
          return (
            <label key={r.id} className={[styles.tile, on ? styles.tileOn : ''].join(' ')}>
              <span className={styles.tileTop}>
                <Check checked={on} disabled={full && !on} onChange={() => onToggle(r.id)} aria-label={`Сравнить: ${r.name}`} />
                <span className={styles.tileName} title={r.name}>
                  {r.name}
                </span>
              </span>
              <DecisionStrip decisions={r.summary.decisions} height={16} radius={6} />
              <span className={styles.tileMeta}>
                <span className={styles.ell}>
                  {fmtFrames(r.summary.n_frames)} · {r.preset.name}
                </span>
                <EvalChip ev={r.summary.eval} size="sm" />
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
