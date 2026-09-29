// The roof of the cab: back, the «Плеер» pill with its mini metro line, the run selector, the
// decision beacon, the camera switch and the fullscreen toggle.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useRuns } from '../../api/hooks';
import type { Decision, Run } from '../../api/types';
import { DECISION_ICON, DecisionChip, Icon, IconButton, Segmented, Spinner } from '../../components';
import { DECISION_CHIP_LABEL, worstDecision } from '../../lib/decisions';
import { fmtDuration, fmtRelDate } from '../../lib/format';
import type { CamMode } from '../../player/geometry';
import { CAMERAS, CAMERA_LABEL } from './cab';
import styles from './Player.module.css';

/** The ReSense mark in brand red on a white pill (mockup player.html). */
export function RedMark() {
  return (
    <svg className={styles.logoMark} viewBox="0 0 40 38" aria-hidden>
      <path d="M3.5 19H12" stroke="#E4000D" strokeWidth="7" strokeLinecap="round" />
      <circle cx="19" cy="19" r="7" fill="#fff" stroke="#E4000D" strokeWidth="5" />
      <path d="M28.2 11.3A12 12 0 0 1 28.2 26.7M32 8.1A17 17 0 0 1 32 29.9" fill="none" stroke="#E4000D" strokeWidth="2.8" strokeLinecap="round" />
    </svg>
  );
}

export function PlayerPill() {
  return (
    <Link to="/" className={styles.rpill} aria-label="На главную">
      <RedMark />
      <span className={styles.pn}>Плеер</span>
      <span className={styles.mline} aria-hidden>
        <i />
        <i />
        <i />
        <i className={styles.c} />
        <i />
      </span>
    </Link>
  );
}

/** Runs for the selector: with clouds first, newest first within each group. */
export function sortRunsForPlayer(runs: readonly Run[]): Run[] {
  return [...runs].sort((a, b) => Number(b.has_clouds) - Number(a.has_clouds) || b.created_at.localeCompare(a.created_at));
}

function RunMenu({ runId, name }: { runId: string; name: string }) {
  const [open, setOpen] = useState(false);
  const runs = useRuns({ enabled: open });
  const navigate = useNavigate();
  const wrap = useRef<HTMLDivElement>(null);
  const list = useMemo(() => sortRunsForPlayer(runs.data ?? []).slice(0, 30), [runs.data]);

  useEffect(() => {
    if (!open) return;
    const down = (e: PointerEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        setOpen(false);
      }
    };
    document.addEventListener('pointerdown', down, true);
    document.addEventListener('keydown', key, true);
    return () => {
      document.removeEventListener('pointerdown', down, true);
      document.removeEventListener('keydown', key, true);
    };
  }, [open]);

  return (
    <div className={styles.menuWrap} ref={wrap}>
      <button type="button" className={`${styles.rpill} ${styles.nameBtn}`} onClick={() => setOpen((v) => !v)} aria-haspopup="listbox" aria-expanded={open} title={name}>
        <span className={styles.runName}>{name}</span>
      </button>
      <IconButton icon="menu" label="Другой прогон" variant="white" size="lg" onClick={() => setOpen((v) => !v)} aria-expanded={open} />
      {open && (
        <div className={styles.menu} role="listbox" aria-label="Прогоны">
          {runs.isLoading && (
            <div className={styles.menuState}>
              <Spinner size={18} />
            </div>
          )}
          {runs.isError && <div className={styles.menuState}>{runs.error.message}</div>}
          {runs.data && !list.length && <div className={styles.menuState}>Прогонов пока нет</div>}
          {list.map((r) => {
            const worst: Decision = worstDecision(r.summary.decisions) ?? 'GO';
            return (
              <button
                key={r.id}
                type="button"
                role="option"
                aria-selected={r.id === runId}
                className={`${styles.menuItem} ${r.id === runId ? styles.menuOn : ''}`}
                onClick={() => {
                  setOpen(false);
                  if (r.id !== runId) navigate(`/player/${encodeURIComponent(r.id)}`);
                }}
              >
                <DecisionChip decision={worst} size="sm" />
                <span className={styles.menuName}>{r.name}</span>
                <span className={styles.menuMeta}>
                  {r.has_clouds ? <Icon name="cube" size={14} /> : null}
                  {fmtDuration(r.summary.duration_s)} · {fmtRelDate(r.created_at)}
                </span>
              </button>
            );
          })}
          <Link to="/player" className={styles.menuAll} onClick={() => setOpen(false)}>
            <Icon name="list" size={16} />
            Все прогоны с облаками
          </Link>
        </div>
      )}
    </div>
  );
}

export function Beacon({ decision }: { decision: Decision | null }) {
  if (!decision) return null;
  return (
    <div className={`${styles.beacon} ${styles[`b_${decision.toLowerCase()}`]}`} role="status" aria-live="polite" aria-label={`Решение: ${DECISION_CHIP_LABEL[decision]}`}>
      <span className={styles.bo}>
        <Icon name={DECISION_ICON[decision]} size={26} strokeWidth={2.6} />
      </span>
      <span className={styles.bt}>{DECISION_CHIP_LABEL[decision]}</span>
    </div>
  );
}

export interface RoofProps {
  runId?: string;
  runName?: string;
  decision: Decision | null;
  mode?: CamMode;
  onMode?: (m: CamMode) => void;
  fullscreen: boolean;
  /** hide the navigation (pseudo fullscreen: the browser refused the real one) */
  kiosk: boolean;
  onFullscreen: () => void;
  onBack: () => void;
}

export function Roof({ runId, runName, decision, mode, onMode, fullscreen, kiosk, onFullscreen, onBack }: RoofProps) {
  return (
    <>
      {!kiosk && (
        <div className={styles.roofL}>
          <IconButton icon="arrow-left" label="Назад" variant="white" size="lg" onClick={onBack} tooltip tooltipPlacement="bottom" />
          <PlayerPill />
          {runId && runName !== undefined && <RunMenu runId={runId} name={runName} />}
        </div>
      )}
      <Beacon decision={decision} />
      <div className={styles.roofR}>
        {mode && onMode && (
          <Segmented<CamMode>
            label="Камера"
            tone="white"
            size="sm"
            className={styles.cseg}
            value={mode}
            onChange={onMode}
            options={CAMERAS.map((c) => ({ value: c, label: CAMERA_LABEL[c], icon: c === 'cab' ? 'train' : undefined }))}
          />
        )}
        <IconButton
          icon={fullscreen ? 'exit-fullscreen' : 'fullscreen'}
          label={fullscreen ? 'Выйти из полноэкранного режима (F)' : 'Во весь экран (F)'}
          variant="white"
          size="lg"
          onClick={onFullscreen}
          tooltip
          tooltipPlacement="bottom-end"
        />
      </div>
    </>
  );
}
