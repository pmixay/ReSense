// «Файл»: a drop zone for files AND folders (folders are walked with webkitGetAsEntry), «Выбрать
// файлы» / «Выбрать папку» (input webkitdirectory); the upload streams with progress (bytes, speed,
// ETA, cancel) and keeps going on other pages (uploadStore); after finalize the page makes the
// detected recording the chosen one.
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type DragEvent, type ReactNode } from 'react';
import { useUploadLabels } from '../../api/hooks';
import type { Recording } from '../../api/types';
import { filesFromDataTransfer, suggestName, toUploadItems, type UploadItem } from '../../api/upload';
import { Button, Chip, ErrorBanner, Help, Icon, IconButton, ProgressBar } from '../../components';
import { FILES, fmtBytes, fmtClock, fmtCount, fmtPercent, fmtSpeed } from '../../lib/format';
import { ACCEPTED, guessKind } from './kinds';
import { RecordingCard } from './RecordingCard';
import { abortUpload, dismissUpload, startUpload, useUploadStore, type Picked, type UploadRun } from './uploadStore';
import styles from './FileSource.module.css';

function UploadingCard({ run, onCancel }: { run: UploadRun; onCancel: () => void }) {
  const { picked, progress: p } = run;
  const finalizing = p?.phase === 'finalizing' || p?.phase === 'done';
  const staging = !p || p.phase === 'staging';
  return (
    <div className={styles.card}>
      <span className={styles.fi} aria-hidden>
        <Icon name={picked.guess.icon} size={20} />
      </span>
      <div className={styles.w}>
        <div className={styles.nm}>
          <span className={styles.name} title={picked.name}>
            {picked.name}
          </span>
          <span className={styles.kind}>{picked.guess.label}</span>
        </div>
        <ProgressBar
          value={finalizing || staging ? null : p.fraction}
          height={10}
          label="Загрузка записи"
          className={styles.bar}
        />
        <div className={styles.line}>
          {finalizing ? (
            <b>проверяем запись на сервере…</b>
          ) : staging ? (
            <b>подготовка…</b>
          ) : (
            <>
              <b>{fmtPercent(p.fraction)}</b>
              <span>
                {fmtBytes(p.loaded)} из {fmtBytes(p.total)}
              </span>
              {p.bytesPerSec !== null && <span>{fmtSpeed(p.bytesPerSec)}</span>}
              {p.etaS !== null && <span>осталось {fmtClock(p.etaS)}</span>}
              {p.fileCount > 1 && (
                <span>
                  файл {p.fileIndex + 1} из {p.fileCount}
                </span>
              )}
            </>
          )}
        </div>
      </div>
      <IconButton icon="x" label="Отменить загрузку" tooltip variant="well" size="sm" onClick={onCancel} disabled={finalizing} />
    </div>
  );
}

export interface FileSourceProps {
  current: Recording | null;
  onRecording: (rec: Recording) => void;
  onClear: () => void;
}

