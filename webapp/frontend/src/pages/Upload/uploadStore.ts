// A file / folder upload that outlives the Загрузка page: the transfer keeps going while the user
// looks at other pages (Главная, Очередь), its progress shows again on return, and the finished
// recording becomes the chosen one (takeUploadResult). One upload at a time; a new one replaces it.
// It can be paused and resumed; the server keeps what arrived, so after a reload (or a closed tab)
// the unfinished upload is offered again (`pending`, kept in localStorage) and continues where it
// stopped once the user picks the same files. The tab that sends it beats a heartbeat into the
// stored session: another tab shows it as running elsewhere and offers neither to resume nor to
// delete it.
import type { QueryClient } from '@tanstack/react-query';
import { useSyncExternalStore } from 'react';
import { ApiError, api } from '../../api/client';
import { qk } from '../../api/hooks';
import type { Recording, UploadStatus } from '../../api/types';
import { UploadAbortedError, dropsArea, uploadRecording, type UploadHandle, type UploadItem, type UploadProgress } from '../../api/upload';
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
  /** a failed upload whose staging area the server keeps: «Повторить» continues it */
  resumeId?: string | null;
}

/** An upload left unfinished by a reload: the server holds part of it, the browser no longer has
 *  the files (it cannot reopen them by itself), so the user picks them again to continue. */
export interface PendingUpload {
  uploadId: string;
  name: string;
  files: { path: string; size: number; lastModified: number }[];
  bytes: number;
  /** picked as a folder (paths with "/"): «Продолжить» opens the folder picker */
  folder: boolean;
  savedAt: string;
  /** the tab sending it and its last heartbeat (ms) */
  tab?: string;
  aliveAt?: number;
  /** being sent by another tab right now (not stored) */
  elsewhere?: boolean;
}

export interface UploadStore {
  run: UploadRun | null;
  /** the recording of the last finished upload, until the page takes it */
  result: Recording | null;
  pending: PendingUpload | null;
  /** bytes the server holds of the pending upload (null until known) */
  pendingReceived: number | null;
}

const STORAGE_KEY = 'resense.upload.v1';
const HEARTBEAT_MS = 5000;
/** a session whose tab has not beaten for this long is no longer being sent */
const ALIVE_MS = 15_000;
const TAB_ID = Math.random().toString(36).slice(2, 10);

let store: UploadStore = { run: null, result: null, pending: null, pendingReceived: null };
let handle: UploadHandle | null = null;
/** identifies the current upload: callbacks of a replaced / aborted one are ignored */
let current: symbol | null = null;
let loaded = false;
/** this tab's session while it sends it (rewritten with each heartbeat) */
let session: PendingUpload | null = null;
let beat: ReturnType<typeof setInterval> | null = null;
let recheck: ReturnType<typeof setTimeout> | null = null;
const listeners = new Set<() => void>();
const setStore = (patch: Partial<UploadStore>) => {
  store = { ...store, ...patch };
  listeners.forEach((l) => l());
};
const subscribe = (l: () => void) => {
  listeners.add(l);
  loadPending();
  return () => {
    listeners.delete(l);
  };
};
const snapshot = () => store;

// ---------------------------------------------------------------- the persisted session

function readSession(): PendingUpload | null {
  try {
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) return null;
    const s = JSON.parse(raw) as PendingUpload;
    return s && typeof s.uploadId === 'string' && Array.isArray(s.files) ? s : null;
  } catch {
    return null;
  }
}

function writeSession(s: PendingUpload | null): void {
  try {
    if (typeof localStorage === 'undefined') return;
    if (s) {
      const { elsewhere: _drop, ...stored } = s;
      void _drop;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    } else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // private mode / quota: resuming after a reload is just not offered
  }
}

// the page goes away (reload, closed tab): its upload stops, so the session stops beating at once
// and is offered again right away (also in this very tab after a reload)
if (typeof window !== 'undefined')
  window.addEventListener('pagehide', () => {
    if (session) writeSession({ ...session, tab: TAB_ID, aliveAt: 0 });
  });

/** This tab sends `s` (null: it stopped): the heartbeat tells other tabs to keep their hands off. */
function own(s: PendingUpload | null, keep = false): void {
  if (beat) clearInterval(beat);
  beat = null;
  session = s;
  if (s) {
    const pulse = () => session && writeSession({ ...session, tab: TAB_ID, aliveAt: Date.now() });
    pulse();
    beat = setInterval(pulse, HEARTBEAT_MS);
  } else if (!keep) writeSession(null);
}

const liveElsewhere = (s: PendingUpload): boolean => !!s.tab && s.tab !== TAB_ID && !!s.aliveAt && Date.now() - s.aliveAt < ALIVE_MS;

function sessionOf(uploadId: string, picked: Picked): PendingUpload {
  return {
    uploadId,
    name: picked.name,
    files: picked.items.map((i) => ({ path: i.path, size: i.file.size, lastModified: i.file.lastModified || 0 })),
    bytes: picked.bytes,
    folder: picked.items.some((i) => i.path.includes('/')),
    savedAt: new Date().toISOString(),
  };
}

/** The picked files are the pending upload's files (paths, sizes, modification times). */
export function matchesPending(p: PendingUpload, items: UploadItem[]): boolean {
  if (p.files.length !== items.length) return false;
  const byPath = new Map(items.map((i) => [i.path, i.file]));
  return p.files.every((f) => {
    const file = byPath.get(f.path);
    return !!file && file.size === f.size && (!f.lastModified || !file.lastModified || file.lastModified === f.lastModified);
  });
}

