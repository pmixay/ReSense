// «Схема пути»: a schematic top view of 0–200 m ahead (across the track stretched ×18) on a canvas —
// the tunnel walls as a density of the cloud's points, the rails, the envelope green up to the
// obstacle (dashed beyond the verified part), the visibility limit, the train and the obstacle.
import { useEffect, useMemo, useRef } from 'react';
import type { DecodedCloud } from '../../api/cloud';
import { FLAG_CORRIDOR } from '../../api/cloud';
import type { FrameResultDict } from '../../api/types';
import { fmtNum } from '../../lib/format';
import { floorZ, type TrackModelDict } from '../../lib/track';

const MW = 292;
const MH = 180;
const X0 = 30;
const X1 = MW - 22;
const CY = 94;
const K = 18;
const RANGE = 200;
const BIN_X = 2; // m
const BIN_Y = 0.25; // m
const NX = RANGE / BIN_X + 1;
const NY = 40; // ±5 m

const X = (x: number): number => X0 + (Math.min(RANGE, Math.max(0, x)) / RANGE) * (X1 - X0);

/** Point density → opacity (0,26 for a single point … 0,8), in a few shades so a redraw is a few fills. */
const ALPHA_LEVELS = 8;
const densityAlpha = (n: number): number => Math.min(0.8, 0.26 + Math.log2(n) / 9);
const alphaLevel = (n: number): number => Math.min(ALPHA_LEVELS - 1, Math.floor(((densityAlpha(n) - 0.26) / (0.8 - 0.26)) * ALPHA_LEVELS));
const LEVEL_ALPHA = Array.from({ length: ALPHA_LEVELS }, (_, i) => 0.26 + ((i + 0.5) / ALPHA_LEVELS) * (0.8 - 0.26));

/** Wall density bins of a cloud: counts per (2 m along, 0.25 m across) of points above the bed. */
export function wallBins(cloud: DecodedCloud, track: TrackModelDict): Uint16Array {
  const bins = new Uint16Array(NX * NY);
  const p = cloud.positions;
  const f = cloud.flags;
  const c = track.center;
  for (let i = 0; i < cloud.n; i += 1) {
    const x = p[i * 3];
    if (x < 0 || x > RANGE || f[i] & FLAG_CORRIDOR) continue;
    const z = p[i * 3 + 2];
    if (z - floorZ(track, x) < 0.6) continue;
    const bx = Math.round(x / BIN_X);
    const by = Math.round((p[i * 3 + 1] - c) / BIN_Y) + NY / 2;
    if (by < 0 || by >= NY) continue;
    const k = bx * NY + by;
    if (bins[k] < 65535) bins[k] += 1;
  }
  return bins;
}

