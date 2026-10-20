import { Card } from '../../components';
import { DECISION_INFO, STATIONS } from './content';
import styles from './About.module.css';

export function HowCard({ className }: { className?: string }) {
  return <Card className={[styles.how, className].filter(Boolean).join(' ')} aria-labelledby="about-lead">
    <div className={styles.introduction}>
      <h2 id="about-lead" className={styles.lead}>Препятствие в габарите поезда — и как далеко</h2>
      <p className={styles.description}>
        По облаку LiDAR ReSense строит модель пути, проверяет габарит поезда
        {' '}2,1 × 3,0 м и сообщает об устойчивом препятствии и расстоянии до него.
      </p>
      <p className={styles.facts}>ROS 2 Humble · Docker · только CPU · без карты</p>
      <ol className={styles.line} aria-label="Обработка кадра">
        {STATIONS.map(station => <li key={station.key}>{station.name}</li>)}
      </ol>
      <details className={styles.pipelineDetails} data-about-detail="pipeline">
        <summary>Подробнее об обработке</summary>
        <ol className={styles.stationDetails} aria-label="Объяснение этапов">
          {STATIONS.map(station => <li key={station.key}>
            <h3>{station.name}{station.value && <span>{station.value}</span>}</h3>
            <p>{station.help}</p>
          </li>)}
        </ol>
      </details>
    </div>
    <section className={styles.decisionSection} aria-labelledby="about-decisions">
      <h3 id="about-decisions">Как читать решение</h3>
      <ul className={styles.decisions} aria-label="Решения">
        {DECISION_INFO.map(item => <li key={item.decision}>
          <span className={`${styles.signal} ${styles[`signal${item.decision}`]}`}>{item.topic}</span>
          <p>{item.rule}</p>
        </li>)}
      </ul>
    </section>
  </Card>;
}
