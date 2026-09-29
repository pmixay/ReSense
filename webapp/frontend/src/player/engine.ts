// The playback engine of the player: owns the clock, the per-frame results (chunks), the cloud cache
// and the animation loop that feeds the three.js scene. React reads a throttled snapshot through
// subscribe / getSnapshot (useSyncExternalStore); the scene is driven directly at 60 fps.
//
// Results are small and fetched ahead in chunks: playback holds before a frame whose result has not
// arrived (buffering). Clouds are big: playback never waits for them — the newest cloud at hand is
// shown and glided along the track, and the HUD says «загрузка облака» while the right one loads.
import { fetchRunCloud, fetchRunFrames } from '../api/hooks';
import type { DecodedCloud } from '../api/cloud';
import type { FrameResultDict } from '../api/types';
import { PlaybackClock, clampSpeed } from './clock';
import { CloudCache, PRIO_NOW } from './cloudCache';
import { FrameStore, type ChunkFetcher } from './frameStore';
import { cloudAtOrBefore, cloudsAhead, frameDt, frameMotion, prefetchStride, type Motion } from './motion';
import type { Fetcher } from './cloudCache';

/** What the scene must offer the engine (PlayerScene; a stub in tests). */
export interface EngineScene {
  setFrame(frame: FrameResultDict | null): void;
  setCloud(cloud: DecodedCloud | null, track?: FrameResultDict['track'] | null): void;
  setDrive(sWorld: number, sCloud: number): void;
  render(dt: number): void;
}

export interface EngineRun {
  id: string;
  /** processed frames */
  n: number;
  /** seconds from the first processed frame, per position (the run's series); null until loaded */
  t: readonly number[] | null;
  /** positions that have a stored cloud */
  clouds: readonly number[];
}

export interface EngineSnapshot {
  n: number;
  pos: number;
  playing: boolean;
  speed: number;
  loop: boolean;
  /** the result on screen (at pos, or the last one while buffering) */
  frame: FrameResultDict | null;
  framePos: number | null;
  buffering: boolean;
  framesError: unknown;
  /** position of the cloud on screen */
  cloudPos: number | null;
  /** the right cloud is not on screen yet (debounced) */
  cloudLoading: boolean;
  cloudError: string | null;
  motion: Motion;
  /** frames shown per second while playing */
  playFps: number | null;
}

export interface EngineOptions {
  initialPos?: number;
  speed?: number;
  loop?: boolean;
  fetchFrames?: ChunkFetcher<FrameResultDict>;
  fetchCloud?: Fetcher<DecodedCloud>;
  /** clouds kept in memory */
  cacheSize?: number;
  /** clouds fetched ahead while playing */
  prefetch?: number;
  /** min interval between React snapshots while playing (ms) */
  notifyMs?: number;
  now?: () => number;
}

const LOADING_DEBOUNCE_MS = 250;

export class PlayerEngine {
  readonly clock: PlaybackClock;
  readonly frames: FrameStore<FrameResultDict>;
  readonly clouds: CloudCache<DecodedCloud>;
  private run: EngineRun;
  private scene: EngineScene | null = null;
  private raf = 0;
  private lastTs = 0;
  private listeners = new Set<() => void>();
  private snap: EngineSnapshot;
  private dirty = true;
  private lastNotify = 0;
  private readonly notifyMs: number;
  private readonly prefetchN: number;
  private readonly now: () => number;

  private shownFramePos: number | null = null;
  private shownFrame: FrameResultDict | null = null;
  private shownCloudPos: number | null = null;
  private wantedCloud: number | null = null;
  private lagSince: number | null = null;
  private motion: Motion = { v: 0, source: null };
  private motionPos: number | null = null;
  private motionHasNext = false;
  private lastPrefetchPos = -1;
  private cloudsDirty = true;
  private buffering = false;
  // playback rate measurement
  private stepsAcc = 0;
  private rateT0 = 0;
  private playFps: number | null = null;
  /** exponential average of the render rate (debug / measurements) */
  renderFps = 0;

  constructor(run: EngineRun, opts: EngineOptions = {}) {
    this.run = run;
    this.now = opts.now ?? (() => performance.now());
    this.notifyMs = opts.notifyMs ?? 50;
    this.prefetchN = opts.prefetch ?? 20;
    this.clock = new PlaybackClock(run.n);
    this.clock.loop = !!opts.loop;
    this.clock.setSpeed(opts.speed ?? 1);
    this.clock.seek(opts.initialPos ?? 0);
    const fetchFrames: ChunkFetcher<FrameResultDict> = opts.fetchFrames ?? ((from, count, signal) => fetchRunFrames(run.id, from, count, signal));
    const fetchCloud: Fetcher<DecodedCloud> = opts.fetchCloud ?? ((pos, signal) => fetchRunCloud(run.id, pos, signal));
    this.frames = new FrameStore(fetchFrames, run.n, { onChange: this.onData });
    this.clouds = new CloudCache(fetchCloud, { capacity: opts.cacheSize ?? 60, concurrency: 4, onChange: this.onCloud });
    this.snap = this.buildSnapshot();
    this.sync();
  }

