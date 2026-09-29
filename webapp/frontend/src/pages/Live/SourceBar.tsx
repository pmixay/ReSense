// The source controls under the title: the rosbridge address and «Подключить», or the run to
// replay with its transport (start, pause, stop, speed, loop) and a seekable strip of the whole run.
import { useState } from 'react';
import type { ApiError } from '../../api/client';
import type { Run } from '../../api/types';
import { Button, Chip, DecisionStrip, ErrorBanner, Help, Icon, IconButton, Segmented, Select, Spinner, TextInput } from '../../components';
import { fmtInt, fmtNum } from '../../lib/format';
import type { FeedSnapshot, LiveFeedStore } from './feed';
import styles from './Live.module.css';

export type SourceKind = 'ros' | 'sim';

const SPEEDS = [0.5, 1, 2, 5, 10] as const;
const speedLabel = (s: number) => `${fmtNum(s, s < 1 ? 1 : 0)}×`;

export interface SourceBarProps {
  kind: SourceKind;
  snap: FeedSnapshot;
  feed: LiveFeedStore;
  url: string;
  onUrl: (url: string) => void;
  runs: Run[] | undefined;
  runsLoading: boolean;
  runsError: ApiError | null;
  onRetryRuns: () => void;
  run: Run | undefined;
  onRun: (id: string) => void;
  speed: number;
  onSpeed: (speed: number) => void;
  loop: boolean;
  onLoop: (loop: boolean) => void;
}

export const isWsUrl = (u: string) => /^wss?:\/\/[^\s/]+/i.test(u.trim());

export function SourceBar(p: SourceBarProps) {
  return <div className={styles.bar}>{p.kind === 'ros' ? <RosControls {...p} /> : <SimControls {...p} />}</div>;
}

function LinkError({ snap, onRetry }: { snap: FeedSnapshot; onRetry: () => void }) {
  if (snap.link !== 'error' && !(snap.link === 'ended' && snap.error)) return null;
  return <ErrorBanner compact title={snap.error ?? 'Нет связи'} onRetry={onRetry} className={styles.barError} />;
}

function RosControls({ snap, feed, url, onUrl }: SourceBarProps) {
  const [touched, setTouched] = useState(false);
  const busy = snap.source?.kind === 'ros' && (snap.link === 'connecting' || snap.link === 'open');
  const valid = isWsUrl(url);
  const connect = () => {
    setTouched(true);
    if (valid) feed.start({ kind: 'ros', url: url.trim() });
  };
  return (
    <>
      <TextInput
        className={styles.url}
        icon="link"
        value={url}
        aria-label="Адрес rosbridge"
        placeholder="ws://хост:9090"
        invalid={touched && !valid}
        spellCheck={false}
        disabled={busy}
        onChange={(e) => {
          onUrl(e.target.value);
          // the error was about the old address
          if (snap.link === 'error' && snap.source?.kind === 'ros') feed.stop();
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !busy) connect();
        }}
      />
      {busy ? (
        <Button variant="outline" icon="x" onClick={() => feed.stop()}>
          Отключить
        </Button>
      ) : (
        <Button variant="primary" icon="live" onClick={connect}>
          Подключить
        </Button>
      )}
      <Help placement="bottom-start" width={320} label="Как подключить узел">
        Браузер подключается к <b>rosbridge</b> напрямую и читает <b>/resense/status</b> (std_msgs/String, JSON) — бэкенд не участвует.
        <br />
        rosbridge нет в образе ноды: запустите рядом с ней
        <br />
        <b>ros2 launch rosbridge_server rosbridge_websocket_launch.xml</b>
        <br />
        (пакет ros-humble-rosbridge-suite, порт 9090).
      </Help>
      {touched && !valid && <span className={styles.hint}>адрес вида ws://хост:9090</span>}
      <span className={styles.sp} />
      <LinkError snap={snap} onRetry={connect} />
      {snap.link !== 'error' && (
        <div className={styles.chips}>
          <Chip variant="outline" icon="live">
            /resense/status
          </Chip>
          {typeof snap.msg?.node?.input_topic === 'string' && <Chip variant="well">{snap.msg.node.input_topic}</Chip>}
        </div>
      )}
    </>
  );
}

