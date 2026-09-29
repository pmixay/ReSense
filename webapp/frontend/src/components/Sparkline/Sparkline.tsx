// A small line chart: ink line over a light area, a dot on the last value; null values leave gaps.
import styles from './Sparkline.module.css';

export interface SparklineProps {
  values: readonly (number | null | undefined)[];
  height?: number;
  min?: number;
  max?: number;
  tone?: 'ink' | 'light';
  area?: boolean;
  dot?: boolean;
  strokeWidth?: number;
  label?: string;
  className?: string;
}

export function Sparkline({ values, height = 34, min, max, tone = 'ink', area = true, dot = true, strokeWidth = 2, label, className }: SparklineProps) {
  const n = values.length;
  const finite = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  if (n < 2 || finite.length === 0) {
    return <div className={[styles.wrap, className].filter(Boolean).join(' ')} style={{ height }} aria-label={label} role={label ? 'img' : undefined} />;
  }
  const lo = min ?? Math.min(...finite);
  const hi = max ?? Math.max(...finite);
  const span = hi - lo || 1;
  const W = 1000;
  const pad = strokeWidth; // keep the stroke inside the box
  const H = height;
  const x = (i: number) => (i / (n - 1)) * W;
  const y = (v: number) => H - pad - ((v - lo) / span) * (H - 2 * pad);

  const segs: string[] = [];
  const areas: string[] = [];
  let cur: [number, number][] = [];
  const flush = () => {
    if (cur.length) {
      segs.push('M' + cur.map(([a, b]) => `${a.toFixed(1)} ${b.toFixed(1)}`).join(' L'));
      areas.push(`M${cur[0][0].toFixed(1)} ${H} L` + cur.map(([a, b]) => `${a.toFixed(1)} ${b.toFixed(1)}`).join(' L') + ` L${cur[cur.length - 1][0].toFixed(1)} ${H} Z`);
    }
    cur = [];
  };
  values.forEach((v, i) => {
    if (typeof v === 'number' && Number.isFinite(v)) cur.push([x(i), y(v)]);
    else flush();
  });
  flush();

  let lastI = n - 1;
  while (lastI >= 0 && !(typeof values[lastI] === 'number' && Number.isFinite(values[lastI] as number))) lastI -= 1;
  const lastV = values[lastI] as number;

  return (
    <div
      className={[styles.wrap, tone === 'light' ? styles.light : '', className].filter(Boolean).join(' ')}
      style={{ height }}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" width="100%" height={H}>
        {area && areas.map((d, i) => <path key={`a${i}`} d={d} className={styles.area} />)}
        {segs.map((d, i) => (
          <path key={`l${i}`} d={d} className={styles.line} style={{ strokeWidth }} vectorEffect="non-scaling-stroke" />
        ))}
      </svg>
      {dot && lastI >= 0 && (
        <span className={styles.dot} style={{ left: `${(lastI / (n - 1)) * 100}%`, top: y(lastV) }} />
      )}
    </div>
  );
}
