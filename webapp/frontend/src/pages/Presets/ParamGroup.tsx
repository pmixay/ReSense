// One group of detector parameters (a white card) and its rows: label, «?» with the spec's help, the
// default and the range; a Stepper (numbers) or a Toggle (bool); changed rows get an ink ring and a
// «↺ default» pill; a backend validation error shows under its row.
import type { ParamSpec, ParamValue } from '../../api/types';
import { Help, Icon, Stepper, Toggle, Tooltip, type IconName } from '../../components';
import { fmtNum } from '../../lib/format';
import { digitsOf, fmtRange, fmtValue, sameValue, type Group, type Values } from './model';
import styles from './Presets.module.css';

const GROUP_ICON: Record<string, IconName> = {
  Датчик: 'live',
  Габарит: 'gauge',
  Кластеризация: 'cube',
  Трекинг: 'target',
  'Низкие объекты': 'ruler',
  Накопление: 'layers',
  Исправность: 'eye',
};

export interface ParamGroupProps {
  group: Group;
  values: Values;
  readOnly: boolean;
  errorKey: string | null;
  error: string | null;
  onChange: (key: string, value: ParamValue) => void;
}

export function ParamGroup({ group, values, readOnly, errorKey, error, onChange }: ParamGroupProps) {
  const changed = group.specs.filter((s) => !sameValue(values[s.key], s.default)).length;
  return (
    <section className={styles.group} aria-label={group.title}>
      <header className={styles.gh}>
        <span className={styles.gic}>
          <Icon name={GROUP_ICON[group.title] ?? 'sliders'} size={17} />
        </span>
        <h3 className={styles.gt}>{group.title}</h3>
        {changed > 0 && (
          <span className={styles.gcount} title="Изменено в группе">
            {changed}
          </span>
        )}
      </header>
      <div className={styles.rows}>
        {group.specs.map((s) => (
          <ParamRow
            key={s.key}
            spec={s}
            value={values[s.key]}
            readOnly={readOnly}
            error={errorKey === s.key ? error : null}
            onChange={(v) => onChange(s.key, v)}
          />
        ))}
      </div>
    </section>
  );
}

interface ParamRowProps {
  spec: ParamSpec;
  value: ParamValue | undefined;
  readOnly: boolean;
  error: string | null;
  onChange: (value: ParamValue) => void;
}

function ParamRow({ spec, value, readOnly, error, onChange }: ParamRowProps) {
  const changed = !sameValue(value, spec.default);
  const range = fmtRange(spec);
  const digits = spec.type === 'int' ? 0 : digitsOf(spec.step);
  const num = typeof value === 'number' ? value : Number(spec.default);
  return (
    <div className={styles.rowWrap}>
      <div className={[styles.row, changed ? styles.changed : '', error ? styles.invalid : ''].filter(Boolean).join(' ')} data-param={spec.key}>
        <span className={styles.pl}>{spec.label}</span>
        <Help placement="top" width={290} label={`Что такое «${spec.label}»`}>
          {spec.help}
          <br />
          <br />
          По умолчанию <b>{fmtValue(spec, spec.default)}</b>
          {range && (
            <>
              {' '}
              · диапазон <b>{range}</b>
            </>
          )}
        </Help>
        <span className={styles.sp} />
        {changed && !readOnly && (
          <Tooltip content={`Сбросить к ${fmtValue(spec, spec.default)}`} width="auto">
            <button type="button" className={styles.reset} onClick={() => onChange(spec.default)} aria-label={`${spec.label}: сбросить к ${fmtValue(spec, spec.default)}`}>
              <Icon name="retry" size={13} strokeWidth={2.6} />
              {spec.type === 'bool' ? (spec.default ? 'да' : 'нет') : fmtNum(Number(spec.default), digits)}
            </button>
          </Tooltip>
        )}
        <div className={styles.ctl}>
          {readOnly ? (
            <span className={styles.ro}>
              {spec.type === 'bool' ? (value ? 'да' : 'нет') : fmtNum(num, digits)}
              {spec.type !== 'bool' && spec.unit && <small>{spec.unit}</small>}
            </span>
          ) : spec.type === 'bool' ? (
            <Toggle ariaLabel={spec.label} checked={Boolean(value)} onChange={onChange} />
          ) : (
            <Stepper
              label={spec.label}
              value={num}
              onChange={onChange}
              min={spec.min}
              max={spec.max}
              step={spec.step}
              digits={digits}
              unit={spec.unit}
              className={styles.stepper}
            />
          )}
        </div>
      </div>
      {error && (
        <div className={styles.err} role="alert">
          {error}
        </div>
      )}
    </div>
  );
}
