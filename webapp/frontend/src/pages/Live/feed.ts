// The live feed: one connection at a time — the backend's replay simulation (WS /api/live/sim) or
// the real node through rosbridge (/resense/status) — turned into snapshots for React
// (useSyncExternalStore). Messages may arrive at up to 100 Hz (sim at 10×): they are collected in
// place and published at most every TICK_MS, which is also the freshness clock.
import { useEffect, useMemo, useSyncExternalStore } from 'react';
import { subscribeRosStatus, type RosStatusHandlers, type RosStatusSubscription } from '../../api/rosbridge';
import { clampSpeed, openLiveSim, type LiveHandlers, type LiveSimParams, type LiveSocket } from '../../api/ws';
import { liveView, sampleOf, trimSamples, type LinkStatus, type LiveView, type Sample, type StatusMessage } from './timeline';

export const TICK_MS = 100;
/** rosbridge: after an established connection drops, try again this often (until «Отключить»). */
export const RECONNECT_MS = 2000;

export type FeedSource =
  | { kind: 'sim'; runId: string; speed: number; loop: boolean; startPos?: number }
  | { kind: 'ros'; url: string };

export interface FeedSnapshot {
  link: LinkStatus;
  view: LiveView;
  error: string | null;
  msg: StatusMessage | null;
  /** ms since the latest message (null before the first one) */
  age: number | null;
  /** messages received on this connection */
  count: number;
  samples: readonly Sample[];
  /** the timeline's "now" in the samples' time basis */
  timeNow: number;
  paused: boolean;
  reconnecting: boolean;
  source: FeedSource | null;
}

export interface FeedDeps {
  openSim: (p: LiveSimParams, h: LiveHandlers) => LiveSocket;
  subscribeRos: (url: string, h: RosStatusHandlers) => Promise<RosStatusSubscription>;
  now: () => number;
}

const DEFAULT_DEPS: FeedDeps = {
  openSim: openLiveSim,
  subscribeRos: (url, h) => subscribeRosStatus(url, h),
  now: () => performance.now(),
};

const SIM_CLOSE: Record<number, string> = {
  4400: 'Неверные параметры эфира',
  4404: 'Прогон не найден',
  1011: 'Ошибка чтения прогона',
};

function isMessage(v: unknown): v is StatusMessage {
  return !!v && typeof v === 'object' && typeof (v as { decision?: unknown }).decision === 'string';
}

export class LiveFeedStore {
  private readonly deps: FeedDeps;
  private listeners = new Set<() => void>();
  private snap: FeedSnapshot;
  private timer: ReturnType<typeof setInterval> | null = null;
  private retry: ReturnType<typeof setTimeout> | null = null;
  private gen = 0;
  private sim: LiveSocket | null = null;
  private ros: RosStatusSubscription | null = null;
  private link: LinkStatus = 'idle';
  private error: string | null = null;
  private msg: StatusMessage | null = null;
  private lastAt: number | null = null;
  private count = 0;
  private samples: Sample[] = [];
  private paused = false;
  private everOpen = false;
  private source: FeedSource | null = null;

  constructor(deps: Partial<FeedDeps> = {}) {
    this.deps = { ...DEFAULT_DEPS, ...deps };
    this.snap = this.compute();
  }

  subscribe = (l: () => void): (() => void) => {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  };

  getSnapshot = (): FeedSnapshot => this.snap;

  // ------------------------------------------------------------ commands

  start(source: FeedSource): void {
    this.gen += 1; // before closing: a synchronous close event of the old link must be ignored
    this.disconnect();
    this.source = source;
    this.error = null;
    this.msg = null;
    this.lastAt = null;
    this.count = 0;
    this.samples = [];
    this.everOpen = false;
    this.paused = false;
    this.link = 'connecting';
    if (source.kind === 'sim') this.openSim(source);
    else void this.openRos(source.url);
    this.publish();
  }

  /** Closes the connection and forgets the source (the last message stays on screen). */
  stop(): void {
    this.gen += 1;
    this.disconnect();
    this.link = 'idle';
    this.error = null;
    this.paused = false;
    this.publish();
  }

