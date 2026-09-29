import { describe, expect, it } from 'vitest';
import { BASE_HZ, MAX_TICK_S, PlaybackClock, SPEEDS, clampSpeed, snapSpeed, stepSpeed } from './clock';

describe('speed helpers', () => {
  it('clamps to 0,25…10 and falls back to 1 on garbage', () => {
    expect(clampSpeed(0.01)).toBe(0.25);
    expect(clampSpeed(50)).toBe(10);
    expect(clampSpeed(2)).toBe(2);
    expect(clampSpeed(Number.NaN)).toBe(1);
  });

  it('snaps to the nearest preset on a log scale', () => {
    expect(snapSpeed(1)).toBe(1);
    expect(snapSpeed(1.3)).toBe(1);
    expect(snapSpeed(1.5)).toBe(2);
    expect(snapSpeed(3)).toBe(2);
    expect(snapSpeed(4)).toBe(5);
    expect(snapSpeed(0.3)).toBe(0.25);
    expect(snapSpeed(100)).toBe(10);
    for (const s of SPEEDS) expect(snapSpeed(s)).toBe(s);
  });

  it('steps through the presets and stops at the ends', () => {
    expect(stepSpeed(1, 1)).toBe(2);
    expect(stepSpeed(1, -1)).toBe(0.5);
    expect(stepSpeed(10, 1)).toBe(10);
    expect(stepSpeed(0.25, -1)).toBe(0.25);
    expect(stepSpeed(3, 1)).toBe(5); // 3 snaps to 2 first
  });
});

describe('PlaybackClock', () => {
  it('advances at 10 Hz × speed and keeps the fraction to the next frame', () => {
    const c = new PlaybackClock(100);
    c.play();
    let r = c.tick(0.05);
    expect(r.steps).toBe(0);
    expect(c.pos).toBe(0);
    expect(c.frac).toBeCloseTo(0.5);
    r = c.tick(0.1);
    expect(r.steps).toBe(1);
    expect(c.pos).toBe(1);
    expect(c.frac).toBeCloseTo(0.5);
    c.setSpeed(5);
    r = c.tick(0.1);
    expect(r.steps).toBe(5);
    expect(c.pos).toBe(6);
  });

  it('does nothing while paused, for a single frame or a non-positive dt', () => {
    const c = new PlaybackClock(10);
    expect(c.tick(1).steps).toBe(0);
    c.play();
    expect(c.tick(0).steps).toBe(0);
    expect(c.tick(-1).steps).toBe(0);
    const one = new PlaybackClock(1);
    one.play();
    expect(one.playing).toBe(false);
    expect(one.tick(1).steps).toBe(0);
  });

  it('caps a long wall-clock gap (background tab) to MAX_TICK_S', () => {
    const c = new PlaybackClock(1000);
    c.play();
    const r = c.tick(10);
    expect(r.steps).toBe(Math.floor(MAX_TICK_S * BASE_HZ));
  });

  it('stops at the last frame without a loop and restarts from 0 on play', () => {
    const c = new PlaybackClock(5);
    c.seek(3);
    c.play();
    const r = c.tick(0.25);
    expect(c.pos).toBe(4);
    expect(r.ended).toBe(true);
    expect(c.playing).toBe(false);
    expect(c.frac).toBe(0);
    c.play();
    expect(c.pos).toBe(0);
    expect(c.playing).toBe(true);
  });

  it('wraps to 0 with a loop and does not carry the glide of the last frame over', () => {
    const c = new PlaybackClock(5);
    c.loop = true;
    c.seek(4);
    c.play();
    const r = c.tick(0.19);
    expect(r.steps).toBe(1);
    expect(r.ended).toBe(false);
    expect(c.pos).toBe(0);
    expect(c.frac).toBeLessThanOrEqual(0.5);
    expect(c.playing).toBe(true);
  });

  it('holds before a frame whose data has not arrived (buffering)', () => {
    const c = new PlaybackClock(100);
    c.setSpeed(2);
    c.play();
    const ready = new Set([0, 1, 2]);
    const r = c.tick(0.2, (next) => ready.has(next));
    expect(c.pos).toBe(2);
    expect(r.holding).toBe(true);
    expect(c.frac).toBeCloseTo(0.999);
    expect(c.playing).toBe(true);
    ready.add(3);
    const r2 = c.tick(0.005, (next) => ready.has(next));
    expect(r2.holding).toBe(false);
    expect(c.pos).toBe(3);
  });

  it('seeks with clamping and rounding and resets the glide', () => {
    const c = new PlaybackClock(50);
    c.play();
    c.tick(0.05);
    expect(c.seek(10.6)).toBe(11);
    expect(c.frac).toBe(0);
    expect(c.seek(-5)).toBe(0);
    expect(c.seek(999)).toBe(49);
    expect(c.seek(Number.NaN)).toBe(0);
    expect(c.step(3)).toBe(3);
    expect(c.step(-10)).toBe(0);
  });

  it('shrinks with the run and pauses when a single frame is left', () => {
    const c = new PlaybackClock(50);
    c.seek(40);
    c.setLength(20);
    expect(c.pos).toBe(19);
    c.play();
    c.setLength(1);
    expect(c.playing).toBe(false);
    expect(c.pos).toBe(0);
  });
});
