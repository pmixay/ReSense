// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createMemoryRouter, RouterProvider, useLocation, useNavigate } from 'react-router-dom';
import { TrainDoors, useTrainDoors } from './TrainDoors';
vi.mock('../../sectionPages', () => ({ preloadSections: vi.fn() }));

function Harness({ isPrepared }: { isPrepared?: () => boolean }) {
  const doors = useTrainDoors({ isPrepared });
  const location = useLocation();
  const navigate = useNavigate();
  return <>
    <output>{location.pathname}{location.search}</output>
    <output data-journey>{JSON.stringify(doors.journey)}</output>
    <button onClick={() => navigate('/runs')}>Runs</button>
    <button onClick={() => navigate('/upload')}>Upload</button>
    <button onClick={() => navigate('/player/second?pos=20')}>Run switch</button>
    <button onClick={() => navigate(-1)}>Back</button>
    <button onClick={doors.finishTravel}>Travel finished</button>
    <TrainDoors phase={doors.phase} />
  </>;
}

function setup(reduced = false, initial = '/player/first?pos=4', isPrepared?: () => boolean) {
  vi.useFakeTimers();
  // Node's Request rejects jsdom's AbortSignal. There are no loaders/fetches here.
  const NativeRequest = globalThis.Request;
  vi.stubGlobal('Request', class extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) { super(input, { ...init, signal: undefined }); }
  });
  const listeners = new Set<() => void>();
  const media = { matches: reduced, addEventListener(_type: string, listener: () => void) { listeners.add(listener); }, removeEventListener(_type: string, listener: () => void) { listeners.delete(listener); } };
  vi.stubGlobal('matchMedia', () => media);
  const router = createMemoryRouter([{ path: '*', element: <Harness isPrepared={isPrepared} /> }], { initialEntries: [initial] });
  const view = render(<RouterProvider router={router} />);
  return { router, overlay: view.container.querySelector('[data-train-doors]')!, reduceMotion() { media.matches = true; listeners.forEach(listener => listener()); } };
}
async function advance(ms: number) { await act(async () => { await vi.advanceTimersByTimeAsync(ms); }); }
async function finishTransition() {
  for (const ms of [360, 25, 670]) await advance(ms);
  fireEvent.click(screen.getByText('Travel finished'));
  await advance(460);
}

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });

describe('train door navigation', () => {
  it('does not restart travel when preparation completes after the watchdog releases it', async () => {
    let ready = false;
    const { router, overlay } = setup(false, '/player/first', () => ready);
    fireEvent.click(screen.getByText('Runs'));
    await advance(270);
    await advance(11700);
    expect(overlay.getAttribute('data-phase')).toBe('covered');
    // Model a blocked main thread: the watchdog and the already queued readiness
    // poll run in one batch, before React can clean up the covered-phase effect.
    window.setTimeout(() => { ready = true; }, 31);
    await advance(100);
    expect(router.state.location.pathname).toBe('/runs');
    expect(overlay.getAttribute('data-phase')).toBe('idle');
    fireEvent.click(screen.getByText('Upload'));
    await finishTransition();
    expect(router.state.location.pathname).toBe('/upload');
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });

  it('closes before committing, then glides into the destination before opening', async () => {
    const { router, overlay } = setup();
    fireEvent.click(screen.getByText('Runs'));
    expect(overlay.getAttribute('data-phase')).toBe('closing');
    await advance(260);
    expect(router.state.location.pathname).toBe('/player/first');
    await advance(10);
    expect(router.state.location.pathname).toBe('/runs');
    expect(overlay.getAttribute('data-phase')).toBe('covered');
    await advance(25);
    expect(overlay.getAttribute('data-phase')).toBe('travelling');
    await advance(670);
    expect(overlay.getAttribute('data-phase')).toBe('travelling');
    fireEvent.click(screen.getByText('Travel finished'));
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
    await finishTransition();
    fireEvent.click(screen.getByText('Back'));
    expect(overlay.getAttribute('data-phase')).toBe('closing');
    await finishTransition();
    expect(router.state.location.pathname).toBe('/player/second');
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });

  it('uses a short non-spatial transition for reduced motion', async () => {
    const { router, overlay } = setup(true);
    fireEvent.click(screen.getByText('Runs'));
    await advance(75);
    expect(router.state.location.pathname).toBe('/runs');
    await advance(25);
    expect(overlay.getAttribute('data-phase')).toBe('opening');
    await advance(100);
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });

  it('releases a running journey when reduced motion is enabled mid-transition', async () => {
    const { overlay, reduceMotion } = setup();
    fireEvent.click(screen.getByText('Runs'));
    await advance(270);
    await advance(25);
    expect(overlay.getAttribute('data-phase')).toBe('travelling');
    act(() => reduceMotion());
    expect(overlay.getAttribute('data-phase')).toBe('opening');
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
    expect(overlay.getAttribute('data-phase')).toBe('travelling');
    await advance(670);
    fireEvent.click(screen.getByText('Travel finished'));
    expect(overlay.getAttribute('data-phase')).toBe('opening');
    await advance(460);
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });

  it('commits the most recently requested section during closing', async () => {
    const { router, overlay } = setup();
    fireEvent.click(screen.getByText('Runs'));
    await advance(150);
    fireEvent.click(screen.getByText('Upload'));
    await advance(210);
    expect(router.state.location.pathname).toBe('/upload');
    expect(overlay.getAttribute('data-phase')).toBe('covered');
    for (const ms of [25, 970]) await advance(ms);
    fireEvent.click(screen.getByText('Travel finished'));
    await advance(460);
    expect(overlay.getAttribute('data-phase')).toBe('idle');
  });

  it('reveals a persistent loading state instead of leaving doors stuck shut', async () => {
    const { router, overlay } = setup();
    const fallback = document.createElement('div');
    fallback.dataset.pageFallback = '';
    document.body.append(fallback);
    fireEvent.click(screen.getByText('Runs'));
    for (const ms of [360, 5100, 670]) await advance(ms);
    fireEvent.click(screen.getByText('Travel finished'));
    await advance(460);
    expect(router.state.location.pathname).toBe('/runs');
    expect(overlay.getAttribute('data-phase')).toBe('idle');
    fallback.remove();
  });

  it('passes Runs between Queue and Player and creates only the selected history entry', async () => {
    const { router, overlay } = setup(false, '/queue');
    fireEvent.click(screen.getByText('Run switch'));
    expect(JSON.parse(document.querySelector('[data-journey]')!.textContent!)).toMatchObject({ direction: 'right', via: ['runs'], steps: 2 });
    for (const ms of [360, 25, 820]) await advance(ms);
    fireEvent.click(screen.getByText('Travel finished'));
    await advance(460);
    expect(router.state.location.pathname).toBe('/player/second');
    expect(overlay.getAttribute('data-phase')).toBe('idle');
    fireEvent.click(screen.getByText('Back'));
    expect(JSON.parse(document.querySelector('[data-journey]')!.textContent!)).toMatchObject({ direction: 'left', via: ['runs'] });
    for (const ms of [360, 25, 820]) await advance(ms);
    fireEvent.click(screen.getByText('Travel finished'));
    await advance(460);
    expect(router.state.location.pathname).toBe('/queue');
  });
});
