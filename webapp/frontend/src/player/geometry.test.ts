import { describe, expect, it } from 'vitest';
import { ENVELOPE_PROFILE, centerY, defaultTrackModel, railZ, type TrackModelDict } from '../lib/track';
import {
  ENV_X1,
  KIND_EDGE,
  KIND_FLOOR,
  KIND_PLAIN,
  KIND_PORTAL,
  NO_OBSTACLE,
  PORTAL_FIRST,
  PORTAL_OFFSETS,
  PORTAL_STEP,
  allocVertices,
  cameraPose,
  closeUpPose,
  envelopeSpan,
  fillPortal,
  fillTrackLines,
  fillTrackMesh,
  portalCapacity,
  portalVisible,
  trackLineCapacity,
  trackMeshCapacity,
  trackMeshIndex,
} from './geometry';

/** A curved, sloped track (like a real result) to check the sweep follows the model. */
const curved: TrackModelDict = {
  floor_coef: [-4e-5, 0.004, -1.5],
  floor_range: [4, 80],
  center: -0.12,
  yaw: 0.002,
  curvature: 2e-4,
  rail_offset: 0.17,
  axis_valid: 180,
};

const vertex = (b: ReturnType<typeof allocVertices>, i: number) => ({
  x: b.pos[i * 3],
  y: b.pos[i * 3 + 1],
  z: b.pos[i * 3 + 2],
  a: b.col[i * 4 + 3],
  kind: b.kind[i],
});

describe('track lines', () => {
  it('fill exactly the preallocated capacity (no reallocation per frame)', () => {
    const b = allocVertices(trackLineCapacity());
    fillTrackLines(b, curved);
    expect(b.count).toBe(b.capacity);
    // refilling does not grow
    fillTrackLines(b, defaultTrackModel());
    expect(b.count).toBe(b.capacity);
  });

  it('sweep the envelope profile along the track axis and bed', () => {
    const b = allocVertices(trackLineCapacity());
    fillTrackLines(b, curved);
    const kinds = new Set<number>();
    for (let i = 0; i < b.count; i += 1) {
      const v = vertex(b, i);
      kinds.add(v.kind);
      if (v.kind !== KIND_EDGE) continue;
      const dy = v.y - centerY(curved, v.x);
      const h = v.z - railZ(curved, v.x);
      // every edge vertex is one of the profile's corners at its x
      expect(ENVELOPE_PROFILE.some(([py, ph]) => Math.abs(py - dy) < 1e-4 && Math.abs(ph - h) < 1e-4)).toBe(true);
      expect(v.x).toBeGreaterThanOrEqual(2);
      expect(v.x).toBeLessThanOrEqual(ENV_X1);
    }
    expect([...kinds].sort()).toEqual([KIND_EDGE, KIND_PORTAL, KIND_PLAIN].sort());
  });

  it('place portals every 10 m from 15 m', () => {
    const b = allocVertices(trackLineCapacity());
    fillTrackLines(b, curved);
    const xs = new Set<number>();
    for (let i = 0; i < b.count; i += 1) {
      const v = vertex(b, i);
      if (v.kind === KIND_PORTAL) xs.add(Math.round(v.x));
    }
    const want: number[] = [];
    for (let x = PORTAL_FIRST; x <= ENV_X1; x += PORTAL_STEP) want.push(x);
    expect([...xs].sort((a, b2) => a - b2)).toEqual(want);
  });

  it('fade the envelope near the train', () => {
    const b = allocVertices(trackLineCapacity());
    fillTrackLines(b, defaultTrackModel());
    const near = vertex(b, 0);
    let far = near;
    for (let i = 0; i < b.count; i += 1) {
      const v = vertex(b, i);
      if (v.kind === KIND_EDGE && Math.abs(v.x - 50) < 0.01) {
        far = v;
        break;
      }
    }
    expect(near.a).toBeLessThan(far.a);
  });
});

describe('envelope surfaces', () => {
  it('have a fixed index buffer for the quads and fill their capacity', () => {
    const b = allocVertices(trackMeshCapacity());
    fillTrackMesh(b, curved);
    expect(b.count).toBe(b.capacity);
    expect(b.count % 4).toBe(0);
    const idx = trackMeshIndex();
    expect(idx.length).toBe((b.count / 4) * 6);
    expect(Math.max(...idx)).toBe(b.count - 1);
    for (let i = 0; i < b.count; i += 1) expect(vertex(b, i).kind).toBe(KIND_FLOOR);
  });

  it('cover the bed and the sides but not the roof', () => {
    const b = allocVertices(trackMeshCapacity());
    fillTrackMesh(b, defaultTrackModel());
    const hs = new Set<number>();
    for (let i = 0; i < b.count; i += 1) {
      const v = vertex(b, i);
      hs.add(Math.round((v.z - railZ(defaultTrackModel(), v.x)) * 100) / 100);
    }
    expect([...hs].sort()).toEqual([0.12, 3]);
    // 3 surfaces (bed + two walls) per metre
    expect(trackMeshCapacity()).toBe(198 * 3 * 4);
  });
});

