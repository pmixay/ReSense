// Rename and delete of a run, each in a small dialog (shared by the runs list and the run page).
import { useEffect, useState, type FormEvent } from 'react';
import { useDeleteRun, useRenameRun } from '../../../api/hooks';
import type { Run } from '../../../api/types';
import { Button, ErrorBanner, TextInput } from '../../../components';
import { fmtFrames } from '../../../lib/format';
import { Dialog } from './Dialog';

export function RenameDialog({ run, onClose }: { run: Pick<Run, 'id' | 'name'> | null; onClose: () => void }) {
  const rename = useRenameRun();
  const [name, setName] = useState('');
  useEffect(() => {
    if (run) {
      setName(run.name);
      rename.reset();
    }
    // reset only when another run opens
  }, [run?.id]);
  const trimmed = name.trim();
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!run || !trimmed) return;
    if (trimmed === run.name) return onClose();
    rename.mutate({ id: run.id, name: trimmed }, { onSuccess: onClose });
  };
  return (
    <Dialog open={!!run} title="Переименовать прогон" onClose={onClose}>
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <TextInput
          icon="edit"
          value={name}
          maxLength={200}
          aria-label="Название прогона"
          invalid={!trimmed}
          onChange={(e) => setName(e.target.value)}
          onFocus={(e) => e.currentTarget.select()}
        />
        {rename.isError && <ErrorBanner error={rename.error} compact />}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <Button variant="outline" onClick={onClose}>
            Отмена
          </Button>
          <Button variant="dark" type="submit" icon="check" loading={rename.isPending} disabled={!trimmed}>
            Сохранить
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export function DeleteDialog({ run, onClose, onDeleted }: { run: Run | null; onClose: () => void; onDeleted?: (id: string) => void }) {
  const del = useDeleteRun();
  useEffect(() => {
    if (run) del.reset();
    // reset only when another run opens
  }, [run?.id]);
  return (
    <Dialog
      open={!!run}
      title={run ? `Удалить «${run.name}»?` : ''}
      onClose={onClose}
      initialFocus="button[data-autofocus]"
      actions={
        <>
          <Button variant="outline" onClick={onClose} data-autofocus="">
            Отмена
          </Button>
          <Button
            variant="dark"
            icon="trash"
            loading={del.isPending}
            onClick={() =>
              run &&
              del.mutate(run.id, {
                onSuccess: () => {
                  onClose();
                  onDeleted?.(run.id);
                },
              })
            }
          >
            Удалить
          </Button>
        </>
      }
    >
      {run && <span>{fmtFrames(run.summary.n_frames)} и облака точек удалятся, запись останется.</span>}
      {del.isError && <ErrorBanner error={del.error} compact />}
    </Dialog>
  );
}
