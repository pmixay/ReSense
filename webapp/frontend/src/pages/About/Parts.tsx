// The smaller blocks of «О системе»: the headline results (big numbers, the caveat in «?»), the
// documentation links and the team.
import { Card, GoodMark, Help, Icon, KpiTile, StopMark, Tooltip } from '../../components';
import { LINKS, RESULTS, TEAM } from './content';
import styles from './About.module.css';

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(' ');

export function Results({ className }: { className?: string }) {
  return (
    <div className={cx(styles.results, className)} role="list" aria-label="Результаты в выборке">
      {RESULTS.map((r, i) => (
        <div key={r.key} role="listitem" className={styles.result}>
          <KpiTile
            label={r.label}
            icon={r.mark === 'stop' ? <StopMark /> : undefined}
            value={r.value}
            unit={r.unit}
            after={r.mark === 'good' ? <GoodMark /> : undefined}
            sub={r.sub}
            help={r.help}
            helpPlacement={i >= RESULTS.length - 2 ? 'bottom-end' : i === 0 ? 'bottom-start' : 'bottom'}
            variant={r.variant}
            className={styles.kpi}
          />
        </div>
      ))}
    </div>
  );
}

export function LinksCard({ className }: { className?: string }) {
  return (
    <Card
      title="Документация"
      className={cx(styles.links, className)}
      help="GitBook и GitHub, в новой вкладке. Наведите на ссылку — что внутри."
      helpPlacement="bottom-end"
      helpWidth={220}
    >
      <ul className={styles.linkList} aria-label="Ссылки на документацию">
        {LINKS.map((l) => (
          <li key={l.key}>
            <Tooltip content={l.help} placement="left" width={260} className={styles.linkTip}>
              <a className={styles.link} href={l.href} target="_blank" rel="noreferrer">
                <span className={styles.linkIc}>
                  <Icon name={l.icon} size={16} />
                </span>
                <span className={styles.linkName}>{l.label}</span>
                <Icon name="external" size={14} className={styles.linkExt} />
              </a>
            </Tooltip>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function TeamCard({ className }: { className?: string }) {
  return (
    <Card
      title="Команда «Молоток»"
      className={cx(styles.team, className)}
      help="Роли — по списку организаторов ЛЦТ 2026."
      helpPlacement="bottom-end"
      helpWidth={220}
    >
      <ul className={styles.members} aria-label="Роли в команде">
        {TEAM.map((m) => (
          <li key={m.id} className={styles.member}>
            <span className={cx(styles.badge, m.captain && styles.captain)}>{m.id}</span>
            <span className={styles.role}>
              {m.role}
              {m.captain && <span className={styles.capTag}>капитан</span>}
            </span>
            <Help placement="left" width={270} label={`Чем занимается ${m.id}`}>
              {m.owns}
            </Help>
          </li>
        ))}
      </ul>
    </Card>
  );
}
