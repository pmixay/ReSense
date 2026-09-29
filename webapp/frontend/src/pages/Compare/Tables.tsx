// The KPI comparison table (best value per row in an ink pill) and «Что изменилось» — the parameters
// that differ between runs of one recording made with different presets.
import type { ParamSpec, RunDetail } from '../../api/types';
import { Help } from '../../components';
import { METRICS, baseName, bestIndices, diffOverrides, fmtParam, lineSwatch } from '../Runs/common/analysis';
import type { Compared } from './data';
import styles from './Compare.module.css';

/** Whether the compared runs used more than one preset (then run labels name the preset too). */
export const mixedPresets = (items: readonly Compared[]): boolean => new Set(items.map((c) => c.run?.preset.id).filter(Boolean)).size > 1;

/** A compared run's label: its line key (as in the chart), the name, and the preset when they differ. */
export function RunLabel({ c, showPreset, className }: { c: Compared; showPreset: boolean; className?: string }) {
  return (
    <span className={[styles.runLabel, className].filter(Boolean).join(' ')} title={c.run?.name}>
      <span className={styles.clamp}>
        {/* let long file-like names break after "_" */}
        {c.run ? baseName(c.run).replace(/_/g, '_\u200b') : '…'}
      </span>
      {showPreset && c.run && <span className={styles.runPreset}>{c.run.preset.name}</span>}
    </span>
  );
}

function RunHead({ c, showPreset }: { c: Compared; showPreset: boolean }) {
  return (
    <th scope="col" className={styles.runTh}>
      <i className={styles.keyBar} style={{ background: lineSwatch(c.slot) }} aria-hidden />
      <RunLabel c={c} showPreset={showPreset} />
    </th>
  );
}

export function KpiTable({ items }: { items: readonly Compared[] }) {
  const showPreset = mixedPresets(items);
  return (
    <table className={styles.kt}>
      <thead>
        <tr>
          <th scope="col">
            <span className="sr-only">Показатель</span>
          </th>
          {items.map((c) => (
            <RunHead key={c.id} c={c} showPreset={showPreset} />
          ))}
        </tr>
      </thead>
      <tbody>
        {METRICS.map((m) => {
          const values = items.map((c) => (c.run ? m.value(c.run) : null));
          const best = bestIndices(values, m.better);
          return (
            <tr key={m.key}>
              <th scope="row">
                <span className={styles.rowHead}>
                  {m.label}
                  <Help placement="right" width={240}>
                    {m.help}
                    {m.better && <b>{m.better === 'max' ? ' Лучше — больше.' : ' Лучше — меньше.'}</b>}
                  </Help>
                </span>
              </th>
              {items.map((c, i) => (
                <td key={c.id}>
                  <span className={best.has(i) ? styles.best : styles.val}>{c.run ? m.fmt(values[i]) : '…'}</span>
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** The largest group of compared runs of one recording made with different presets (≥ 2), else null. */
export function presetGroup(items: readonly Compared[]): Compared[] | null {
  const by = new Map<string, Compared[]>();
  for (const c of items) {
    const rec = c.run?.recording_id;
    if (!rec) continue;
    by.set(rec, [...(by.get(rec) ?? []), c]);
  }
  let best: Compared[] | null = null;
  for (const g of by.values()) {
    if (g.length < 2 || new Set(g.map((c) => c.run?.preset.id)).size < 2) continue;
    if (!best || g.length > best.length) best = g;
  }
  return best;
}

export function PresetDiff({ group, schema }: { group: readonly Compared[]; schema: readonly ParamSpec[] | undefined }) {
  const runs = group.map((c) => c.run).filter((r): r is RunDetail => !!r);
  const diff = diffOverrides(
    runs.map((r) => r.overrides ?? {}),
    schema,
  );
  if (!diff.length) return <div className={styles.same}>Параметры совпадают</div>;
  return (
    <table className={`${styles.kt} ${styles.diff}`}>
      <thead>
        <tr>
          <th scope="col">
            <span className="sr-only">Параметр</span>
          </th>
          {group.map((c) => (
            <th key={c.id} scope="col" className={styles.runTh}>
              <i className={styles.keyBar} style={{ background: lineSwatch(c.slot) }} aria-hidden />
              <span className={`${styles.runLabel} ${styles.ell}`} title={c.run?.preset.name}>
                {c.run?.preset.name ?? '…'}
              </span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {diff.map((d) => (
          <tr key={d.key}>
            <th scope="row">
              <span className={styles.rowHead}>
                <span className={styles.ell}>{d.label}</span>
                {d.help && (
                  <Help placement="right" width={260}>
                    {d.help}
                  </Help>
                )}
              </span>
            </th>
            {d.values.map((v, i) => (
              <td key={group[i].id}>
                <span className={styles.val}>{fmtParam(v, d.unit)}</span>
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
