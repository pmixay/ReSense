import { describe, expect, it } from 'vitest';
import {
  ENVELOPE_PROFILE,
  axisPolyline,
  centerY,
  corridorCoordinates,
  envelopeSection,
  floorZ,
  headingAt,
  inEnvelope,
  pointInPolygon,
  railZ,
  samples,
  widenedProfile,
  type TrackModelDict,
} from './track';

// Reference values computed with resense.track.TrackModel / resense.gauge (the sealed detector).
const track: TrackModelDict = {
  floor_coef: [0.00012, -0.021, -1.62],
  floor_range: [4.0, 86.0],
  center: -0.137,
  yaw: 0.0042,
  curvature: -0.00031,
  rail_offset: 0.33,
  rail_score: 0,
  axis_valid: 9999,
};
const XS = [0.0, 2.0, 4.0, 30.0, 55.6, 86.0, 120.0, 200.0];

const close = (a: number[], b: number[], eps = 1e-9) => a.forEach((v, i) => expect(v).toBeCloseTo(b[i], -Math.log10(eps)));

describe('track model', () => {
  it('floor_z: quadratic inside floor_range, linear outside', () => {
    close(XS.map((x) => floorZ(track, x)), [-1.62192, -1.662, -1.70208, -2.142, -2.4166368, -2.53848, -2.55072, -2.57952]);
  });
  it('floor_z of a cubic profile', () => {
    const t3 = { ...track, floor_coef: [1e-6, 0.00012, -0.021, -1.62], center: 0, yaw: 0, curvature: 0 };
    close(XS.map((x) => floorZ(t3, x)), [-1.622048, -1.662032, -1.702016, -2.115, -2.244757184, -1.902424, -1.160272, 0.585968]);
  });
  it('center_y', () => {
    close(XS.map((x) => centerY(track, x)), [-0.137, -0.129219951, -0.122679901, -0.150499259, -0.382639427, -0.922177876, -1.864997036, -5.496995061]);
  });
  it('rail_z', () => {
    close(XS.map((x) => railZ(track, x)), [-1.29192, -1.332, -1.37208, -1.812, -2.0866368, -2.20848, -2.22072, -2.24952]);
  });
  it('corridor coordinates', () => {
    const pts = [[55.6, 0.3, 0.5], [30.0, -1.4, -1.0], [120.0, 2.0, 1.2], [10.0, 0.0, -1.5]];
    const r = pts.map((p) => corridorCoordinates(track, p));
    close(r.map((v) => v[0]), [0.682639427, -1.249500741, 3.864997036, 0.110499753]);
    close(r.map((v) => v[1]), [2.5866368, 0.812, 3.42072, -0.012]);
  });
  it('heading follows the curvature', () => {
    expect(headingAt(track, 0)).toBeCloseTo(0.0042, 9);
    expect(headingAt(track, 100)).toBeCloseTo(Math.atan(Math.tan(0.0042) - 0.031), 9);
  });
});

describe('envelope', () => {
  it('matches resense.gauge.point_in_polygon (even-odd, edges)', () => {
    const q: [number, number][] = [[0, 1], [1.05, 1], [1, 0.1], [-1.2, 2], [0.5, 3.1], [0, 0.12]];
    expect(q.map(([x, y]) => pointInPolygon(x, y, ENVELOPE_PROFILE))).toEqual([true, false, false, false, false, true]);
  });
  it('widens the outer edges by the warning margin', () => {
    expect(widenedProfile()).toEqual([[-1.4, 0.12], [1.4, 0.12], [1.4, 3.0], [-1.4, 3.0]]);
  });
  it('classifies vehicle-frame points', () => {
    const [x, dy, h] = [40, 0.2, 1.0];
    const p = [x, centerY(track, x) + dy, railZ(track, x) + h];
    expect(inEnvelope(track, p)).toBe(true);
    expect(inEnvelope(track, [x, p[1] + 1.2, p[2]])).toBe(false);
    expect(inEnvelope(track, [2, centerY(track, 2), railZ(track, 2) + 1])).toBe(false); // before range_min
  });
  it('sweeps sections along the axis', () => {
    const sec = envelopeSection(track, 50);
    expect(sec).toHaveLength(4);
    sec.forEach((v, i) => {
      const [dy, h] = corridorCoordinates(track, v);
      expect(dy).toBeCloseTo(ENVELOPE_PROFILE[i][0], 9);
      expect(h).toBeCloseTo(ENVELOPE_PROFILE[i][1], 9);
    });
    const axis = axisPolyline(track, 3, 13, 5);
    expect(axis.map((v) => v[0])).toEqual([3, 8, 13]);
    expect(samples(0, 10, 4)).toEqual([0, 4, 8, 10]);
  });
});
