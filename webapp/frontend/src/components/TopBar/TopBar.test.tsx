// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TopBar } from './TopBar';

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <TopBar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('TopBar', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('offline'))));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('marks the group of the current page and shows the backend offline', async () => {
    renderAt('/queue');
    const data = screen.getByRole('button', { name: /Данные/ });
    expect(data.className).toMatch(/active/);
    expect(await screen.findByText('бэкенд офлайн')).toBeTruthy();
  });

  it('opens a menu from the keyboard, moves with arrows and closes on Escape', async () => {
    renderAt('/');
    const sys = screen.getByRole('button', { name: /Система/ });
    expect(sys.getAttribute('aria-expanded')).toBe('false');
    act(() => sys.focus());
    fireEvent.keyDown(sys, { key: 'ArrowDown' });
    expect(sys.getAttribute('aria-expanded')).toBe('true');
    const menu = screen.getByRole('menu', { name: 'Система' });
    const items = Array.from(menu.querySelectorAll('[role="menuitem"]'));
    expect(items.map((i) => i.textContent)).toEqual([
      expect.stringContaining('Прямой эфир'),
      expect.stringContaining('Параметры'),
      expect.stringContaining('О системе'),
    ]);
    expect(document.activeElement).toBe(items[0]);
    fireEvent.keyDown(menu, { key: 'ArrowDown' });
    expect(document.activeElement).toBe(items[1]);
    fireEvent.keyDown(menu, { key: 'ArrowUp' });
    fireEvent.keyDown(menu, { key: 'ArrowUp' });
    expect(document.activeElement).toBe(items[2]);
    fireEvent.keyDown(menu, { key: 'Escape' });
    expect(sys.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(sys);
  });

  it('moves to the neighbouring group with ArrowRight while open', () => {
    renderAt('/');
    const data = screen.getByRole('button', { name: /Данные/ });
    const analysis = screen.getByRole('button', { name: /Анализ/ });
    fireEvent.click(data);
    expect(data.getAttribute('aria-expanded')).toBe('true');
    fireEvent.keyDown(screen.getByRole('menu', { name: 'Данные' }), { key: 'ArrowRight' });
    expect(data.getAttribute('aria-expanded')).toBe('false');
    expect(analysis.getAttribute('aria-expanded')).toBe('true');
  });
});
