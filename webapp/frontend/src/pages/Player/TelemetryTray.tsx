import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from 'react';
import styles from './Player.module.css';

/** Scroll reveals information over the fixed installation; transport never participates. */
export function TelemetryTray({ workspaceRef, children }: { workspaceRef: RefObject<HTMLDivElement>; children: ReactNode }) {
  const [amount, setAmount] = useState(0);
  const [height, setHeight] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const touchY = useRef<number | null>(null);
  const amountRef = useRef(0);
  amountRef.current = amount;
  const id = useId();

  useEffect(() => {
    const panel = panelRef.current;
    const viewport = viewportRef.current;
    if (!panel || !viewport) return;
    const measure = () => setHeight(panel.getBoundingClientRect().height);
    const observer = new ResizeObserver(measure);
    observer.observe(panel);
    observer.observe(viewport);
    measure();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) return;
    const wheel = (event: WheelEvent) => {
      const target = event.target as HTMLElement;
      if (event.ctrlKey || Math.abs(event.deltaX) > Math.abs(event.deltaY) || target.closest('button, input, [role="slider"], [role="navigation"], [data-player-persistent]')) return;
      const panel = panelRef.current;
      if (amountRef.current === 100 && panel?.contains(target) && panel.scrollHeight > panel.clientHeight) {
        const canScroll = event.deltaY > 0 ? panel.scrollTop + panel.clientHeight < panel.scrollHeight - 1 : panel.scrollTop > 1;
        if (canScroll) return;
      }
      event.preventDefault();
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? height : 1);
      setAmount(value => Math.max(0, Math.min(100, value + delta / Math.max(1, height) * 100)));
    };
    workspace.addEventListener('wheel', wheel, { passive: false });
    return () => workspace.removeEventListener('wheel', wheel);
  }, [workspaceRef, height]);

  useEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) return;
    const start = (event: TouchEvent) => {
      touchY.current = null;
      if ((event.target as HTMLElement).closest('button, input, [role="slider"], [data-player-persistent]')) return;
      touchY.current = event.touches[0]?.clientY ?? null;
    };
    const move = (event: TouchEvent) => {
      if (touchY.current === null) return;
      const y = event.touches[0]?.clientY ?? touchY.current;
      const delta = touchY.current - y;
      const panel = panelRef.current;
      if (amountRef.current === 100 && panel?.contains(event.target as Node)) {
        const canScroll = delta > 0 ? panel.scrollTop + panel.clientHeight < panel.scrollHeight - 1 : panel.scrollTop > 1;
        if (canScroll) { touchY.current = y; return; }
      }
      if (event.cancelable) event.preventDefault();
      touchY.current = y;
      setAmount(value => Math.max(0, Math.min(100, value + delta / Math.max(1, height) * 100)));
    };
    const end = () => { touchY.current = null; };
    workspace.addEventListener('touchstart', start, { passive: true });
    workspace.addEventListener('touchmove', move, { passive: false });
    workspace.addEventListener('touchend', end);
    workspace.addEventListener('touchcancel', end);
    return () => {
      workspace.removeEventListener('touchstart', start);
      workspace.removeEventListener('touchmove', move);
      workspace.removeEventListener('touchend', end);
      workspace.removeEventListener('touchcancel', end);
    };
  }, [workspaceRef, height]);

  return (
    <div className={styles.telemetryTray} data-telemetry-tray style={{ '--tray-reveal': `${height * amount / 100}px` } as CSSProperties}>
      <div ref={viewportRef} className={styles.trayViewport}>
        <div id={id} ref={panelRef} className={styles.trayPanel} aria-hidden={amount === 0}>
          {children}
        </div>
      </div>
      <div className={styles.trayHandle}>
        <label htmlFor={`${id}-reveal`}>Телеметрия</label>
        <input id={`${id}-reveal`} type="range" min="0" max="100" step="1" value={amount}
          aria-label="Показать телеметрию" aria-controls={id} aria-valuetext={amount === 0 ? 'Скрыта' : amount === 100 ? 'Открыта' : `${Math.round(amount)} %`}
          onChange={event => setAmount(Number(event.target.value))} />
        <span aria-hidden="true">{Math.round(amount)} %</span>
      </div>
    </div>
  );
}
