// Прогоны (/runs): every run of the detector — search, filters (STOP / no STOP / labels / source),
// sorting, inline rename, delete, and a floating «Сравнить (N)» when 2–4 runs are ticked.
// Filters live in the URL (?q=&f=&kind=&sort=) so «back» from a run returns to the same list.
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useRenameRun, useRuns, useSystem } from '../../api/hooks';
import type { Run } from '../../api/types';
import {
  Button,
  Card,
  Chip,
  DecisionStrip,
  EmptyState,
  ErrorBanner,
  Help,
  IconButton,
  PageHeader,
  Segmented,
  Select,
  TextInput,
} from '../../components';
import { RUNS, fmtCount, fmtDuration, fmtFrames, fmtNum, fmtRelDate } from '../../lib/format';
import {
  KIND_LABEL,
  MAX_COMPARE,
  compareUrl,
  episodesText,
  filterRuns,
  matchesFilter,
  playerUrl,
  reconnect,
  runUrl,
  type KindFilter,
  type RunFilter,
  type RunSort,
} from './common/analysis';
import { Check, EvalChip, Skeleton } from './common/Bits';
import { Menu } from './common/Menu';
import { useMedia } from './common/useMedia';
import { DeleteDialog } from './common/RunDialogs';
import { useUrlParams } from './common/useUrlParams';
import styles from './Runs.module.css';

const FILTERS: readonly RunFilter[] = ['all', 'stop', 'nostop', 'labels'];
const FILTER_LABEL: Record<RunFilter, string> = { all: 'Все', stop: 'Со СТОП', nostop: 'Без СТОП', labels: 'С разметкой' };
const SORTS: readonly RunSort[] = ['date', 'name', 'frames'];
const KINDS: readonly KindFilter[] = ['all', 'rosbag2', 'npy', 'jsonl'];
/** the search box writes the URL this long after the last keystroke */
const SEARCH_DEBOUNCE_MS = 250;
/** the ticked runs survive a trip to /compare and «back» (per tab) */
const SELECTION_KEY = 'resense.runs.selected';

function loadSelection(): string[] {
  try {
    const v: unknown = JSON.parse(window.sessionStorage.getItem(SELECTION_KEY) ?? '[]');
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string').slice(0, MAX_COMPARE) : [];
  } catch {
    return [];
  }
}

function pick<T extends string>(v: string | null, allowed: readonly T[], def: T): T {
  return allowed.includes(v as T) ? (v as T) : def;
}

/** Inline rename of a run's name: Enter saves, Escape cancels. */
function RenameInline({ run, onDone }: { run: Run; onDone: () => void }) {
  const rename = useRenameRun();
  const [name, setName] = useState(run.name);
  const trimmed = name.trim();
  const save = () => {
    if (!trimmed || trimmed === run.name) return onDone();
    rename.mutate({ id: run.id, name: trimmed }, { onSuccess: onDone });
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      save();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      onDone();
    }
  };
  return (
    <div className={styles.rename}>
      <TextInput
        autoFocus
        value={name}
        maxLength={200}
        invalid={!trimmed || rename.isError}
        aria-label="Новое название прогона"
        onChange={(e) => setName(e.target.value)}
        onKeyDown={onKey}
        onFocus={(e) => e.currentTarget.select()}
        className={styles.renameInput}
      />
      <IconButton icon="check" label="Сохранить" size="sm" variant="dark" loading={rename.isPending} disabled={!trimmed} onClick={save} />
      <IconButton icon="x" label="Отмена" size="sm" onClick={onDone} />
      {rename.isError && (
        <span className={styles.renameErr} role="alert">
          {rename.error.message}
        </span>
      )}
    </div>
  );
}

