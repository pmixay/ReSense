import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useBlocker, useLocation } from 'react-router-dom';
import styles from './TrainDoors.module.css';
import { navigationJourney } from '../../lib/navigationJourney';
import { preloadSections } from '../../sectionPages';

type Phase = 'idle' | 'closing' | 'covered' | 'travelling' | 'opening';
const section = (pathname: string) => pathname.split('/')[1] || 'overview';

/** One continuous directional journey, with intermediate views behind closed glass. */
export function useTrainDoors(options: { onCover?: () => void; isPrepared?: () => boolean; onFinishRequested?: () => void } = {}) {
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
    }, reduced ? 75 : 270);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  useEffect(() => {
    if (phase !== 'covered' || location.key === origin.current) return;
    // Keep the outgoing snapshot centered until destination and passing views are ready.
    const started = performance.now();
    const reveal = () => {
      const preparing = !reduced && latest.current.isPrepared?.() === false;
      if (preparing || (document.querySelector('[data-page-fallback]') && performance.now() - started < 5000)) {
        timer = window.setTimeout(reveal, 50);
      } else {
        // The watchdog may have released this journey while the poll was queued.
        setPhase(current => current === 'covered' ? (reduced ? 'opening' : 'travelling') : current);
      }
    };
    let timer = window.setTimeout(reveal, 25);
    return () => window.clearTimeout(timer);
  }, [location.key, phase, reduced]);

  useEffect(() => {
    if (phase !== 'travelling') return;
    if (reduced) {
      setPhase('opening');
      return;
    }
    // Normal completion comes from the compositor's finished promise, not a wall-clock race.
    const timer = window.setTimeout(() => latest.current.onFinishRequested?.(), journey.duration + 2000);
    return () => window.clearTimeout(timer);
  }, [phase, reduced, journey.duration]);

  const finishTravel = useCallback(() => setPhase(current => current === 'travelling' ? 'opening' : current), []);

  useEffect(() => {
    if (phase !== 'opening') return;
    const timer = window.setTimeout(() => setPhase('idle'), reduced ? 100 : 330);
    return () => window.clearTimeout(timer);
  }, [phase, reduced]);

  // Back/Forward can cancel an in-flight departure. Always release the overlay.
  const active = phase !== 'idle';
  useEffect(() => {
    if (!active) return;
    const timer = window.setTimeout(() => {
      if (latest.current.onFinishRequested && document.querySelector('[data-section-motion="travelling"]')) {
        latest.current.onFinishRequested();
        return;
      }
      proceed.current?.();
      setPhase('idle');
    }, 12000);
    return () => window.clearTimeout(timer);
  }, [active]);

  return { phase, active, journey, reduced, finishTravel };
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
