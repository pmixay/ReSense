// Параметры: detector presets. The sealed «Стандарт 1.0» (configs/default.yaml) and user presets;
// the editor is built from GET /api/presets/schema (20 parameters in 7 groups), stores only what
// differs from the default, keeps unsaved edits per preset while you switch, and shows the backend's
// validation errors at the parameter they name. «Обработать с этим пресетом» → /upload?preset=<id>.
import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useCreatePreset, useDeletePreset, usePresetSchema, usePresets, useUpdatePreset } from '../../api/hooks';
import type { ParamSpec, ParamValue, Preset } from '../../api/types';
import { Button, Chip, EmptyState, ErrorBanner, PageHeader, Spinner, Tooltip } from '../../components';
import { PRESETS, fmtCount } from '../../lib/format';
import { EditorHead } from './EditorHead';
import {
  NEW_ID,
  balanceColumns,
  changedKeys,
  defaultsOf,
  draftOf,
  groupSpecs,
  isNameError,
  overridesOf,
  paramOfError,
  sameDraft,
  uniqueName,
  type Draft,
} from './model';
import { ParamGroup } from './ParamGroup';
import { PresetStrip, stripItems } from './PresetStrip';
import { useWidth } from './useWidth';
import styles from './Presets.module.css';

const STANDARD = 'standard';