  /** Closes the connection and forgets everything it delivered (another source is chosen: its
   *  predecessor's frames must not be shown as its own). */
  reset(): void {
    this.gen += 1;
    this.disconnect();
    this.source = null;
    this.link = 'idle';
    this.error = null;
    this.msg = null;
    this.lastAt = null;
    this.count = 0;
    this.samples = [];
    this.paused = false;
    this.everOpen = false;
    this.publish();
  }

  pause(): void {
    if (this.source?.kind !== 'sim' || this.link !== 'open') return;
    this.paused = true;
    this.sim?.send({ cmd: 'pause' });
    this.publish();
  }

  play(): void {
    const src = this.source;
    if (src?.kind !== 'sim') return;
    if (this.link !== 'open') {
      const last = typeof this.msg?.pos === 'number' ? this.msg.pos : (src.startPos ?? 0);
      this.start({ ...src, startPos: this.link === 'ended' ? 0 : last });
      return;
    }
    this.paused = false;
    this.sim?.send({ cmd: 'play' });
    this.publish();
  }

  /** Jumps to a processed-order position; starts the replay there when it is not running. */
  seek(pos: number, runId?: string): void {
    const src = this.source;
    const p = Math.max(0, Math.floor(pos));
    if (src?.kind === 'sim' && this.link === 'open' && (!runId || runId === src.runId)) {
      this.sim?.send({ cmd: 'seek', pos: p });
      this.samples = [];
      this.publish();
      return;
    }
    if (src?.kind === 'sim' || runId) {
      const base = src?.kind === 'sim' ? src : { kind: 'sim' as const, runId: runId ?? '', speed: 1, loop: true };
      // a replay paused on purpose stays paused when a seek lands while it (re)connects
      const keepPaused = this.paused && this.link === 'connecting' && src?.kind === 'sim' && (!runId || runId === src.runId);
      this.start({ ...base, runId: runId ?? base.runId, startPos: p });
      if (keepPaused) {
        this.paused = true;
        this.publish();
      }
    }
  }

  setSpeed(speed: number): void {
    const src = this.source;
    if (src?.kind !== 'sim') return;
    const s = clampSpeed(speed);
    this.source = { ...src, speed: s };
    if (this.link === 'open') this.sim?.send({ cmd: 'speed', speed: s });
    this.publish();
  }

  /** Loop is a query parameter of the socket: an open replay reconnects at the current frame. */
  setLoop(loop: boolean): void {
    const src = this.source;
    if (src?.kind !== 'sim') return;
    if (this.link === 'open') {
      const pos = typeof this.msg?.pos === 'number' ? this.msg.pos : 0;
      const paused = this.paused;
      this.start({ ...src, loop, startPos: pos });
      this.paused = paused;
      this.publish();
    } else {
      this.source = { ...src, loop };
      this.publish();
    }
  }

  /** Stops everything (component unmount); the store can be started again. */
  destroy(): void {
    this.stop();
    this.setTimer(false);
  }

  // ------------------------------------------------------------ connections

  private disconnect(): void {
    if (this.retry !== null) clearTimeout(this.retry);
    this.retry = null;
    const sim = this.sim;
    const ros = this.ros;
    this.sim = null;
    this.ros = null;
    try {
      sim?.close();
    } catch {
      /* already closed */
    }
    try {
      ros?.close();
    } catch {
      /* already closed */
    }
  }

  private openSim(src: Extract<FeedSource, { kind: 'sim' }>): void {
    const g = this.gen;
    const mine = () => g === this.gen;
    try {
      this.sim = this.deps.openSim(
        { runId: src.runId, speed: src.speed, loop: src.loop },
        {
          onOpen: () => {
            if (!mine()) return;
            this.link = 'open';
            this.everOpen = true;
            if (src.startPos) this.sim?.send({ cmd: 'seek', pos: src.startPos });
            if (this.paused) this.sim?.send({ cmd: 'pause' });
            this.publish();
          },
          onMessage: (m) => mine() && this.receive(m),
          onError: () => undefined, // the close event that follows carries the reason
          onClose: (ev) => {
            if (!mine()) return;
            this.sim = null;
            if (ev.code === 1000) {
              this.link = 'ended';
              this.error = ev.reason && ev.reason !== 'Конец записи' ? ev.reason : null;
            } else {
              this.link = 'error';
              this.error = SIM_CLOSE[ev.code] ?? (ev.reason || (this.everOpen ? 'Соединение с эфиром прервано' : 'Бэкенд недоступен — эфир не открылся'));
            }
            this.paused = false;
            this.publish();
          },
        },
      );
    } catch {
      this.link = 'error';
      this.error = 'Не удалось открыть эфир';
    }
  }

