// @vitest-environment jsdom
import { act, render } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { useUrlParams, type UpdateParams } from './useUrlParams';

function Probe({ onReady }: { onReady: (update: UpdateParams) => void }) {
  const [, update] = useUrlParams();
  const loc = useLocation();
  onReady(update);
  return <output data-testid="search">{loc.search}</output>;
}

describe('useUrlParams', () => {
  it('applies quick successive updates on top of each other, commas kept readable', () => {
    let update: UpdateParams = () => undefined;
    const { getByTestId } = render(
      <MemoryRouter initialEntries={['/compare?runs=a,b']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Probe onReady={(u) => (update = u)} />
      </MemoryRouter>,
    );
    // two updates in one tick (before the router commits the first)
    act(() => {
      update((p) => p.set('runs', `${p.get('runs')},c`));
      update((p) => p.set('sort', 'name'));
    });
    expect(getByTestId('search').textContent).toBe('?runs=a,b,c&sort=name');
    act(() => update((p) => ['runs', 'sort'].forEach((k) => p.delete(k))));
    expect(getByTestId('search').textContent).toBe('');
  });
});
