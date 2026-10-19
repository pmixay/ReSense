// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createMemoryRouter, RouterProvider, useLocation, useNavigate } from 'react-router-dom';
import { TrainDoors, useTrainDoors } from './TrainDoors';

function Harness() {
  const doors = useTrainDoors();
  const location = useLocation();
  const navigate = useNavigate();
  return <>
    <output>{location.pathname}{location.search}</output>
    <button onClick={() => navigate('/runs')}>Runs</button>
    <button onClick={() => navigate('/player/second?pos=20')}>Run switch</button>
    <button onClick={() => navigate(-1)}>Back</button>
    <TrainDoors phase={doors.phase} />
  </>;
}

function setup(reduced = false) {
  vi.useFakeTimers();
  // Node's Request rejects jsdom's AbortSignal. There are no loaders/fetches here.
  const NativeRequest = globalThis.Request;
  vi.stubGlobal('Request', class extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) { super(input, { ...init, signal: undefined }); }
  });
  vi.stubGlobal('matchMedia', () => ({ matches: reduced, addEventListener() {}, removeEventListener() {} }));
  const router = createMemoryRouter([{ path: '*', element: <Harness /> }], { initialEntries: ['/player/first?pos=4'] });
  const view = render(<RouterProvider router={router} />);
  return { router, overlay: view.container.querySelector('[data-train-doors]')! };
}
async function advance(ms: number) { await act(async () => { await vi.advanceTimersByTimeAsync(ms); }); }

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

describe('train door navigation', () => {
  it('keeps the departing page until both leaves close, then opens over the destination', async () => {
    const { router, overlay } = setup();
    fireEvent.click(screen.getByText('Runs'));
    expect(overlay.getAttribute('data-phase')).toBe('closing');
    await advance(350);
    expect(router.state.location.pathname).toBe('/player/first');
    await advance(10);
    expect(router.state.location.pathname).toBe('/runs');
    expect(overlay.getAttribute('data-phase')).toBe('covered');
    await advance(100);
    expect(overlay.getAttribute('data-phase')).toBe('opening');
    await advance(460);
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });

  it('leaves run/seek URL edits immediate and animates Back to a different section', async () => {
    const { router, overlay } = setup();
    await act(async () => fireEvent.click(screen.getByText('Run switch')));
    expect(router.state.location.pathname).toBe('/player/second');
    expect(overlay.getAttribute('data-phase')).toBe('idle');
    fireEvent.click(screen.getByText('Runs'));
    await advance(360);
    await advance(100);
    await advance(460);
    fireEvent.click(screen.getByText('Back'));
    expect(overlay.getAttribute('data-phase')).toBe('closing');
    await advance(360);
    await advance(100);
    await advance(460);
    expect(router.state.location.pathname).toBe('/player/second');
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });

  it('uses a short non-spatial transition for reduced motion', async () => {
    const { router, overlay } = setup(true);
    fireEvent.click(screen.getByText('Runs'));
    await advance(75);
    expect(router.state.location.pathname).toBe('/runs');
    await advance(25);
    await advance(100);
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });

  it('keeps a suspended destination covered and releases after its chunk arrives', async () => {
    const { overlay } = setup();
    const fallback = document.createElement('div');
    fallback.dataset.pageFallback = '';
    document.body.append(fallback);
    fireEvent.click(screen.getByText('Runs'));
    await advance(360);
    await advance(300);
    expect(overlay.getAttribute('data-phase')).toBe('covered');
    fallback.remove();
    await advance(50);
    expect(overlay.getAttribute('data-phase')).toBe('opening');
    await advance(460);
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });
});
