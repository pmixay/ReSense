// The metro line under the top bar: Главная → Загрузка → Очередь → Прогоны → Плеер → Сравнение.
// The current page is a big white station with a red ring. Pages of group 3 (Прямой эфир,
// Параметры, О системе) are off the line: the line then shortens, has no current station, and a
// short branch «3 Система» with those three stations appears at its end.
import { Link, useLocation } from 'react-router-dom';
import { BRANCH, LINE, PAGES, pageOfPath, type PageKey } from '../../lib/nav';
import { Icon } from '../Icon/Icon';
import styles from './LineRail.module.css';

export interface LineRailProps {
  /** extra text after the current station's label ("/ doubleT_obstacle") */
  sub?: string;
  /** marks the Очередь station as busy (jobs running or waiting) */
  queueBusy?: boolean;
}

export function LineRail({ sub, queueBusy }: LineRailProps) {
  const { pathname } = useLocation();
  const current = pageOfPath(pathname);
  const onBranch = current !== null && BRANCH.includes(current);

  const station = (key: PageKey, i: number, list: PageKey[]) => {
    const pg = PAGES[key];
    const cur = key === current;
    const home = key === 'overview';
    const busy = key === 'queue' && queueBusy && !cur;
    const cls = [styles.st, home ? styles.home : '', cur ? styles.cur : '', busy ? styles.busy : ''].join(' ');
    const edge = i === 0 ? styles.first : i === list.length - 1 ? styles.last : '';
    return (
      <Link key={key} to={pg.path} className={[cls, edge].join(' ')} aria-current={cur ? 'page' : undefined} title={busy ? 'идёт обработка' : undefined}>
        <span className={styles.c}>{home && !cur && <Icon name="home" size={16} strokeWidth={2.4} />}</span>
        <span className={styles.lbl}>
          {pg.label}
          {cur && sub ? <span className={styles.sub}>/ {sub}</span> : null}
        </span>
      </Link>
    );
  };

  return (
    <nav className={[styles.band, onBranch ? styles.branched : ''].join(' ')} aria-label="Линия: путь работы с записью">
      <div className={styles.main}>
        <div className={styles.line} aria-hidden />
        <div className={styles.stations}>{LINE.map((k, i) => station(k, i, LINE))}</div>
      </div>
      <div className={styles.branch} aria-hidden={!onBranch}>
        <span className={styles.transfer} aria-hidden />
        <span className={styles.roundel} title="Ветка «Система»">
          3
        </span>
        <span className={styles.branchName}>Система</span>
        <div className={styles.bline} aria-hidden />
        <div className={styles.bstations}>{BRANCH.map((k, i) => station(k, i, BRANCH))}</div>
      </div>
    </nav>
  );
}
