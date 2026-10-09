// «Файл»: a drop zone for files AND folders (folders are walked with webkitGetAsEntry), «Выбрать
// файлы» / «Выбрать папку» (input webkitdirectory). The upload is resumable (api/upload.ts): bytes,
// speed, time left, the compression saved, pause / resume / cancel, automatic retries while the
// connection is gone, the server's unpacking progress; it keeps going on other pages
// (uploadStore) and, after a reload, continues where it stopped once the same files are picked
// again. After finalize the page makes the detected recording the chosen one.
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type DragEvent, type ReactNode } from 'react';
import { useUploadLabels } from '../../api/hooks';
import type { FinalizeStage, Recording } from '../../api/types';
import { filesFromDataTransfer, suggestName, toUploadItems, type UploadItem, type UploadProgress } from '../../api/upload';
import { Button, Chip, ErrorBanner, Help, Icon, IconButton, ProgressBar } from '../../components';
import { FILES, fmtBytes, fmtClock, fmtCount, fmtPercent, fmtSpeed } from '../../lib/format';
import { ACCEPTED, guessKind } from './kinds';
import { RecordingCard } from './RecordingCard';
import {
  abortUpload,
  discardPending,
  dismissUpload,
  matchesPending,
  pauseUpload,
  resumeUpload,
  startUpload,
  useUploadStore,
  type PendingUpload,
  type Picked,
  type UploadRun,
} from './uploadStore';
import styles from './FileSource.module.css';

const STAGE: Record<FinalizeStage, string> = {
  starting: 'проверяем запись на сервере…',
  unpacking: 'распаковываем архив на сервере',
  probing: 'проверяем запись на сервере…',
  saving: 'сохраняем запись…',
};

function finalizeText(p: UploadProgress): ReactNode {
  const f = p.finalize;
  if (f?.stage === 'unpacking' && f.fraction !== null)
    return (
      <>
        <b>{STAGE.unpacking}</b>
        <span>{fmtPercent(f.fraction)}</span>
      </>
    );
  return <b>{f ? STAGE[f.stage] : STAGE.starting}</b>;
}

function TransferLine({ p }: { p: UploadProgress }) {
  const saved = p.compression !== null ? 1 - p.compression : null;
  return (
    <>
      <b>{fmtPercent(p.fraction)}</b>
      <span>
        {fmtBytes(p.loaded)} из {fmtBytes(p.total)}
      </span>
      {p.state === 'paused' && <span className={styles.warn}>пауза</span>}
      {p.state === 'waiting' && (
        <span className={styles.warn} title={p.notice ?? undefined}>
          нет связи · повтор через {p.retryInS ?? 1} с
        </span>
      )}
      {p.state === 'running' && p.bytesPerSec !== null && <span>{fmtSpeed(p.bytesPerSec)}</span>}
      {p.state === 'running' && p.etaS !== null && <span>осталось {fmtClock(p.etaS)}</span>}
      {saved !== null && saved >= 0.01 && <span title="Сжатие при передаче: столько байт не пришлось отправлять">сжатие −{fmtPercent(saved)}</span>}
      {p.resumed > 0 && <span title={`${fmtBytes(p.resumed)} уже были на сервере`}>докачка</span>}
      {p.fileCount > 1 && (
        <span>
          файл {p.fileIndex + 1} из {p.fileCount}
        </span>
      )}
    </>
  );
}

function UploadingCard({ run }: { run: UploadRun }) {
  const { picked, progress: p } = run;
  const finalizing = p?.phase === 'finalizing' || p?.phase === 'done';
  const staging = !p || p.phase === 'staging';
  const paused = p?.state === 'paused';
  const waiting = p?.state === 'waiting';
  const bar = finalizing ? (p?.finalize?.stage === 'unpacking' ? p.finalize.fraction : null) : staging ? null : p.fraction;
  return (
    <div className={styles.card}>
      <span className={[styles.fi, paused || waiting ? styles.fiWarn : ''].join(' ')} aria-hidden>
        <Icon name={paused ? 'pause' : waiting ? 'wifi-off' : picked.guess.icon} size={20} />
      </span>
      <div className={styles.w}>
        <div className={styles.nm}>
          <span className={styles.name} title={picked.name}>
            {picked.name}
          </span>
          <span className={styles.kind}>{picked.guess.label}</span>
        </div>
        <ProgressBar value={bar} height={10} label="Загрузка записи" className={styles.bar} />
        <div className={styles.line} aria-live="polite">
          {finalizing && p ? finalizeText(p) : staging ? <b>подготовка…</b> : <TransferLine p={p} />}
        </div>
        {(paused || waiting) && p?.notice && <div className={styles.notice}>{p.notice}</div>}
      </div>
      {!finalizing &&
        (paused ? (
          <IconButton icon="play" label="Продолжить загрузку" tooltip variant="dark" size="sm" onClick={resumeUpload} />
        ) : waiting ? (
          <IconButton icon="retry" label="Повторить сейчас" tooltip variant="well" size="sm" onClick={resumeUpload} />
        ) : (
          <IconButton icon="pause" label="Приостановить загрузку" tooltip variant="well" size="sm" onClick={pauseUpload} disabled={staging} />
        ))}
      <IconButton icon="x" label="Отменить загрузку" tooltip variant="well" size="sm" onClick={abortUpload} disabled={finalizing} />
    </div>
  );
}

