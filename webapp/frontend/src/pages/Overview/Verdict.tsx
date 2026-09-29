// The verdict chip (detector vs labels: outlined, never a decision chip) and the labels tag.
import { DecisionChip, Icon } from '../../components';
import { fmtInt } from '../../lib/format';
import type { LabelsTag, Verdict } from './verdict';
import styles from './Verdict.module.css';

export function VerdictChip({ verdict, className }: { verdict: Verdict; className?: string }) {
  if (verdict.kind === 'stops') {
    return verdict.episodes > 0 ? (
      <DecisionChip decision="STOP" size="sm" extra={`×${fmtInt(verdict.episodes)}`} className={className} />
    ) : (
      <DecisionChip decision="GO" size="sm" label="БЕЗ СТОП" className={className} />
    );
  }
  const ok = verdict.kind === 'ok';
  return (
    <span className={[styles.vd, ok ? styles.ok : styles.bad, className].filter(Boolean).join(' ')}>
      <span className={styles.vi} aria-hidden>
        <Icon name={ok ? 'check' : 'stop-octagon'} size={ok ? 13 : 19} strokeWidth={ok ? 3.2 : 2.4} />
      </span>
      {verdict.text}
    </span>
  );
}

export function LabelsTagChip({ tag }: { tag: LabelsTag }) {
  return <span className={[styles.gt, styles[tag.kind]].join(' ')}>{tag.text}</span>;
}
