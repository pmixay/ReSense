import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { HEAD_RANGE, ScreenDisplay } from './screenDisplay';
import { CAB_EYE, CAB_FOV, cabLayout } from './cockpit';
import { BOOT_IMAGE, CAB_BOOT_MS } from './cabBoot';

const settle = (display: ScreenDisplay, frames = 120) => { for (let i = 0; i < frames; i += 1) display.step(1 / 60); };

describe('driver cab display', () => {
  it.each([[1366, 320, 1], [1840, 616, 2], [1440, 816, 1.5]])('keeps the live surface and HUD pixel bounds aligned at %s×%s, also with the head moved', (width, height, pr) => {
    const display = new ScreenDisplay();
    display.setSize(width, height, pr);
    const rest = { ...display.viewport.transform! };
    expect(rest.a).toBeCloseTo(1, 8);
    expect(rest.d).toBeCloseTo(1, 8);
    expect(rest.b).toBeCloseTo(0, 10);
    expect(rest.c).toBeCloseTo(0, 10);
    expect(rest.x).toBeCloseTo(display.viewport.x, 8);
    display.setPointer(1, -1);
    settle(display);
    const active = display.scene.getObjectByName('live-display-surface') as THREE.Mesh;
    display.scene.updateMatrixWorld(true);
    const positions = active.geometry.getAttribute('position');
    const uv = active.geometry.getAttribute('uv');
    const rect = display.viewport;
    const m = rect.transform!;
    // leaning right and up: the picture shifts left and down, and stays parallel to the screen
    expect(m.x).toBeLessThan(rest.x - 5);
    expect(m.y).toBeGreaterThan(rest.y + 2);
    expect(m.b).toBeCloseTo(0, 8);
    expect(m.c).toBeCloseTo(0, 8);
    for (let i = 0; i < positions.count; i += 1) {
      const p = new THREE.Vector3().fromBufferAttribute(positions, i).applyMatrix4(active.matrixWorld).project(display.camera);
      const x = uv.getX(i) * rect.width;
      const y = (1 - uv.getY(i)) * rect.height;
      expect((p.x + 1) * width / 2).toBeCloseTo(m.x + m.a * x + m.c * y, 3);
      expect((1 - p.y) * height / 2).toBeCloseTo(m.y + m.b * x + m.d * y, 3);
    }
    expect(display.target.width).toBe(Math.round(rect.width * pr));
    expect(display.target.height).toBe(Math.round(rect.height * pr));
    display.dispose();
  });

  it('places the windshield inside the measured region with the seated eye and field of view', () => {
    const region = { width: 1368, left: 36, height: 648, top: 8 };
    const layout = cabLayout(1440, 816, region);
    expect(layout.face.x).toBeGreaterThan(region.left);
    expect(layout.face.y).toBeGreaterThan(region.top);
    expect(layout.face.x + layout.face.width).toBeLessThan(region.left + region.width);
    expect(layout.face.y + layout.face.height).toBeLessThan(region.top + region.height);
    expect(layout.unit * 816).toBeCloseTo(2 * CAB_EYE * Math.tan(THREE.MathUtils.degToRad(CAB_FOV / 2)), 10);
    expect(layout.glass.x0).toBeLessThan(layout.faceWorld.x0);
    expect(layout.frame.x0).toBeLessThan(layout.glass.x0);
    const display = new ScreenDisplay();
    display.setSize(1440, 816, 1, region);
    for (const key of ['x', 'y', 'width', 'height'] as const) expect(display.viewport[key]).toBeCloseTo(layout.face[key], 6);
    expect(display.camera.fov).toBe(CAB_FOV);
    expect(display.camera.position.toArray()).toEqual([0, 0, CAB_EYE]);
    display.dispose();
  });

  it('releases the old cab geometry on resize and the live textures on disposal', () => {
    const display = new ScreenDisplay();
    display.setSize(1280, 400, 1);
    const disposed = vi.fn();
    const geometries = new Set<THREE.BufferGeometry>();
    display.scene.traverse((object) => {
      if (object instanceof THREE.Mesh) geometries.add(object.geometry);
    });
    for (const g of geometries) g.addEventListener('dispose', disposed);
    display.setSize(1400, 500, 2);
    expect(disposed).toHaveBeenCalledTimes(geometries.size);
    const targetDisposed = vi.fn();
    display.target.addEventListener('dispose', targetDisposed);
    display.emission.addEventListener('dispose', targetDisposed);
    display.dispose();
    expect(targetDisposed).toHaveBeenCalledTimes(2);
  });

  it('feeds the live image to the windshield and its light to the cab', () => {
    const display = new ScreenDisplay();
    display.setSize(1298, 640, 2);
    const face = display.scene.getObjectByName('live-display-surface') as THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>;
    expect(face.material.uniforms.uImage.value).toBe(display.target.texture);
    expect(face.material.uniforms.uEmission.value).toBe(display.emission.texture);
    for (const name of ['windshield-moulded-trim', 'left-pillar', 'sun-visor-housing', 'glare-shield', 'left-camera-monitor', 'desk-traction-display', 'controller-grip', 'emergency-stop']) {
      expect(display.scene.getObjectByName(name), name).toBeDefined();
    }
    display.dispose();
  });

  it.each([
    [1366, 907, 1298, 556], [1440, 816, 1368, 611], [1920, 996, 1840, 828], [1280, 636, 1216, 468], [1440, 1273, 1368, 922],
  ])('keeps every cab part clear of the live picture at every head position (%s×%s)', (width, height, regionWidth, regionHeight) => {
    const display = new ScreenDisplay();
    display.setSize(width, height, 1, { width: regionWidth, left: (width - regionWidth) / 2, height: regionHeight, top: 8 });
    const face = display.scene.getObjectByName('live-display-surface') as THREE.Mesh;
    face.geometry.computeBoundingBox();
    const bounds = face.geometry.boundingBox!;
    const blocked = (eye: THREE.Vector3, point: THREE.Vector3) => {
      const direction = point.clone().sub(eye);
      const ray = new THREE.Raycaster(eye, direction.clone().normalize(), 0, direction.length() - 1e-4);
      return ray.intersectObject(display.cockpit.group, true).filter(hit => !(hit.object as THREE.Mesh<THREE.BufferGeometry, THREE.Material>).material.transparent).map(hit => hit.object.name);
    };
    // positive control: a part put in front of the picture is found by the same ray test
    const probe = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.05, 0.05), new THREE.MeshBasicMaterial());
    probe.name = 'probe';
    const eye0 = display.camera.position.clone();
    const target = new THREE.Vector3(bounds.max.x * 0.49, 0, 0).applyMatrix4(face.matrixWorld);
    probe.position.copy(eye0).lerp(target, (CAB_EYE - 0.6) / CAB_EYE);
    display.cockpit.group.add(probe);
    display.scene.updateMatrixWorld(true);
    expect(blocked(eye0, target)).toContain('probe');
    display.cockpit.group.remove(probe);
    probe.geometry.dispose();
    for (const px of [-1, 0, 1]) for (const py of [-1, 0, 1]) {
      display.setPointer(px, py);
      settle(display);
      display.scene.updateMatrixWorld(true);
      const eye = display.camera.position.clone();
      for (const x of [-0.49, -0.25, 0, 0.25, 0.49]) for (const y of [-0.49, 0, 0.49]) {
        const point = new THREE.Vector3(x * (bounds.max.x - bounds.min.x), y * (bounds.max.y - bounds.min.y), 0).applyMatrix4(face.matrixWorld);
        expect(blocked(eye, point), `${px},${py} ${x},${y}`).toEqual([]);
      }
    }
    display.scene.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return;
      expect(Array.from(object.geometry.getAttribute('position').array).every(Number.isFinite)).toBe(true);
    });
    display.dispose();
  });

  it('leans the eye within its range, damps it, and settles exactly back to neutral', () => {
    const display = new ScreenDisplay();
    display.setSize(1440, 752, 1, { width: 1368, left: 36, height: 410, top: 16 });
    const matrix = display.viewport.transform;
    display.setPointer(1, -0.8);
    expect(display.animating).toBe(true);
    display.step(1 / 60);
    expect(display.viewport.motion!.headX).toBeGreaterThan(0);
    expect(display.viewport.motion!.headX).toBeLessThan(HEAD_RANGE.x);
    settle(display);
    expect(display.viewport.motion!.headX).toBeCloseTo(HEAD_RANGE.x, 6);
    expect(display.viewport.motion!.headY).toBeCloseTo(0.64 * HEAD_RANGE.y, 6);
    expect(display.viewport.transform).toBe(matrix);
    display.setPointer(0, 0);
    // Slow devices still settle in elapsed time, rather than needing 120 costly frames.
    for (let i = 0; i < 3; i += 1) display.step(0.5);
    expect(display.animating).toBe(false);
    expect(display.camera.position.toArray()).toEqual([0, 0, CAB_EYE]);
    display.dispose();
  });

  it('boots the cab: dark before the driver sits, the picture scanned in, then steady', () => {
    const display = new ScreenDisplay();
    display.setSize(1440, 816, 1, { width: 1368, left: 36, height: 611, top: 8 });
    const face = display.scene.getObjectByName('live-display-surface') as THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>;
    const monitor = display.scene.getObjectByName('left-camera-monitor') as THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>;
    expect(face.material.uniforms.uBoot.value).toBe(1);
    display.setBoot('off');
    expect(display.bootState).toBe('off');
    expect(face.material.uniforms.uBoot.value).toBe(0);
    expect(monitor.material.uniforms.uPower.value).toBe(0);
    expect(display.animating).toBe(false);
    display.setBoot(0);
    expect(display.animating).toBe(true);
    for (let t = 0; t < BOOT_IMAGE.start - 20; t += 50) display.step(0.05);
    expect(face.material.uniforms.uBoot.value).toBe(0);
    expect(monitor.material.uniforms.uPower.value).toBeGreaterThan(0);
    for (let t = 0; t < BOOT_IMAGE.length / 2; t += 50) display.step(0.05);
    expect(face.material.uniforms.uBoot.value).toBeGreaterThan(0.2);
    expect(face.material.uniforms.uBoot.value).toBeLessThan(0.8);
    for (let t = 0; t < CAB_BOOT_MS; t += 50) display.step(0.05);
    expect(display.bootState).toBe('on');
    expect(display.animating).toBe(false);
    expect(face.material.uniforms.uBoot.value).toBe(1);
    expect(monitor.material.uniforms.uPower.value).toBe(1);
    display.setBoot(CAB_BOOT_MS + 5);
    expect(display.bootState).toBe('on');
    display.dispose();
  });

  it('keeps the cab without an active picture for the picker and error states', () => {
    const empty = new ScreenDisplay(true);
    empty.setSize(1440, 752, 1);
    expect(empty.scene.getObjectByName('live-display-surface')!.visible).toBe(false);
    expect(empty.scene.getObjectByName('windshield-glass')!.visible).toBe(true);
    expect(empty.scene.getObjectByName('windshield-moulded-trim')).toBeDefined();
    empty.dispose();
  });
});
