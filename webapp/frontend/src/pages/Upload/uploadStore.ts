// A file / folder upload that outlives the Загрузка page: the transfer keeps going while the user
// looks at other pages (Главная, Очередь), its progress shows again on return, and the finished
// recording becomes the chosen one (takeUploadResult). One upload at a time; a new one replaces it.
import type { QueryClient } from '@tanstack/react-query';
import { useSyncExternalStore } from 'react';
import { qk } from '../../api/hooks';
import type { Recording } from '../../api/types';
import { UploadAbortedError, uploadRecording, type UploadHandle, type UploadItem, type UploadProgress } from '../../api/upload';
import type { KindGuess } from './kinds';

/** What the user chose: the files (relative paths kept), the guessed kind, a display name. */
export interface Picked {
  items: UploadItem[];
  guess: KindGuess;
  name: string;
  bytes: number;
}

export interface UploadRun {
  picked: Picked;
  status: 'uploading' | 'error';
  progress: UploadProgress | null;
  /** the Russian message of a failed upload (the server's detail) */
  error: string | null;
}

export interface UploadStore {
  run: UploadRun | null;
  /** the recording of the last finished upload, until the page takes it */
  result: Recording | null;
}

let store: UploadStore = { run: null, result: null };
let handle: UploadHandle | null = null;
/** identifies the current upload: callbacks of a replaced / aborted one are ignored */
let current: symbol | null = null;
const listeners = new Set<() => void>();
const setStore = (patch: Partial<UploadStore>) => {
  store = { ...store, ...patch };
  listeners.forEach((l) => l());
};
const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
};
const snapshot = () => store;

/** Uploads the picked files as one recording (an upload already running is aborted first). */
export function startUpload(qc: QueryClient, picked: Picked): void {
  handle?.abort();
  const token = Symbol('upload');
  current = token;
  setStore({ run: { picked, status: 'uploading', progress: null, error: null }, result: null });
  // (the first progress report comes synchronously, from inside uploadRecording)
  const h = uploadRecording(picked.items, {
    name: picked.name || undefined,
    onProgress: (progress) => {
      if (current === token && store.run) setStore({ run: { ...store.run, progress } });
    },
  });
  handle = h;
  h.promise.then(
    (rec) => {
      if (current !== token) return;
      current = null;
      handle = null;
      qc.setQueryData(qk.recording(rec.id), rec);
      void qc.invalidateQueries({ queryKey: qk.recordings });
      void qc.invalidateQueries({ queryKey: qk.system });
      setStore({ run: null, result: rec });
    },
    (err: unknown) => {
      if (current !== token) return;
      current = null;
      handle = null;
      if (err instanceof UploadAbortedError || !store.run) setStore({ run: null });
      else setStore({ run: { ...store.run, status: 'error', progress: null, error: err instanceof Error ? err.message : String(err) } });
    },
  );
}

/** Cancels the running upload (its staging area on the server is removed). */
export function abortUpload(): void {
  const h = handle;
  current = null;
  handle = null;
  h?.abort();
  setStore({ run: null });
}

/** Forgets a failed upload. */
export function dismissUpload(): void {
  if (store.run?.status === 'error') setStore({ run: null });
}

/** The recording of the finished upload (once; null when there is none). */
export function takeUploadResult(): Recording | null {
  const rec = store.result;
  if (rec) setStore({ result: null });
  return rec;
}

export function useUploadStore(): UploadStore {
  return useSyncExternalStore(subscribe, snapshot, snapshot);
}
