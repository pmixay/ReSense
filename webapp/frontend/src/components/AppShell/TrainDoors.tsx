import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useBlocker, useLocation } from 'react-router-dom';
import styles from './TrainDoors.module.css';

type Phase = 'idle' | 'closing' | 'covered' | 'opening';
const section = (pathname: string) => pathname.split('/')[1] || 'overview';

/** Close before committing navigation. Query edits and run/camera changes stay immediate. */
export function useTrainDoors() {
  const location = useLocation();
  const blocker = useBlocker(({ currentLocation, nextLocation }) => section(currentLocation.pathname) !== section(nextLocation.pathname));
  const [phase, setPhase] = useState<Phase>('idle');
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const origin = useRef(location.key);
  const proceed = useRef<(() => void) | undefined>();
  proceed.current = blocker.state === 'blocked' ? blocker.proceed : undefined;

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const change = () => setReduced(media.matches);
    media.addEventListener('change', change);
    return () => media.removeEventListener('change', change);
  }, []);

  useLayoutEffect(() => {
    if (blocker.state === 'blocked' && phase === 'idle') {
      origin.current = location.key;
      setPhase('closing');
    }
  }, [blocker.state, location.key, phase]);

  useEffect(() => {
    if (phase !== 'closing') return;
    const timer = window.setTimeout(() => {
      setPhase('covered');
      proceed.current?.();
    }, reduced ? 75 : 360);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  useEffect(() => {
    if (phase !== 'covered' || location.key === origin.current) return;
    // Give the committed destination a paint behind the closed, opaque-frosted leaves.
    const started = performance.now();
    const reveal = () => {
      if (document.querySelector('[data-page-fallback]') && performance.now() - started < 1000) {
        timer = window.setTimeout(reveal, 50);
      } else setPhase('opening');
    };
    let timer = window.setTimeout(reveal, reduced ? 25 : 100);
    return () => window.clearTimeout(timer);
  }, [location.key, phase, reduced]);

  useEffect(() => {
    if (phase !== 'opening') return;
    const timer = window.setTimeout(() => setPhase('idle'), reduced ? 100 : 460);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  // Back/Forward can cancel an in-flight departure. Always release the overlay.
  useEffect(() => {
    if (phase === 'idle') return;
    const timer = window.setTimeout(() => {
      proceed.current?.();
      setPhase('idle');
    }, 2000);
    return () => window.clearTimeout(timer);
  }, [phase]);

  return { phase, active: phase !== 'idle' };
}

export function TrainDoors({ phase }: { phase: Phase }) {
  return (
    <div className={styles.portal} data-train-doors data-phase={phase} aria-hidden="true">
      <div className={styles.header}><span /><i /><span /></div>
      <div className={styles.frame}>
        {(['left', 'right'] as const).map(side => (
          <div key={side} className={`${styles.leaf} ${styles[side]}`} data-door-leaf={side}>
            <div className={styles.skin}>
              <div className={styles.window} data-door-glass>
                <div className={styles.glare} />
                <div className={styles.safetyMark}><span /><span /></div>
              </div>
              <div className={styles.lowerPanel}><span /><i /></div>
              <span className={styles.edgeLight} />
              <span className={styles.seal} />
            </div>
            <div className={styles.thickness} />
          </div>
        ))}
      </div>
      <div className={styles.sill} />
    </div>
  );
}
