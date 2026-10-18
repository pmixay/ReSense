// Player-specific tools in normal page flow; global navigation is supplied by AppShell.
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useRuns } from '../../api/hooks';
import type { Decision, Run } from '../../api/types';
import { DecisionChip, ErrorBanner, Icon, IconButton, Segmented, Spinner } from '../../components';
import { DECISION_CHIP_LABEL, worstDecision } from '../../lib/decisions';
import { fmtDuration, fmtRelDate } from '../../lib/format';
import type { CamMode } from '../../player/geometry';
import { CAMERAS, CAMERA_LABEL } from './cab';
import styles from './Player.module.css';

/** Runs for the selector: with clouds first, newest first within each group. */
export function sortRunsForPlayer(runs: readonly Run[]): Run[] {
  return [...runs].sort((a, b) => Number(b.has_clouds) - Number(a.has_clouds) || b.created_at.localeCompare(a.created_at));
}

function RunMenu({ runId, name }: { runId: string; name: string }) {
  const [open, setOpen] = useState(false);
  const runs = useRuns({ enabled: open });
  const navigate = useNavigate();
  const wrap = useRef<HTMLDivElement>(null);
  const menuId = useId();
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
      <button
        type="button"
        className={styles.nameBtn}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        title={name}
        aria-label={`Другой прогон: ${name}`}
      >
        <Icon name="cube" size={16} />
        <span className={styles.runName}>{name}</span>
        <Icon name="chevron-down" size={16} />
      </button>
      {open && (
        <nav id={menuId} className={styles.menu} aria-label="Прогоны">
          {runs.isLoading && (
            <div className={styles.menuState}>
              <Spinner size={18} />
            </div>
          )}
          {runs.isError && <ErrorBanner compact error={runs.error} title="Прогоны не загрузились" onRetry={() => void runs.refetch()} retrying={runs.isFetching} />}
          {runs.data && !list.length && <div className={styles.menuState}>Прогонов пока нет</div>}
          {list.map((r) => {
            const worst: Decision = worstDecision(r.summary.decisions) ?? 'GO';
            return (
              <button
                key={r.id}
                type="button"
                aria-current={r.id === runId ? 'page' : undefined}
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
            Все прогоны
          </Link>
        </nav>
      )}
    </div>
  );
}

export function Beacon({ decision }: { decision: Decision | null }) {
  if (!decision) return null;
  return (
    <div role="status" aria-live="polite" aria-label={`Решение: ${DECISION_CHIP_LABEL[decision]}`}>
      <DecisionChip decision={decision} />
    </div>
  );
}

export interface ViewControlsProps {
  runId?: string;
  runName?: string;
  decision: Decision | null;
  reason?: string;
  mode?: CamMode;
  onMode?: (m: CamMode) => void;
  fullscreen: boolean;
  onFullscreen: () => void;
}

export function ViewControls({ runId, runName, decision, reason, mode, onMode, fullscreen, onFullscreen }: ViewControlsProps) {
  return (
    <div className={styles.controls} role="group" aria-label="Параметры просмотра">
      {runId && runName !== undefined && <RunMenu runId={runId} name={runName} />}
      <Beacon decision={decision} />
      {reason && <span className={styles.viewReason}>{reason}</span>}
      <div className={styles.viewTools}>
        {mode && onMode && (
          <Segmented<CamMode>
            label="Камера"
            tone="well"
            className={styles.cameraModes}
            size="sm"
            value={mode}
            onChange={onMode}
            options={CAMERAS.map((c) => ({ value: c, label: CAMERA_LABEL[c], icon: c === 'cab' ? 'train' : c === 'top' ? 'view-top' : 'view-back' }))}
          />
        )}
        <IconButton
          icon={fullscreen ? 'exit-fullscreen' : 'fullscreen'}
          label={fullscreen ? 'Выйти из полноэкранного режима (F)' : 'Во весь экран (F)'}
          variant="outline"
          className={styles.toolButton}
          size="md"
          onClick={onFullscreen}
          tooltip
          tooltipPlacement="bottom-end"
        />
      </div>
    </div>
  );
}
