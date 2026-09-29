// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { LineRail } from './LineRail';

const at = (path: string, sub?: string) =>
  render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <LineRail sub={sub} />
    </MemoryRouter>,
  );

describe('LineRail', () => {
  it('marks the current station, with a sub label', () => {
    at('/runs/abc', 'doubleT_obstacle');
    const cur = screen.getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page');
    expect(cur).toHaveLength(1);
    expect(cur[0].textContent).toBe('Прогоны/ doubleT_obstacle');
  });

  it('has no current station on the line for a Система page, and shows the branch', () => {
    const { container } = at('/presets');
    const cur = screen.getAllByRole('link').filter((a) => a.getAttribute('aria-current') === 'page');
    expect(cur.map((a) => a.textContent)).toEqual(['Параметры']);
    const nav = container.querySelector('nav')!;
    expect(nav.className).toMatch(/branched/);
  });

  it('shows no branch on the line pages', () => {
    const { container } = at('/');
    expect(container.querySelector('nav')!.className).not.toMatch(/branched/);
  });
});
