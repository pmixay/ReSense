// Recording facts in Russian (kind, source, frames, duration, size) for chips and meta lines.
import type { IconName } from '../../components';
import type { Recording, RecordingKind, RecordingSource, ServerEntry } from '../../api/types';
import { fmtBytes, fmtDuration, fmtFrames } from '../../lib/format';

/** The built-in preset (webapp/API.md: "standard" is the read-only default). */
export const DEFAULT_PRESET = 'standard';

export const KIND_LABEL: Record<RecordingKind, string> = {
  rosbag2: 'rosbag2',
  npy: 'кэш .npy',
  jsonl: 'результаты .jsonl',
};

export const KIND_ICON: Record<RecordingKind, IconName> = {
  rosbag2: 'zip',
  npy: 'cube',
  jsonl: 'list',
};

export const SOURCE_LABEL: Record<RecordingSource, string> = {
  upload: 'файл',
  server: 'папка на сервере',
  demo: 'демо',
};

export const SOURCE_ICON: Record<RecordingSource, IconName> = {
  upload: 'file',
  server: 'server',
  demo: 'sparkle',
};

/** "201 кадр · 20,4 с · 2,6 ГБ" (missing parts skipped). */
export function recordingMeta(r: Pick<Recording, 'n_frames' | 'duration_s' | 'size_bytes'>, withSize = true): string {
  const parts: string[] = [];
  if (r.n_frames !== null) parts.push(fmtFrames(r.n_frames));
  if (r.duration_s !== null) parts.push(fmtDuration(r.duration_s));
  if (withSize && r.size_bytes > 0) parts.push(fmtBytes(r.size_bytes));
  return parts.join(' · ');
}

/** PointCloud2 topics of a recording (the ones a job may read). */
export function cloudTopics(r: Pick<Recording, 'topics'>): string[] {
  return r.topics.filter((t) => /PointCloud2$/.test(t.type)).map((t) => t.name);
}

const FILE_RECORDING = /\.(jsonl|db3|mcap)$|(^|\/)metadata\.yaml$/i;

/** A recording can be registered from this server entry (a bag / npy folder, a .jsonl / storage file). */
export function isRecordingEntry(e: ServerEntry): boolean {
  if (e.type === 'dir') return e.is_bag || e.is_npy_dir;
  return FILE_RECORDING.test(e.name);
}
