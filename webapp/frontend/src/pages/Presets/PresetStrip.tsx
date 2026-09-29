// The presets as a row of cards: the sealed built-in first, user presets, an unsaved new one, and
// «Новый пресет». The selected card is ink.
import type { Preset } from '../../api/types';
import { Icon } from '../../components';
import { fmtRelDate } from '../../lib/format';
import { NEW_ID } from './model';
import styles from './Presets.module.css';

export interface StripItem {
  id: string;
  name: string;
  builtin: boolean;
  /** parameters that differ from the defaults */
  changed: number;
  /** unsaved edits */
  dirty: boolean;
  created_at: string | null;
}

export function stripItems(presets: readonly Preset[], changedOf: (p: Preset) => number, dirtyOf: (id: string) => boolean, newDraft: { name: string; changed: number } | null): StripItem[] {
  const items: StripItem[] = presets.map((p) => ({
    id: p.id,
    name: p.name,
    builtin: p.builtin,
    changed: changedOf(p),
    dirty: dirtyOf(p.id),
    created_at: p.builtin ? null : p.created_at,
  }));
  if (newDraft) items.push({ id: NEW_ID, name: newDraft.name, builtin: false, changed: newDraft.changed, dirty: true, created_at: null });
  return items;
}

export interface PresetStripProps {
  items: StripItem[];
  selected: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function PresetStrip({ items, selected, onSelect, onNew }: PresetStripProps) {
  return (
    <nav className={styles.strip} aria-label="Пресеты">
      {items.map((it) => {
        const on = it.id === selected;
        return (
          <button
            key={it.id}
            type="button"
            className={[styles.pc, on ? styles.pcOn : '', it.id === NEW_ID ? styles.pcNew : ''].filter(Boolean).join(' ')}
            aria-current={on ? 'true' : undefined}
            onClick={() => onSelect(it.id)}
          >
            <span className={styles.pcIc}>
              <Icon name={it.builtin ? 'lock' : 'sliders'} size={17} />
            </span>
            <span className={styles.pcBody}>
              <span className={styles.pcName}>{it.name}</span>
              <span className={styles.pcMeta}>
                {it.builtin ? (
                  <span className={styles.tag}>опечатан</span>
                ) : (
                  <span className={styles.tag}>{it.changed ? `изменено ${it.changed}` : 'как стандарт'}</span>
                )}
                {it.id === NEW_ID ? <span className={styles.tag}>черновик</span> : it.dirty ? <span className={styles.tag}>не сохранён</span> : null}
                {it.created_at && !it.dirty && <span className={styles.when}>{fmtRelDate(it.created_at)}</span>}
              </span>
            </span>
          </button>
        );
      })}
      <button type="button" className={styles.pcAdd} onClick={onNew}>
        <Icon name="plus" size={18} strokeWidth={2.6} />
        Новый пресет
      </button>
    </nav>
  );
}
