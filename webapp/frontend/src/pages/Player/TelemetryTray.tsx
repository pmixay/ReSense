import { useId, useRef, useState, type ReactNode } from 'react';
import { Button } from '../../components';
import styles from './Player.module.css';

/** Button-controlled side telemetry leaves the fixed screen's center unobstructed. */
export function TelemetryTray({ left, right }: { left: ReactNode; right: ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const buttonRef = useRef<HTMLButtonElement | HTMLAnchorElement>(null);

  return (
    <div className={styles.telemetryTray} data-telemetry-tray onKeyDown={event => {
      if (open && event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        buttonRef.current?.focus();
      }
    }}>
      <Button ref={buttonRef} variant={open ? 'primary' : 'outline'} icon="bars" iconRight={open ? 'x' : undefined}
        className={styles.telemetryToggle} aria-expanded={open} aria-controls={id} onClick={() => setOpen(value => !value)}
        onKeyDown={event => { if (event.key === ' ' || event.key === 'Enter') event.stopPropagation(); }}>
        Телеметрия
      </Button>
      <div id={id} className={styles.telemetrySides} hidden={!open}>
        <aside className={styles.telemetrySide} aria-label="Телеметрия слева" tabIndex={0}>
          {left}
        </aside>
        <aside className={styles.telemetrySide} aria-label="Телеметрия справа" tabIndex={0}>
          {right}
        </aside>
      </div>
    </div>
  );
}
