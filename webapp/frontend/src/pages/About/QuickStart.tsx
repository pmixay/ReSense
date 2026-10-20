import type { UseQueryResult } from '@tanstack/react-query';
import type { ApiError } from '../../api/client';
import type { SystemInfo } from '../../api/types';
import { ErrorBanner, IconButton, Spinner } from '../../components';
import { FEATURES, ROS_COMMANDS, UDP_BUFFER_CMD, WEBAPP_CMD, WEBAPP_URL, fmtVersion } from './content';
import { useCopy } from './useCopy';
import styles from './About.module.css';

export function CodeLine({ cmd, step, what }: { cmd: string; step?: number; what?: string }) {
  const [state, copy] = useCopy();
  const label = state === 'copied' ? 'Скопировано' : state === 'failed' ? 'Не удалось скопировать' : 'Скопировать';
  return <div className={styles.codeLine}>
    <div className={styles.command}>
      {what && <p className={styles.commandLabel}>{step !== undefined && `${step}. `}{what}</p>}
      <code>{cmd}</code>
    </div>
    <IconButton icon={state === 'copied' ? 'check' : 'copy'} label={label} size="sm" variant="outline" onClick={() => copy(cmd)} />
    <span className="sr-only" aria-live="polite">{state === 'copied' ? 'Команда скопирована' : state === 'failed' ? 'Не удалось скопировать' : ''}</span>
  </div>;
}

export function RosCard({ className }: { className?: string }) {
  return <details className={[styles.disclosure, className].filter(Boolean).join(' ')} data-about-detail="ros">
    <summary>Как проверить — ROS 2<span className={styles.summaryNote}>Команды для Docker и записи</span></summary>
    <div className={styles.disclosureBody}>
      <p className={styles.context}>Образ загружается из архива без интернета. Обязательны <code>--net=host</code> и <code>--read-ahead-queue-size 10</code>. Перед запуском настройте на хосте буфер UDP для облаков 360°:</p>
      <CodeLine cmd={UDP_BUFFER_CMD} />
      <div className={styles.term}>
        {ROS_COMMANDS.map((command, i) => <CodeLine key={command.cmd} step={i + 1} cmd={command.cmd} what={command.what} />)}
      </div>
      <p className={styles.context}>Одной командой: <code>scripts/play_bag.sh &lt;бэг&gt;</code>.</p>
    </div>
  </details>;
}

export function WebCard({ system, className }: { system: UseQueryResult<SystemInfo, ApiError>; className?: string }) {
  const sys = system.data;
  return <details className={[styles.disclosure, className].filter(Boolean).join(' ')} data-about-detail="web">
    <summary>Как проверить — веб<span className={styles.summaryNote}>{system.isError ? 'Сведения о стенде недоступны' : 'Запуск и сведения о стенде'}</span></summary>
    <div className={styles.disclosureBody}>
      <p className={styles.context}>Бэкенд и сайт работают на одном порту. Первый запуск с интернетом — с ключом <code>--install</code>. Записи, прогоны и пресеты хранятся в <code>webapp/data</code>.</p>
      <CodeLine cmd={WEBAPP_CMD} />
      <a href={WEBAPP_URL} target="_blank" rel="noreferrer" className={styles.localLink}>Открыть localhost:8080</a>
      <section className={styles.stand} aria-labelledby="about-stand">
        <h3 id="about-stand">Этот стенд</h3>
        {system.isError ? <ErrorBanner compact error={system.error} title={system.error.offline ? 'Нет связи с бэкендом' : 'Сведения не получены'} />
          : !sys ? <Spinner size={22} label="Сведения о стенде загружаются" />
          : <>
            <dl className={styles.versions}>
              <div><dt>детектор</dt><dd>{fmtVersion(sys.detector_version)}</dd></div>
              <div><dt>веб</dt><dd>{fmtVersion(sys.version)}</dd></div>
            </dl>
            <ul className={styles.features}>
              {FEATURES.map(feature => <li key={feature.key}>
                <span>{feature.label}</span>
                <span className={styles.featureState}>{sys.features?.[feature.key] ? ': есть' : ': нет'}</span>
                <p>{feature.help}</p>
              </li>)}
            </ul>
          </>}
      </section>
    </div>
  </details>;
}
