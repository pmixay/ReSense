// The existing steel backdrop around a flush, rounded-rectangle 3D window.
// The glass has no bezel, rim, outline or raised surround.
import { memo } from 'react';

const WINDOW_PATH =
  'M52 76 H1548 Q1572 76 1572 100 V540 Q1572 564 1548 564 H52 Q28 564 28 540 V100 Q28 76 52 76 Z';

export const CabFrame = memo(function CabFrame({ stop, className }: { stop: boolean; className?: string }) {
  return (
    <svg className={className} viewBox="0 0 1600 900" width="1600" height="900" aria-hidden>
      <defs>
        <clipPath id="cab-outside-window">
          <path clipRule="evenodd" d={`M0 0 H1600 V900 H0 Z ${WINDOW_PATH}`} />
        </clipPath>
        <linearGradient id="cab-ceiling" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8895A2" />
          <stop offset=".09" stopColor="#B5BFC9" />
          <stop offset=".3" stopColor="#C7CFD7" />
          <stop offset="1" stopColor="#929FAB" />
        </linearGradient>
        <linearGradient id="cab-walls" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#1F2A35" stopOpacity=".45" />
          <stop offset=".035" stopColor="#1F2A35" stopOpacity="0" />
          <stop offset=".965" stopColor="#1F2A35" stopOpacity="0" />
          <stop offset="1" stopColor="#1F2A35" stopOpacity=".45" />
        </linearGradient>
        <linearGradient id="cab-console" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8996A3" />
          <stop offset=".3" stopColor="#BBC5CF" />
          <stop offset="1" stopColor="#919DA9" />
        </linearGradient>
        <filter id="cab-ambient" x="-30%" y="-100%" width="160%" height="300%">
          <feGaussianBlur stdDeviation="28" />
        </filter>
      </defs>
      <g clipPath="url(#cab-outside-window)">
        <rect width="1600" height="900" fill="url(#cab-ceiling)" />
        <rect width="1600" height="900" fill="url(#cab-walls)" />
        <rect y="564" width="1600" height="336" fill="url(#cab-console)" />
        {stop && (
          <g fill="#FF2A3C" filter="url(#cab-ambient)">
            <ellipse cx="800" cy="40" rx="560" ry="70" fillOpacity=".2" />
            <ellipse cx="800" cy="612" rx="760" ry="34" fillOpacity=".08" />
          </g>
        )}
      </g>
    </svg>
  );
});
