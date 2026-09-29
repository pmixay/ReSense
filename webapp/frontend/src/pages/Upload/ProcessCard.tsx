// «Обработка»: preset, cloud topic, frame step, clouds for the player, scoring against labels (and
// attaching a labels file), estimates, and «Обработать» → POST /api/jobs → the queue.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateJob, useDeleteLabels, usePresets, useUploadLabels } from '../../api/hooks';
import type { Recording } from '../../api/types';
import { Button, Card, Chip, ErrorBanner, Help, Icon, IconButton, Select, Stepper, Toggle } from '../../components';
import { fmtBytes, fmtDuration, fmtFrames } from '../../lib/format';
import { cloudBytes, framesToProcess, processSeconds } from './estimate';
import { cloudTopics } from './recording';
import styles from './ProcessCard.module.css';

const AUTO = '__auto__';

function FieldLabel({ children, help }: { children: string; help?: string }) {
  return (
    <div className={styles.fl}>
      {children}
      {help && <Help placement="top">{help}</Help>}
    </div>
  );
}

export function ProcessCard({ rec, className }: { rec: Recording | null; className?: string }) {
  const navigate = useNavigate();
  const presets = usePresets({ retry: false });
  const createJob = useCreateJob();
  const putLabels = useUploadLabels();
  const delLabels = useDeleteLabels();
  const labelsInput = useRef<HTMLInputElement>(null);

  const [presetId, setPresetId] = useState('standard');
  const [topic, setTopic] = useState(AUTO);
  const [every, setEvery] = useState(1);
  const [clouds, setClouds] = useState(true);
  const [evaluate, setEvaluate] = useState(true);

  const results = rec?.kind === 'jsonl';
  const topics = useMemo(() => (rec ? cloudTopics(rec) : []), [rec]);
  const hasLabels = !!rec?.labels.available;

  // a new recording: its own topics; results-only recordings carry no clouds
  useEffect(() => {
    setTopic(AUTO);
    createJob.reset();
    putLabels.reset();
    delLabels.reset();
  }, [rec?.id]); // only when another recording is chosen
  useEffect(() => {
    if (presets.data && !presets.data.some((p) => p.id === presetId)) setPresetId(presets.data[0]?.id ?? 'standard');
  }, [presets.data, presetId]);

  const frames = rec ? framesToProcess(rec.n_frames, results ? 1 : every) : null;
  const seconds = processSeconds(frames);
  const cloudSize = !results && clouds ? cloudBytes(frames) : null;
  const disabled = !rec;

  const presetOptions = (presets.data ?? []).map((p) => ({ value: p.id, label: p.name }));
  if (!presetOptions.length) presetOptions.push({ value: 'standard', label: presets.isLoading ? 'загрузка…' : 'стандартный' });
  const topicOptions = [
    { value: AUTO, label: 'авто' },
    ...topics.map((t) => ({ value: t, label: t })),
  ];

  const start = async () => {
    if (!rec) return;
    const job = await createJob
      .mutateAsync({
        recording_id: rec.id,
        preset_id: presetId,
        options: results
          ? { every: 1, evaluate: hasLabels && evaluate }
          : { topic: topic === AUTO ? null : topic, every, clouds, evaluate: hasLabels && evaluate },
      })
      .catch(() => null);
    if (job) navigate('/queue');
  };

  const onLabelsFile = async (file: File | undefined) => {
    if (!rec || !file) return;
    await putLabels.mutateAsync({ id: rec.id, labels: file }).catch(() => null);
  };

  const err = createJob.error ?? putLabels.error ?? delLabels.error;

  return (
    <Card
      title="Обработка"
      className={[styles.card, className].filter(Boolean).join(' ')}
      badges={
        rec ? (
          <Chip variant="well" size="sm" icon="check" className={styles.target} title={rec.name}>
            {rec.name}
          </Chip>
        ) : (
          <Chip variant="outline" size="sm">
            запись не выбрана
          </Chip>
        )
      }
    >
      <div className={styles.row}>
        <div className={styles.field}>
          <FieldLabel help="Набор параметров детектора; свои пресеты — на странице «Параметры».">Пресет</FieldLabel>
          <Select label="Пресет" icon="sliders" options={presetOptions} value={presetId} onChange={setPresetId} disabled={!presets.data} />
        </div>
        <div className={styles.field}>
          <FieldLabel>Топик облака</FieldLabel>
          <Select label="Топик облака" icon="sparkle" options={topicOptions} value={topic} onChange={setTopic} disabled={results} />
        </div>
        <div className={styles.field}>
          <FieldLabel help="1 — каждый кадр, как на поезде. 2 и больше — быстрее, но решения реже.">Шаг кадров</FieldLabel>
          <Stepper value={results ? 1 : every} onChange={setEvery} min={1} max={10} label="Шаг кадров" disabled={results} />
        </div>
        <div className={styles.field}>
          <FieldLabel help="Прореженные облака точек для 3D-плеера: до 3000 кадров по 30 000 точек.">Для плеера</FieldLabel>
          <Toggle
            label={
              <>
                <span className={styles.long}>Облака точек</span>
                <span className={styles.short}>Облака</span>
              </>
            }
            checked={!results && clouds}
            onChange={setClouds}
            disabled={results}
          />
        </div>
      </div>

      <div className={styles.foot}>
        {frames !== null && (
          <Chip icon="layers" title="Кадров к обработке и время при ~10 кадрах в секунду">
            {fmtFrames(frames)}
            {seconds !== null ? ` · ≈ ${fmtDuration(Math.max(1, seconds))}` : ''}
          </Chip>
        )}
        {cloudSize !== null && (
          <Chip icon="cube" className={styles.cloudChip}>
            облака ≈ {fmtBytes(cloudSize)}
          </Chip>
        )}
        {rec && (
          <div className={styles.evalPill}>
            <Icon name="tag" size={16} />
            <span className={styles.evalText}>По разметке</span>
            <Help placement="top" width={260}>
              {hasLabels ? (
                <>
                  Сравнить решения с разметкой <b>{rec.labels.name}</b>: верные СТОП на объектах, пропуски и ложные СТОП.
                </>
              ) : (
                <>
                  У записи нет разметки — оценка недоступна. Прикрепите файл в формате <b>labels/*.json</b> кнопкой «+».
                </>
              )}
            </Help>
            <Toggle ariaLabel="Оценка по разметке" checked={hasLabels && evaluate} onChange={setEvaluate} disabled={!hasLabels} />
            {!hasLabels && (
              <IconButton
                icon="plus"
                label="Прикрепить разметку .json"
                tooltip
                variant="white"
                size="xs"
                loading={putLabels.isPending}
                onClick={() => labelsInput.current?.click()}
              />
            )}
            {hasLabels && rec.labels.source === 'upload' && (
              <IconButton
                icon="x"
                label="Убрать загруженную разметку"
                tooltip
                variant="white"
                size="xs"
                loading={delLabels.isPending}
                onClick={() => delLabels.mutate(rec.id)}
              />
            )}
          </div>
        )}
        <span className={styles.sp} />
        <Button variant="primary" size="lg" icon="play" onClick={() => void start()} disabled={disabled} loading={createJob.isPending}>
          Обработать
        </Button>
        <input
          ref={labelsInput}
          type="file"
          accept=".json,application/json"
          hidden
          onChange={(e) => {
            void onLabelsFile(e.target.files?.[0]);
            e.target.value = '';
          }}
        />
      </div>
      {err && <ErrorBanner error={err} compact className={styles.err} />}
    </Card>
  );
}
