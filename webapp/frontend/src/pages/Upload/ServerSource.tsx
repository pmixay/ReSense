// «Папка на сервере»: a read-only browser of RESENSE_DATA (GET /api/server-files): breadcrumbs,
// folders first, rosbag2 / npy badges with frame counts; a double click opens a folder, choosing a
// recording registers it in place (POST /api/recordings/from-server, nothing is copied).
import { useEffect, useMemo, useState, type KeyboardEvent } from 'react';
import { useRegisterServerRecording, useServerFiles, useSystem } from '../../api/hooks';
import type { Recording, ServerEntry } from '../../api/types';
import { Button, Chip, EmptyState, ErrorBanner, Help, Icon, Spinner, type IconName } from '../../components';
import { fmtBytes, fmtFrames, fmtInt } from '../../lib/format';
import { RecordingCard } from './RecordingCard';
import styles from './ServerSource.module.css';

const FILE_RECORDING = /\.(jsonl|db3|mcap)$|(^|\/)metadata\.yaml$/i;

/** A recording can be registered from this entry (a bag / npy folder, a .jsonl / storage file). */
export function isRecordingEntry(e: ServerEntry): boolean {
  if (e.type === 'dir') return e.is_bag || e.is_npy_dir;
  return FILE_RECORDING.test(e.name);
}

function entryIcon(e: ServerEntry): IconName {
  if (e.is_bag) return 'zip';
  if (e.is_npy_dir) return 'cube';
  if (e.type === 'dir') return 'folder';
  if (/\.jsonl$/i.test(e.name)) return 'list';
  return 'file';
}

export interface ServerSourceProps {
  current: Recording | null;
  onRecording: (rec: Recording) => void;
  onClear: () => void;
}