  private async openRos(url: string): Promise<void> {
    const g = this.gen;
    const mine = () => g === this.gen;
    const fail = (message: string) => {
      if (!mine() || this.link === 'error') return;
      if (this.everOpen) {
        this.scheduleReconnect(url);
        return;
      }
      this.link = 'error';
      this.error = message;
      const ros = this.ros;
      this.ros = null;
      ros?.close();
      this.publish();
    };
    try {
      const sub = await this.deps.subscribeRos(url, {
        onConnection: () => {
          if (!mine()) return;
          this.link = 'open';
          this.everOpen = true;
          this.error = null;
          this.publish();
        },
        onMessage: (m) => mine() && this.receive(m),
        onError: (message) => {
          // a malformed message is not a broken link
          if (mine() && this.link === 'open' && /сообщение/i.test(message)) {
            this.error = message;
            this.publish();
            return;
          }
          fail(message);
        },
        onClose: () => fail('Нет связи с узлом ROS (rosbridge)'),
      });
      if (!mine()) {
        sub.close();
        return;
      }
      this.ros = sub;
    } catch {
      fail('Не удалось загрузить клиент ROS (roslib)');
    }
  }

  private scheduleReconnect(url: string): void {
    const ros = this.ros;
    this.ros = null;
    try {
      ros?.close();
    } catch {
      /* already closed */
    }
    if (this.retry !== null) return;
    this.link = 'connecting';
    this.publish();
    this.retry = setTimeout(() => {
      this.retry = null;
      if (this.source?.kind !== 'ros' || this.link !== 'connecting') return;
      this.gen += 1;
      void this.openRos(url);
    }, RECONNECT_MS);
  }

  private receive(raw: unknown): void {
    if (!isMessage(raw)) return;
    const now = this.deps.now();
    const sim = this.source?.kind === 'sim';
    const t = typeof raw.t === 'number' && Number.isFinite(raw.t) ? raw.t * 1000 : null;
    const at = sim && t !== null ? t : now;
    const prev = this.samples.length ? this.samples[this.samples.length - 1].at : null;
    // a seek or a loop restart jumps the recording clock: the rolling window starts over
    if (prev !== null && (at < prev - 1 || at > prev + 5000)) this.samples = [];
    this.samples.push(sampleOf(raw, at));
    this.samples = trimSamples(this.samples, at);
    this.msg = raw;
    this.lastAt = now;
    this.count += 1;
    if (this.link === 'connecting') this.link = 'open';
  }

  // ------------------------------------------------------------ snapshots

  private active(): boolean {
    return this.link === 'connecting' || this.link === 'open';
  }

  private setTimer(on: boolean): void {
    if (on && this.timer === null) this.timer = setInterval(() => this.publish(), TICK_MS);
    else if (!on && this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  private compute(): FeedSnapshot {
    const now = this.deps.now();
    const sim = this.source?.kind === 'sim';
    if (!sim) this.samples = trimSamples(this.samples, now);
    const timeNow = sim ? (this.samples.length ? this.samples[this.samples.length - 1].at : 0) : now;
    return {
      link: this.link,
      view: liveView(this.link, this.lastAt, now, this.paused),
      error: this.error,
      msg: this.msg,
      age: this.lastAt === null ? null : Math.max(0, now - this.lastAt),
      count: this.count,
      samples: this.samples.slice(),
      timeNow,
      paused: this.paused,
      reconnecting: this.link === 'connecting' && this.everOpen,
      source: this.source,
    };
  }

  private publish(): void {
    this.setTimer(this.active());
    this.snap = this.compute();
    this.listeners.forEach((l) => l());
  }
}

/** One store per page; closed when the page unmounts. */
export function useLiveFeed(): [FeedSnapshot, LiveFeedStore] {
  const store = useMemo(() => new LiveFeedStore(), []);
  useEffect(() => () => store.destroy(), [store]);
  const snap = useSyncExternalStore(store.subscribe, store.getSnapshot);
  return [snap, store];
}
