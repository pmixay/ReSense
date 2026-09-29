// Inline SVG icon set: the mockup sprite (webapp/design/mockup/common.js) plus what the pages need.
// 24×24 grid, stroke = currentColor, 2 px, round caps.
import type { CSSProperties } from 'react';

const P = {
  home: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  'chevron-down': '<path d="M6 9l6 6 6-6"/>',
  'chevron-up': '<path d="M6 15l6-6 6 6"/>',
  'chevron-left': '<path d="M15 6l-6 6 6 6"/>',
  'chevron-right': '<path d="M9 6l6 6-6 6"/>',
  'arrow-right': '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
  'arrow-left': '<path d="M19 12H5"/><path d="M11 6l-6 6 6 6"/>',
  'arrow-up': '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
  'arrow-down': '<path d="M12 5v14"/><path d="M6 13l6 6 6-6"/>',
  upload: '<path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 002 2h12a2 2 0 002-2v-3"/>',
  download: '<path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M4 20h16"/>',
  play: '<path d="M8 5.5v13a1 1 0 001.5.9l10.4-6.5a1 1 0 000-1.8L9.5 4.6A1 1 0 008 5.5z" fill="currentColor" stroke="none"/>',
  pause:
    '<rect x="6" y="5" width="4" height="14" rx="1.5" fill="currentColor" stroke="none"/><rect x="14" y="5" width="4" height="14" rx="1.5" fill="currentColor" stroke="none"/>',
  'step-back': '<path d="M6 5v14"/><path d="M18 6l-8 6 8 6z" fill="currentColor"/>',
  'step-forward': '<path d="M18 5v14"/><path d="M6 6l8 6-8 6z" fill="currentColor"/>',
  'event-back': '<path d="M10.5 7l-5 5 5 5"/><path d="M17 8l4 4-4 4-4-4z" fill="currentColor"/>',
  'event-forward': '<path d="M13.5 7l5 5-5 5"/><path d="M7 8l4 4-4 4-4-4z" fill="currentColor"/>',
  loop: '<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 014-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 01-4 4H4"/>',
  fullscreen: '<path d="M4 9V4h5"/><path d="M20 9V4h-5"/><path d="M4 15v5h5"/><path d="M20 15v5h-5"/>',
  'exit-fullscreen': '<path d="M9 4v5H4"/><path d="M15 4v5h5"/><path d="M9 20v-5H4"/><path d="M15 20v-5h5"/>',
  camera:
    '<path d="M3 8a2 2 0 012-2h2l2-2h6l2 2h2a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><circle cx="12" cy="13" r="3.5"/>',
  file: '<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M14 3v5h5"/>',
  folder: '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
  zip: '<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M11 5h1M11 8h1M11 11h1"/><rect x="10" y="13" width="3" height="4" rx="1"/>',
  server:
    '<rect x="4" y="4" width="16" height="7" rx="2"/><rect x="4" y="13" width="16" height="7" rx="2"/><path d="M8 7.5h.01M8 16.5h.01"/>',
  sparkle:
    '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  cancel: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  'stop-octagon': '<path d="M8.2 3h7.6L21 8.2v7.6L15.8 21H8.2L3 15.8V8.2z"/><path d="M8 12h8" stroke-width="2.8"/>',
  warning: '<path d="M12 4l9 16H3z"/><path d="M12 10v4"/><path d="M12 17.2v.1"/>',
  'go-circle': '<circle cx="12" cy="12" r="9"/><path d="M8 12.3l2.8 2.8L16.3 9.5"/>',
  'fault-circle': '<circle cx="12" cy="12" r="9"/><path d="M6 18L18 6"/>',
  list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
  compare: '<path d="M4 7h11"/><path d="M12 3l4 4-4 4"/><path d="M20 17H9"/><path d="M12 13l-4 4 4 4"/>',
  live: '<circle cx="12" cy="12" r="2.2"/><path d="M7.8 7.8a6 6 0 000 8.4M16.2 7.8a6 6 0 010 8.4M5 5a10 10 0 000 14M19 5a10 10 0 010 14"/>',
  sliders: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  settings:
    '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.5v.1"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 014.9.7c0 1.7-2.4 2-2.4 3.6"/><path d="M12 17.2v.1"/>',
  cube: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  queue: '<rect x="3" y="4" width="18" height="5" rx="2"/><rect x="3" y="11" width="18" height="5" rx="2"/><path d="M7 20h10"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
  more: '<circle cx="5" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="19" cy="12" r="1.3" fill="currentColor"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  train: '<rect x="5" y="3" width="14" height="14" rx="4"/><path d="M5 11h14"/><path d="M8.5 14h.01M15.5 14h.01"/><path d="M8 21l2-4M16 21l-2-4"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  rails: '<path d="M8 3L6 21M16 3l2 18"/><path d="M6.8 8h10.4M6.2 14h11.6"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3"/>',
  trash: '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/>',
  'view-top': '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M12 4v16"/>',
  'view-back': '<path d="M3 17l9-10 9 10"/>',
  retry: '<path d="M20 11a8 8 0 10-2.3 5.7"/><path d="M20 4v7h-7"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>',
  chart: '<path d="M4 4v16h16"/><path d="M8 15l3.5-4 3 2.5L20 7"/>',
  bars: '<path d="M6 20V11M12 20V5M18 20v-6"/>',
  edit: '<path d="M4 20h4L19 9a2.8 2.8 0 00-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2.5"/><path d="M16 8V6a2 2 0 00-2-2H6a2 2 0 00-2 2v8a2 2 0 002 2h2"/>',
  external: '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v4a2 2 0 01-2 2H6a2 2 0 01-2-2V8a2 2 0 012-2h4"/>',
  tag: '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.3"/>',
  ruler: '<rect x="2" y="8" width="20" height="8" rx="2"/><path d="M6 8v3M10 8v4M14 8v3M18 8v4"/>',
  gauge: '<rect x="6" y="3" width="12" height="16" rx="2"/><path d="M4 21h16"/><path d="M9 21v-2M15 21v-2"/>',
  link: '<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
  wifi: '<path d="M2 9a15 15 0 0120 0"/><path d="M5.5 12.5a10 10 0 0113 0"/><path d="M9 16a5 5 0 016 0"/><path d="M12 19.5v.1"/>',
  'wifi-off': '<path d="M3 3l18 18"/><path d="M8.5 16.4a5 5 0 016.6-.3"/><path d="M5.5 12.5a10 10 0 014.3-2.3"/><path d="M2 9a15 15 0 014.4-2.9"/><path d="M12 19.5v.1"/>',
  database: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.5"/><path d="M4.5 5.5v13c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-13"/><path d="M4.5 12c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5"/>',
} as const;

export type IconName = keyof typeof P;
export const ICON_NAMES = Object.keys(P) as IconName[];

export interface IconProps {
  name: IconName;
  /** px; default 20 (mockup: 16 small, 20 default, 24 large, 34 xl) */
  size?: number;
  strokeWidth?: number;
  className?: string;
  style?: CSSProperties;
  /** accessible name; icons are decorative (aria-hidden) without it */
  title?: string;
}

const escapeXml = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export function Icon({ name, size = 20, strokeWidth, className, style, title }: IconProps) {
  const inner = (title ? `<title>${escapeXml(title)}</title>` : '') + P[name];
  return (
    <svg
      className={className}
      style={{ flex: 'none', ...style }}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth ?? 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
      focusable="false"
      dangerouslySetInnerHTML={{ __html: inner }}
    />
  );
}
