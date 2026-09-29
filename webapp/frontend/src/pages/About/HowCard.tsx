// «Как это работает»: one line on what ReSense does, the detector's pipeline as a metro line
// (a «?» per station) that ends in the four decisions (big signal tiles, the rule in each «?»).
import { Card, Chip, DECISION_ICON, Help, Icon } from '../../components';
import { DECISION_CHIP_LABEL } from '../../lib/decisions';
import { DECISION_INFO, STATIONS } from './content';
import styles from './About.module.css';

export function HowCard({ className }: { className?: string }) {
  const last = STATIONS.length - 1;
  return (
    <Card className={[styles.how, className].filter(Boolean).join(' ')} aria-labelledby="about-lead">
      <div className={styles.howHead}>
        <h2 id="about-lead" className={styles.lead}>
          Препятствие в габарите поезда — и как далеко
        </h2>
        <Help placement="bottom-start" width={340} label="Что делает ReSense">
          Нода ROS 2 в Docker, только CPU. Десять раз в секунду по каждому облаку лидара строит модель тоннеля — полотно, рельсы, ось пути, — вырезает вдоль
          неё габарит поезда <b>2,1 × 3,0 м</b> и сообщает о каждом устойчивом объекте внутри. Без классов объектов, без карты, без обучения на препятствиях.
        </Help>
        <span className={styles.sp} />
        <div className={styles.facts}>
          <Chip variant="well" icon="clock">
            10 раз в секунду
          </Chip>
          <Chip variant="well" icon="cpu">
            только CPU
          </Chip>
          <Chip variant="well" icon="rails">
            без карты
          </Chip>
        </div>
      </div>

      <div className={styles.metro}>
        <ol className={styles.line} aria-label="Обработка кадра">
          {STATIONS.map((s, i) => (
            <li key={s.key} className={[styles.st, i === last ? styles.stEnd : ''].filter(Boolean).join(' ')}>
              <span className={styles.stTop}>
                {i === last ? (
                  <span className={styles.quad} aria-hidden>
                    <i className={styles.qGo} />
                    <i className={styles.qCaution} />
                    <i className={styles.qStop} />
                    <i className={styles.qFault} />
                  </span>
                ) : (
                  <span className={styles.stIc} aria-hidden>
                    <Icon name={s.icon} size={20} />
                  </span>
                )}
                <Help
                  placement={i >= last - 1 ? 'bottom-end' : i === 0 ? 'bottom-start' : 'bottom'}
                  width={290}
                  label={`Этап «${s.name}»`}
                  className={styles.stHelp}
                >
                  {s.help}
                </Help>
              </span>
              <span className={styles.dot} aria-hidden />
              <span className={styles.stName}>{s.name}</span>
              {s.value && <span className={styles.stVal}>{s.value}</span>}
            </li>
          ))}
        </ol>

        <span className={styles.arrow} aria-hidden>
          <Icon name="arrow-right" size={22} strokeWidth={2.6} />
        </span>

        <ul className={styles.decisions} aria-label="Решения">
          {DECISION_INFO.map((d) => (
            <li key={d.decision} className={[styles.sig, styles[`sig-${d.decision.toLowerCase()}`]].join(' ')}>
              <Icon name={DECISION_ICON[d.decision]} size={22} strokeWidth={2.6} />
              <span className={styles.sigLabel}>{DECISION_CHIP_LABEL[d.decision]}</span>
              <Help
                tone={d.decision === 'CAUTION' ? 'dark' : 'light'}
                placement={d.decision === 'GO' || d.decision === 'CAUTION' ? 'bottom-end' : 'top-end'}
                width={280}
                label={`Когда ${DECISION_CHIP_LABEL[d.decision]}`}
              >
                {d.rule} Топик /resense/decision: <b>{d.topic}</b>.
              </Help>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
