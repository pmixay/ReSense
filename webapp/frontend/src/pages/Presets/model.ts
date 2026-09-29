// Pure helpers of the presets editor: full value sets from a preset's overrides and back (only what
// differs from the default is stored), the parameter groups, their balanced placement in columns,
// number formatting per step and the parameter a backend validation message names.
import type { ParamSpec, ParamValue, Preset } from '../../api/types';
import { fmtNum } from '../../lib/format';

export type Values = Record<string, ParamValue>;

export interface Draft {
  name: string;
  description: string;
  values: Values;
}

/** The id of the unsaved new preset (new or duplicated) in the drafts map. */
export const NEW_ID = '__new__';

export function defaultsOf(schema: readonly ParamSpec[]): Values {
  const out: Values = {};
  for (const s of schema) out[s.key] = s.default;
  return out;
}

/** Every parameter's value: the preset's override, else the default. */
export function valuesOf(preset: Pick<Preset, 'overrides'>, schema: readonly ParamSpec[]): Values {
  const out = defaultsOf(schema);
  for (const s of schema) if (s.key in preset.overrides) out[s.key] = coerce(s, preset.overrides[s.key]);
  return out;
}

/** A stored value in the spec's type ("0,4" and "true" from older clients included). */
export function coerce(spec: ParamSpec, v: ParamValue): ParamValue {
  if (spec.type === 'bool') return typeof v === 'string' ? v.trim().toLowerCase() === 'true' : Boolean(v);
  const n = typeof v === 'string' ? Number(v.trim().replace(',', '.')) : Number(v);
  return Number.isFinite(n) ? n : spec.default;
}

export function sameValue(a: ParamValue | undefined, b: ParamValue | undefined): boolean {
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) < 1e-9;
  return a === b;
}

/** Overrides to store: the values that differ from the defaults, in the schema's order. */
export function overridesOf(values: Values, schema: readonly ParamSpec[]): Values {
  const out: Values = {};
  for (const s of schema) if (s.key in values && !sameValue(values[s.key], s.default)) out[s.key] = values[s.key];
  return out;
}

/** Keys whose value differs from the default. */
export function changedKeys(values: Values, schema: readonly ParamSpec[]): Set<string> {
  return new Set(Object.keys(overridesOf(values, schema)));
}

export function draftOf(preset: Preset, schema: readonly ParamSpec[]): Draft {
  return { name: preset.name, description: preset.description ?? '', values: valuesOf(preset, schema) };
}

export function sameDraft(a: Draft, b: Draft, schema: readonly ParamSpec[]): boolean {
  if (a.name.trim() !== b.name.trim() || a.description.trim() !== b.description.trim()) return false;
  return schema.every((s) => sameValue(a.values[s.key], b.values[s.key]));
}

/** "Имя", "Имя 2", "Имя 3"… not taken by another preset (case-insensitive, like the backend). */
export function uniqueName(base: string, taken: readonly string[]): string {
  const used = new Set(taken.map((t) => t.trim().toLowerCase()));
  const b = base.trim().slice(0, 74) || 'Пресет';
  if (!used.has(b.toLowerCase())) return b;
  for (let i = 2; i < 1000; i += 1) {
    const c = `${b} ${i}`;
    if (!used.has(c.toLowerCase())) return c;
  }
  return `${b} ${Date.now()}`;
}

// ---------------------------------------------------------------- groups and columns

export interface Group {
  title: string;
  specs: ParamSpec[];
}

/** Groups in the schema's order (the detector's pipeline order). */
export function groupSpecs(schema: readonly ParamSpec[]): Group[] {
  const out: Group[] = [];
  for (const s of schema) {
    let g = out.find((x) => x.title === s.group);
    if (!g) {
      g = { title: s.group, specs: [] };
      out.push(g);
    }
    g.specs.push(s);
  }
  return out;
}

/** Places items of the given heights into n columns so the tallest column is as short as possible
 *  (exhaustive for up to 10 items, greedy beyond); each column keeps the items' order. Returns the
 *  item indices per column. */
export function balanceColumns(heights: readonly number[], n: number, gap = 0): number[][] {
  const k = Math.max(1, Math.min(n, heights.length || 1));
  const cols = (assign: number[]) => {
    const out: number[][] = Array.from({ length: k }, () => []);
    assign.forEach((c, i) => out[c].push(i));
    return out;
  };
  const tallest = (assign: number[]) => {
    const h = new Array(k).fill(0);
    const cnt = new Array(k).fill(0);
    assign.forEach((c, i) => {
      h[c] += heights[i];
      cnt[c] += 1;
    });
    return Math.max(...h.map((v, c) => v + Math.max(0, cnt[c] - 1) * gap));
  };
  if (heights.length <= 10) {
    let best: number[] | null = null;
    let bestH = Infinity;
    const cur = new Array(heights.length).fill(0);
    const total = k ** heights.length;
    for (let code = 0; code < total; code += 1) {
      let x = code;
      for (let i = heights.length - 1; i >= 0; i -= 1) {
        cur[i] = x % k;
        x = Math.floor(x / k);
      }
      // every column used when there are enough items; on a tie the first assignment found wins
      // (item 0 is the most significant digit: earlier items stay in earlier columns)
      if (heights.length >= k && new Set(cur).size < k) continue;
      const h = tallest(cur);
      if (h < bestH - 1e-9) {
        bestH = h;
        best = cur.slice();
      }
    }
    return cols(best ?? cur.map(() => 0));
  }
  const h = new Array(k).fill(0);
  const assign = heights.map((v) => {
    const c = h.indexOf(Math.min(...h));
    h[c] += v + gap;
    return c;
  });
  return cols(assign);
}

// ---------------------------------------------------------------- numbers

/** Decimals a step needs: 0.05 → 2, 0.5 → 1, 10 → 0. */
export function digitsOf(step: number | undefined): number {
  if (!step || !Number.isFinite(step)) return 0;
  const s = String(step);
  if (s.includes('e-')) return Number(s.split('e-')[1]);
  return s.includes('.') ? s.split('.')[1].length : 0;
}

/** "0,5 с", "20 000 шт", "да" / "нет", "0,35" (no unit). */
export function fmtValue(spec: ParamSpec, v: ParamValue | undefined): string {
  if (spec.type === 'bool') return v ? 'да' : 'нет';
  const n = typeof v === 'number' ? v : Number(v);
  const s = fmtNum(n, spec.type === 'int' ? 0 : digitsOf(spec.step));
  return spec.unit ? `${s} ${spec.unit}` : s;
}

/** "0–2 с" */
export function fmtRange(spec: ParamSpec): string {
  if (spec.type === 'bool' || spec.min === undefined || spec.max === undefined) return '';
  const d = spec.type === 'int' ? 0 : digitsOf(spec.step);
  const r = `${fmtNum(spec.min, d)}–${fmtNum(spec.max, d)}`;
  return spec.unit ? `${r} ${spec.unit}` : r;
}

/** The parameter a backend 422 message names: «Метка» (section.field): … → "section.field". */
export function paramOfError(message: string, keys: readonly string[]): string | null {
  const m = /\(([a-z_]+\.[a-z_0-9]+)\)/i.exec(message);
  if (m && keys.includes(m[1])) return m[1];
  const q = /«([a-z_]+\.[a-z_0-9]+)»/i.exec(message);
  if (q && keys.includes(q[1])) return q[1];
  return null;
}

/** A backend message about the preset's name (blank, too long, taken). */
export function isNameError(message: string): boolean {
  return /назван/i.test(message);
}
