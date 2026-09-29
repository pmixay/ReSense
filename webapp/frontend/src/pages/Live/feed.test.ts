import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { RosStatusHandlers } from '../../api/rosbridge';
import type { LiveHandlers, LiveSimParams } from '../../api/ws';
import { LiveFeedStore, RECONNECT_MS, SEEK_SKIP_MAX, TICK_MS } from './feed';

/** A store with a fake socket / rosbridge and a hand-driven clock. */
function setup() {
  let clock = 1000;
  const sims: { params: LiveSimParams; h: LiveHandlers; send: ReturnType<typeof vi.fn>; close: ReturnType<typeof vi.fn> }[] = [];
  const ros: { url: string; h: RosStatusHandlers; close: ReturnType<typeof vi.fn> }[] = [];
  const store = new LiveFeedStore({
    now: () => clock,
    openSim: (params, h) => {
      const s = { params, h, send: vi.fn(), close: vi.fn() };
      sims.push(s);
      return { send: s.send, close: s.close, socket: {} as WebSocket };
    },
    subscribeRos: async (url, h) => {
      const r = { url, h, close: vi.fn() };
      ros.push(r);
      return { close: r.close };
    },
  });
  const tick = (ms: number) => {
    clock += ms;
    vi.advanceTimersByTime(ms);
  };
  const frame = (over: Record<string, unknown> = {}) => ({ decision: 'GO', snapshot_kind: 'frame', node: { fps: 10, latency_ms: 20, frames: 1, dropped_frames: 0 }, ...over });
  return { store, sims, ros, tick, frame, setClock: (v: number) => (clock = v) };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe('LiveFeedStore — simulation', () => {
  it('goes connecting → waiting → live, then stale after 0,5 s without a message', () => {
    const { store, sims, tick, frame } = setup();
    store.start({ kind: 'sim', runId: 'r1', speed: 2, loop: true });
    expect(store.getSnapshot().view).toBe('connecting');
    expect(sims[0].params).toEqual({ runId: 'r1', speed: 2, loop: true });

    sims[0].h.onOpen?.();
    expect(store.getSnapshot().view).toBe('waiting');

    sims[0].h.onMessage(frame({ decision: 'STOP', t: 0.1, pos: 1, nearest_distance: 55.2 }) as never);
    tick(TICK_MS);
    let snap = store.getSnapshot();
    expect(snap.view).toBe('live');
    expect(snap.msg?.decision).toBe('STOP');
    expect(snap.count).toBe(1);
    expect(snap.samples).toHaveLength(1);

    tick(600);
    snap = store.getSnapshot();
    expect(snap.view).toBe('stale');
    expect(snap.age).toBeGreaterThan(500);
    store.destroy();
  });

  it('sends pause / play / seek / speed to an open replay', () => {
    const { store, sims, frame } = setup();
    store.start({ kind: 'sim', runId: 'r1', speed: 1, loop: false, startPos: 5 });
    sims[0].h.onOpen?.();
    expect(sims[0].send).toHaveBeenCalledWith({ cmd: 'seek', pos: 5 });
    sims[0].h.onMessage(frame({ t: 0.5, pos: 5 }) as never);

    store.pause();
    expect(sims[0].send).toHaveBeenLastCalledWith({ cmd: 'pause' });
    expect(store.getSnapshot().view).toBe('paused');
    store.play();
    expect(sims[0].send).toHaveBeenLastCalledWith({ cmd: 'play' });
    store.seek(42.7);
    expect(sims[0].send).toHaveBeenLastCalledWith({ cmd: 'seek', pos: 42 });
    expect(store.getSnapshot().samples).toHaveLength(0); // the rolling window starts over
    store.setSpeed(50);
    expect(sims[0].send).toHaveBeenLastCalledWith({ cmd: 'speed', speed: 10 });
    store.destroy();
  });

  it('reconnects at the current frame when loop changes', () => {
    const { store, sims, frame } = setup();
    store.start({ kind: 'sim', runId: 'r1', speed: 1, loop: false });
    sims[0].h.onOpen?.();
    sims[0].h.onMessage(frame({ t: 3, pos: 30 }) as never);
    store.setLoop(true);
    expect(sims[0].close).toHaveBeenCalled();
    expect(sims).toHaveLength(2);
    expect(sims[1].params.loop).toBe(true);
    sims[1].h.onOpen?.();
    expect(sims[1].send).toHaveBeenCalledWith({ cmd: 'seek', pos: 30 });
    store.destroy();
  });

  it('reports the backend close codes in Russian and ignores the old socket after a restart', () => {
    const { store, sims } = setup();
    store.start({ kind: 'sim', runId: 'gone', speed: 1, loop: false });
    sims[0].h.onClose?.({ code: 4404, reason: '' } as CloseEvent);
    expect(store.getSnapshot()).toMatchObject({ link: 'error', view: 'error', error: 'Прогон не найден' });

    store.start({ kind: 'sim', runId: 'r2', speed: 1, loop: false });
    sims[0].h.onClose?.({ code: 1011, reason: '' } as CloseEvent); // stale handler: no effect
    expect(store.getSnapshot().view).toBe('connecting');
    sims[1].h.onOpen?.();
    sims[1].h.onClose?.({ code: 1000, reason: 'Конец записи' } as CloseEvent);
    expect(store.getSnapshot()).toMatchObject({ link: 'ended', view: 'ended', error: null });

    store.start({ kind: 'sim', runId: 'r3', speed: 1, loop: false });
    sims[2].h.onClose?.({ code: 1006, reason: '' } as CloseEvent);
    expect(store.getSnapshot().error).toBe('Бэкенд недоступен — эфир не открылся');
    store.destroy();
  });

  it('keeps a paused replay paused when a seek lands while it reconnects (loop toggled)', () => {
    const { store, sims, frame } = setup();
    store.start({ kind: 'sim', runId: 'r1', speed: 1, loop: true });
    sims[0].h.onOpen?.();
    sims[0].h.onMessage(frame({ t: 2, pos: 20 }) as never);
    store.pause();
    store.setLoop(false); // reconnects, still paused
    expect(store.getSnapshot()).toMatchObject({ link: 'connecting', paused: true });
    store.seek(49, { runId: 'r1', speed: 1, loop: false }); // before the new socket opened
    expect(sims).toHaveLength(3);
    expect(store.getSnapshot().paused).toBe(true);
    sims[2].h.onOpen?.();
    expect(sims[2].send).toHaveBeenCalledWith({ cmd: 'seek', pos: 49 });
    expect(sims[2].send).toHaveBeenLastCalledWith({ cmd: 'pause' });
    expect(store.getSnapshot().view).toBe('paused');
    store.destroy();
  });

  it('starts a seek on an idle page with the speed and loop chosen there', () => {
    const { store, sims } = setup();
    store.seek(30, { runId: 'r7', speed: 5, loop: false });
    expect(sims).toHaveLength(1);
    expect(sims[0].params).toEqual({ runId: 'r7', speed: 5, loop: false });
    sims[0].h.onOpen?.();
    expect(sims[0].send).toHaveBeenCalledWith({ cmd: 'seek', pos: 30 });
    store.seek(3); // no target, no replay of another run: ignored for the node
    store.reset();
    store.seek(3);
    expect(sims).toHaveLength(1);
    store.destroy();
  });

  it('drops the frames sent before a seek landed (no flash of the old position)', () => {
    const { store, sims, tick, frame } = setup();
    store.start({ kind: 'sim', runId: 'r1', speed: 1, loop: true, startPos: 40 });
    sims[0].h.onOpen?.();
    sims[0].h.onMessage(frame({ decision: 'GO', t: 0, pos: 0 }) as never); // sent before the seek arrived
    tick(TICK_MS);
    expect(store.getSnapshot()).toMatchObject({ msg: null, count: 0, view: 'waiting' });
    sims[0].h.onMessage(frame({ decision: 'STOP', t: 4, pos: 40 }) as never);
    sims[0].h.onMessage(frame({ decision: 'STOP', t: 4.1, pos: 41 }) as never);
    tick(TICK_MS);
    expect(store.getSnapshot()).toMatchObject({ view: 'live', count: 2 });
    expect(store.getSnapshot().msg?.pos).toBe(41);

    store.seek(10); // an open replay: frames in flight before the jump are dropped too
    sims[0].h.onMessage(frame({ t: 4.2, pos: 42 }) as never);
    expect(store.getSnapshot().msg?.pos).toBe(41);
    sims[0].h.onMessage(frame({ t: 1, pos: 10 }) as never);
    tick(TICK_MS);
    expect(store.getSnapshot().msg?.pos).toBe(10);
    store.destroy();
  });

  it('gives up waiting for a seek that never lands after a bounded number of frames', () => {
    const { store, sims, tick, frame } = setup();
    store.start({ kind: 'sim', runId: 'r1', speed: 10, loop: true, startPos: 999 });
    sims[0].h.onOpen?.();
    for (let i = 0; i <= SEEK_SKIP_MAX; i += 1) sims[0].h.onMessage(frame({ t: i / 10, pos: i }) as never);
    tick(TICK_MS);
    expect(store.getSnapshot().count).toBe(1);
    store.destroy();
  });

  it('reset forgets the frames of the previous source', () => {
    const { store, sims, frame } = setup();
    store.start({ kind: 'sim', runId: 'r1', speed: 1, loop: false });
    sims[0].h.onOpen?.();
    sims[0].h.onMessage(frame({ decision: 'STOP', t: 1, pos: 10 }) as never);
    store.reset();
    const snap = store.getSnapshot();
    expect(sims[0].close).toHaveBeenCalled();
    expect(snap).toMatchObject({ link: 'idle', view: 'idle', msg: null, age: null, count: 0, source: null });
    expect(snap.samples).toHaveLength(0);
    store.destroy();
  });

  it('stop keeps the last message on screen but is no longer live', () => {
    const { store, sims, frame } = setup();
    store.start({ kind: 'sim', runId: 'r1', speed: 1, loop: false });
    sims[0].h.onOpen?.();
    sims[0].h.onMessage(frame({ decision: 'CAUTION', t: 1 }) as never);
    store.stop();
    const snap = store.getSnapshot();
    expect(sims[0].close).toHaveBeenCalled();
    expect(snap.view).toBe('idle');
    expect(snap.msg?.decision).toBe('CAUTION');
    store.destroy();
  });
});

describe('LiveFeedStore — ROS node', () => {
  it('connects, receives, and retries every 2 s after an established link drops', async () => {
    const { store, ros, tick, frame } = setup();
    store.start({ kind: 'ros', url: 'ws://node:9090' });
    await vi.waitFor(() => expect(ros).toHaveLength(1));
    expect(ros[0].url).toBe('ws://node:9090');
    ros[0].h.onConnection?.();
    ros[0].h.onMessage(frame() as never);
    tick(TICK_MS);
    expect(store.getSnapshot().view).toBe('live');

    ros[0].h.onClose?.();
    let snap = store.getSnapshot();
    expect(snap.link).toBe('connecting');
    expect(snap.reconnecting).toBe(true);
    expect(ros[0].close).toHaveBeenCalled();

    tick(RECONNECT_MS);
    await vi.waitFor(() => expect(ros).toHaveLength(2));
    ros[1].h.onConnection?.();
    snap = store.getSnapshot();
    expect(snap.link).toBe('open');
    expect(snap.reconnecting).toBe(false);
    store.destroy();
  });

  it('shows an error when the first connection fails, and keeps a malformed message from breaking the link', async () => {
    const { store, ros } = setup();
    store.start({ kind: 'ros', url: 'ws://nowhere:9090' });
    await vi.waitFor(() => expect(ros).toHaveLength(1));
    ros[0].h.onError?.('Нет связи с узлом ROS (rosbridge)');
    expect(store.getSnapshot()).toMatchObject({ link: 'error', error: 'Нет связи с узлом ROS (rosbridge)' });

    store.start({ kind: 'ros', url: 'ws://node:9090' });
    await vi.waitFor(() => expect(ros).toHaveLength(2));
    ros[1].h.onConnection?.();
    ros[1].h.onError?.('Некорректное сообщение узла');
    expect(store.getSnapshot()).toMatchObject({ link: 'open', error: 'Некорректное сообщение узла' });
    store.destroy();
  });

  it('uses the receive time for the node (its messages carry no recording time)', async () => {
    const { store, ros, tick, frame } = setup();
    store.start({ kind: 'ros', url: 'ws://node:9090' });
    await vi.waitFor(() => expect(ros).toHaveLength(1));
    ros[0].h.onConnection?.();
    for (let i = 0; i < 5; i += 1) {
      ros[0].h.onMessage(frame({ decision: i === 4 ? 'STOP' : 'GO' }) as never);
      tick(TICK_MS);
    }
    const snap = store.getSnapshot();
    expect(snap.samples.map((s) => s.d)).toEqual(['GO', 'GO', 'GO', 'GO', 'STOP']);
    expect(snap.samples[1].at - snap.samples[0].at).toBe(TICK_MS);
    expect(snap.timeNow).toBeGreaterThanOrEqual(snap.samples[4].at);
    store.destroy();
  });
});
