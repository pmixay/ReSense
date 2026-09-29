// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DecisionStrip } from './DecisionStrip';

describe('DecisionStrip', () => {
  it('is a slider when seekable: keys and clicks seek', () => {
    const onSeek = vi.fn();
    render(<DecisionStrip decisions={'GGGGSSSSSC'} playhead={4} onSeek={onSeek} />);
    const slider = screen.getByRole('slider');
    expect(slider.getAttribute('aria-valuemax')).toBe('9');
    expect(slider.getAttribute('aria-valuenow')).toBe('4');
    expect(slider.getAttribute('aria-valuetext')).toContain('стоп');
    fireEvent.keyDown(slider, { key: 'ArrowRight' });
    expect(onSeek).toHaveBeenLastCalledWith(5);
    fireEvent.keyDown(slider, { key: 'Home' });
    expect(onSeek).toHaveBeenLastCalledWith(0);
    fireEvent.keyDown(slider, { key: 'End' });
    expect(onSeek).toHaveBeenLastCalledWith(9);

    slider.getBoundingClientRect = () => ({ left: 100, width: 200, top: 0, height: 22, right: 300, bottom: 22, x: 100, y: 0, toJSON: () => ({}) });
    fireEvent.pointerDown(slider, { clientX: 250, button: 0, pointerId: 1 });
    expect(onSeek).toHaveBeenLastCalledWith(7); // 150 / 200 · 10 frames
  });

  it('is a plain image without onSeek, with markers and ticks', () => {
    render(<DecisionStrip decisions={'G'.repeat(201)} markers={[{ pos: 8, label: 'кадр 8', tone: 'stop' }]} ticks tickUnit="кадр" />);
    expect(screen.queryByRole('slider')).toBeNull();
    expect(screen.getByRole('img', { name: 'Решения по кадрам' })).toBeTruthy();
    expect(screen.getByText('кадр 8')).toBeTruthy();
    expect(screen.getByText('0 кадр')).toBeTruthy();
    expect(screen.getByText('200')).toBeTruthy();
  });
});
