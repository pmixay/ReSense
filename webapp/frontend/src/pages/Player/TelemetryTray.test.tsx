// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { TelemetryTray } from './TelemetryTray';

describe('side telemetry', () => {
  it('opens both sides only by button and closes with the button or Escape', () => {
    render(<TelemetryTray left={<p>Track</p>} right={<p>Health</p>} />);
    const button = screen.getByRole('button', { name: 'Телеметрия' });
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(screen.queryByRole('complementary')).toBeNull();
    fireEvent.wheel(button.parentElement!, { deltaY: 500 });
    fireEvent.touchStart(button.parentElement!, { touches: [{ clientY: 500 }] });
    fireEvent.touchMove(button.parentElement!, { touches: [{ clientY: 100 }] });
    expect(button.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(button);
    expect(screen.getByRole('complementary', { name: 'Телеметрия слева' }).textContent).toBe('Track');
    expect(screen.getByRole('complementary', { name: 'Телеметрия справа' }).textContent).toBe('Health');
    expect(button.getAttribute('aria-expanded')).toBe('true');
    fireEvent.wheel(button.parentElement!, { deltaY: -500 });
    expect(button.getAttribute('aria-expanded')).toBe('true');
    fireEvent.keyDown(screen.getByText('Health'), { key: 'Escape' });
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(button);
    fireEvent.click(button);
    fireEvent.click(button);
    expect(screen.queryByRole('complementary')).toBeNull();
  });
});
