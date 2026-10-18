import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { ScreenDisplay } from './screenDisplay';

describe('modeled display projection', () => {
  it.each([[1366, 320, 1], [1840, 616, 2], [358, 240, 2]])('keeps the live surface and HUD pixel bounds aligned at %s×%s', (width, height, pr) => {
    const display = new ScreenDisplay();
    display.setSize(width, height, pr);
    display.camera.updateMatrixWorld();
    let active: THREE.Mesh | undefined;
    display.scene.traverse((object) => {
      if (object instanceof THREE.Mesh && object.material instanceof THREE.MeshBasicMaterial) active = object;
    });
    expect(active).toBeDefined();
    display.scene.updateMatrixWorld(true);
    const positions = active!.geometry.getAttribute('position');
    const uv = active!.geometry.getAttribute('uv');
    const rect = display.viewport;
    for (let i = 0; i < positions.count; i += 1) {
      const p = new THREE.Vector3().fromBufferAttribute(positions, i).applyMatrix4(active!.matrixWorld).project(display.camera);
      expect((p.x + 1) * width / 2).toBeCloseTo(rect.x + uv.getX(i) * rect.width, 3);
      expect((1 - p.y) * height / 2).toBeCloseTo(rect.y + (1 - uv.getY(i)) * rect.height, 3);
    }
    expect(display.target.width).toBe(Math.round(rect.width * pr));
    expect(display.target.height).toBe(Math.round(rect.height * pr));
    expect(rect.x).toBeGreaterThan(0);
    expect(rect.y).toBeGreaterThan(0);
    display.dispose();
  });

  it('releases the old mesh geometry on resize and the live texture on disposal', () => {
    const display = new ScreenDisplay();
    display.setSize(1280, 400, 1);
    const disposed = vi.fn();
    display.scene.traverse((object) => {
      if (object instanceof THREE.Mesh) object.geometry.addEventListener('dispose', disposed);
    });
    display.setSize(1400, 500, 2);
    expect(disposed).toHaveBeenCalledTimes(4);
    const targetDisposed = vi.fn();
    display.target.addEventListener('dispose', targetDisposed);
    display.dispose();
    expect(targetDisposed).toHaveBeenCalledOnce();
  });
});