export function ServerSource({ current, onRecording, onClear }: ServerSourceProps) {
  const sys = useSystem();
  const [path, setPath] = useState('');
  const [sel, setSel] = useState<ServerEntry | null>(null);
  const exists = sys.data?.server_root_exists;
  const root = sys.data?.server_root ?? '';
  const files = useServerFiles(path, { enabled: exists !== false, retry: false });
  const register = useRegisterServerRecording();

  useEffect(() => setSel(null), [path]);

  const crumbs = useMemo(() => {
    const parts = path ? path.split('/') : [];
    return parts.map((name, i) => ({ name, path: parts.slice(0, i + 1).join('/') }));
  }, [path]);
  const rootName = root.split('/').filter(Boolean).pop() || 'данные';

  const use = async (e: ServerEntry) => {
    const rec = await register.mutateAsync({ path: e.path }).catch(() => null);
    if (rec) onRecording(rec);
  };
  /** double click / Enter: a recording is used, a plain folder is opened */
  const open = (e: ServerEntry) => {
    if (isRecordingEntry(e)) void use(e);
    else if (e.type === 'dir') setPath(e.path);
  };
  const onRowKey = (ev: KeyboardEvent<HTMLButtonElement>, e: ServerEntry) => {
    if (ev.key === 'Enter') {
      ev.preventDefault();
      open(e);
    } else if (ev.key === 'Backspace' && files.data?.parent !== null && files.data?.parent !== undefined) {
      ev.preventDefault();
      setPath(files.data.parent);
    }
  };

  if (sys.isLoading) {
    return (
      <div className={styles.center}>
        <Spinner size={24} />
      </div>
    );
  }
  if (exists === false) {
    return (
      <div className={styles.box}>
        <EmptyState
          icon="server"
          title="Папка данных не найдена"
          action={
            <div className={styles.missing}>
              <code className={styles.code}>{root}</code>
              <Help placement="top" width={270}>
                Сервер ищет записи в этой папке. Путь задаёт переменная <b>RESENSE_DATA</b> при запуске сервера (по умолчанию <b>/data</b>). Положите туда папки
                rosbag2 и обновите страницу.
              </Help>
            </div>
          }
        />
      </div>
    );
  }

  const entries = files.data?.entries ?? [];
  const selectable = sel && isRecordingEntry(sel);

  return (
    <div className={styles.wrap}>
      {current && <RecordingCard rec={current} onClear={onClear} />}
      <div className={styles.box}>
        <nav className={styles.crumbs} aria-label="Путь">
          <button type="button" className={[styles.crumb, styles.rootCrumb].join(' ')} onClick={() => setPath('')} title={root}>
            <Icon name="server" size={15} />
            {rootName}
          </button>
          {crumbs.map((c) => (
            <span key={c.path} className={styles.crumbWrap}>
              <Icon name="chevron-right" size={14} />
              <button type="button" className={styles.crumb} onClick={() => setPath(c.path)} aria-current={c.path === path ? 'location' : undefined}>
                {c.name}
              </button>
            </span>
          ))}
          <span className={styles.sp} />
          {files.data?.truncated && <Chip size="sm">первые {fmtInt(entries.length)}</Chip>}
          {files.isFetching && <Spinner size={16} />}
          <Help placement="bottom-end" width={260}>
            Двойной щелчок открывает папку или выбирает запись. Записи с сервера не копируются — детектор читает их на месте.
          </Help>
        </nav>

        {files.isError ? (
          <div className={styles.pad}>
            <ErrorBanner error={files.error} onRetry={() => void files.refetch()} retrying={files.isFetching} />
            {path && (
              <Button variant="outline" size="sm" icon="arrow-left" onClick={() => setPath('')} className={styles.back}>
                В корень
              </Button>
            )}
          </div>
        ) : files.isLoading ? (
          <div className={styles.center}>
            <Spinner size={24} />
          </div>
        ) : entries.length === 0 ? (
          <EmptyState icon="folder" size="sm" title="Папка пуста" />
        ) : (
          <div className={styles.list} aria-label="Содержимое папки">
            {files.data?.parent !== null && files.data?.parent !== undefined && (
              <button type="button" className={styles.row} onClick={() => setPath(files.data?.parent ?? '')}>
                <span className={[styles.ic, styles.up].join(' ')}>
                  <Icon name="arrow-up" size={16} />
                </span>
                <span className={styles.name}>..</span>
              </button>
            )}
            {entries.map((e) => {
              const on = sel?.path === e.path;
              return (
                <button
                  key={e.path}
                  type="button"
                  aria-pressed={on}
                  className={[styles.row, on ? styles.on : ''].join(' ')}
                  onClick={() => setSel(e)}
                  onDoubleClick={() => open(e)}
                  onKeyDown={(ev) => onRowKey(ev, e)}
                >
                  <span className={[styles.ic, e.type === 'dir' && !e.is_bag && !e.is_npy_dir ? styles.dir : styles.rec].join(' ')}>
                    <Icon name={entryIcon(e)} size={16} />
                  </span>
                  <span className={styles.name} title={e.name}>
                    {e.name}
                  </span>
                  {e.is_bag && <span className={styles.badge}>rosbag2</span>}
                  {e.is_npy_dir && <span className={styles.badge}>npy</span>}
                  {e.n_frames !== undefined && <span className={styles.frames}>{fmtFrames(e.n_frames)}</span>}
                  <span className={styles.size}>{e.size_bytes > 0 ? fmtBytes(e.size_bytes) : ''}</span>
                  {e.type === 'dir' && <Icon name="chevron-right" size={16} className={styles.chev} />}
                </button>
              );
            })}
          </div>
        )}

        <div className={styles.bar}>
          {register.isError ? (
            <ErrorBanner error={register.error} compact className={styles.barErr} />
          ) : (
            <span className={styles.selName}>{sel ? sel.name : 'Выберите папку записи'}</span>
          )}
          <span className={styles.sp} />
          {sel && sel.type === 'dir' && (
            <Button variant="outline" size="sm" icon="folder" onClick={() => setPath(sel.path)}>
              Открыть
            </Button>
          )}
          <Button variant="dark" size="sm" icon="check" disabled={!selectable} loading={register.isPending} onClick={() => sel && void use(sel)}>
            Использовать запись
          </Button>
        </div>
      </div>
    </div>
  );
}
