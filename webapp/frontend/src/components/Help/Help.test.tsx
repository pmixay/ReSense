// @vitest-environment jsdom
import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Help } from './Help';

describe('Help', () => {
  it('describes the button by its tooltip and opens on hover, closes on Escape', () => {
    render(<Help>Шаг кадров: 1 — каждый кадр.</Help>);
    const btn = screen.getByRole('button', { name: 'Подсказка' });
    const tipId = btn.getAttribute('aria-describedby');
    expect(tipId).toBeTruthy();
    const tip = document.getElementById(tipId!)!;
    expect(tip.getAttribute('role')).toBe('tooltip');
    expect(tip.textContent).toContain('каждый кадр');
    expect(tip.hidden).toBe(true);

    fireEvent.mouseEnter(btn.parentElement!);
    expect(tip.hidden).toBe(false);
    expect(btn.getAttribute('data-tip-open')).toBe('true');

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(tip.hidden).toBe(true);
  });

  it('opens on keyboard focus and closes on blur', () => {
    vi.useFakeTimers();
    render(<Help>Текст</Help>);
    const btn = screen.getByRole('button', { name: 'Подсказка' });
    const tip = document.getElementById(btn.getAttribute('aria-describedby')!)!;
    act(() => btn.focus());
    expect(tip.hidden).toBe(false);
    act(() => btn.blur());
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(tip.hidden).toBe(true);
    vi.useRealTimers();
  });

  it('keeps one tooltip open per screen', () => {
    render(
      <>
        <Help>Первая</Help>
        <Help>Вторая</Help>
      </>,
    );
    const [a, b] = screen.getAllByRole('button', { name: 'Подсказка' });
    const tipA = document.getElementById(a.getAttribute('aria-describedby')!)!;
    const tipB = document.getElementById(b.getAttribute('aria-describedby')!)!;
    fireEvent.click(a);
    expect(tipA.hidden).toBe(false);
    fireEvent.click(b);
    expect(tipB.hidden).toBe(false);
    expect(tipA.hidden).toBe(true);
  });
});
