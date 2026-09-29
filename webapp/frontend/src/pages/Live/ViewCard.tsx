// The view of the path: for the replay, the run's stored point cloud at the frame on air (the player's
// CloudPreview, lazy so three.js loads only here) or the scheme; for the real node, the scheme (the
// node does not stream clouds to the browser).
import { lazy, Suspense, useState } from 'react';
import type { Run } from '../../api/types';
import { Card, Chip, DecisionChip, Help, Segmented, Spinner } from '../../components';
import { fmtInt, fmtNum } from '../../lib/format';
import type { FeedSnapshot } from './feed';
import type { SourceKind } from './SourceBar';
import { TrackSchematic } from './TrackSchematic';
import styles from './View.module.css';

const CloudPreview = lazy(() => import('../../player/CloudPreview'));

type Mode = '3d' | 'scheme';

export interface ViewCardProps {
  snap: FeedSnapshot;
  kind: SourceKind;
  run: Run | undefined;
  fresh: boolean;
  className?: string;
}

export function ViewCard({ snap, kind, run, fresh, className }: ViewCardProps) {
  const [mode, setMode] = useState<Mode>('3d');
  const can3d = kind === 'sim' && !!run?.has_clouds;
  const show3d = can3d && mode === '3d';
  const msg = snap.msg;
  const onAir = snap.source?.kind === 'sim' && snap.source.runId === run?.id;
  const pos = onAir && typeof msg?.pos === 'number' ? msg.pos : 0;
  const cloudPos = onAir && typeof msg?.cloud_pos === 'number' ? msg.cloud_pos : pos;
  const decision = msg?.decision;
  const shown = fresh || snap.view === 'paused';

  return (
    <Card variant="night" padding="none" className={[styles.view, className].filter(Boolean).join(' ')}>
      {show3d && run ? (
        <Suspense
          fallback={
            <div className={styles.center}>
              <Spinner tone="light" label="3D-вид загружается" />
            </div>
          }
        >
          <CloudPreview runId={run.id} pos={cloudPos} height="100%" interactive className={styles.cloud} />
        </Suspense>
      ) : (
        <TrackSchematic msg={msg} fresh={fresh} show={shown} />
      )}

      <div className={styles.top}>
        <h2 className={styles.title}>{show3d ? '3D-вид' : 'Схема пути'}</h2>
        <Help tone="light" placement="bottom-start" width={290} label="Что на виде">
          {show3d ? (
            <>
              Облако точек прогона на кадре в эфире (сохранённое при обработке, ближайшее не позже). Мышь — вращение.
            </>
          ) : (
            <>
              Вид сверху по данным узла: ось пути и рельсы из модели пути, габарит <b>2,1 м</b> до дальности контроля, зона предупреждения <b>+0,35 м</b>, объекты —
              красные в габарите, жёлтые рядом. Поперечный масштаб растянут.
            </>
          )}
        </Help>
        <span className={styles.sp} />
        {can3d && (
          <Segmented
            size="sm"
            tone="white"
            label="Вид"
            value={mode}
            onChange={setMode}
            options={[
              { value: '3d', label: '3D', icon: 'cube' },
              { value: 'scheme', label: 'Схема', icon: 'view-top' },
            ]}
          />
        )}
      </div>

      {show3d && (
        <div className={styles.bottom}>
          {shown && decision && (
            <DecisionChip decision={decision} extra={decision === 'STOP' && typeof msg?.nearest_distance === 'number' ? `${fmtNum(msg.nearest_distance, 1)} м` : undefined} />
          )}
          {onAir && run && (
            <Chip variant="glass">
              кадр {fmtInt(pos)} / {fmtInt(run.summary.n_frames)}
            </Chip>
          )}
        </div>
      )}
    </Card>
  );
}
