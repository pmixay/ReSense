// The red top bar: logo · «Главная» pill · three group pills with dropdown menus · status pills.
// Menus: click or Enter / Space / ArrowDown to open, arrows to move, Escape to close (focus returns
// to the pill), ArrowLeft / ArrowRight to the neighbouring group, a click outside or Tab closes.
import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useBackendStatus, usePresets } from '../../api/hooks';
import { PRESETS, RUNS, fmtCount, fmtDuration } from '../../lib/format';
import { GROUPS, PAGES, pageOfPath, type NavGroup, type PageKey } from '../../lib/nav';
import type { SystemInfo } from '../../api/types';
import { Icon } from '../Icon/Icon';
import { Tooltip } from '../Tooltip/Tooltip';
import styles from './TopBar.module.css';

export function Logo({ compact }: { compact?: boolean }) {
  return (
    <>
      <svg className={styles.logoMark} viewBox="0 0 40 38" aria-hidden>
        <path d="M3.5 19H12" stroke="#fff" strokeWidth="7" strokeLinecap="round" />
        <circle cx="19" cy="19" r="7" fill="#E4000D" stroke="#fff" strokeWidth="5" />
        <path d="M28.2 11.3A12 12 0 0 1 28.2 26.7M32 8.1A17 17 0 0 1 32 29.9" fill="none" stroke="#fff" strokeWidth="2.8" strokeLinecap="round" />
      </svg>
      {!compact && <span className={styles.logoWord}>ReSense</span>}
    </>
  );
}

function subtitle(key: PageKey, sys: SystemInfo | undefined, presets: number | undefined): string {
  switch (key) {
    case 'upload':
      return 'файл · папка · демо';
    case 'queue': {
      if (!sys) return 'обработка записей';
      const { jobs_running: r, jobs_queued: q } = sys.counts;
      if (r || q) return [r ? `${r} в работе` : '', q ? `${q} ждёт` : ''].filter(Boolean).join(' · ');
      return 'пусто';
    }
    case 'runs':
      return sys ? (sys.counts.runs ? fmtCount(sys.counts.runs, RUNS) : 'пока нет') : 'результаты';
    case 'player':
      return '3D-вид из кабины';
    case 'compare':
      return 'два прогона рядом';
    case 'live':
      return 'симуляция · узел ROS';
    case 'presets':
      return presets !== undefined ? fmtCount(presets, PRESETS) : 'пресеты детектора';
    case 'about':
      return 'как это работает';
    default:
      return '';
  }
}

interface GroupMenuProps {
  group: NavGroup;
  current: PageKey | null;
  open: boolean;
  onOpen: (focus: 'first' | 'last' | null) => void;
  onClose: (refocus: boolean) => void;
  onMove: (dir: -1 | 1) => void;
  focusRequest: 'first' | 'last' | null;
  system: SystemInfo | undefined;
  registerButton: (el: HTMLButtonElement | null) => void;
}

