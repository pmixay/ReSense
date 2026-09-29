// The interior of the future-train cab around the 3D view (webapp/design/mockup/player.html): the
// glass cut-out with its vignette, the white canopy frame, the red roof lip broken for the beacon,
// the curved console with the recess of the scrubber, the red ambient wash while STOP, and the
// 0–200 m distance line on the dash with the obstacle as its only red mark.
import { memo } from 'react';
import styles from './Player.module.css';

export const GLASS_PATH =
  'M150 110 C520 76 1080 76 1450 110 Q1522 118 1530 184 C1542 310 1542 452 1524 540 Q1512 598 1446 606 C1100 650 500 650 154 606 Q88 598 76 540 C58 452 58 310 70 184 Q78 118 150 110 Z';

/** A point of the dash line (quadratic 190,627 → 800,687 → 1410,627) at a distance 0–200 m. */
export function dashPoint(m: number): { x: number; y: number } {
  const t = Math.min(1, Math.max(0, m / 200));
  return { x: 190 + 1220 * t, y: 627 + 120 * t * (1 - t) };
}

/** The roof lip (a cubic), broken where the beacon hangs (x 664–936): a dash pattern by arc length. */
const LIP = 'M154 74 C520 40 1080 40 1446 74';
const LIP_DASH = (() => {
  const P = [
    [154, 74],
    [520, 40],
    [1080, 40],
    [1446, 74],
  ];
  const at = (t: number, i: 0 | 1) => {
    const u = 1 - t;
    return u * u * u * P[0][i] + 3 * u * u * t * P[1][i] + 3 * u * t * t * P[2][i] + t * t * t * P[3][i];
  };
  let len = 0;
  let a = 0;
  let b = 0;
  let px = at(0, 0);
  let py = at(0, 1);
  for (let k = 1; k <= 2000; k += 1) {
    const x = at(k / 2000, 0);
    const y = at(k / 2000, 1);
    len += Math.hypot(x - px, y - py);
    if (!a && x >= 664) a = len;
    if (!b && x >= 936) b = len;
    px = x;
    py = y;
  }
  return `${a.toFixed(1)} ${(b - a).toFixed(1)} ${len.toFixed(1)}`;
})();

const Interior = memo(function Interior() {
  return (
    <>
      <defs>
        <path id="cab-glass" d={GLASS_PATH} />
        <clipPath id="cab-glassClip">
          <use href="#cab-glass" />
        </clipPath>
        <clipPath id="cab-outG">
          <path clipRule="evenodd" d={`M0 0 H1600 V1000 H0 Z ${GLASS_PATH}`} />
        </clipPath>
        <linearGradient id="cab-ceilG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#D5CCC0" />
          <stop offset=".09" stopColor="#E1DAD1" />
          <stop offset=".3" stopColor="#E4DDD4" />
          <stop offset="1" stopColor="#DAD2C7" />
        </linearGradient>
        <linearGradient id="cab-wallV" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#6A5846" stopOpacity=".3" />
          <stop offset=".035" stopColor="#6A5846" stopOpacity="0" />
          <stop offset=".965" stopColor="#6A5846" stopOpacity="0" />
          <stop offset="1" stopColor="#6A5846" stopOpacity=".3" />
        </linearGradient>
        <linearGradient id="cab-dashG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FFFFFF" />
          <stop offset=".55" stopColor="#F8F6F2" />
          <stop offset="1" stopColor="#EEEAE4" />
        </linearGradient>
        <linearGradient id="cab-consG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#E4DDD4" />
          <stop offset=".3" stopColor="#E9E3DB" />
          <stop offset="1" stopColor="#DDD5CA" />
        </linearGradient>
        <linearGradient id="cab-sheen" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity=".09" />
          <stop offset=".3" stopColor="#fff" stopOpacity="0" />
          <stop offset=".64" stopColor="#fff" stopOpacity="0" />
          <stop offset=".7" stopColor="#fff" stopOpacity=".045" />
          <stop offset=".76" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="cab-lipG" gradientUnits="userSpaceOnUse" x1="154" x2="1446" y1="0" y2="0">
          <stop offset="0" stopColor="#E4000D" stopOpacity="0" />
          <stop offset=".1" stopColor="#E4000D" />
          <stop offset=".9" stopColor="#E4000D" />
          <stop offset="1" stopColor="#E4000D" stopOpacity="0" />
        </linearGradient>
        <filter id="cab-b28" x="-30%" y="-100%" width="160%" height="300%">
          <feGaussianBlur stdDeviation="28" />
        </filter>
        <filter id="cab-b18" x="-20%" y="-50%" width="140%" height="200%">
          <feGaussianBlur stdDeviation="18" />
        </filter>
        <filter id="cab-b8" x="-20%" y="-50%" width="140%" height="200%">
          <feGaussianBlur stdDeviation="8" />
        </filter>
        <filter id="cab-b4" x="-10%" y="-50%" width="120%" height="200%">
          <feGaussianBlur stdDeviation="4" />
        </filter>
      </defs>
      {/* glass: vignette, sheen, the beacon's glow, a faint reflection of the console */}
      <g clipPath="url(#cab-glassClip)">
        <use href="#cab-glass" fill="none" stroke="#000" strokeOpacity=".8" strokeWidth="70" filter="url(#cab-b18)" />
        <rect x="0" y="0" width="1600" height="700" fill="url(#cab-sheen)" />
        <path d="M120 600 C470 630 1130 630 1480 600" fill="none" stroke="#FFFFFF" strokeOpacity=".04" strokeWidth="16" filter="url(#cab-b8)" />
      </g>
      {/* the interior around the glass */}
      <g clipPath="url(#cab-outG)">
        <rect width="1600" height="1000" fill="url(#cab-ceilG)" />
        <rect width="1600" height="1000" fill="url(#cab-wallV)" />
        <use href="#cab-glass" fill="none" stroke="#3A2E22" strokeOpacity=".32" strokeWidth="96" filter="url(#cab-b8)" />
        <path fill="url(#cab-dashG)" d="M0 574 C34 578 62 590 92 606 L1508 606 C1538 590 1566 578 1600 574 L1600 640 Q800 720 0 640 Z" />
        <use href="#cab-glass" fill="none" stroke="#F8F6F3" strokeWidth="72" />
        <use href="#cab-glass" fill="none" stroke="#FFFFFF" strokeWidth="70" strokeOpacity=".9" transform="translate(0 -1.5)" />
        <use href="#cab-glass" fill="none" stroke="#E6E0D8" strokeWidth="24" />
        <use href="#cab-glass" fill="none" stroke="#DCD5CB" strokeWidth="12" />
        <path d={LIP} fill="none" stroke="url(#cab-lipG)" strokeWidth="3" strokeLinecap="round" strokeDasharray={LIP_DASH} />
        <path d="M190 627 Q800 687 1410 627" fill="none" stroke="#16151A" strokeWidth="6" strokeLinecap="round" />
        {[0, 50, 100, 150, 200].map((m) => {
          const p = dashPoint(m);
          return <circle key={m} cx={p.x} cy={p.y} r={m === 0 ? 8.5 : 6.5} fill="#fff" stroke="#16151A" strokeWidth={m === 0 ? 4.5 : 3.5} />;
        })}
        <path d="M0 646 Q800 726 1600 646" fill="none" stroke="#4A3A2A" strokeOpacity=".35" strokeWidth="10" filter="url(#cab-b4)" />
      </g>
      {/* console: a curved satin shell under the glass; tiles ride its arc */}
      <path fill="url(#cab-consG)" d="M0 640 Q800 720 1600 640 V1000 H0 Z" />
      <path d="M0 645 Q800 725 1600 645" fill="none" stroke="#4A3A2A" strokeOpacity=".22" strokeWidth="12" filter="url(#cab-b8)" />
      <path d="M0 640 Q800 720 1600 640" fill="none" stroke="#FFFFFF" strokeWidth="2" />
      <rect x="28" y="885" width="1544" height="102" rx="51" fill="#D3CABE" />
      <rect x="28" y="885" width="1544" height="102" rx="51" fill="none" stroke="#3A2E22" strokeOpacity=".25" strokeWidth="8" filter="url(#cab-b4)" clipPath="inset(0 round 51px)" />
      <path d="M79 987.5 H1521" stroke="#fff" strokeOpacity=".8" strokeWidth="1.5" />
    </>
  );
});

