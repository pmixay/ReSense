// A round icon button that asks once before a destructive action: the first click turns it into a
// small «…?» pill for a few seconds, the second click runs the action.
import { useEffect, useState } from 'react';
import { Button, IconButton, type IconButtonProps, type IconName } from '../../components';

export interface ConfirmButtonProps {
  icon: IconName;
  /** accessible name / tooltip of the idle button ("Отменить обработку") */
  label: string;
  /** text of the confirming pill ("Отменить?") */
  confirm: string;
  onConfirm: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: IconButtonProps['variant'];
  size?: IconButtonProps['size'];
}

const ARM_MS = 3500;

export function ConfirmButton({ icon, label, confirm, onConfirm, loading, disabled, variant = 'well', size = 'sm' }: ConfirmButtonProps) {
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    if (!armed) return;
    const t = window.setTimeout(() => setArmed(false), ARM_MS);
    return () => window.clearTimeout(t);
  }, [armed]);

  if (armed || loading) {
    return (
      <Button
        variant="dark"
        size="sm"
        icon={icon}
        loading={loading}
        onClick={() => {
          setArmed(false);
          onConfirm();
        }}
        onBlur={() => setArmed(false)}
        autoFocus
      >
        {confirm}
      </Button>
    );
  }
  return <IconButton icon={icon} label={label} tooltip variant={variant} size={size} disabled={disabled} onClick={() => setArmed(true)} />;
}