function PendingCard({ pending, received, onContinue }: { pending: PendingUpload; received: number | null; onContinue: () => void }) {
  const what = pending.folder ? 'ту же папку' : pending.files.length > 1 ? 'те же файлы' : 'тот же файл';
  return (
    <div className={styles.card}>
      <span className={[styles.fi, styles.fiWarn].join(' ')} aria-hidden>
        <Icon name="pause" size={20} />
      </span>
      <div className={styles.w}>
        <div className={styles.nm}>
          <span className={styles.name} title={pending.name}>
            {pending.name}
          </span>
          <span className={[styles.kind, styles.kindWarn].join(' ')}>не завершена</span>
        </div>
        <ProgressBar value={received === null ? null : received / Math.max(1, pending.bytes)} height={10} label="Незавершённая загрузка" className={styles.bar} />
        <div className={styles.line}>
          {received !== null && (
            <span>
              на сервере {fmtBytes(received)} из {fmtBytes(pending.bytes)}
            </span>
          )}
          <span>выберите {what}, чтобы продолжить</span>
        </div>
      </div>
      <Button variant="dark" size="sm" icon="play" onClick={onContinue}>
        Продолжить
      </Button>
      <IconButton icon="trash" label="Удалить незавершённую загрузку" tooltip variant="well" size="sm" onClick={discardPending} />
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
  const { run, pending, pendingReceived } = useUploadStore();
  const labels = useUploadLabels();
  const [picked, setPicked] = useState<Picked | null>(null);
  /** files picked while another upload is unfinished: start over only when the user confirms */
  const [replacing, setReplacing] = useState<Picked | null>(null);
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
    setReplacing(null);
    startUpload(qc, p);
  };

  // the same files as the unfinished upload continue it; other files replace it once confirmed
  const begin = (p: Picked) => {
    if (pending && matchesPending(pending, p.items)) {
      setPicked(null);
      setReplacing(null);
      startUpload(qc, { ...p, name: pending.name || p.name }, pending.uploadId);
    } else if (pending) {
      setPicked(null);
      setReplacing(p);
    } else start(p);
  };

  const take = (items: UploadItem[]) => {
    if (!items.length) return;
    const guess = guessKind(items.map((i) => i.path));
    const p: Picked = { items, guess, name: suggestName(items), bytes: items.reduce((s, i) => s + i.file.size, 0) };
    labels.reset();
    dismissUpload();
    setReplacing(null);
    if (guess.ok) begin(p);
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
  if (run?.status === 'uploading') top = <UploadingCard run={run} />;
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
          <Button variant="outline" size="sm" icon="upload" onClick={() => begin(picked)}>
            Всё равно загрузить
          </Button>
        )}
        <IconButton icon="x" label="Убрать" tooltip variant="well" size="sm" onClick={() => setPicked(null)} />
      </div>
    );
  else if (replacing && pending)
    top = (
      <div className={styles.card}>
        <span className={[styles.fi, styles.fiWarn].join(' ')} aria-hidden>
          <Icon name="warning" size={20} />
        </span>
        <div className={styles.w}>
          <div className={styles.nm}>
            <span className={styles.name} title={replacing.name}>
              {replacing.name}
            </span>
            <span className={styles.kind}>{replacing.guess.label}</span>
          </div>
          <div className={styles.line}>
            <span>
              это не файлы незавершённой загрузки «{pending.name}» — она будет удалена{pendingReceived ? ` (${fmtBytes(pendingReceived)} на сервере)` : ''}
            </span>
          </div>
        </div>
        <Button variant="outline" size="sm" icon="upload" onClick={() => start(replacing)}>
          Начать новую
        </Button>
        <IconButton icon="x" label="Отмена" tooltip variant="well" size="sm" onClick={() => setReplacing(null)} />
      </div>
    );
  else if (pending)
    top = <PendingCard pending={pending} received={pendingReceived} onContinue={() => (pending.folder ? dirRef : filesRef).current?.click()} />;
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
