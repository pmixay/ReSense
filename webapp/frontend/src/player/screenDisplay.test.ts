import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { ScreenDisplay } from './screenDisplay';

describe('modeled display projection', () => {
  it.each([[1366, 320, 1], [1840, 616, 2], [358, 240, 2]])('keeps the live surface and HUD pixel bounds aligned at %s×%s', (width, height, pr) => {
    const display = new ScreenDisplay();
    display.setSize(width, height, pr);
    display.camera.updateMatrixWorld();
    const active = display.scene.getObjectByName('live-display-surface') as THREE.Mesh;
    expect(active).toBeDefined();
    display.scene.updateMatrixWorld(true);
    const positions = active!.geometry.getAttribute('position');
    const uv = active!.geometry.getAttribute('uv');
    const rect = display.viewport;
    const m = rect.transform!;
    expect(Math.abs(m.b)).toBeGreaterThan(0.001);
    expect(m.a).toBeLessThan(1);
    for (let i = 0; i < positions.count; i += 1) {
      const p = new THREE.Vector3().fromBufferAttribute(positions, i).applyMatrix4(active!.matrixWorld).project(display.camera);
      const x = uv.getX(i) * rect.width;
      const y = (1 - uv.getY(i)) * rect.height;
      expect((p.x + 1) * width / 2).toBeCloseTo(m.x + m.a * x + m.c * y, 3);
      expect((1 - p.y) * height / 2).toBeCloseTo(m.y + m.b * x + m.d * y, 3);
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
    let geometryCount = 0;
    display.scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.geometry.addEventListener('dispose', disposed);
        geometryCount += 1;
      }
    });
    display.setSize(1400, 500, 2);
    expect(disposed).toHaveBeenCalledTimes(geometryCount);
    const targetDisposed = vi.fn();
    display.target.addEventListener('dispose', targetDisposed);
    display.dispose();
    expect(targetDisposed).toHaveBeenCalledOnce();
  });

  it('keeps the tilted hardware visible and derives both optics passes from the live image', () => {
    const display = new ScreenDisplay();
    display.setSize(1298, 280, 2);
    display.scene.updateMatrixWorld(true);
    const housing = display.scene.getObjectByName('display-housing')!;
    const bounds = new THREE.Box3().setFromObject(housing);
    expect(bounds.getSize(new THREE.Vector3()).z).toBeGreaterThan(1);
    housing.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      const p = object.geometry.getAttribute('position');
      for (let i = 0; i < p.count; i += 1) {
        const v = new THREE.Vector3().fromBufferAttribute(p, i).applyMatrix4(object.matrixWorld).project(display.camera);
        expect(Math.abs(v.x)).toBeLessThanOrEqual(1);
        expect(Math.abs(v.y)).toBeLessThanOrEqual(1);
      }
    });
    const face = display.scene.getObjectByName('live-display-surface') as THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>;
    const light = display.scene.getObjectByName('content-driven-light') as THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>;
    expect(face.material.uniforms.uImage.value).toBe(display.target.texture);
    expect(face.material.uniforms.uEmission.value).toBe(display.emission.texture);
    expect(light.material.uniforms.uEmission.value).toBe(display.emission.texture);
    const released = vi.fn();
    display.emission.addEventListener('dispose', released);
    display.dispose();
    expect(released).toHaveBeenCalledOnce();
  });
});