describe('obstacle portal', () => {
  it('is the profile at the obstacle, thickened by offset copies', () => {
    const b = allocVertices(portalCapacity());
    fillPortal(b, curved, 54.5, [1, 0, 0]);
    expect(b.count).toBe(ENVELOPE_PROFILE.length * PORTAL_OFFSETS.length * 2);
    for (let i = 0; i < b.count; i += 1) {
      const v = vertex(b, i);
      expect(v.x).toBe(54.5);
      expect(v.a).toBe(1);
      expect(Math.abs(v.y - centerY(curved, 54.5))).toBeLessThanOrEqual(1.05 + 0.03);
    }
  });
});

describe('envelopeSpan', () => {
  it('is green up to the obstacle, red over it, and ends at the monitored range', () => {
    const s = envelopeSpan({ center: [55, 0, 0], size: [0.4, 0.5, 1.5] }, 54.8, 190);
    expect(s.near).toBeCloseTo(55 - 0.2 - 0.15);
    expect(s.far).toBeCloseTo(55 + 0.2 + 1.2);
    expect(s.end).toBeCloseTo(s.far); // the obstacle ends the verified part
  });

  it('without an obstacle ends at min(clear_distance, axis_valid, 200)', () => {
    expect(envelopeSpan(null, 120, 150)).toEqual({ near: NO_OBSTACLE, far: NO_OBSTACLE, end: 120 });
    expect(envelopeSpan(null, 180, 150).end).toBe(150);
    expect(envelopeSpan(null, 500, 0).end).toBe(200);
    expect(envelopeSpan(null, null, null).end).toBe(200);
    expect(envelopeSpan(null, -5, 100).end).toBe(0);
  });

  it('shows portals only before the obstacle and within the monitored range', () => {
    const s = envelopeSpan({ center: [55, 0, 0], size: [0.4, 0.5, 1.5] }, 54.8, 190);
    expect(portalVisible(45, s)).toBe(true);
    expect(portalVisible(55, s)).toBe(false);
    const clear = envelopeSpan(null, 100, 200);
    expect(portalVisible(95, clear)).toBe(true);
    expect(portalVisible(105, clear)).toBe(false);
  });
});

describe('camera poses', () => {
  const t = defaultTrackModel();

  it('cab: the driver eye just behind the sensor, looking down the track with a long lens', () => {
    const p = cameraPose('cab', t, 1600 / 700);
    expect(p.pos[0]).toBeLessThan(0);
    expect(p.pos[1]).toBeCloseTo(centerY(t, 0));
    expect(p.pos[2]).toBeGreaterThan(railZ(t, 0) + 1);
    expect(p.target[0]).toBeGreaterThan(40);
    expect(p.fov).toBeGreaterThanOrEqual(22);
    expect(p.fov).toBeLessThanOrEqual(35);
  });

  it('top: straight down over the stretch from the train to past the obstacle', () => {
    const p = cameraPose('top', t, 1600 / 700, 80);
    expect(p.pos[2] - p.target[2]).toBeGreaterThan(30);
    expect(Math.abs(p.pos[0] - p.target[0])).toBeLessThan(1e-9);
    expect(p.target[0]).toBeGreaterThan(20);
    expect(p.ceil).toBeLessThan(5); // the vault is hidden
    const farther = cameraPose('top', t, 1600 / 700, 150);
    expect(farther.pos[2]).toBeGreaterThan(p.pos[2]);
  });

  it('chase: behind and above the train', () => {
    const p = cameraPose('chase', t, 1600 / 700);
    expect(p.pos[0]).toBeLessThan(-3);
    expect(p.pos[2]).toBeGreaterThan(railZ(t, 0) + 4);
    expect(p.target[0]).toBeGreaterThan(p.pos[0]);
  });

  it('close-up: in front of the object, framing its height, cropping around it', () => {
    const c = closeUpPose([54.9, -0.1, -0.7], [0.3, 0.48, 1.47], t);
    expect(c.pos[0]).toBeLessThan(54.9);
    expect(c.target[0]).toBeCloseTo(54.9);
    expect(c.crop[0]).toBeLessThan(54.9);
    expect(c.crop[1]).toBeGreaterThan(54.9);
    expect(c.crop[3]).toBeGreaterThanOrEqual(1.8);
  });
});