function GroupMenu({ group, current, open, onOpen, onClose, onMove, focusRequest, system, registerButton }: GroupMenuProps) {
  const menuId = useId();
  const items = useRef<(HTMLAnchorElement | null)[]>([]);
  const btn = useRef<HTMLButtonElement | null>(null);
  const active = !!current && group.pages.includes(current);
  const presets = usePresets({ enabled: open && group.n === 3, retry: false });

  useEffect(() => {
    if (!open || !focusRequest) return;
    const list = items.current.filter(Boolean) as HTMLAnchorElement[];
    (focusRequest === 'first' ? list[0] : list[list.length - 1])?.focus();
  }, [open, focusRequest]);

  const onButtonKey = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onOpen('first');
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      onOpen('last');
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      onMove(1);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      onMove(-1);
    } else if (e.key === 'Escape' && open) {
      e.preventDefault();
      onClose(true);
    }
  };

  const onMenuKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const list = items.current.filter(Boolean) as HTMLAnchorElement[];
    const i = list.indexOf(document.activeElement as HTMLAnchorElement);
    let next = -1;
    if (e.key === 'ArrowDown') next = (i + 1) % list.length;
    else if (e.key === 'ArrowUp') next = (i - 1 + list.length) % list.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = list.length - 1;
    else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      onClose(true);
      return;
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      onMove(e.key === 'ArrowRight' ? 1 : -1);
      return;
    } else if (e.key === 'Tab') {
      onClose(false);
      return;
    }
    if (next >= 0) {
      e.preventDefault();
      list[next]?.focus();
    }
  };

  return (
    <div className={styles.grpWrap}>
      <button
        ref={(el) => {
          btn.current = el;
          registerButton(el);
        }}
        type="button"
        className={[styles.pill, styles.grp, active ? styles.active : '', open ? styles.open : ''].join(' ')}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => (open ? onClose(false) : onOpen(null))}
        onKeyDown={onButtonKey}
      >
        <span className={styles.ln}>{group.n}</span>
        {group.label}
        <Icon name="chevron-down" size={14} strokeWidth={2.6} className={styles.chev} />
      </button>
      <div id={menuId} role="menu" aria-label={group.label} className={styles.dd} hidden={!open} onKeyDown={onMenuKey}>
        {group.pages.map((key, i) => {
          const pg = PAGES[key];
          const here = key === current;
          return (
            <Link
              key={key}
              ref={(el) => {
                items.current[i] = el;
              }}
              to={pg.path}
              role="menuitem"
              tabIndex={-1}
              aria-current={here ? 'page' : undefined}
              className={[styles.ddItem, here ? styles.hl : ''].join(' ')}
              onClick={() => onClose(false)}
            >
              <span className={styles.ddIc}>
                <Icon name={pg.icon} />
              </span>
              <span className={styles.ddText}>
                <span className={styles.ddT}>{pg.label}</span>
                <span className={styles.ddS}>{subtitle(key, system, presets.data?.length)}</span>
              </span>
              <Icon name="arrow-right" size={16} className={styles.ddGo} />
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export function TopBar() {
  const location = useLocation();
  const current = pageOfPath(location.pathname);
  const [openGroup, setOpenGroup] = useState<number | null>(null);
  const [focusReq, setFocusReq] = useState<'first' | 'last' | null>(null);
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const navRef = useRef<HTMLElement>(null);
  const { status, system } = useBackendStatus();

  const openRef = useRef<number | null>(null);
  openRef.current = openGroup;

  const close = useCallback((refocus: boolean) => {
    const g = openRef.current;
    setOpenGroup(null);
    setFocusReq(null);
    if (refocus && g !== null) buttons.current[g]?.focus();
  }, []);

  // route change closes; click outside closes
  useEffect(() => close(false), [location.pathname, close]);
  useEffect(() => {
    if (openGroup === null) return;
    const onDown = (e: PointerEvent) => {
      if (!navRef.current?.contains(e.target as Node)) close(false);
    };
    document.addEventListener('pointerdown', onDown);
    return () => document.removeEventListener('pointerdown', onDown);
  }, [openGroup, close]);

  const statusText = status === 'online' ? 'бэкенд онлайн' : status === 'offline' ? 'бэкенд офлайн' : 'подключение…';
  const statusTip =
    status === 'online' && system
      ? `Бэкенд обрабатывает записи на этой машине: работает ${fmtDuration(system.uptime_s)}, детектор v${system.detector_version}. Проверка каждые 5 с.`
      : status === 'offline'
        ? 'Сервер не отвечает: запустите python -m resense_web. Страница переподключится сама.'
        : 'Проверяем связь с сервером…';

  return (
    <header className={styles.top}>
      <Link to="/" className={styles.logo} aria-label="ReSense — на главную">
        <Logo />
      </Link>
      <nav ref={navRef} className={styles.nav} aria-label="Разделы">
        <NavLink to="/" end className={({ isActive }) => [styles.pill, isActive ? styles.active : ''].join(' ')}>
          <Icon name="home" size={16} />
          Главная
        </NavLink>
        {GROUPS.map((g, gi) => (
          <GroupMenu
            key={g.n}
            group={g}
            current={current}
            open={openGroup === gi}
            focusRequest={openGroup === gi ? focusReq : null}
            system={system}
            registerButton={(el) => {
              buttons.current[gi] = el;
            }}
            onOpen={(focus) => {
              setOpenGroup(gi);
              setFocusReq(focus);
            }}
            onClose={close}
            onMove={(dir) => {
              const next = (gi + dir + GROUPS.length) % GROUPS.length;
              const wasOpen = openGroup !== null;
              setOpenGroup(wasOpen ? next : null);
              setFocusReq(wasOpen ? 'first' : null);
              if (!wasOpen) buttons.current[next]?.focus();
            }}
          />
        ))}
      </nav>
      <div className={styles.right}>
        <Tooltip content={statusTip} placement="bottom-end" width={260}>
          <span className={styles.chip} tabIndex={0} role="status" aria-live="polite">
            <span className={[styles.dot, styles[status]].join(' ')} aria-hidden />
            {statusText}
          </span>
        </Tooltip>
        <span className={styles.chip}>ЛЦТ 2026 · кейс 05</span>
        <Tooltip content="Команда «Молоток»" placement="bottom-end" width="auto">
          <span className={styles.avatar} tabIndex={0} aria-label="Команда «Молоток»">
            М
          </span>
        </Tooltip>
      </div>
    </header>
  );
}
