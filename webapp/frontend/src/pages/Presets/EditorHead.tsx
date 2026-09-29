// The editor's header card: the name and description (read-only for the sealed built-in), how many
// parameters differ from the standard, and the actions — revert, duplicate, delete (asks once), save.
import { useEffect, useState } from 'react';
import { Button, Chip, Help, Icon, IconButton, TextInput, Tooltip } from '../../components';
import type { Draft } from './model';
import styles from './Presets.module.css';

export interface EditorHeadProps {
  draft: Draft;
  builtin: boolean;
  isNew: boolean;
  dirty: boolean;
  changed: number;
  saving: boolean;
  deleting: boolean;
  nameError: string | null;
  onName: (name: string) => void;
  onDescription: (text: string) => void;
  onResetAll: () => void;
  onRevert: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onSave: () => void;
}

export function EditorHead(p: EditorHeadProps) {
  const blank = !p.draft.name.trim();
  return (
    <div className={styles.head}>
      {p.builtin ? (
        <div className={styles.sealed}>
          <span className={styles.lock}>
            <Icon name="lock" size={18} strokeWidth={2.4} />
          </span>
          <h2 className={styles.sealedName}>{p.draft.name}</h2>
          <Chip variant="ink" size="sm" icon="lock">
            опечатан
          </Chip>
          <Help placement="bottom-start" width={300} label="Что такое встроенный пресет">
            {p.draft.description || 'Параметры детектора по умолчанию.'} Изменить нельзя — дублируйте, чтобы попробовать свои значения.
          </Help>
        </div>
      ) : (
        <div className={styles.fields}>
          <div className={styles.nameField}>
            <TextInput
              icon="edit"
              value={p.draft.name}
              maxLength={80}
              aria-label="Название пресета"
              placeholder="Название"
              invalid={blank || !!p.nameError}
              onChange={(e) => p.onName(e.target.value)}
            />
            {(blank || p.nameError) && <span className={styles.fieldErr}>{blank ? 'Укажите название' : p.nameError}</span>}
          </div>
          <TextInput
            className={styles.descField}
            icon="info"
            value={p.draft.description}
            maxLength={1000}
            aria-label="Описание пресета"
            placeholder="Описание — по желанию"
            onChange={(e) => p.onDescription(e.target.value)}
          />
        </div>
      )}

      <div className={styles.diff}>
        <Chip variant={p.changed ? 'ink' : 'well'}>{p.changed ? `изменено ${p.changed}` : 'как стандарт'}</Chip>
        <Help placement="bottom" width={260} label="Что изменено">
          Сколько параметров отличается от «Стандарт 1.0». Такие строки обведены, «↺» возвращает значение по умолчанию.
        </Help>
        {!p.builtin && p.changed > 0 && <IconButton icon="retry" size="sm" label="Все к стандарту" tooltip onClick={p.onResetAll} />}
      </div>

      <span className={styles.sp} />

      <div className={styles.actions}>
        {p.dirty && !p.isNew && (
          <Button variant="ghost" icon="x" onClick={p.onRevert}>
            Отменить
          </Button>
        )}
        {!p.isNew && (
          <Button variant={p.builtin ? 'dark' : 'outline'} icon="copy" onClick={p.onDuplicate}>
            Дублировать
          </Button>
        )}
        {p.isNew && (
          <Button variant="ghost" icon="trash" onClick={p.onRevert}>
            Удалить черновик
          </Button>
        )}
        {!p.builtin && !p.isNew && <ConfirmDelete onConfirm={p.onDelete} loading={p.deleting} />}
        {!p.builtin && (
          <Tooltip content={blank ? 'Укажите название' : 'Изменений нет'} width="auto" disabled={p.dirty && !blank}>
            <span className={styles.saveWrap}>
              <Button variant="primary" icon="check" onClick={p.onSave} loading={p.saving} disabled={!p.dirty || blank}>
                {p.isNew ? 'Создать' : 'Сохранить'}
              </Button>
            </span>
          </Tooltip>
        )}
      </div>
    </div>
  );
}

const ARM_MS = 3500;

/** Trash icon that asks once: the first click turns it into «Удалить?», the second deletes. */
function ConfirmDelete({ onConfirm, loading }: { onConfirm: () => void; loading: boolean }) {
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    if (!armed) return;
    const t = window.setTimeout(() => setArmed(false), ARM_MS);
    return () => window.clearTimeout(t);
  }, [armed]);
  if (armed || loading)
    return (
      <Button
        variant="dark"
        icon="trash"
        loading={loading}
        autoFocus
        onBlur={() => setArmed(false)}
        onClick={() => {
          setArmed(false);
          onConfirm();
        }}
      >
        Удалить?
      </Button>
    );
  return <IconButton icon="trash" label="Удалить пресет" tooltip variant="outline" onClick={() => setArmed(true)} />;
}
