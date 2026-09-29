// «Записи»: recordings already on the server — pick one to process again (e.g. with another preset),
// download a demo bag, or delete one.
import { downloads, useDeleteRecording, useRecordings } from '../../api/hooks';
import type { Recording } from '../../api/types';
import { Button, EmptyState, ErrorBanner, Icon, Spinner } from '../../components';
import { fmtRelDate } from '../../lib/format';
import { ConfirmButton } from '../Queue/ConfirmButton';
import { KIND_ICON, KIND_LABEL, SOURCE_LABEL, recordingMeta } from './recording';
import styles from './RecordingsSource.module.css';

export interface RecordingsSourceProps {
  currentId: string | null;
  onPick: (rec: Recording) => void;
  onDeleted: (id: string) => void;
  /** switch to another source (the empty state's calls to action) */
  onSource: (source: 'file' | 'demo') => void;
}

export function RecordingsSource({ currentId, onPick, onDeleted, onSource }: RecordingsSourceProps) {
  const recs = useRecordings({ retry: false });
  const del = useDeleteRecording();

  if (recs.isError) return <ErrorBanner error={recs.error} onRetry={() => void recs.refetch()} retrying={recs.isFetching} />;
  if (recs.isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size={24} />
      </div>
    );
  }
  if (!recs.data?.length) {
    return (
      <EmptyState
        icon="database"
        className={styles.empty}
        title="Записей пока нет"
        action={
          <div className={styles.emptyActs}>
            <Button variant="dark" icon="sparkle" onClick={() => onSource('demo')}>
              Создать демо
            </Button>
            <Button variant="outline" icon="upload" onClick={() => onSource('file')}>
              Загрузить файл
            </Button>
          </div>
        }
      />
    );
  }

  return (
    <div className={styles.wrap}>
      {del.isError && <ErrorBanner error={del.error} compact className={styles.err} />}
      <div className={styles.list}>
        {recs.data.map((r) => {
          const on = r.id === currentId;
          return (
            <div key={r.id} className={[styles.row, on ? styles.on : ''].join(' ')}>
              <button type="button" className={styles.pick} aria-pressed={on} onClick={() => onPick(r)}>
                <span className={styles.ic}>
                  <Icon name={on ? 'check' : KIND_ICON[r.kind]} size={16} strokeWidth={on ? 3 : 2} />
                </span>
                <span className={styles.w}>
                  <span className={styles.nm} title={r.name}>
                    {r.name}
                  </span>
                  <span className={styles.mt}>
                    <b>{r.source === 'demo' ? 'демо' : SOURCE_LABEL[r.source]}</b> · {KIND_LABEL[r.kind]}
                    {recordingMeta(r) ? ` · ${recordingMeta(r)}` : ''}
                  </span>
                </span>
                <span className={[styles.tag, r.labels.available ? styles.tagOn : ''].join(' ')}>{r.labels.available ? 'разметка' : 'без разметки'}</span>
                <span className={styles.when}>{fmtRelDate(r.created_at)}</span>
              </button>
              {r.source === 'demo' && (
                <a className={styles.dl} href={downloads.recording(r.id)} download aria-label={`Скачать ${r.name} (.zip)`} title="Скачать .zip">
                  <Icon name="download" size={16} />
                </a>
              )}
              <ConfirmButton
                icon="trash"
                label={r.source === 'server' ? 'Убрать из списка (файлы на сервере останутся)' : 'Удалить запись'}
                confirm={r.source === 'server' ? 'Убрать?' : 'Удалить?'}
                loading={del.isPending && del.variables === r.id}
                onConfirm={() => del.mutate(r.id, { onSuccess: () => onDeleted(r.id) })}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
