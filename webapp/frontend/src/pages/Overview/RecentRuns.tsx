// «Последние прогоны»: the decision strip of each run, what its labels say, the verdict (detector vs
// labels, else its STOP count) and when; a row opens the run.
import { useNavigate } from 'react-router-dom';
import type { Run } from '../../api/types';
import { Button, Card, DecisionLegend, DecisionStrip, EmptyState, ErrorBanner, Help, IconButton, Spinner } from '../../components';
import { fmtDuration, fmtFrames, fmtRelDate } from '../../lib/format';
import { LabelsTagChip, VerdictChip } from './Verdict';
import { labelsTag, runVerdict } from './verdict';
import styles from './Overview.module.css';

export function RecentRuns({ runs, error, loading, retry }: { runs: Run[] | undefined; error: unknown; loading: boolean; retry: () => void }) {
  const navigate = useNavigate();
  const list = (runs ?? []).slice(0, 6);
  return (
    <Card
      title="Последние прогоны"
      help="Полоса — решение детектора в каждом кадре записи."
      helpPlacement="bottom-start"
      className={styles.runs}
      actions={
        <>
          <DecisionLegend className={styles.legend} />
          <Button variant="outline" size="sm" iconRight="arrow-right" to="/runs">
            Все прогоны
          </Button>
        </>
      }
    >
      {error ? (
        <ErrorBanner error={error} onRetry={retry} />
      ) : loading ? (
        <div className={styles.center}>
          <Spinner />
        </div>
      ) : list.length === 0 ? (
        <EmptyState
          icon="list"
          title="Прогонов пока нет"
          action={
            <Button variant="dark" icon="upload" to="/upload">
              Загрузить запись
            </Button>
          }
        >
          Загрузите запись или запустите демо — результат появится здесь.
        </EmptyState>
      ) : (
        <div className={styles.rtWrap}>
          <table className={styles.rt}>
            <colgroup>
              <col className={styles.cNm} />
              <col className={styles.cSt} />
              <col className={styles.cGt} />
              <col className={styles.cVd} />
              <col className={styles.cWh} />
              <col className={styles.cAr} />
            </colgroup>
            <thead>
              <tr>
                <th>Запись</th>
                <th>Решения по кадрам</th>
                <th>Разметка</th>
                <th>
                  <span className={styles.thHelp}>
                    Итог
                    <Help placement="top" width="auto">
                      Детектор против разметки:
                      <br />
                      <b>верно</b> — СТОП на объекте,
                      <br />
                      <b>ложный СТОП</b> — на пустом пути.
                      <br />
                      Без разметки — число эпизодов СТОП.
                    </Help>
                  </span>
                </th>
                <th className={styles.whH}>Когда</th>
                <th aria-label="Открыть" />
              </tr>
            </thead>
            <tbody>
              {list.map((r) => (
                <tr key={r.id} className={styles.rowLink} onClick={(e) => !(e.target as HTMLElement).closest('a,button') && navigate(`/runs/${r.id}`)}>
                  <td>
                    <div className={styles.nm} title={r.name}>
                      {r.name}
                    </div>
                    <div className={styles.mt}>
                      {fmtFrames(r.summary.n_frames)} · {fmtDuration(r.summary.duration_s)}
                    </div>
                  </td>
                  <td>
                    <DecisionStrip decisions={r.summary.decisions} height={22} />
                  </td>
                  <td>
                    <LabelsTagChip tag={labelsTag(r.summary)} />
                  </td>
                  <td>
                    <VerdictChip verdict={runVerdict(r.summary)} />
                  </td>
                  <td className={styles.wh}>{fmtRelDate(r.created_at)}</td>
                  <td>
                    <IconButton icon="arrow-right" label={`Открыть прогон ${r.name}`} to={`/runs/${r.id}`} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
