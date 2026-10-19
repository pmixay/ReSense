import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useBlocker, useLocation } from 'react-router-dom';
import styles from './TrainDoors.module.css';
import { navigationJourney } from '../../lib/navigationJourney';
import { preloadSections } from '../../sectionPages';

type Phase = 'idle' | 'closing' | 'covered' | 'travelling' | 'opening';
const section = (pathname: string) => pathname.split('/')[1] || 'overview';

/** One continuous directional journey, with intermediate views behind closed glass. */
export function useTrainDoors(options: { onCover?: () => void; isPrepared?: () => boolean } = {}) {
  const location = useLocation();
  const blocker = useBlocker(({ currentLocation, nextLocation }) => section(currentLocation.pathname) !== section(nextLocation.pathname));
  const [phase, setPhase] = useState<Phase>('idle');
  const [journey, setJourney] = useState(() => navigationJourney(location.pathname, location.pathname));
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const origin = useRef(location.key);
  const proceed = useRef<(() => void) | undefined>();
  const latest = useRef(options);
  latest.current = options;
  proceed.current = blocker.state === 'blocked' ? blocker.proceed : undefined;

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const change = () => setReduced(media.matches);
    media.addEventListener('change', change);
    return () => media.removeEventListener('change', change);
  }, []);

  useLayoutEffect(() => {
    if (blocker.state === 'blocked' && (phase === 'idle' || phase === 'closing')) {
      const next = navigationJourney(location.pathname, blocker.location.pathname);
      setJourney(next);
      if (phase === 'idle') {
        origin.current = location.key;
        setPhase('closing');
      }
    }
  }, [blocker.state, blocker.location?.pathname, location.key, location.pathname, phase]);

  useEffect(() => {
    if (phase === 'closing' && !reduced) preloadSections([...journey.via, ...(journey.target ? [journey.target] : [])]);
  }, [journey, phase, reduced]);

  useEffect(() => {
    if (phase !== 'closing') return;
    const timer = window.setTimeout(() => {
      if (!reduced) latest.current.onCover?.();
      setPhase('covered');
      proceed.current?.();
    }, reduced ? 75 : 360);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  useEffect(() => {
    if (phase !== 'covered' || location.key === origin.current) return;
    // Keep the outgoing snapshot centered until destination and passing views are ready.
    const started = performance.now();
    const reveal = () => {
      if ((document.querySelector('[data-page-fallback]') || (!reduced && latest.current.isPrepared?.() === false)) && performance.now() - started < 1200) {
        timer = window.setTimeout(reveal, 50);
      } else setPhase(reduced ? 'opening' : 'travelling');
    };
    let timer = window.setTimeout(reveal, 25);
    return () => window.clearTimeout(timer);
  }, [location.key, phase, reduced]);

  useEffect(() => {
    if (phase !== 'travelling') return;
    const timer = window.setTimeout(() => setPhase('opening'), reduced ? 0 : journey.duration + 20);
    return () => window.clearTimeout(timer);
  }, [phase, reduced, journey.duration]);

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
    }, 6000);
    return () => window.clearTimeout(timer);
  }, [active]);

  return { phase, active, journey, reduced };
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
