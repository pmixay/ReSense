import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useBlocker, useLocation } from 'react-router-dom';
import styles from './TrainDoors.module.css';

type Phase = 'idle' | 'closing' | 'departing' | 'covered' | 'arriving' | 'opening';
const section = (pathname: string) => pathname.split('/')[1] || 'overview';

/** Close, move the old page right, swap offscreen, bring the new page in from the left. */
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
      if (reduced) {
        setPhase('covered');
        proceed.current?.();
      } else setPhase('departing');
    }, reduced ? 75 : 360);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  useEffect(() => {
    if (phase !== 'departing') return;
    const timer = window.setTimeout(() => {
      setPhase('covered');
      proceed.current?.();
    }, reduced ? 0 : 160);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  useEffect(() => {
    if (phase !== 'covered' || location.key === origin.current) return;
    // Hold an unloaded chunk offscreen; the frosted panes keep the lateral swap continuous.
    const started = performance.now();
    const reveal = () => {
      if (document.querySelector('[data-page-fallback]') && performance.now() - started < 1000) {
        timer = window.setTimeout(reveal, 50);
      } else setPhase(reduced ? 'opening' : 'arriving');
    };
    let timer = window.setTimeout(reveal, 25);
    return () => window.clearTimeout(timer);
  }, [location.key, phase, reduced]);

  useEffect(() => {
    if (phase !== 'arriving') return;
    const timer = window.setTimeout(() => setPhase('opening'), reduced ? 0 : 230);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  useEffect(() => {
    if (phase !== 'opening') return;
    const timer = window.setTimeout(() => setPhase('idle'), reduced ? 100 : 460);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  // Back/Forward can cancel an in-flight departure. Always release the overlay.
  const active = phase !== 'idle';
  useEffect(() => {
    if (!active) return;
    const timer = window.setTimeout(() => {
      proceed.current?.();
      setPhase('idle');
    }, 3500);
    return () => window.clearTimeout(timer);
  }, [active]);

  return { phase, active };
}

export function TrainDoors({ phase }: { phase: Phase }) {
  return (
    <div className={styles.portal} data-train-doors data-phase={phase} aria-hidden="true">
      {(['left', 'right'] as const).map(side => (
        <div key={side} className={`${styles.leaf} ${styles[side]}`} data-door-leaf={side}>
          <div className={styles.skin} />
          <div className={styles.window} data-door-glass>
            <div className={styles.glare} />
            <span className={styles.glazingMark}><i /><i /><i /></span>
          </div>
          <span className={styles.glazingBead} />
          <span className={styles.edgeLight} />
          <span className={styles.seal} />
          <span className={styles.thickness} />
        </div>
      ))}
    </div>
  );
}