const Ambient = memo(function Ambient() {
  return (
    <g clipPath="url(#cab-outG)">
      <ellipse cx="800" cy="40" rx="560" ry="70" fill="#FF2A3C" fillOpacity=".2" filter="url(#cab-b28)" />
      <path d="M154 90 C520 56 1080 56 1446 90" fill="none" stroke="#FF2A3C" strokeOpacity=".12" strokeWidth="40" filter="url(#cab-b18)" />
      <ellipse cx="800" cy="664" rx="700" ry="30" fill="#FF2A3C" fillOpacity=".13" filter="url(#cab-b18)" />
      <ellipse cx="800" cy="712" rx="760" ry="34" fill="#FF2A3C" fillOpacity=".08" filter="url(#cab-b28)" />
    </g>
  );
});

const Shell = memo(function Shell({ stop, className }: { stop: boolean; className?: string }) {
  return (
    <svg className={className} viewBox="0 0 1600 1000" width="1600" height="1000" aria-hidden>
      <Interior />
      {stop && (
        <g clipPath="url(#cab-glassClip)">
          <path d="M0 110 Q800 40 1600 110" fill="none" stroke="#FF3040" strokeOpacity=".2" strokeWidth="60" filter="url(#cab-b18)" />
        </g>
      )}
      {stop && <Ambient />}
      {/* glass rim */}
      <use href="#cab-glass" fill="none" stroke="#FFFFFF" strokeWidth="6" />
      <use href="#cab-glass" fill="none" stroke="#2A2830" strokeOpacity=".6" strokeWidth="2" />
    </svg>
  );
});

/** The obstacle on the dash line: its own small SVG, so the blurred cab above never repaints at 10 Hz. */
function DashMarker({ m }: { m: number }) {
  const ob = dashPoint(m);
  const x = ob.x - 20;
  const y = ob.y - 20;
  return (
    <svg className={styles.dashMark} style={{ left: x, top: y }} width="40" height="40" viewBox="0 0 40 40" aria-hidden>
      <circle cx="20" cy="20" r="18" fill="#FF2A3C" fillOpacity=".18" />
      <circle cx="20" cy="20" r="11" fill="#D0001B" stroke="#fff" strokeWidth="3" />
      <path d="M15 20h10" stroke="#fff" strokeWidth="2.8" strokeLinecap="round" />
    </svg>
  );
}

export function CabFrame({ stop, obstacleM, className }: { stop: boolean; obstacleM: number | null; className?: string }) {
  const show = obstacleM !== null && obstacleM >= 0 && obstacleM <= 200;
  return (
    <>
      <Shell stop={stop} className={className} />
      {show && <DashMarker m={obstacleM} />}
    </>
  );
}
