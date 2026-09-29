// @vitest-environment jsdom
import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { Job } from '../../api/types';
import { LabelsTagChip, VerdictChip } from '../Overview/Verdict';
import { ConfirmButton } from './ConfirmButton';
import { groupJobs } from './jobs';
import { CountChips } from './QueueParts';

const job = (id: string, status: Job['status']) => ({ id, status, position: null }) as Job;
const text = (el: HTMLElement) => el.textContent?.replace(/ /g, ' ');

describe('CountChips', () => {
  it('counts running / waiting / done jobs and shows errors only when there are some', () => {
    const { container, rerender } = render(<CountChips groups={groupJobs([job('r', 'running'), job('q', 'queued'), job('d', 'done')])} />);
    expect(text(container)).toBe('1 в работе1 ждёт1 готово');
    rerender(<CountChips groups={groupJobs([job('f1', 'failed'), job('f2', 'failed'), job('c', 'cancelled')])} />);
    expect(text(container)).toContain('2 ошибки');
  });
});

describe('VerdictChip / LabelsTagChip', () => {
  it('renders the verdict text, a STOP count as a decision chip, the labels tag', () => {
    const { container, rerender } = render(<VerdictChip verdict={{ kind: 'bad', text: 'ложный СТОП ×2' }} />);
    expect(text(container)).toBe('ложный СТОП ×2');
    rerender(<VerdictChip verdict={{ kind: 'stops', episodes: 3 }} />);
    expect(text(container)).toBe('СТОП×3');
    rerender(<VerdictChip verdict={{ kind: 'stops', episodes: 0 }} />);
    expect(text(container)).toBe('БЕЗ СТОП');
    rerender(<LabelsTagChip tag={{ kind: 'object', text: 'препятствие' }} />);
    expect(text(container)).toBe('препятствие');
  });
});

describe('ConfirmButton', () => {
  it('asks once, then runs the action; disarms by itself', () => {
    vi.useFakeTimers();
    const onConfirm = vi.fn();
    render(<ConfirmButton icon="x" label="Отменить обработку" confirm="Отменить?" onConfirm={onConfirm} />);
    fireEvent.click(screen.getByRole('button', { name: 'Отменить обработку' }));
    expect(onConfirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Отменить?' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Отменить обработку' }));
    act(() => vi.advanceTimersByTime(4000));
    expect(screen.getByRole('button', { name: 'Отменить обработку' })).toBeTruthy();
    expect(onConfirm).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});