export function FileSource({ current, onRecording, onClear }: FileSourceProps) {
  const qc = useQueryClient();
  const { run } = useUploadStore();
  const labels = useUploadLabels();
  const [picked, setPicked] = useState<Picked | null>(null);
  const [drag, setDrag] = useState(false);
  const [reading, setReading] = useState(false);
  const filesRef = useRef<HTMLInputElement>(null);
  const dirRef = useRef<HTMLInputElement>(null);
  const depth = useRef(0);

  useEffect(() => {
    // not in React's input typings: pick a whole folder (File.webkitRelativePath keeps the layout)
    dirRef.current?.setAttribute('webkitdirectory', '');
    dirRef.current?.setAttribute('directory', '');
  }, []);

  // the page picks the finished recording up (takeUploadResult), also after a trip elsewhere
  const start = (p: Picked) => {
    setPicked(null);
    startUpload(qc, p);
  };

  const take = (items: UploadItem[]) => {
    if (!items.length) return;
    const guess = guessKind(items.map((i) => i.path));
    const p: Picked = { items, guess, name: suggestName(items), bytes: items.reduce((s, i) => s + i.file.size, 0) };
    labels.reset();
    dismissUpload();
    if (guess.ok) start(p);
    else setPicked(p); // not uploaded by itself: labels go to a recording, unknown files on request
  };

  const onDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    depth.current = 0;
    setDrag(false);
    if (run?.status === 'uploading') return;
    setReading(true);
    try {
      take(await filesFromDataTransfer(e.dataTransfer));
    } finally {
      setReading(false);
    }
  };

  const busy = run?.status === 'uploading' || reading;
  const attachLabels = async (p: Picked) => {
    if (!current) return;
    const rec = await labels.mutateAsync({ id: current.id, labels: p.items[0].file }).catch(() => null);
    if (rec) {
      setPicked(null);
      onRecording(rec);
    }
  };

  let top: ReactNode = null;
  if (run?.status === 'uploading') top = <UploadingCard run={run} onCancel={abortUpload} />;
  else if (run?.status === 'error')
    top = (
      <div className={styles.errBox}>
        <ErrorBanner error={run.error} title="Запись не принята" onRetry={() => start(run.picked)} />
        <IconButton icon="x" label="Убрать" tooltip variant="white" size="sm" onClick={dismissUpload} />
      </div>
    );
  else if (picked && !picked.guess.ok)
    top = (
      <div className={styles.card}>
        <span className={[styles.fi, styles.fiWarn].join(' ')} aria-hidden>
          <Icon name={picked.guess.icon} size={20} />
        </span>
        <div className={styles.w}>
          <div className={styles.nm}>
            <span className={styles.name} title={picked.name}>
              {picked.name}
            </span>
            <span className={[styles.kind, styles.kindWarn].join(' ')}>{picked.guess.label}</span>
          </div>
          <div className={styles.line}>
            <span>{fmtCount(picked.items.length, FILES)}</span>
            <span>{fmtBytes(picked.bytes)}</span>
          </div>
          {labels.isError && <ErrorBanner error={labels.error} compact className={styles.inlineErr} />}
        </div>
        {picked.guess.kind === 'labels' ? (
          current ? (
            <Button variant="dark" size="sm" icon="tag" loading={labels.isPending} onClick={() => void attachLabels(picked)}>
              К записи «{current.name}»
            </Button>
          ) : (
            <Chip variant="well">сначала выберите запись</Chip>
          )
        ) : (
          <Button variant="outline" size="sm" icon="upload" onClick={() => start(picked)}>
            Всё равно загрузить
          </Button>
        )}
        <IconButton icon="x" label="Убрать" tooltip variant="well" size="sm" onClick={() => setPicked(null)} />
      </div>
    );
  else if (current) top = <RecordingCard rec={current} onClear={onClear} />;

  return (
    <div
      className={[styles.drop, drag ? styles.over : '', top ? styles.hasTop : ''].join(' ')}
      onDragEnter={(e) => {
        e.preventDefault();
        depth.current += 1;
        setDrag(true);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = busy ? 'none' : 'copy';
      }}
      onDragLeave={() => {
        depth.current = Math.max(0, depth.current - 1);
        if (depth.current === 0) setDrag(false);
      }}
      onDrop={(e) => void onDrop(e)}
    >
      {top && <div className={styles.top}>{top}</div>}

      <div className={styles.prompt}>
        <span className={styles.big} aria-hidden>
          <Icon name="upload" size={40} strokeWidth={2.2} />
        </span>
        <div>
          <h2 className={styles.h}>{drag ? 'Отпустите здесь' : 'Перетащите запись'}</h2>
          <div className={styles.or}>
            <Button variant="dark" icon="file" disabled={busy} onClick={() => filesRef.current?.click()}>
              Выбрать файлы
            </Button>
            <Button variant="outline" icon="folder" disabled={busy} onClick={() => dirRef.current?.click()}>
              Выбрать папку
            </Button>
          </div>
        </div>
      </div>

      <div className={styles.fm}>
        {ACCEPTED.map((f) => (
          <span key={f.label} className={styles.fchip}>
            <span className={styles.fci}>
              <Icon name={f.icon} size={13} strokeWidth={2.4} />
            </span>
            {f.label}
          </span>
        ))}
        <Help placement="top" width={270}>
          Папку rosbag2 можно перетащить целиком или упаковать в <b>.zip</b>. Готовые результаты <b>.jsonl</b> открываются без облаков точек. Файл разметки <b>.json</b>
          прикрепляется к выбранной записи.
        </Help>
      </div>

      <input
        ref={filesRef}
        type="file"
        multiple
        hidden
        accept=".zip,.db3,.mcap,.yaml,.jsonl,.npy,.npz,.json"
        onChange={(e) => {
          take(toUploadItems(Array.from(e.target.files ?? [])));
          e.target.value = '';
        }}
      />
      <input
        ref={dirRef}
        type="file"
        multiple
        hidden
        onChange={(e) => {
          take(toUploadItems(Array.from(e.target.files ?? [])));
          e.target.value = '';
        }}
      />
      {reading && (
        <Chip variant="ink" className={styles.reading}>
          читаем папку…
        </Chip>
      )}
    </div>
  );
}