export function MiniMap({ frame, cloud, pixelRatio }: { frame: FrameResultDict | null; cloud: DecodedCloud | null; pixelRatio: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const track = frame?.track ?? null;
  const bins = useMemo(() => (cloud && track ? wallBins(cloud, track) : null), [cloud, track]);

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const pr = Math.min(3, Math.max(1, pixelRatio));
    cv.width = Math.round(MW * pr);
    cv.height = Math.round(MH * pr);
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(pr, 0, 0, pr, 0, 0);
    ctx.clearRect(0, 0, MW, MH);
    const C = track?.center ?? 0;
    const Y = (y: number) => CY - (y - C) * K;

    // tunnel walls from the real points: the density as ALPHA_LEVELS shades, one path per shade
    if (bins) {
      ctx.fillStyle = '#5AB4F5';
      for (let level = 0; level < ALPHA_LEVELS; level += 1) {
        ctx.beginPath();
        let any = false;
        for (let bx = 0; bx < NX; bx += 1) {
          for (let by = 0; by < NY; by += 1) {
            const n = bins[bx * NY + by];
            if (!n || alphaLevel(n) !== level) continue;
            const yy = CY - (by - NY / 2) * BIN_Y * K - 2;
            if (yy < 34 || yy > MH - 34) continue;
            ctx.roundRect(X(bx * BIN_X), yy, 2.4, 4, 1.2);
            any = true;
          }
        }
        if (!any) continue;
        ctx.globalAlpha = LEVEL_ALPHA[level];
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    const vis = typeof frame?.health?.visibility === 'number' ? Math.min(RANGE, frame.health.visibility) : null;
    const railEnd = vis ?? RANGE;
    // rails
    ctx.strokeStyle = 'rgba(221,233,255,0.7)';
    ctx.lineWidth = 1.3;
    for (const s of [-0.8, 0.8]) {
      ctx.beginPath();
      ctx.moveTo(X(0), Y(C + s));
      ctx.lineTo(X(railEnd), Y(C + s));
      ctx.stroke();
    }

    // envelope: green up to the obstacle (or the verified distance), dashed beyond
    const det = frame?.obstacle ? (frame.detections?.[0] ?? null) : null;
    // FAULT: nothing is verified, no green
    const clear = typeof frame?.clear_distance === 'number' && frame.decision !== 'FAULT' ? frame.clear_distance : 0;
    const greenTo = Math.max(0, Math.min(RANGE, det ? det.center[0] - det.size[0] / 2 : clear));
    const top = Y(C + 1.05);
    const h = 2.1 * K;
    if (greenTo > 0.5) {
      const g = ctx.createLinearGradient(X(0), 0, X(greenTo), 0);
      g.addColorStop(0, 'rgba(43,212,111,0.45)');
      g.addColorStop(0.8, 'rgba(43,212,111,0.45)');
      g.addColorStop(1, det ? 'rgba(255,42,60,0.75)' : 'rgba(43,212,111,0.45)');
      ctx.fillStyle = g;
      ctx.strokeStyle = '#2BD46F';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(X(0), top, Math.max(4, X(greenTo) - X(0)), h, 7);
      ctx.fill();
      ctx.stroke();
    }
    const dashEnd = vis ?? RANGE;
    if (dashEnd > greenTo + 2) {
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = 'rgba(255,255,255,0.4)';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.roundRect(X(greenTo), top, X(dashEnd) - X(greenTo), h, 7);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // warnings: amber dots
    for (const w of frame?.warnings ?? []) {
      if (w.center[0] < 0 || w.center[0] > RANGE) continue;
      ctx.fillStyle = '#FFB300';
      ctx.beginPath();
      ctx.arc(X(w.center[0]), Math.min(MH - 34, Math.max(34, Y(w.center[1]))), 4.5, 0, Math.PI * 2);
      ctx.fill();
    }

    // visibility
    ctx.font = '800 12px Montserrat, system-ui, sans-serif';
    if (vis !== null) {
      const vx = X(vis);
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(vx, CY - 46);
      ctx.lineTo(vx, CY + 40);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#FFFFFF';
      ctx.textAlign = vis > 110 ? 'right' : 'left';
      ctx.fillText(`видимость ${fmtNum(vis, 0)} м`, vis > 110 ? vx - 6 : vx + 6, CY - 34);
    }

    // the train
    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.roundRect(4, CY - 13, X(0) - 2, 26, 8);
    ctx.fill();
    ctx.fillStyle = '#16151A';
    ctx.beginPath();
    ctx.roundRect(X(0) - 5, CY - 13, 5, 26, 2);
    ctx.fill();

    // the obstacle: a marker only
    if (det && det.center[0] <= RANGE) {
      const ox = X(det.center[0]);
      const oy = Math.min(MH - 34, Math.max(34, Y(det.center[1])));
      ctx.fillStyle = 'rgba(255,42,60,0.22)';
      ctx.beginPath();
      ctx.arc(ox, oy, 19, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#D0001B';
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(ox, oy, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.lineWidth = 2.4;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(ox - 4.5, oy);
      ctx.lineTo(ox + 4.5, oy);
      ctx.stroke();
      ctx.lineCap = 'butt';
    }

    // axis
    ctx.fillStyle = '#FFFFFF';
    for (const m of [0, 50, 100, 150, 200]) {
      ctx.textAlign = m === 200 ? 'right' : 'center';
      ctx.fillText(m === 200 ? '200 м' : String(m), m === 200 ? X(m) + 14 : X(m), MH - 13);
    }
  }, [bins, frame, track, pixelRatio]);

  return <canvas ref={ref} style={{ position: 'absolute', inset: 0, width: MW, height: MH }} aria-hidden />;
}