  // ---------------------------------------------------------------- React store

  subscribe = (fn: () => void): (() => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };

  getSnapshot = (): EngineSnapshot => this.snap;

  private emit(force = false): void {
    const t = this.now();
    if (!force && t - this.lastNotify < this.notifyMs) {
      this.dirty = true;
      return;
    }
    this.lastNotify = t;
    this.dirty = false;
    this.snap = this.buildSnapshot();
    for (const fn of this.listeners) fn();
  }

  private buildSnapshot(): EngineSnapshot {
    const c = this.clock;
    const lagging = this.lagSince !== null && this.now() - this.lagSince > LOADING_DEBOUNCE_MS;
    return {
      n: c.n,
      pos: c.pos,
      playing: c.playing,
      speed: c.speed,
      loop: c.loop,
      frame: this.shownFrame,
      framePos: this.shownFramePos,
      buffering: this.buffering,
      framesError: this.frames.lastError,
      cloudPos: this.shownCloudPos,
      cloudLoading: lagging,
      cloudError: this.wantedCloud !== null ? this.clouds.error(this.wantedCloud) : null,
      motion: this.motion,
      playFps: c.playing ? this.playFps : null,
    };
  }

  // ---------------------------------------------------------------- controls

  play(): void {
    this.clock.play();
    this.stepsAcc = 0;
    this.rateT0 = this.now();
    this.playFps = null;
    this.after();
  }

  pause(): void {
    this.clock.pause();
    this.after();
  }

  toggle(): void {
    if (this.clock.playing) this.pause();
    else this.play();
  }

  seek(pos: number): void {
    const p = this.clock.seek(pos);
    // prefetches far from the new playhead are useless now
    this.clouds.cancelQueued((q) => q >= p - 2 && q <= p + 40);
    this.lastPrefetchPos = -1;
    this.after();
  }

  step(delta: number): void {
    this.clock.pause();
    this.seek(this.clock.pos + delta);
  }

  setSpeed(s: number): void {
    this.clock.setSpeed(clampSpeed(s));
    this.lastPrefetchPos = -1;
    this.after();
  }

  setLoop(on: boolean): void {
    this.clock.loop = on;
    this.after();
  }

  /** A cached cloud without touching the cache order (the mini-map reads the one on screen). */
  cloudAt(pos: number | null): DecodedCloud | null {
    return pos === null ? null : (this.clouds.cache.peek(pos) ?? null);
  }

  /** Forget failed requests and fetch again (the retry button). */
  retry(): void {
    this.frames.retry();
    this.after();
  }

  private after(): void {
    this.sync();
    this.emit(true);
  }

  // ---------------------------------------------------------------- run / scene

  /** New series timing or cloud list for the same run (arrives after the engine was created). */
  updateRun(run: Partial<Omit<EngineRun, 'id'>>): void {
    this.run = { ...this.run, ...run };
    if (run.n !== undefined && run.n !== this.clock.n) {
      this.clock.setLength(run.n);
      this.frames.total = run.n;
    }
    this.cloudsDirty = true;
    this.after();
  }

  attach(scene: EngineScene): void {
    this.scene = scene;
    this.shownFramePos = null;
    this.shownCloudPos = null;
    if (!this.run.clouds.length) scene.setCloud(null);
    this.cloudsDirty = true;
    this.sync();
    if (!this.raf && typeof requestAnimationFrame !== 'undefined') {
      this.lastTs = 0;
      this.raf = requestAnimationFrame(this.loop);
    }
  }

  detach(): void {
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
    this.scene = null;
  }

  dispose(): void {
    this.detach();
    this.frames.dispose();
    this.clouds.dispose();
    this.listeners.clear();
  }

  private loop = (ts: number): void => {
    this.raf = requestAnimationFrame(this.loop);
    const dt = this.lastTs ? (ts - this.lastTs) / 1000 : 0;
    this.lastTs = ts;
    if (dt > 0) this.renderFps = this.renderFps ? this.renderFps + (1 / dt - this.renderFps) * 0.05 : 1 / dt;
    this.advance(dt);
    const scene = this.scene;
    if (!scene) return;
    const d = this.drive();
    scene.setDrive(d.world, d.cloud);
    scene.render(dt);
  };

