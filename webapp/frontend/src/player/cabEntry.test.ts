import { describe, expect, it } from 'vitest';
import { DOOR, ENTRY_MS, SALOON, STAND, START, entryPose } from './cabEntry';
import { CAB_BULKHEAD, CAB_DOOR, CAB_EYE, CAB_HALF_WIDTH } from './cockpit';

const samples = (step = 10) => Array.from({ length: Math.floor(ENTRY_MS / step) + 1 }, (_, i) => i * step);

describe('boarding walk', () => {
  it('starts facing the open doors (the page) and ends exactly in the Player\'s seated view', () => {
    const start = entryPose(0);
    expect(start).toMatchObject({ x: START.x, y: STAND, z: START.z, yaw: Math.PI / 2, pitch: 0, roll: 0 });
    const seated = entryPose(ENTRY_MS);
    expect(seated).toEqual({ x: 0, y: 0, z: CAB_EYE, yaw: 0, pitch: 0, roll: 0 });
    expect(entryPose(ENTRY_MS + 500)).toEqual(seated);
  });

  it('turns right only, by a quarter turn, before walking off', () => {
    let previous = entryPose(0).yaw;
    for (const t of samples(5).filter(t => t <= 720)) {
      const yaw = entryPose(t).yaw;
      expect(yaw).toBeLessThanOrEqual(previous + 1e-9);
      previous = yaw;
    }
    expect(entryPose(720).yaw).toBeLessThan(0.05);
  });

  it('stays inside the car, passes through the cab door and never walks through the seat', () => {
    let crossed = false;
    for (const t of samples()) {
      const p = entryPose(t);
      expect(Math.abs(p.x)).toBeLessThan((p.z > CAB_BULKHEAD ? SALOON.halfWidth : CAB_HALF_WIDTH) - 0.3);
      if (Math.abs(p.z - CAB_BULKHEAD - 0.06) < 0.08) {
        crossed = true;
        expect(Math.abs(p.x)).toBeLessThan(CAB_DOOR.halfWidth - 0.25);
        expect(t).toBeGreaterThan(DOOR.start + DOOR.length * 0.6);
      }
      // the seat back and headrest (|x| < 0.3, 1.9 < z < 2.4) are passed beside, not through
      if (p.z > 1.9 && p.z < 2.4 && p.y > -0.3) expect(Math.abs(p.x) > 0.36 || p.y > 0.32).toBe(true);
    }
    expect(crossed).toBe(true);
  });

  it('sits down: the eye lowers from standing height to the seat, with a small landing bounce', () => {
    const before = entryPose(2700);
    expect(before.y).toBeGreaterThan(STAND - 0.1);
    const lows = samples(5).filter(t => t > 3250).map(t => entryPose(t).y);
    expect(Math.min(...lows)).toBeLessThan(-0.005);
    expect(Math.min(...lows)).toBeGreaterThan(-0.03);
    const steps = samples(5).slice(1).map(t => Math.hypot(entryPose(t).x - entryPose(t - 5).x, entryPose(t).y - entryPose(t - 5).y, entryPose(t).z - entryPose(t - 5).z));
    // no jumps: at most a brisk walking pace (5 m/s) between 5 ms samples
    expect(Math.max(...steps)).toBeLessThan(0.025);
  });
});