export default function Presets() {
  const presets = usePresets({ retry: false });
  const schema = usePresetSchema({ retry: false });
  const [params, setParams] = useSearchParams();
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const create = useCreatePreset();
  const update = useUpdatePreset();
  const remove = useDeletePreset();

  const list = presets.data;
  const specs: ParamSpec[] = useMemo(() => schema.data ?? [], [schema.data]);
  const wanted = params.get('id') ?? STANDARD;
  const selectedId = wanted === NEW_ID ? (drafts[NEW_ID] ? NEW_ID : STANDARD) : list?.some((p) => p.id === wanted) ? wanted : STANDARD;
  const preset = list?.find((p) => p.id === selectedId);
  const isNew = selectedId === NEW_ID;
  const base: Draft | null = isNew ? null : preset && specs.length ? draftOf(preset, specs) : null;
  const draft: Draft | null = drafts[selectedId] ?? base;
  const dirty = isNew || (!!draft && !!base && !sameDraft(draft, base, specs));
  const builtin = !!preset?.builtin && !isNew;
  const changed = draft ? changedKeys(draft.values, specs).size : 0;

  const select = (id: string) => {
    create.reset();
    update.reset();
    setParams(id === STANDARD ? {} : { id }, { replace: true });
  };
  const edit = (next: Partial<Draft>) => {
    if (!draft || builtin) return;
    update.reset();
    create.reset();
    setDrafts((d) => ({ ...d, [selectedId]: { ...draft, ...next } }));
  };
  const setValue = (key: string, v: ParamValue) => draft && edit({ values: { ...draft.values, [key]: v } });
  const dropDraft = (id: string) =>
    setDrafts((d) => {
      const rest = { ...d };
      delete rest[id];
      return rest;
    });
  const takenNames = (list ?? []).map((p) => p.name);
  const startNew = (from: Draft | null, name: string) => {
    setDrafts((d) => ({
      ...d,
      [NEW_ID]: { name: uniqueName(name, takenNames), description: from?.description ?? '', values: from ? { ...from.values } : defaultsOf(specs) },
    }));
    select(NEW_ID);
  };

  const save = () => {
    if (!draft) return;
    const body = { name: draft.name.trim(), description: draft.description.trim(), overrides: overridesOf(draft.values, specs) };
    if (isNew)
      create.mutate(body, {
        onSuccess: (p) => {
          dropDraft(NEW_ID);
          select(p.id);
        },
      });
    else if (preset) update.mutate({ id: preset.id, patch: body }, { onSuccess: () => dropDraft(preset.id) });
  };
  const del = () => {
    if (!preset || builtin) return;
    remove.mutate(preset.id, {
      onSuccess: () => {
        dropDraft(preset.id);
        select(STANDARD);
      },
    });
  };

  // backend errors: at the parameter they name, at the name field, or as a banner
  const saveError = (isNew ? create.error : update.error) ?? null;
  const message = saveError?.message ?? '';
  const errKey = saveError ? paramOfError(message, specs.map((s) => s.key)) : null;
  const nameError = saveError && !errKey && isNameError(message) ? message : null;
  const bannerError = saveError && !errKey && !nameError ? saveError : remove.error;

  const changedOf = (p: Preset) => changedKeys((drafts[p.id] ?? draftOf(p, specs)).values, specs).size;
  const dirtyOf = (id: string) => {
    const d = drafts[id];
    const p = list?.find((x) => x.id === id);
    return !!d && !!p && !sameDraft(d, draftOf(p, specs), specs);
  };
  const fresh = drafts[NEW_ID];
  const items = list ? stripItems(list, changedOf, dirtyOf, fresh ? { name: fresh.name || 'Новый пресет', changed: changedKeys(fresh.values, specs).size } : null) : [];

  const loading = presets.isLoading || schema.isLoading;
  const loadError = presets.error ?? schema.error;
  const processTip = isNew ? 'Сначала создайте пресет' : dirty ? 'Сначала сохраните изменения' : null;

  return (
    <>
      <PageHeader
        title="Параметры"
        station={3}
        chips={
          <>
            {list && <Chip variant="outline">{fmtCount(list.length, PRESETS)}</Chip>}
            {specs.length > 0 && <Chip variant="outline">{specs.length} параметров детектора</Chip>}
          </>
        }
        actions={
          preset || isNew ? (
            <Tooltip content={processTip ?? ''} width="auto" disabled={!processTip}>
              <span className={styles.saveWrap}>
                <Button variant="dark" icon="play" to={`/upload?preset=${encodeURIComponent(selectedId)}`} disabled={!!processTip}>
                  Обработать с этим пресетом
                </Button>
              </span>
            </Tooltip>
          ) : undefined
        }
      />
      <section className={`fill-viewport ${styles.page}`}>
        {loadError ? (
          <div className={styles.state}>
            <ErrorBanner
              error={loadError}
              onRetry={() => {
                void presets.refetch();
                void schema.refetch();
              }}
              retrying={presets.isFetching || schema.isFetching}
            />
          </div>
        ) : loading || !list ? (
          <div className={styles.state}>
            <Spinner size={28} label="Пресеты загружаются" />
          </div>
        ) : (
          <>
            <PresetStrip items={items} selected={selectedId} onSelect={select} onNew={() => startNew(null, 'Новый пресет')} />
            {!draft ? (
              <div className={styles.state}>
                <EmptyState icon="sliders" title="Параметров нет" action={<Button variant="outline" icon="retry" onClick={() => void schema.refetch()}>Обновить</Button>} />
              </div>
            ) : (
              <>
                <EditorHead
                  draft={draft}
                  builtin={builtin}
                  isNew={isNew}
                  dirty={dirty}
                  changed={changed}
                  saving={create.isPending || update.isPending}
                  deleting={remove.isPending}
                  nameError={nameError}
                  onName={(name) => edit({ name })}
                  onDescription={(description) => edit({ description })}
                  onResetAll={() => edit({ values: defaultsOf(specs) })}
                  onRevert={() => {
                    dropDraft(selectedId);
                    create.reset();
                    update.reset();
                    if (isNew) select(STANDARD);
                  }}
                  onDuplicate={() => startNew(draft, `${draft.name} (копия)`)}
                  onDelete={del}
                  onSave={save}
                />
                {bannerError && <ErrorBanner error={bannerError} title="Не сохранено" className={styles.banner} />}
                <Groups specs={specs} draft={draft} readOnly={builtin} errKey={errKey} error={errKey ? message : null} onChange={setValue} />
              </>
            )}
          </>
        )}
      </section>
    </>
  );
}

/** The parameter groups in balanced columns (3 on wide screens, 2 or 1 below), scrolling inside. */
function Groups({
  specs,
  draft,
  readOnly,
  errKey,
  error,
  onChange,
}: {
  specs: ParamSpec[];
  draft: Draft;
  readOnly: boolean;
  errKey: string | null;
  error: string | null;
  onChange: (key: string, v: ParamValue) => void;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const groups = useMemo(() => groupSpecs(specs), [specs]);
  const n = width >= 1080 ? 3 : width >= 700 ? 2 : 1;
  const columns = useMemo(() => balanceColumns(groups.map((g) => 76 + 50 * g.specs.length), n, 16), [groups, n]);
  return (
    <div ref={ref} className={styles.groups} style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}>
      {columns.map((col, c) => (
        <div key={c} className={styles.col}>
          {col.map((gi) => (
            <ParamGroup key={groups[gi].title} group={groups[gi]} values={draft.values} readOnly={readOnly} errorKey={errKey} error={error} onChange={onChange} />
          ))}
        </div>
      ))}
    </div>
  );
}
