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
      if (!(object instanceof THREE.Mesh) || object.name === 'content-driven-light' || object.name === 'antialiased-mount-contact') return;
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
    // Slow devices still settle in elapsed time, rather than needing 120 costly frames.
    for (let i = 0; i < 3; i += 1) display.step(.5);
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

  it('adds reference-style seating below the housing while preserving the fixed door and rail anchors', () => {
    const display = new ScreenDisplay();
    display.setSize(1440, 816, 1, { width: 1368, left: 36, height: 611, top: 8 });
    const door = display.scene.getObjectByName('metro-door-aluminium-stile')!;
    expect(door.position.toArray()).toEqual([7.78, 0, -.4]);
    const rail = display.scene.getObjectByName('stainless-grab-rail') as THREE.Mesh<THREE.TubeGeometry>;
    expect(rail.geometry.parameters.path.getPoint(0).toArray()).toEqual([-7.5, -(816 * 16 / 1440 + 2) / 2, 1.8]);
    const housing = display.scene.getObjectByName('display-housing')!;
    const bench = display.scene.getObjectByName('cantilever-bench-shell')!;
    display.scene.updateMatrixWorld(true);
    const housingBounds = new THREE.Box3().setFromObject(housing.children[0]);
    const benchBounds = new THREE.Box3().setFromObject(bench);
    expect(benchBounds.max.y).toBeLessThan(housingBounds.min.y);
    let seats = 0;
    display.scene.traverse(object => { if (object.name === 'contoured-seat-cushion') seats++; });
    expect(seats).toBeGreaterThanOrEqual(2);
    const back = display.scene.getObjectByName('woven-individual-seat-back') as THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial>;
    const textureDisposal = vi.fn();
    back.material.map!.addEventListener('dispose', textureDisposal);
    display.dispose();
    expect(textureDisposal).toHaveBeenCalledOnce();
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

  it.each([
    [1366, 907, 1298, 556], [1440, 1039, 1368, 688], [1920, 1219, 1840, 868],
    [390, 1230, 358, 410], [1440, 1273, 1368, 922],
  ])('keeps every interior part clear of the active screen at %s×%s', (width, height, regionWidth, regionHeight) => {
    const display = new ScreenDisplay();
    display.setSize(width, height, 1, { width: regionWidth, left: (width - regionWidth) / 2, height: regionHeight, top: 16 });
    const face = display.scene.getObjectByName('live-display-surface') as THREE.Mesh;
    const interior = display.scene.getObjectByName('train-wall-installation')!;
    const background = display.scene.getObjectByName('train-background-layer')!;
    const rail = display.scene.getObjectByName('stainless-grab-rail') as THREE.Mesh;
    face.geometry.computeBoundingBox();
    const bounds = face.geometry.boundingBox!;
    for (const px of [-1, 0, 1]) for (const py of [-1, 0, 1]) {
      display.setPointer(px, py);
      for (let i = 0; i < 100; i++) display.step(1 / 60);
      display.scene.updateMatrixWorld(true);
      const railPoints = rail.geometry.getAttribute('position');
      for (let i = 0; i < railPoints.count; i += 32) {
        const point = new THREE.Vector3().fromBufferAttribute(railPoints, i).applyMatrix4(rail.matrixWorld);
        expect(new THREE.Raycaster(point, new THREE.Vector3(0, 0, -1), 0, .5).intersectObject(background, true)).toHaveLength(0);
      }
      for (const x of [-.45, 0, .45]) for (const y of [-.45, 0, .45]) {
        const point = new THREE.Vector3(x * (bounds.max.x - bounds.min.x), y * (bounds.max.y - bounds.min.y), 0).applyMatrix4(face.matrixWorld);
        const origin = point.clone().add(new THREE.Vector3(0, 0, 20));
        const ray = new THREE.Raycaster(origin, new THREE.Vector3(0, 0, -1), 0, 19.99);
        const opaqueHits = ray.intersectObject(interior, true).filter(hit => {
          const material = (hit.object as THREE.Mesh).material as THREE.Material;
          return !material.transparent;
        });
        expect(opaqueHits).toHaveLength(0);
      }
    }
    display.setPointer(0, 0);
    for (let i = 0; i < 100; i++) display.step(1 / 60);
    display.scene.updateMatrixWorld(true);
    expect(display.scene.getObjectByName('formed-ceiling-valance')).toBeUndefined();
    expect(display.scene.getObjectByName('ceiling-ventilation-louvers')).toBeUndefined();
    const pillar = new THREE.Box3().setFromObject(display.scene.getObjectByName('formed-door-pillar')!);
    const sockets = display.scene.getObjectByName('charging-socket-service-plate');
    const door = new THREE.Box3().setFromObject(display.scene.getObjectByName('metro-door-aluminium-stile')!);
    if (sockets) {
      const socket = new THREE.Box3().setFromObject(sockets);
      expect(socket.getCenter(new THREE.Vector3()).x).toBeCloseTo(pillar.getCenter(new THREE.Vector3()).x, 6);
      expect(socket.max.x).toBeLessThan(door.min.x);
      expect(socket.min.x).toBeGreaterThan(pillar.min.x);
    }
    for (const name of ['brushed-aluminium-wall-dado', 'lower-service-panel-joint']) {
      const trim = new THREE.Box3().setFromObject(display.scene.getObjectByName(name)!);
      expect(trim.max.x).toBeLessThan(door.min.x);
    }
    display.scene.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return;
      const position = object.geometry.getAttribute('position');
      expect(Array.from(position.array).every(Number.isFinite)).toBe(true);
    });
    display.dispose();
  });
});
