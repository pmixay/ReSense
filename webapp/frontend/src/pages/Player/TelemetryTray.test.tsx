// @vitest-environment jsdom
import { act, fireEvent, render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { TelemetryTray } from './TelemetryTray';

describe('fixed-scene telemetry tray', () => {
  it('reveals with wheel, range and touch without consuming playback gestures', () => {
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
    const workspace = createRef<HTMLDivElement>();
    render(<div ref={workspace}><TelemetryTray workspaceRef={workspace}><p>Information</p></TelemetryTray><div data-player-persistent><button>Play</button></div></div>);
    const range = screen.getByRole('slider', { name: 'Показать телеметрию' }) as HTMLInputElement;
    const panel = screen.getByText('Information').parentElement!;
    expect(range.value).toBe('0');
    expect(panel.getAttribute('aria-hidden')).toBe('true');
    fireEvent.wheel(workspace.current!, { deltaY: 100 });
    expect(range.value).toBe('100');
    expect(panel.getAttribute('aria-hidden')).toBe('false');
    fireEvent.wheel(screen.getByText('Play'), { deltaY: -100 });
    expect(range.value).toBe('100');
    fireEvent.wheel(workspace.current!, { deltaY: -100 });
    expect(range.value).toBe('0');
    fireEvent.change(range, { target: { value: '35' } });
    expect(range.value).toBe('35');
    const handle = range.parentElement!;
    fireEvent.touchStart(handle, { touches: [{ clientY: 200 }] });
    fireEvent.touchMove(handle, { touches: [{ clientY: 100 }] });
    expect(range.value).toBe('100');
    fireEvent.touchEnd(handle);
    act(() => { fireEvent.change(range, { target: { value: '0' } }); });
    fireEvent.wheel(workspace.current!, { deltaY: 100, ctrlKey: true });
    expect(range.value).toBe('0');
    vi.unstubAllGlobals();
  });
});
