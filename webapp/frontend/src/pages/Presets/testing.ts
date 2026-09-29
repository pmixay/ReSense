// Fixtures of the presets tests: a small schema shaped like GET /api/presets/schema.
import type { ParamSpec, Preset } from '../../api/types';

export const SPECS: ParamSpec[] = [
  { key: 'gauge.range_max', group: 'Габарит', label: 'Дальность контроля', help: 'Дальше не проверяется.', type: 'float', default: 250, min: 30, max: 250, step: 10, unit: 'м' },
  { key: 'cluster.eps', group: 'Кластеризация', label: 'Радиус объединения точек', help: 'Радиус.', type: 'float', default: 0.35, min: 0.1, max: 1, step: 0.05, unit: 'м' },
  { key: 'cluster.min_points', group: 'Кластеризация', label: 'Минимум точек объекта', help: 'Минимум.', type: 'int', default: 5, min: 2, max: 30, step: 1, unit: 'шт' },
  { key: 'tracking.min_hit_fraction', group: 'Трекинг', label: 'Доля кадров с объектом', help: 'Доля.', type: 'float', default: 0.6, min: 0, max: 1, step: 0.05 },
  { key: 'lowobj.enabled', group: 'Низкие объекты', label: 'Поиск низких предметов', help: 'Искать.', type: 'bool', default: true },
];

export const STANDARD: Preset = {
  id: 'standard',
  name: 'Стандарт 1.0',
  description: 'Опечатанные параметры детектора (configs/default.yaml, 27.09) — как в ноде ROS 2',
  builtin: true,
  overrides: {},
  created_at: '2026-09-27T20:55:07Z',
};
