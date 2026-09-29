// «Как проверить»: the ROS 2 node in five commands (a terminal block, each line copyable) and the web
// prototype (one command, the address) with this stand's versions and features from GET /api/system.
import type { UseQueryResult } from '@tanstack/react-query';
import type { ApiError } from '../../api/client';
import type { SystemInfo } from '../../api/types';
import { Button, Card, Chip, ErrorBanner, Help, IconButton, Spinner, Tooltip } from '../../components';
import { FEATURES, ROS_COMMANDS, UDP_BUFFER_CMD, WEBAPP_CMD, WEBAPP_URL, fmtVersion } from './content';
import { useCopy } from './useCopy';
import styles from './About.module.css';

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(' ');

/** One copyable command; `step` numbers it (its tooltip says what the step does). */
export function CodeLine({ cmd, step, what, tone = 'dark' }: { cmd: string; step?: number; what?: string; tone?: 'dark' | 'light' }) {
  const [state, copy] = useCopy();
  const label = state === 'copied' ? 'Скопировано' : state === 'failed' ? 'Не удалось скопировать' : 'Скопировать';
  return (
    <div className={cx(styles.codeLine, tone === 'light' && styles.codeLight)}>
      {step !== undefined &&
        (what ? (
          <Tooltip content={what} placement="top-start" width="auto">
            <span className={styles.step} tabIndex={0} aria-label={`Шаг ${step}: ${what}`}>
              {step}
            </span>
          </Tooltip>
        ) : (
          <span className={styles.step}>{step}</span>
        ))}
      <code className={styles.cmd}>{cmd}</code>
      <IconButton
        icon={state === 'copied' ? 'check' : 'copy'}
        label={label}
        size="xs"
        variant={tone === 'dark' ? 'glass' : 'white'}
        tooltip
        tooltipPlacement="left"
        className={cx(styles.copy, state === 'copied' && styles.copied)}
        onClick={() => copy(cmd)}
      />
      <span className="sr-only" aria-live="polite">
        {state === 'copied' ? 'Команда скопирована' : state === 'failed' ? 'Не удалось скопировать' : ''}
      </span>
    </div>
  );
}

export function RosCard({ className }: { className?: string }) {
  return (
    <Card
      title="Как проверить — ROS 2"
      className={cx(styles.ros, className)}
      badges={
        <Chip size="sm" variant="outline" icon="wifi-off">
          без интернета
        </Chip>
      }
      help={
        <>
          Образ — архив <b>resense-image-&lt;версия&gt;.tar.gz</b>, загружается без сети. До шага 1, на хосте:
          <br />
          <b>{UDP_BUFFER_CMD}</b>
          <br />
          (буфер UDP для облаков 360°). Обязательно <b>--net=host</b> и <b>--read-ahead-queue-size 10</b>. Одной командой: <b>scripts/play_bag.sh &lt;бэг&gt;</b>.
        </>
      }
      helpPlacement="bottom-start"
      helpWidth={340}
    >
      <div className={styles.term}>
        {ROS_COMMANDS.map((c, i) => (
          <CodeLine key={c.cmd} step={i + 1} cmd={c.cmd} what={c.what} />
        ))}
      </div>
    </Card>
  );
}

const FEATURE_ON = 'var(--go)';
const FEATURE_OFF = 'var(--hair-2)';

export function WebCard({ system, className }: { system: UseQueryResult<SystemInfo, ApiError>; className?: string }) {
  const sys = system.data;
  return (
    <Card
      title="Как проверить — веб"
      className={cx(styles.web, className)}
      help={
        <>
          Бэкенд и этот сайт на одном порту. Первый запуск с интернетом — с ключом <b>--install</b>. Записи, прогоны и пресеты хранятся в <b>webapp/data</b>.
        </>
      }
      helpPlacement="bottom-end"
      helpWidth={290}
    >
      <CodeLine cmd={WEBAPP_CMD} tone="light" />
      <Button variant="outline" size="sm" icon="arrow-right" iconRight="external" href={WEBAPP_URL} target="_blank" className={styles.open}>
        localhost:8080
      </Button>

      <div className={styles.stand}>
        <div className={styles.standHead}>
          <span className={styles.standTitle}>Этот стенд</span>
          <Help placement="top-end" width={300} label="Что известно о стенде">
            Версии и возможности сервера, на котором открыт сайт. {FEATURES.map((f) => `${f.label} — ${f.help}`).join(' ')}
          </Help>
        </div>
        {system.isError ? (
          // no retry button here: the system is polled every 5 s, the card fills in by itself
          <ErrorBanner compact error={system.error} title={system.error.offline ? 'Нет связи с бэкендом' : 'Сведения не получены'} className={styles.standErr} />
        ) : !sys ? (
          <div className={styles.standWait}>
            <Spinner size={22} label="Сведения о стенде загружаются" />
          </div>
        ) : (
          <>
            <div className={styles.versions}>
              <div className={styles.ver}>
                <span className={styles.verL}>детектор</span>
                <span className={styles.verV}>{fmtVersion(sys.detector_version)}</span>
              </div>
              <div className={styles.ver}>
                <span className={styles.verL}>веб</span>
                <span className={styles.verV}>{fmtVersion(sys.version)}</span>
              </div>
            </div>
            <ul className={styles.features}>
              {FEATURES.map((f) => {
                const on = !!sys.features?.[f.key];
                return (
                  <li key={f.key} className={cx(styles.feat, !on && styles.featOff)}>
                    <span className={styles.featDot} style={{ background: on ? FEATURE_ON : FEATURE_OFF }} aria-hidden />
                    {f.label}
                    <span className="sr-only">{on ? ': есть' : ': нет'}</span>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </div>
    </Card>
  );
}
