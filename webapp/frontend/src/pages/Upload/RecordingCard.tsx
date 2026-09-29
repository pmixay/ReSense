// The chosen recording as the server detected it: kind, frames, duration, size, topic, labels and
// warnings — the pre-flight summary the jury checks before «Обработать».
import type { Recording } from '../../api/types';
import { Help, Icon, IconButton } from '../../components';
import { fmtBytes, fmtDuration, fmtFrames } from '../../lib/format';
import { KIND_ICON, KIND_LABEL, SOURCE_LABEL, cloudTopics } from './recording';
import styles from './RecordingCard.module.css';

export function RecordingCard({ rec, onClear, className }: { rec: Recording; onClear?: () => void; className?: string }) {
  const topics = cloudTopics(rec);
  return (
    <div className={[styles.sel, className].filter(Boolean).join(' ')}>
      <span className={styles.fi} aria-hidden>
        <Icon name={KIND_ICON[rec.kind]} size={20} />
      </span>
      <div className={styles.w}>
        <div className={styles.nm}>
          <span className={styles.name} title={rec.name}>
            {rec.name}
          </span>
          <span className={styles.ok}>
            <Icon name="check" size={13} strokeWidth={3.2} />
            проверено
          </span>
          <Help placement="bottom" width={260}>
            Сводка прочитана сервером из самой записи: формат, кадры, длительность, топики облака и разметка.
          </Help>
        </div>
        <div className={styles.facts}>
          <span className={styles.ink}>{KIND_LABEL[rec.kind]}</span>
          {rec.source === 'demo' ? <span className={styles.ink}>синтетическая</span> : <span>{SOURCE_LABEL[rec.source]}</span>}
          {rec.n_frames !== null && <span>{fmtFrames(rec.n_frames)}</span>}
          {rec.duration_s !== null && <span>{fmtDuration(rec.duration_s)}</span>}
          {rec.size_bytes > 0 && <span>{fmtBytes(rec.size_bytes)}</span>}
          {rec.kind !== 'jsonl' && (
            <span>
              топик<b>{rec.default_topic ?? topics[0] ?? '—'}</b>
              {topics.length > 1 ? ` · ещё ${topics.length - 1}` : ''}
            </span>
          )}
          <span className={rec.labels.available ? styles.good : undefined}>{rec.labels.available ? 'разметка есть' : 'без разметки'}</span>
          {rec.warnings.map((w) => (
            <span key={w} className={styles.warn} title={w}>
              <Icon name="warning" size={13} strokeWidth={2.6} />
              {w}
            </span>
          ))}
        </div>
      </div>
      {onClear && <IconButton icon="x" label="Снять выбор записи" tooltip variant="well" size="sm" onClick={onClear} />}
    </div>
  );
}
