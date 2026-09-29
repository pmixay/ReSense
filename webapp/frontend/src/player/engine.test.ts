import { describe, expect, it } from 'vitest';
import type { DecodedCloud } from '../api/cloud';
import type { FrameResultDict } from '../api/types';
import { PlayerEngine, type EngineScene } from './engine';
import type { FramesChunk } from './frameStore';

const flush = () => new Promise((r) => setTimeout(r, 0));

const frame = (pos: number, extra: Partial<FrameResultDict> = {}): FrameResultDict =>
  ({ pos, frame: pos, t: pos / 10, decision: 'GO', detections: [], warnings: [], ego_speed: 10, ...extra }) as unknown as FrameResultDict;

const cloud = (tag: number): DecodedCloud => ({ n: tag, positions: new Float32Array(tag * 3), intensity: new Uint8Array(tag), flags: new Uint8Array(tag) });

class StubScene implements EngineScene {
  frames: (number | null)[] = [];
  clouds: (number | null)[] = [];
  drive: [number, number] = [0, 0];
  setFrame(f: FrameResultDict | null) {
    this.frames.push(f ? (f as unknown as { pos: number }).pos : null);
  }
  setCloud(c: DecodedCloud | null) {
    this.clouds.push(c ? c.n : null);
  }
  setDrive(w: number, c: number) {
    this.drive = [w, c];
  }
  render() {}
}

function setup(n: number, opts: { cloudPositions?: number[]; holdClouds?: boolean } = {}) {
  let now = 0;
  const cloudCalls: number[] = [];
  const pendingClouds = new Map<number, () => void>();
  const engine = new PlayerEngine(
    { id: 'r1', n, t: null, clouds: opts.cloudPositions ?? [] },
    {
      now: () => now,
      notifyMs: 0,
      prefetch: 5,
      fetchFrames: async (from, count): Promise<FramesChunk<FrameResultDict>> => ({
        from,
        total: n,
        frames: Array.from({ length: Math.min(count, n - from) }, (_, i) => frame(from + i)),
      }),
      fetchCloud: (pos) =>
        new Promise<DecodedCloud>((resolve) => {
          cloudCalls.push(pos);
          // cloud "tag" = pos + 1000 so tests can tell which one is on screen
          if (opts.holdClouds) pendingClouds.set(pos, () => resolve(cloud(pos + 1000)));
          else resolve(cloud(pos + 1000));
        }),
    },
  );
  return {
    engine,
    cloudCalls,
    pendingClouds,
    tick: (ms: number) => {
      now += ms;
    },
  };
}

describe('PlayerEngine', () => {
  it('loads the first chunk and shows the frame under the playhead', async () => {
    const { engine } = setup(50);
    const scene = new StubScene();
    engine.attach(scene);
    await flush();
    engine.advance(0);
    expect(engine.getSnapshot().frame).not.toBeNull();
    expect(engine.getSnapshot().framePos).toBe(0);
    expect(scene.frames.at(-1)).toBe(0);
    engine.dispose();
  });

  it('plays at 10 Hz and notifies subscribers', async () => {
    const { engine, tick } = setup(50);
    engine.attach(new StubScene());
    await flush();
    let calls = 0;
    const off = engine.subscribe(() => {
      calls += 1;
    });
    engine.play();
    for (let i = 0; i < 10; i += 1) {
      tick(100);
      engine.advance(0.1);
    }
    expect(engine.getSnapshot().pos).toBe(10);
    expect(engine.getSnapshot().playing).toBe(true);
    expect(calls).toBeGreaterThan(0);
    off();
    engine.dispose();
  });

  it('holds (buffering) before a frame whose chunk has not arrived', async () => {
    const { engine } = setup(300, {});
    engine.attach(new StubScene());
    await flush();
    engine.seek(99);
    engine.play();
    // chunk 100.. was requested by ensureAround but has not resolved yet: the playhead holds
    engine.advance(0.25);
    expect(engine.getSnapshot().pos).toBe(99);
    expect(engine.getSnapshot().buffering).toBe(true);
    await flush();
    engine.advance(0.1);
    expect(engine.getSnapshot().pos).toBeGreaterThan(99);
    expect(engine.getSnapshot().buffering).toBe(false);
    engine.dispose();
  });

  it('never waits for a cloud: the newest cloud at hand stays on screen while the right one loads', async () => {
    const { engine, pendingClouds, tick } = setup(50, { cloudPositions: Array.from({ length: 50 }, (_, i) => i), holdClouds: true });
    const scene = new StubScene();
    engine.attach(scene);
    await flush();
    pendingClouds.get(0)?.();
    await flush();
    engine.advance(0);
    expect(scene.clouds.at(-1)).toBe(1000);
    engine.play();
    for (let i = 0; i < 5; i += 1) {
      tick(100);
      engine.advance(0.1);
    }
    // the playhead moved on although no other cloud arrived
    expect(engine.getSnapshot().pos).toBe(5);
    expect(engine.getSnapshot().cloudPos).toBe(0);
    tick(400);
    engine.advance(0.001);
    expect(engine.getSnapshot().cloudLoading).toBe(true);
    // the prefetch ahead was queued behind the requests in flight
    expect(['queued', 'loading']).toContain(engine.clouds.status(6));
    // the backend answers: requests in flight first, then the queue (the cloud under the playhead first)
    for (let round = 0; round < 4 && !pendingClouds.has(5); round += 1) {
      for (const [p, resolve] of [...pendingClouds]) {
        pendingClouds.delete(p);
        resolve();
      }
      await flush();
    }
    pendingClouds.get(5)?.();
    await flush();
    engine.advance(0.001);
    expect(engine.getSnapshot().cloudPos).toBe(5);
    expect(scene.clouds.at(-1)).toBe(1005);
    expect(engine.getSnapshot().cloudLoading).toBe(false);
    engine.dispose();
  });

  it('glides the world back by v·Δt between frames (the live drive)', async () => {
    const { engine, tick } = setup(50);
    const scene = new StubScene();
    engine.attach(scene);
    await flush();
    engine.advance(0);
    engine.play();
    tick(50);
    engine.advance(0.05); // half way to the next frame at 10 m/s → 0,5 m
    const d = engine.drive();
    expect(d.world).toBeCloseTo(0.5, 5);
    engine.pause();
    expect(engine.drive().world).toBe(0);
    engine.dispose();
  });

  it('steps, seeks, changes speed and loop', async () => {
    const { engine } = setup(30);
    engine.attach(new StubScene());
    await flush();
    engine.play();
    engine.step(1);
    expect(engine.getSnapshot().playing).toBe(false);
    expect(engine.getSnapshot().pos).toBe(1);
    engine.step(-5);
    expect(engine.getSnapshot().pos).toBe(0);
    engine.seek(200);
    expect(engine.getSnapshot().pos).toBe(29);
    engine.setSpeed(7);
    expect(engine.getSnapshot().speed).toBe(7);
    engine.setSpeed(100);
    expect(engine.getSnapshot().speed).toBe(10);
    engine.setLoop(true);
    expect(engine.getSnapshot().loop).toBe(true);
    engine.dispose();
  });

  it('prefetches the clouds ahead while playing', async () => {
    const { engine, cloudCalls, tick } = setup(40, { cloudPositions: Array.from({ length: 40 }, (_, i) => i) });
    engine.attach(new StubScene());
    await flush();
    engine.play();
    tick(100);
    engine.advance(0.1);
    await flush();
    expect(cloudCalls.filter((p) => p > 1).length).toBeGreaterThanOrEqual(5);
    engine.dispose();
  });
});
