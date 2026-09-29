// Site map: pages, the three nav groups of the top bar, the metro line and the «Система» branch.
import type { IconName } from '../components/Icon/Icon';

export type PageKey = 'overview' | 'upload' | 'queue' | 'runs' | 'player' | 'compare' | 'live' | 'presets' | 'about';

export interface NavPage {
  key: PageKey;
  path: string;
  label: string;
  icon: IconName;
  /** nav group number (0 = Главная) */
  group: 0 | 1 | 2 | 3;
}

export const PAGES: Record<PageKey, NavPage> = {
  overview: { key: 'overview', path: '/', label: 'Главная', icon: 'home', group: 0 },
  upload: { key: 'upload', path: '/upload', label: 'Загрузка', icon: 'upload', group: 1 },
  queue: { key: 'queue', path: '/queue', label: 'Очередь', icon: 'queue', group: 1 },
  runs: { key: 'runs', path: '/runs', label: 'Прогоны', icon: 'list', group: 2 },
  player: { key: 'player', path: '/player', label: 'Плеер', icon: 'cube', group: 2 },
  compare: { key: 'compare', path: '/compare', label: 'Сравнение', icon: 'compare', group: 2 },
  live: { key: 'live', path: '/live', label: 'Прямой эфир', icon: 'live', group: 3 },
  presets: { key: 'presets', path: '/presets', label: 'Параметры', icon: 'sliders', group: 3 },
  about: { key: 'about', path: '/about', label: 'О системе', icon: 'info', group: 3 },
};

export interface NavGroup {
  n: 1 | 2 | 3;
  label: string;
  pages: PageKey[];
}

export const GROUPS: NavGroup[] = [
  { n: 1, label: 'Данные', pages: ['upload', 'queue'] },
  { n: 2, label: 'Анализ', pages: ['runs', 'player', 'compare'] },
  { n: 3, label: 'Система', pages: ['live', 'presets', 'about'] },
];

/** The metro line (breadcrumb) of the work flow. */
export const LINE: PageKey[] = ['overview', 'upload', 'queue', 'runs', 'player', 'compare'];
/** Pages off the line: drawn as a short branch of group 3. */
export const BRANCH: PageKey[] = ['live', 'presets', 'about'];

/** The page a pathname belongs to ('/runs/abc' → 'runs'); null for unknown paths. */
export function pageOfPath(pathname: string): PageKey | null {
  const p = pathname.replace(/\/+$/, '') || '/';
  if (p === '/') return 'overview';
  const first = '/' + p.split('/')[1];
  const hit = (Object.values(PAGES) as NavPage[]).find((pg) => pg.path === first);
  return hit ? hit.key : null;
}