function SimControls({ snap, feed, runs, runsLoading, runsError, onRetryRuns, run, onRun, speed, onSpeed, loop, onLoop }: SourceBarProps) {
  if (runsError) return <ErrorBanner compact title="Прогоны не загрузились" error={runsError} onRetry={onRetryRuns} className={styles.barFull} />;
  if (runsLoading || !runs)
    return (
      <div className={styles.barCenter}>
        <Spinner label="Прогоны загружаются" />
      </div>
    );
  if (!runs.length || !run)
    return (
      <div className={styles.noRuns}>
        <span className={styles.noRunsIc}>
          <Icon name="list" size={20} />
        </span>
        Нет обработанных прогонов
        <Help placement="bottom-start">
          Симуляция проигрывает готовый прогон. Создайте демо-запись или загрузите свою — после обработки она появится здесь.
        </Help>
        <span className={styles.sp} />
        <Button variant="outline" icon="upload" to="/upload">
          Загрузить
        </Button>
        <Button variant="primary" icon="sparkle" to="/upload?source=demo">
          Демо-запись
        </Button>
      </div>
    );

  const src = snap.source?.kind === 'sim' ? snap.source : null;
  const onThis = src?.runId === run.id;
  const running = onThis && (snap.link === 'connecting' || snap.link === 'open');
  const pos = onThis && typeof snap.msg?.pos === 'number' ? snap.msg.pos : null;
  const n = run.summary.n_frames;
  const start = (startPos?: number) => feed.start({ kind: 'sim', runId: run.id, speed, loop, startPos });

  return (
    <>
      <Select
        className={styles.runSel}
        label="Прогон"
        icon="list"
        value={run.id}
        onChange={(id) => {
          onRun(id);
          if (src && (snap.link === 'open' || snap.link === 'connecting')) feed.start({ kind: 'sim', runId: id, speed, loop });
        }}
        options={runs.map((r) => ({ value: r.id, label: r.name }))}
      />
      {running ? (
        <>
          {snap.paused ? (
            <IconButton icon="play" label="Продолжить" variant="dark" size="lg" tooltip aria-keyshortcuts="Space" onClick={() => feed.play()} />
          ) : (
            <IconButton
              icon="pause"
              label="Пауза"
              variant="dark"
              size="lg"
              tooltip
              aria-keyshortcuts="Space"
              onClick={() => feed.pause()}
              disabled={snap.link !== 'open'}
            />
          )}
          <IconButton icon="x" label="Остановить эфир" variant="outline" size="lg" tooltip onClick={() => feed.stop()} />
        </>
      ) : (
        <Button variant="primary" icon="play" aria-keyshortcuts="Space" onClick={() => start(snap.link === 'ended' || !onThis ? 0 : (pos ?? 0))}>
          Запустить
        </Button>
      )}
      <Segmented
        size="sm"
        label="Скорость"
        value={String(speed)}
        onChange={(v) => {
          const s = Number(v);
          onSpeed(s);
          feed.setSpeed(s);
        }}
        options={SPEEDS.map((s) => ({
          value: String(s),
          label: speedLabel(s),
        }))}
      />
      <IconButton
        icon="loop"
        label={loop ? 'По кругу: вкл.' : 'По кругу: выкл.'}
        tooltip
        active={loop}
        onClick={() => {
          onLoop(!loop);
          feed.setLoop(!loop);
        }}
      />
      <div className={styles.seek}>
        <DecisionStrip
          decisions={run.summary.decisions}
          height={22}
          radius={8}
          playhead={pos}
          onSeek={(p) => feed.seek(p, { runId: run.id, speed, loop })}
          posLabel={(p) => `кадр ${fmtInt(p)}`}
          ariaLabel="Перемотка прогона"
        />
      </div>
      <div className={styles.frame}>
        <span className="num">{pos === null ? '—' : fmtInt(pos)}</span>
        <small>/ {fmtInt(n)}</small>
      </div>
      <Help placement="bottom-end" width={300} label="Как работает симуляция">
        Бэкенд проигрывает готовый прогон как живой узел: кадр за кадром с частотой <b>10 Гц × скорость</b>, с теми же полями, что и /resense/status. Клик по
        полосе — перемотка, <b>пробел</b> — пуск и пауза.
      </Help>
      <LinkError snap={snap} onRetry={() => start(pos ?? 0)} />
    </>
  );
}
