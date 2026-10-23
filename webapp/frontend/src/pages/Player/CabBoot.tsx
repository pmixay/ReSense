// The windshield display's power-up, drawn over the live picture while the cab boots: a line of
// light opens the screen, frame brackets snap to its corners, a reticle spins up and a short
// initialization log types out the run's facts. Decorative and CSS-timed (cabBoot.ts timeline);
// the controls stay usable underneath. Unmounted when the boot ends.
import type { CSSProperties } from 'react';
import styles from './Player.module.css';

export function CabBoot({ lines }: { lines: readonly string[] }) {
  return (
    <div className={styles.boot} data-cab-boot aria-hidden="true">
      <i className={styles.bootFlash} />
      {(['tl', 'tr', 'bl', 'br'] as const).map(c => <i key={c} className={styles.bootCorner} data-corner={c} />)}
      <i className={styles.bootEdge} data-edge="top" />
      <i className={styles.bootEdge} data-edge="bottom" />
      <div className={styles.bootReticle}><i /><i /><i /></div>
      <div className={styles.bootLog}>
        <b>Инициализация кабины</b>
        {lines.map((line, i) => <span key={line} style={{ '--i': i } as CSSProperties}>{line}</span>)}
        <span className={styles.bootBar}><i /></span>
        <strong>Система готова</strong>
      </div>
    </div>
  );
}