/** Reads the unfinished upload of an earlier visit (once per page load: the first subscriber) and
 *  follows what other tabs do with it. */
function loadPending(): void {
  if (loaded) return;
  loaded = true;
  if (typeof window !== 'undefined')
    window.addEventListener('storage', (e) => {
      if (e.key === STORAGE_KEY && !store.run) void restorePending();
    });
  void restorePending();
}

/** The unfinished upload kept in localStorage becomes `pending` (marked `elsewhere` while another
 *  tab sends it); the server says what it holds. */
export async function restorePending(): Promise<void> {
  if (recheck) clearTimeout(recheck);
  recheck = null;
  const s = readSession();
  if (store.run) return;
  if (!s) {
    if (store.pending) setStore({ pending: null, pendingReceived: null });
    return;
  }
  const elsewhere = liveElsewhere(s);
  setStore({ pending: { ...s, elsewhere }, pendingReceived: store.pending?.uploadId === s.uploadId ? store.pendingReceived : null });
  if (elsewhere) recheck = setTimeout(() => void restorePending(), HEARTBEAT_MS); // its tab may close
  await refreshPending();
}

export async function refreshPending(): Promise<void> {
  const p = store.pending;
  if (!p) return;
  try {
    const st = await api.get<UploadStatus>(`/uploads/${encodeURIComponent(p.uploadId)}`);
    if (store.pending?.uploadId !== p.uploadId) return;
    if (st.state === 'done') {
      // finished while the page was away: nothing to resume
      writeSession(null);
      setStore({ pending: null, pendingReceived: null, result: st.recording ?? store.result });
      return;
    }
    setStore({ pendingReceived: st.bytes_received });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404 && store.pending?.uploadId === p.uploadId) {
      writeSession(null); // expired or removed on the server
      setStore({ pending: null, pendingReceived: null });
    }
  }
}

/** Forgets the unfinished upload and removes what the server holds of it (never one another tab
 *  is sending). */
export function discardPending(): void {
  const p = store.pending;
  if (!p || p.elsewhere) return;
  writeSession(null);
  setStore({ pending: null, pendingReceived: null });
  api.del(`/uploads/${encodeURIComponent(p.uploadId)}`).catch(() => undefined);
}

// ---------------------------------------------------------------- leaving the page

const onBeforeUnload = (e: BeforeUnloadEvent) => {
  e.preventDefault();
  e.returnValue = ''; // the browser asks «Покинуть сайт?»; the upload can be resumed afterwards
};
function guardUnload(on: boolean) {
  if (typeof window === 'undefined') return;
  if (on) window.addEventListener('beforeunload', onBeforeUnload);
  else window.removeEventListener('beforeunload', onBeforeUnload);
}

// ---------------------------------------------------------------- the upload

/** Uploads the picked files as one recording (an upload already running is aborted first).
 *  With `resumeId` (the pending upload's id) the server's part is kept and only the rest is sent. */
export function startUpload(qc: QueryClient, picked: Picked, resumeId?: string | null): void {
  if (store.pending?.elsewhere) return; // one upload at a time: another tab is sending one
  handle?.abort();
  const token = Symbol('upload');
  current = token;
  if (store.pending && store.pending.uploadId !== resumeId) discardPending();
  setStore({ run: { picked, status: 'uploading', progress: null, error: null }, result: null, pending: null, pendingReceived: null });
  guardUnload(true);
  // (the first progress report comes synchronously, from inside uploadRecording)
  const h = uploadRecording(picked.items, {
    name: picked.name || undefined,
    resumeId,
    onStaged: (uploadId) => {
      if (current === token) own(sessionOf(uploadId, picked));
    },
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
      guardUnload(false);
      own(null);
      qc.setQueryData(qk.recording(rec.id), rec);
      void qc.invalidateQueries({ queryKey: qk.recordings });
      void qc.invalidateQueries({ queryKey: qk.system });
      setStore({ run: null, result: rec });
    },
    (err: unknown) => {
      if (current !== token) return;
      current = null;
      handle = null;
      guardUnload(false);
      // the staging area is removed when it cannot become a recording (uploadRecording); any other
      // stays on the server and in the session, for «Повторить» or the same files picked again
      const keep = !(err instanceof UploadAbortedError) && !dropsArea(err) && !!h.uploadId;
      own(null, keep);
      if (err instanceof UploadAbortedError || !store.run) setStore({ run: null });
      else
        setStore({
          run: { ...store.run, status: 'error', progress: null, error: err instanceof Error ? err.message : String(err), resumeId: keep ? h.uploadId : null },
        });
    },
  );
}

/** Cancels the running upload (its staging area on the server is removed). */
export function abortUpload(): void {
  const h = handle;
  current = null;
  handle = null;
  guardUnload(false);
  own(null);
  h?.abort();
  setStore({ run: null });
}

/** Pauses the transfer (what arrived stays on the server). */
export function pauseUpload(): void {
  handle?.pause();
}

/** Continues a paused / waiting transfer at once. */
export function resumeUpload(): void {
  handle?.resume();
}

/** Forgets a failed upload (one the server keeps is offered again as the unfinished upload). */
export function dismissUpload(): void {
  if (store.run?.status !== 'error') return;
  const kept = !!store.run.resumeId;
  setStore({ run: null });
  if (kept) void restorePending();
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
