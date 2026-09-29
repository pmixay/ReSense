// Загрузка: choose a source (a file / folder upload, a folder on the server, a synthetic demo, or a
// recording already here), check what the server detected, set the processing options and start
// it; the live queue runs in the right column. `?source=`, `?rec=` and `?preset=` keep the choice in
// the URL (e.g. «Обработать с этим пресетом» on Параметры links to /upload?preset=<id>).
import { useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useRecording, useRecordings, useSystem } from '../../api/hooks';
import type { Recording } from '../../api/types';
import { Button, Card, Chip, PageHeader, Segmented } from '../../components';
import { RECORDINGS, fmtBytes, fmtCount } from '../../lib/format';
import { QueuePanel } from '../Queue/QueuePanel';
import { DemoSource } from './DemoSource';
import { FileSource } from './FileSource';
import { ProcessCard } from './ProcessCard';
import { DEFAULT_PRESET } from './recording';
import { RecordingsSource } from './RecordingsSource';
import { ServerSource } from './ServerSource';
import { takeUploadResult, useUploadStore } from './uploadStore';
import { useDemoGenerator } from './useDemo';
import styles from './Upload.module.css';

type Source = 'file' | 'server' | 'demo' | 'list';
const SOURCES: readonly Source[] = ['file', 'server', 'demo', 'list'];

export default function Upload() {
  const [params, setParams] = useSearchParams();
  const source: Source = SOURCES.find((s) => s === params.get('source')) ?? 'file';
  const recId = params.get('rec');
  const presetId = params.get('preset') ?? DEFAULT_PRESET;
  const sys = useSystem();
  const recs = useRecordings({ retry: false });
  const one = useRecording(recId, { retry: false });
  const demo = useDemoGenerator('upload');
  const current: Recording | null = one.data ?? recs.data?.find((r) => r.id === recId) ?? null;
  const free = sys.isError ? undefined : sys.data?.disk_free_bytes;

  const patch = useCallback(
    (f: (p: URLSearchParams) => void) =>
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          f(next);
          return next;
        },
        { replace: true },
      ),
    [setParams],
  );
  const setSource = (s: Source) => patch((p) => p.set('source', s));
  const choose = useCallback((r: Recording) => patch((p) => p.set('rec', r.id)), [patch]);
  const clear = useCallback(() => patch((p) => p.delete('rec')), [patch]);
  const setPreset = useCallback((id: string) => patch((p) => (id === DEFAULT_PRESET ? p.delete('preset') : p.set('preset', id))), [patch]);

  // a demo made from this page becomes the chosen recording, also when it finished while the user
  // was on another page (the generation outlives the page)
  const { active: demoActive, take: takeDemo } = demo;
  useEffect(() => {
    if (demoActive) return;
    const rec = takeDemo();
    if (rec) choose(rec);
  }, [demoActive, takeDemo, choose]);

  // the same for a finished upload
  const uploaded = useUploadStore().result;
  useEffect(() => {
    if (!uploaded) return;
    const rec = takeUploadResult();
    if (rec) choose(rec);
  }, [uploaded, choose]);

  // a recording that is gone (deleted elsewhere, stale link) is no longer the chosen one
  useEffect(() => {
    if (recId && one.isError && one.error.status === 404) clear();
  }, [recId, one.isError, one.error, clear]);

  const nRecs = recs.data?.length;
  return (
    <>
      <PageHeader
        title="Загрузка"
        station={1}
        chips={nRecs !== undefined ? <Chip variant="outline">{fmtCount(nRecs, RECORDINGS)} на сервере</Chip> : undefined}
        actions={
          <>
            <Chip variant="outline" icon="server">
              свободно {free !== undefined ? fmtBytes(free) : '—'}
            </Chip>
            <Button variant="outline" icon="sliders" to="/presets">
              Пресеты
            </Button>
          </>
        }
      />
      <section className={`grid-12 fill-viewport ${styles.grid}`}>
        <Card
          title="Источник"
          className={styles.src}
          headGap={16}
          actions={
            <Segmented
              label="Источник записи"
              value={source}
              onChange={setSource}
              className={styles.seg}
              options={[
                { value: 'file', label: 'Файл', icon: 'file' },
                { value: 'server', label: 'Папка на сервере', icon: 'server' },
                { value: 'demo', label: 'Демо-запись', icon: 'sparkle' },
                {
                  value: 'list',
                  label: (
                    <>
                      Записи
                      {nRecs ? <span className={styles.cnt}>{nRecs}</span> : null}
                    </>
                  ),
                  icon: 'database',
                  ariaLabel: 'Записи на сервере',
                },
              ]}
            />
          }
        >
          {source === 'file' && <FileSource current={current} onRecording={choose} onClear={clear} />}
          {source === 'server' && <ServerSource current={current} onRecording={choose} onClear={clear} />}
          {source === 'demo' && <DemoSource demo={demo} current={current} onClear={clear} />}
          {source === 'list' && (
            <RecordingsSource currentId={current?.id ?? null} onPick={choose} onDeleted={(id) => id === recId && clear()} onSource={setSource} />
          )}
        </Card>
        <ProcessCard rec={current} presetId={presetId} onPresetChange={setPreset} className={styles.opts} />
        <QueuePanel className={styles.queue} />
      </section>
    </>
  );
}
