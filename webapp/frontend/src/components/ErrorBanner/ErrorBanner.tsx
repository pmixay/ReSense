// An error line in the FAULT palette (violet), with an optional retry. `offline` = the backend
// cannot be reached.
import type { ReactNode } from 'react';
import { ApiError, OFFLINE_MESSAGE, errorMessage } from '../../api/client';
import { Button } from '../Button/Button';
import { Icon } from '../Icon/Icon';
import styles from './ErrorBanner.module.css';

export interface ErrorBannerProps {
  /** an Error / ApiError, or the message itself */
  error?: unknown;
  title?: ReactNode;
  offline?: boolean;
  onRetry?: () => void;
  retrying?: boolean;
  compact?: boolean;
  className?: string;
}

export function ErrorBanner({ error, title, offline, onRetry, retrying, compact, className }: ErrorBannerProps) {
  const isOffline = offline ?? (error instanceof ApiError && error.offline);
  let message = typeof error === 'string' ? error : error !== undefined && error !== null ? errorMessage(error) : undefined;
  if (isOffline && (message === undefined || message === OFFLINE_MESSAGE)) message = 'Проверьте, что сервер запущен — страница переподключится сама.';
  return (
    <div className={[styles.banner, compact ? styles.compact : '', className].filter(Boolean).join(' ')} role="alert">
      <span className={styles.icon}>
        <Icon name={isOffline ? 'wifi-off' : 'fault-circle'} size={compact ? 16 : 18} strokeWidth={2.4} />
      </span>
      <div className={styles.body}>
        <div className={styles.title}>{title ?? (isOffline ? 'Бэкенд недоступен' : 'Ошибка')}</div>
        {message && message !== title && <div className={styles.msg}>{message}</div>}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" icon="retry" onClick={onRetry} loading={retrying}>
          Повторить
        </Button>
      )}
    </div>
  );
}
