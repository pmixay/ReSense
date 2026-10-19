import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { ScreenDisplay } from './screenDisplay';

describe('modeled display projection', () => {
  it.each([[1366, 320, 1], [1840, 616, 2], [358, 240, 2]])('keeps the live surface and HUD pixel bounds aligned at %s×%s', (width, height, pr) => {
    const display = new ScreenDisplay();
    display.setSize(width, height, pr);
    expect(display.viewport.transform!.a).toBeCloseTo(1, 8);
    expect(display.viewport.transform!.d).toBeCloseTo(1, 8);
    expect(display.viewport.transform!.b).toBe(0);
    expect(display.viewport.transform!.c).toBe(0);
    display.setPointer(1, -1);
    for (let i = 0; i < 100; i += 1) display.step(1 / 60);
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
    display.setPointer(1, -1);
    for (let i = 0; i < 100; i += 1) display.step(1 / 60);
    display.scene.updateMatrixWorld(true);
    const housing = display.scene.getObjectByName('display-housing')!;
    const bounds = new THREE.Box3().setFromObject(housing);
    expect(bounds.getSize(new THREE.Vector3()).z).toBeGreaterThan(1);
    housing.traverse((object) => {
      if (!(object instanceof THREE.Mesh) || object.name === 'content-driven-light') return;
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

  it('installs the display through a real wall opening and releases the train material textures', () => {
    const display = new ScreenDisplay();
    display.setSize(1366, 320, 1);
    display.scene.updateMatrixWorld(true);
    const wall = display.scene.getObjectByName('laminate-wall-with-display-aperture') as THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>;
    const housing = display.scene.getObjectByName('display-housing')!;
    const interior = display.scene.getObjectByName('train-wall-installation')!;
    expect(wall).toBeDefined();
    const localCenter = new THREE.Vector3(0, housing.position.y, 2);
    const origin = localCenter.applyMatrix4(interior.matrixWorld);
    const direction = new THREE.Vector3(0, 0, -1).transformDirection(interior.matrixWorld);
    expect(new THREE.Raycaster(origin, direction).intersectObject(wall)).toHaveLength(0);
    const disposal = vi.fn();
    wall.material.bumpMap!.addEventListener('dispose', disposal);
    display.dispose();
    expect(disposal).toHaveBeenCalledOnce();
  });

  it('separates the railings, dampens pressure, and settles exactly back to neutral', () => {
    const display = new ScreenDisplay();
    display.setSize(1440, 752, 1, { width: 1368, left: 36, height: 410, top: 16 });
    const background = display.scene.getObjectByName('train-background-layer')!;
    const railings = display.scene.getObjectByName('train-railings-layer')!;
    expect(railings.parent).toBe(display.scene);
    expect(railings.parent).not.toBe(background);
    const matrix = display.viewport.transform;
    display.setPointer(1, -.8);
    expect(display.animating).toBe(true);
    display.step(1 / 60);
    expect(background.rotation.y).toBeGreaterThan(0);
    expect(background.rotation.y).toBeLessThan(.055);
    for (let i = 0; i < 100; i += 1) display.step(1 / 60);
    expect(display.viewport.transform).toBe(matrix);
    expect(railings.rotation.y / background.rotation.y).toBeCloseTo(.24, 8);
    expect(railings.rotation.x / background.rotation.x).toBeCloseTo(.24, 8);
    expect(railings.rotation.z / background.rotation.z).toBeCloseTo(.24, 8);
    display.setPointer(0, 0);
    for (let i = 0; i < 120; i += 1) display.step(1 / 60);
    expect(display.animating).toBe(false);
    expect(background.rotation.x).toBe(0);
    expect(background.rotation.y).toBe(0);
    expect(background.rotation.z).toBe(0);
    expect(railings.rotation.y).toBe(0);
    display.dispose();
  });

  it('keeps the original display region within a full-height wall backdrop', () => {
    const display = new ScreenDisplay();
    display.setSize(1440, 752, 1, { width: 1368, left: 36, height: 410, top: 16 });
    expect(display.viewport.y).toBeGreaterThan(16);
    expect(display.viewport.y + display.viewport.height).toBeLessThan(426);
    expect(display.camera.top - display.camera.bottom).toBeCloseTo(752 * 16 / 1440);
    const empty = new ScreenDisplay(true);
    empty.setSize(1440, 752, 1);
    expect(empty.scene.getObjectByName('display-housing')!.visible).toBe(false);
    expect(empty.scene.getObjectByName('recessed-mounting-gasket')).toBeUndefined();
    display.dispose();
    empty.dispose();
  });

  it('keeps the foreground post entirely in front of the train wall at every pressure extreme', () => {
    const display = new ScreenDisplay();
    display.setSize(1440, 844, 1, { width: 1368, left: 36, height: 502, top: 16 });
    const background = display.scene.getObjectByName('train-background-layer')!;
    const railings = display.scene.getObjectByName('train-railings-layer')!;
    for (const x of [-1, 0, 1]) for (const y of [-1, 0, 1]) {
      display.setPointer(x, y);
      for (let i = 0; i < 100; i += 1) display.step(1 / 60);
      display.scene.updateMatrixWorld(true);
      const wall = new THREE.Box3().setFromObject(background);
      const near = new THREE.Box3().setFromObject(railings);
      expect(near.min.z - wall.max.z).toBeGreaterThan(.5);
    }
    expect(display.scene.getObjectByName('antialiased-mount-contact')).toBeDefined();
    display.dispose();
  });
});