export default function Runs() {
  const runs = useRuns({ refetchInterval: reconnect });
  const sys = useSystem();
  const navigate = useNavigate();
  const [params, update] = useUrlParams();
  const q = params.get('q') ?? '';
  const filter = pick(params.get('f'), FILTERS, 'all');
  const kind = pick(params.get('kind'), KINDS, 'all');
  const sort = pick(params.get('sort'), SORTS, 'date');
  const [selected, setSelected] = useState<string[]>(loadSelection);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<Run | null>(null);
  const narrow = useMedia('(max-width: 1360px)');

  // the search box is local state (instant, never loses a keystroke); the URL follows it debounced
  const [text, setText] = useState(q);
  const pushed = useRef(q);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => {
    // the URL changed from outside (back / forward, «Сбросить фильтры»)
    if (q !== pushed.current) {
      pushed.current = q;
      setText(q);
    }
  }, [q]);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  useEffect(() => {
    try {
      window.sessionStorage.setItem(SELECTION_KEY, JSON.stringify(selected));
    } catch {
      // storage blocked: the selection just does not outlive the page
    }
  }, [selected]);
  const onSearch = (value: string) => {
    setText(value);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      pushed.current = value;
      update((p) => (value ? p.set('q', value) : p.delete('q')));
    }, SEARCH_DEBOUNCE_MS);
  };

  const setParam = (key: string, value: string, def: string) => update((p) => (value === def ? p.delete(key) : p.set(key, value)));
  const resetFilters = () => {
    window.clearTimeout(timer.current);
    setText('');
    pushed.current = '';
    update((p) => ['q', 'f', 'kind'].forEach((k) => p.delete(k)));
  };

  const all = useMemo(() => runs.data ?? [], [runs.data]);
  const list = useMemo(() => filterRuns(all, { q: text, filter, kind, sort }), [all, text, filter, kind, sort]);
  const counts = useMemo(() => Object.fromEntries(FILTERS.map((f) => [f, all.filter((r) => matchesFilter(r, f)).length])) as Record<RunFilter, number>, [all]);
  const kindsPresent = useMemo(() => new Set(all.map((r) => r.source_kind)), [all]);
  // ticked runs that still exist
  const chosen = selected.filter((id) => all.some((r) => r.id === id));
  const full = chosen.length >= MAX_COMPARE;
  const active = sys.data ? sys.data.counts.jobs_queued + sys.data.counts.jobs_running : 0;

  const toggle = (id: string) =>
    setSelected((s) => {
      const live = s.filter((x) => all.some((r) => r.id === x)); // drop runs deleted meanwhile
      return live.includes(id) ? live.filter((x) => x !== id) : live.length >= MAX_COMPARE ? live : [...live, id];
    });

  const onRowClick = (e: MouseEvent<HTMLTableRowElement>, r: Run) => {
    if ((e.target as HTMLElement).closest('button, a, input, label, [role="menu"]') || renaming === r.id) return;
    navigate(runUrl(r.id));
  };

  return (
    <>
      <PageHeader
        title="Прогоны"
        station={2}
        chips={
          <>
            {runs.data && <Chip variant="outline">{fmtCount(all.length, RUNS)}</Chip>}
            {active > 0 && (
              <Link to="/queue" className={styles.queueLink}>
                <Chip variant="ink" icon="queue">
                  {fmtNum(active)} в очереди
                </Chip>
              </Link>
            )}
          </>
        }
        actions={
          <Button variant="dark" icon="upload" to="/upload">
            Новая запись
          </Button>
        }
      />
      <Card className={styles.card} padding="none">
        {/* no filters to show before the first run */}
        {!(runs.data && all.length === 0) && (
          <div className={styles.toolbar}>
            <TextInput
              icon="search"
              placeholder="Название или пресет"
              aria-label="Поиск по названию"
              value={text}
              onChange={(e) => onSearch(e.target.value)}
              className={styles.search}
            />
            <Segmented<RunFilter>
              label="Фильтр прогонов"
              value={filter}
              onChange={(v) => setParam('f', v, 'all')}
              options={FILTERS.map((f) => ({ value: f, label: runs.data ? `${FILTER_LABEL[f]} ${counts[f]}` : FILTER_LABEL[f] }))}
            />
            <span className={styles.sp} />
            <Select<KindFilter>
              label="Источник"
              icon="file"
              value={kind}
              onChange={(v) => setParam('kind', v, 'all')}
              options={KINDS.map((k) => ({ value: k, label: k === 'all' ? 'Все источники' : KIND_LABEL[k], disabled: k !== 'all' && !kindsPresent.has(k) && kind !== k }))}
              className={styles.select}
            />
            <Select<RunSort>
              label="Сортировка"
              icon="bars"
              value={sort}
              onChange={(v) => setParam('sort', v, 'date')}
              options={[
                { value: 'date', label: 'Сначала новые' },
                { value: 'name', label: 'По названию' },
                { value: 'frames', label: 'По числу кадров' },
              ]}
              className={styles.select}
            />
          </div>
        )}

        <div className={styles.scroll}>
          {runs.isError && !runs.data ? (
            <div className={styles.pad}>
              <ErrorBanner error={runs.error} onRetry={() => void runs.refetch()} retrying={runs.isFetching} />
            </div>
          ) : runs.isLoading ? (
            <div className={styles.pad}>
              <Skeleton rows={7} height={48} />
            </div>
          ) : all.length === 0 ? (
            <div className={styles.center}>
              <EmptyState
                icon="list"
                title="Прогонов пока нет"
                action={
                  <div className={styles.row}>
                    <Button variant="dark" icon="upload" to="/upload">
                      Загрузить запись
                    </Button>
                    <Button variant="outline" icon="sparkle" to="/upload?source=demo">
                      Демо
                    </Button>
                  </div>
                }
              >
                Результат обработки записи появится здесь.
              </EmptyState>
            </div>
          ) : list.length === 0 ? (
            <div className={styles.center}>
              <EmptyState
                icon="search"
                title="Ничего не найдено"
                action={
                  <Button variant="outline" icon="x" onClick={resetFilters}>
                    Сбросить фильтры
                  </Button>
                }
              />
            </div>
          ) : (
            <table className={styles.table}>
              <colgroup>
                <col className={styles.cSel} />
                <col className={styles.cName} />
                <col className={styles.cStrip} />
                {!narrow && <col className={styles.cPreset} />}
                <col className={styles.cStop} />
                <col className={styles.cEval} />
                <col className={styles.cWhen} />
                <col className={styles.cAct} />
              </colgroup>
              <thead>
                <tr>
                  <th>
                    <span className="sr-only">Выбор для сравнения</span>
                  </th>
                  <th>Запись</th>
                  <th>Решения по кадрам</th>
                  {!narrow && <th>Пресет</th>}
                  <th>
                    <span className={styles.th}>
                      Первый СТОП
                      <Help placement="bottom" width={240}>
                        Дистанция до препятствия в первом кадре СТОП и число эпизодов СТОП.
                      </Help>
                    </span>
                  </th>
                  <th>
                    <span className={styles.th}>
                      Разметка
                      <Help placement="bottom" width={260}>
                        Детектор против ручной разметки: <b>верно</b> — СТОП на объекте (обнаружено / в габарите), <b>ложный СТОП</b> — на пустом пути.
                      </Help>
                    </span>
                  </th>
                  <th>Когда</th>
                  <th>
                    <span className="sr-only">Действия</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((r) => {
                  const s = r.summary;
                  const on = chosen.includes(r.id);
                  const fs = s.first_stop;
                  return (
                    <tr key={r.id} className={on ? styles.on : undefined} onClick={(e) => onRowClick(e, r)}>
                      <td>
                        <Check
                          checked={on}
                          disabled={full && !on}
                          onChange={() => toggle(r.id)}
                          aria-label={full && !on ? `Для сравнения выбрано ${MAX_COMPARE}` : `Выбрать для сравнения: ${r.name}`}
                        />
                      </td>
                      <td>
                        {renaming === r.id ? (
                          <RenameInline run={r} onDone={() => setRenaming(null)} />
                        ) : (
                          <>
                            <Link to={runUrl(r.id)} className={styles.nm} title={r.name}>
                              {r.name}
                            </Link>
                            <div className={styles.mt}>
                              {KIND_LABEL[r.source_kind]} · {fmtFrames(s.n_frames)} · {fmtDuration(s.duration_s)}
                              {narrow ? ` · ${r.preset.name}` : ''}
                            </div>
                          </>
                        )}
                      </td>
                      <td>
                        <DecisionStrip decisions={s.decisions} height={22} ariaLabel={`Решения по кадрам: ${r.name}`} />
                      </td>
                      {!narrow && (
                        <td>
                          <Chip variant="outline" size="sm" icon="sliders" className={styles.preset} title={r.preset.name}>
                            <span className={styles.ell}>{r.preset.name}</span>
                          </Chip>
                        </td>
                      )}
                      <td>
                        {fs ? (
                          <>
                            <div className={styles.big}>
                              {fs.distance !== null ? fmtNum(fs.distance, 1) : '—'}
                              {fs.distance !== null && <small>м</small>}
                            </div>
                            <div className={styles.mt}>
                              {episodesText(s.stop_episodes)} · кадр {fs.frame}
                            </div>
                          </>
                        ) : (
                          <span className={styles.none}>без СТОП</span>
                        )}
                      </td>
                      <td>
                        <EvalChip ev={s.eval} size="sm" />
                      </td>
                      <td className={styles.when}>{fmtRelDate(r.created_at)}</td>
                      <td>
                        <div className={styles.acts}>
                          <IconButton icon="play" label={`Открыть в плеере: ${r.name}`} size="sm" to={playerUrl(r.id)} />
                          <IconButton icon="arrow-right" label={`Открыть прогон ${r.name}`} size="sm" variant="dark" to={runUrl(r.id)} />
                          <Menu
                            label={`Действия: ${r.name}`}
                            size="sm"
                            items={[
                              { label: 'Переименовать', icon: 'edit', onSelect: () => setRenaming(r.id) },
                              { label: 'Удалить', icon: 'trash', onSelect: () => setDeleting(r) },
                            ]}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {chosen.length > 0 && (
          <div className={styles.bar} role="region" aria-label="Выбранные прогоны">
            <span className={styles.barN}>{chosen.length}</span>
            <div className={styles.barNames}>
              {chosen.map((id) => {
                const r = all.find((x) => x.id === id);
                return (
                  <span key={id} className={styles.barChip} title={r?.name}>
                    <span className={styles.ell}>{r?.name ?? id}</span>
                    <button type="button" aria-label={`Убрать ${r?.name ?? id}`} onClick={() => toggle(id)}>
                      ×
                    </button>
                  </span>
                );
              })}
            </div>
            {chosen.length < 2 && (
              <Help tone="light" placement="top" width="auto">
                Выберите от 2 до {MAX_COMPARE} прогонов
              </Help>
            )}
            <Button variant="ghost-light" size="sm" onClick={() => setSelected([])}>
              Сбросить
            </Button>
            <Button variant="outline" size="sm" icon="compare" disabled={chosen.length < 2} to={compareUrl(chosen)}>
              Сравнить ({chosen.length})
            </Button>
          </div>
        )}
      </Card>
      <DeleteDialog
        run={deleting}
        onClose={() => setDeleting(null)}
        onDeleted={(id) => setSelected((s) => s.filter((x) => x !== id))}
      />
    </>
  );
}