  /** One clock step (exposed for tests): tick, fetch what the playhead needs, update the scene. */
  advance(dt: number): void {
    const wasPlaying = this.clock.playing;
    const res = this.clock.tick(dt, (next) => this.frames.has(next));
    if (res.steps) {
      this.stepsAcc += res.steps;
      this.cloudsDirty = true;
    }
    if (this.buffering !== res.holding) {
      this.buffering = res.holding;
      this.dirty = true;
    }
    const t = this.now();
    if (this.clock.playing && t - this.rateT0 >= 1000) {
      this.playFps = (this.stepsAcc * 1000) / (t - this.rateT0);
      this.stepsAcc = 0;
      this.rateT0 = t;
      this.dirty = true;
    }
    this.sync();
    if (res.steps || res.ended || wasPlaying !== this.clock.playing) this.emit(res.ended || wasPlaying !== this.clock.playing);
    else if (this.dirty) this.emit();
  }

  private onData = (): void => {
    this.cloudsDirty = true;
    this.dirty = true;
    if (!this.raf) this.after();
  };

  private onCloud = (): void => {
    this.cloudsDirty = true;
    this.dirty = true;
    if (!this.raf) this.after();
  };

  /** Fetch what the playhead needs and push new data to the scene. */
  private sync(): void {
    const pos = this.clock.pos;
    this.frames.ensureAround(pos);
    const fr = this.frames.get(pos);
    if (fr && this.shownFramePos !== pos) {
      this.shownFramePos = pos;
      this.shownFrame = fr;
      this.scene?.setFrame(fr);
      this.dirty = true;
    }
    // motion between this frame and the next (the next may arrive later)
    const fp = this.shownFramePos;
    if (this.shownFrame && fp !== null) {
      const nx = this.frames.get(fp + 1);
      if (fp !== this.motionPos || !!nx !== this.motionHasNext) {
        this.motionPos = fp;
        this.motionHasNext = !!nx;
        this.motion = frameMotion(this.shownFrame, nx, frameDt(this.run.t, fp));
      }
    }
    if (this.cloudsDirty) this.syncClouds(pos);
  }

  private syncClouds(pos: number): void {
    this.cloudsDirty = false;
    const list = this.run.clouds;
    if (!list.length) {
      this.wantedCloud = null;
      this.lagSince = null;
      return;
    }
    const want = cloudAtOrBefore(list, pos) ?? list[0];
    this.wantedCloud = want;
    this.clouds.request(want, PRIO_NOW);
    if (this.clock.playing && pos !== this.lastPrefetchPos) {
      this.lastPrefetchPos = pos;
      this.clouds.prefetch(cloudsAhead(list, pos, this.prefetchN, prefetchStride(this.clock.speed)));
    }
    let show: number | null = this.clouds.get(want) ? want : this.clouds.latestAtOrBefore(pos);
    if (show === null) show = this.shownCloudPos;
    if (show !== null && show !== this.shownCloudPos) {
      const cloud = this.clouds.get(show);
      if (cloud) {
        this.shownCloudPos = show;
        this.scene?.setCloud(cloud, this.frames.get(show)?.track ?? this.shownFrame?.track ?? null);
        this.dirty = true;
      }
    }
    const lag = this.shownCloudPos !== want;
    if (lag && this.lagSince === null) this.lagSince = this.now();
    if (!lag && this.lagSince !== null) {
      this.lagSince = null;
      this.dirty = true;
    }
    if (lag) this.dirty = true;
  }

  private tOf(pos: number): number {
    const t = this.run.t;
    return t && pos >= 0 && pos < t.length ? t[pos] : pos / 10;
  }

  /** Metres the world and the cloud on screen glide back at this instant. */
  private readonly driveOut = { world: 0, cloud: 0 };

  drive(): { world: number; cloud: number } {
    const out = this.driveOut;
    out.world = 0;
    out.cloud = 0;
    const v = this.motion.v;
    const fp = this.shownFramePos;
    if (!(v > 0) || fp === null) return out;
    const pos = this.clock.pos;
    const tNow = this.tOf(pos) + this.clock.frac * frameDt(this.run.t, pos);
    const lagW = tNow - this.tOf(fp);
    out.world = lagW >= 0 && lagW <= 1 ? v * lagW : 0;
    const cp = this.shownCloudPos;
    const lagC = cp === null ? 0 : tNow - this.tOf(cp);
    out.cloud = lagC >= 0 && lagC <= 1 ? v * lagC : out.world;
    return out;
  }
}
