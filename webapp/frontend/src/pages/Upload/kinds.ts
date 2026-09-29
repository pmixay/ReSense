// What the chosen files look like before they are uploaded (the server decides for real on
// finalize): a rosbag2 folder, a zip, a lone .db3 / .mcap, results .jsonl or .npy / .npz frames.
import type { IconName } from '../../components';

export type GuessedKind = 'zip' | 'rosbag2' | 'db3' | 'mcap' | 'jsonl' | 'npy' | 'labels' | 'unknown';

export interface KindGuess {
  kind: GuessedKind;
  label: string;
  icon: IconName;
  /** the server accepts this (labels are attached to a recording instead) */
  ok: boolean;
}

const GUESS: Record<GuessedKind, Omit<KindGuess, 'kind'>> = {
  zip: { label: 'архив .zip', icon: 'zip', ok: true },
  rosbag2: { label: 'rosbag2', icon: 'zip', ok: true },
  db3: { label: 'rosbag2 · .db3', icon: 'file', ok: true },
  mcap: { label: 'rosbag2 · .mcap', icon: 'file', ok: true },
  jsonl: { label: 'результаты .jsonl', icon: 'list', ok: true },
  npy: { label: 'кэш .npy / .npz', icon: 'cube', ok: true },
  labels: { label: 'разметка .json', icon: 'tag', ok: false },
  unknown: { label: 'формат не распознан', icon: 'file', ok: false },
};

const ext = (p: string) => {
  const name = p.toLowerCase().split('/').pop() ?? '';
  const i = name.lastIndexOf('.');
  return i > 0 ? name.slice(i) : '';
};

/** Guess of the recording kind from the relative paths of the chosen files. */
export function guessKind(paths: readonly string[]): KindGuess {
  const exts = new Set(paths.map(ext));
  const names = new Set(paths.map((p) => p.toLowerCase().split('/').pop() ?? ''));
  let kind: GuessedKind = 'unknown';
  if (exts.has('.zip')) kind = 'zip';
  else if (names.has('metadata.yaml') && (exts.has('.db3') || exts.has('.mcap'))) kind = 'rosbag2';
  else if (exts.has('.mcap')) kind = 'mcap';
  else if (exts.has('.db3')) kind = 'db3';
  else if (exts.has('.jsonl')) kind = 'jsonl';
  else if (exts.has('.npy') || exts.has('.npz')) kind = 'npy';
  else if (paths.length > 0 && [...exts].every((e) => e === '.json')) kind = 'labels';
  return { kind, ...GUESS[kind] };
}

/** Accepted formats (chips of the drop zone and the hero). */
export const ACCEPTED: { label: string; icon: IconName }[] = [
  { label: 'rosbag2 · .zip', icon: 'zip' },
  { label: '.db3 + metadata.yaml', icon: 'file' },
  { label: '.mcap', icon: 'file' },
  { label: 'результаты .jsonl', icon: 'list' },
  { label: 'кэш .npy / .npz', icon: 'cube' },
];
