import { lazy } from 'react';
import type { PageKey } from './lib/nav';

const loaders = {
  overview: () => import('./pages/Overview'),
  upload: () => import('./pages/Upload'),
  queue: () => import('./pages/Queue'),
  runs: () => import('./pages/Runs'),
  player: () => import('./pages/Player'),
  compare: () => import('./pages/Compare'),
  live: () => import('./pages/Live'),
  presets: () => import('./pages/Presets'),
  about: () => import('./pages/About'),
};

export const sectionPages = {
  overview: lazy(loaders.overview), upload: lazy(loaders.upload), queue: lazy(loaders.queue),
  runs: lazy(loaders.runs), player: lazy(loaders.player), compare: lazy(loaders.compare),
  live: lazy(loaders.live), presets: lazy(loaders.presets), about: lazy(loaders.about),
};

export function preloadSections(pages: PageKey[]): void {
  for (const key of pages) void loaders[key]().catch(() => undefined);
}
