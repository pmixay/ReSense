import { LINKS, RESULTS, TEAM } from './content';
import styles from './About.module.css';

export function Results({ className }: { className?: string }) {
  return <details className={[styles.disclosure, className].filter(Boolean).join(' ')} data-about-detail="results">
    <summary>Результаты в выборке<span className={styles.summaryNote}>Измерения и условия</span></summary>
    <div className={styles.disclosureBody}>
      <p className={styles.context}>Исторические измерения README: данные разработки, не оценка текущего стенда. Условия каждого измерения указаны ниже.</p>
      <ul className={styles.results} aria-label="Результаты в выборке">
        {RESULTS.map(result => <li key={result.key}>
          <div className={styles.resultHead}>
            <h3>{result.label}</h3>
            <strong>{result.value}{result.unit && <span> {result.unit}</span>}</strong>
          </div>
          <p className={styles.resultSub}>{result.sub}</p>
          <p>{result.help}</p>
        </li>)}
      </ul>
    </div>
  </details>;
}

export function LinksCard({ className }: { className?: string }) {
  return <section className={[styles.links, className].filter(Boolean).join(' ')} aria-labelledby="about-docs">
    <h2 id="about-docs">Документация</h2>
    <ul className={styles.linkList} aria-label="Ссылки на документацию">
      {LINKS.map(link => <li key={link.key}>
        <a href={link.href} title={link.help} target="_blank" rel="noreferrer">{link.label}</a>
      </li>)}
    </ul>
  </section>;
}

export function TeamCard({ className }: { className?: string }) {
  return <details className={[styles.disclosure, className].filter(Boolean).join(' ')} data-about-detail="team">
    <summary>Команда «Молоток»<span className={styles.summaryNote}>Роли и зоны ответственности</span></summary>
    <div className={styles.disclosureBody}>
      <ul className={styles.members} aria-label="Роли в команде">
        {TEAM.map(member => <li key={member.id}>
          <span className={styles.memberId}>{member.id}</span>
          <div>
            <h3>{member.role}{member.captain && <span className={styles.capTag}>капитан</span>}</h3>
            <p>{member.owns}</p>
          </div>
        </li>)}
      </ul>
    </div>
  </details>;
}
