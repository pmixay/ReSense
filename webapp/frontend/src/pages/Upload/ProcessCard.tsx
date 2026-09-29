// «Обработка»: preset, cloud topic, frame step, clouds for the player, scoring against labels (and
// attaching a labels file), estimates, and «Обработать» → POST /api/jobs → the queue.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateJob, useDeleteLabels, usePresets, useUploadLabels } from '../../api/hooks';
import type { Recording } from '../../api/types';
import { Button, Card, Chip, ErrorBanner, Help, IconButton, Select, Stepper, Toggle } from '../../components';
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

  const presetOptions = (presets.data ?? []).map((p) => ({ value: p.id, label: p.builtin ? `${p.name} · базовый` : p.name }));
  if (!presetOptions.length) presetOptions.push({ value: 'standard', label: presets.isLoading ? 'загрузка…' : 'стандартный' });
  const topicOptions = [
    { value: AUTO, label: rec?.default_topic ? `авто · ${rec.default_topic}` : 'авто' },
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
          <Select label="Пресет" icon="sliders" options={presetOptions} value={presetId} onChange={setPresetId} disabled={disabled || !presets.data} />
        </div>
        <div className={styles.field}>
          <FieldLabel>Топик облака</FieldLabel>
          <Select label="Топик облака" icon="sparkle" options={topicOptions} value={topic} onChange={setTopic} disabled={disabled || results || topics.length < 2} />
        </div>
        <div className={styles.field}>
          <FieldLabel help="1 — каждый кадр, как на поезде. 2 и больше — быстрее, но решения реже.">Шаг кадров</FieldLabel>
          <Stepper value={results ? 1 : every} onChange={setEvery} min={1} max={10} label="Шаг кадров" disabled={disabled || results} />
        </div>
        <div className={styles.field}>
          <FieldLabel help="Прореженные облака точек для 3D-плеера: до 3000 кадров по 30 000 точек.">Для плеера</FieldLabel>
          <Toggle label="Облака точек" checked={!results && clouds} onChange={setClouds} disabled={disabled || results} />
        </div>
        <div className={styles.field}>
          <FieldLabel
            help={
              hasLabels
                ? 'Сравнить решения с разметкой: верные СТОП на объектах, пропуски и ложные СТОП.'
                : 'У записи нет разметки. Прикрепите файл labels/*.json кнопкой «Разметка .json».'
            }
          >
            По разметке
          </FieldLabel>
          <Toggle label="Оценка" checked={hasLabels && evaluate} onChange={setEvaluate} disabled={disabled || !hasLabels} />
        </div>
      </div>

      <div className={styles.foot}>
        <Chip icon="layers">{frames !== null ? fmtFrames(frames) : 'кадров —'}</Chip>
        <Chip icon="clock">{seconds !== null ? `≈ ${fmtDuration(Math.max(1, seconds))}` : 'время —'}</Chip>
        {cloudSize !== null && <Chip icon="cube">облака ≈ {fmtBytes(cloudSize)}</Chip>}
        {rec &&
          (hasLabels ? (
            <Chip variant="well" icon="tag" className={styles.labels} title={rec.labels.name ?? undefined}>
              разметка
              {rec.labels.source === 'upload' && (
                <IconButton
                  icon="x"
                  label="Убрать загруженную разметку"
                  variant="white"
                  size="xs"
                  className={styles.labelsX}
                  loading={delLabels.isPending}
                  onClick={() => delLabels.mutate(rec.id)}
                />
              )}
            </Chip>
          ) : (
            <Button variant="outline" size="sm" icon="tag" loading={putLabels.isPending} onClick={() => labelsInput.current?.click()}>
              Разметка .json
            </Button>
          ))}
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
