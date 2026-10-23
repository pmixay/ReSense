// The Player's physical presentation: the driver's cab of a future metro train, seen from the seat.
// The live LiDAR render target is the windshield's active display; the cab (cockpit.ts) is built
// around the measured display region. The camera is a perspective eye looking straight down -z
// at the windshield plane, so the active face projects affinely and the DOM HUD stays aligned.
// Mouse pressure moves the eye (head parallax, never a rotation); the boot powers the cab up.
import * as THREE from 'three';
import { DISPLAY_FRAGMENT, DISPLAY_VERTEX, FILTER_FRAGMENT, FILTER_VERTEX } from './screenEffects';
import { roundedRect } from './screenGeometry';
import { ScreenLighting } from './screenLighting';
import { CabCockpit, CAB_EYE, CAB_FOV, cabLayout } from './cockpit';
import { CAB_VERTEX, GLASS_FRAGMENT } from './cabShaders';
import { BOOT_ACCENTS, BOOT_IMAGE, CAB_BOOT_MS, bootProgress, type BootState } from './cabBoot';

export interface DisplayTransform { a: number; b: number; c: number; d: number; x: number; y: number }
/** Current eye offset from the seated position (m). */
export interface DisplayMotion { headX: number; headY: number }
export interface DisplayViewport { x: number; y: number; width: number; height: number; transform?: DisplayTransform; motion?: DisplayMotion }
export interface DisplayRegion { height: number; top: number; width?: number; left?: number }

/** Largest eye offsets of the pressure parallax (m). */
export const HEAD_RANGE = { x: 0.06, y: 0.035 };

/** Cab lights shared by the Player and the boarding animation: neutral ceiling LEDs, a soft
 * windshield fill, a warm fill from the saloon side and a dim floor bounce. */
export function cabLights(): THREE.Object3D[] {
  const ambient = new THREE.HemisphereLight(0xeef3ff, 0x3a3f46, 1.35);
  ambient.name = 'cab-soft-ambient';
  const roof = new THREE.DirectionalLight(0xf4f8ff, 1.7);
  roof.name = 'cab-ceiling-led-light';
  roof.position.set(0.4, 3, 2.4);
  const windshield = new THREE.DirectionalLight(0xb8dcff, 0.45);
  windshield.name = 'cab-windshield-fill';
  windshield.position.set(0, 0.3, -3);
  const rear = new THREE.DirectionalLight(0xffe2c2, 0.6);
  rear.name = 'cab-rear-warm-fill';
  rear.position.set(-1.5, 1, 4);
  return [ambient, roof, windshield, rear];
}

/** A small, cached cab reflection probe: the glowing windshield ahead, roof strips above. */
export function cabEnvironment(renderer: THREE.WebGLRenderer): THREE.WebGLRenderTarget {
  const width = 256;
  const height = 128;
  const data = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const v = (y + 0.5) / height;
    const u = (x + 0.5) / width;
    const ahead = Math.exp(-Math.pow((u - 0.25) / 0.11, 4)) * Math.exp(-Math.pow((v - 0.53) / 0.1, 4));
    const strips = Math.exp(-Math.pow((v - 0.88) / 0.02, 2)) + Math.exp(-Math.pow((v - 0.8) / 0.015, 2)) * 0.6;
    const base = 0.05 + 0.08 * v;
    const i = (y * width + x) * 4;
    data[i] = Math.min(255, (base + ahead * 0.22 + strips * 0.55) * 255);
    data[i + 1] = Math.min(255, (base + ahead * 0.42 + strips * 0.6) * 255);
    data[i + 2] = Math.min(255, (base * 1.2 + ahead * 0.55 + strips * 0.66) * 255);
    data[i + 3] = 255;
  }
  const source = new THREE.DataTexture(data, width, height);
  source.mapping = THREE.EquirectangularReflectionMapping;
  source.needsUpdate = true;
  const generator = new THREE.PMREMGenerator(renderer);
  const target = generator.fromEquirectangular(source);
  source.dispose();
  generator.dispose();
  return target;
}

export class ScreenDisplay {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(CAB_FOV, 1, 0.05, 40);
  readonly target = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: true });
  readonly emission = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: false });
  readonly viewport: DisplayViewport = { x: 0, y: 0, width: 1, height: 1 };
  private readonly lighting = new ScreenLighting(this.emission.texture);
  readonly cockpit = new CabCockpit({ lighting: this.lighting });
  private readonly filterTarget = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: false });
  private readonly filterScene = new THREE.Scene();
  private readonly filterCamera = new THREE.Camera();
  private readonly filterGeometry = new THREE.PlaneGeometry(2, 2);
  private readonly filter = new THREE.ShaderMaterial({
    vertexShader: FILTER_VERTEX, fragmentShader: FILTER_FRAGMENT,
    uniforms: { uImage: { value: this.target.texture }, uDirection: { value: new THREE.Vector2() }, uExtract: { value: 0 } },
    depthTest: false, depthWrite: false,
  });
  private readonly pixels = new THREE.ShaderMaterial({
    vertexShader: DISPLAY_VERTEX, fragmentShader: DISPLAY_FRAGMENT, toneMapped: false,
    uniforms: { uImage: { value: this.target.texture }, uEmission: { value: this.emission.texture }, uSurfaceSize: { value: new THREE.Vector2() }, uBoot: { value: 1 } },
  });
  private readonly glass = new THREE.ShaderMaterial({ vertexShader: CAB_VERTEX, fragmentShader: GLASS_FRAGMENT, toneMapped: false, uniforms: { uPower: { value: 1 }, uSize: { value: new THREE.Vector2(1, 1) }, uBand: { value: 0.03 } } });
  private readonly windshield = new THREE.Group();
  private geometries: THREE.BufferGeometry[] = [];
  private size = { width: 0, height: 0, pixelRatio: 0, regionHeight: 0, regionTop: 0, regionWidth: 0, regionLeft: 0 };
  private readonly motion: DisplayMotion = { headX: 0, headY: 0 };
  private readonly headTarget = new THREE.Vector2();
  private surfaceWidth = 1;
  private surfaceHeight = 1;
  private face: THREE.Mesh | null = null;
  private boot: BootState = 'on';
  private bootT = 0;
  private environment: THREE.WebGLRenderTarget | null = null;

  constructor(private readonly wallOnly = false) {
    this.windshield.name = 'windshield-display';
    this.viewport.motion = this.motion;
    this.filterScene.add(new THREE.Mesh(this.filterGeometry, this.filter));
    this.scene.add(this.cockpit.group, this.windshield, ...cabLights());
    this.applyPower();
  }

  setSize(width: number, height: number, pixelRatio: number, region: DisplayRegion = { height, top: 0 }): void {
    const viewWidth = region.width ?? width;
    const viewLeft = region.left ?? (width - viewWidth) / 2;
    if (this.size.width === width && this.size.height === height && this.size.pixelRatio === pixelRatio && this.size.regionHeight === region.height && this.size.regionTop === region.top && this.size.regionWidth === viewWidth && this.size.regionLeft === viewLeft) return;
    Object.assign(this.size, { width, height, pixelRatio, regionHeight: region.height, regionTop: region.top, regionWidth: viewWidth, regionLeft: viewLeft });
    const layout = cabLayout(width, height, { height: region.height, top: region.top, width: viewWidth, left: viewLeft });
    this.cockpit.build(layout);
    for (const g of this.geometries) g.dispose();
    this.geometries = [];
    this.windshield.clear();
    const A = layout.faceWorld;
    const G = layout.glass;
    const glass = new THREE.PlaneGeometry(G.x1 - G.x0 + 0.02, G.y1 - G.y0 + 0.02);
    this.geometries.push(glass);
    this.glass.uniforms.uSize.value.set(G.x1 - G.x0 + 0.02, G.y1 - G.y0 + 0.02);
    this.glass.uniforms.uBand.value = G.x1 - A.x1 + 0.01;
    const backing = new THREE.Mesh(glass, this.glass);
    backing.name = 'windshield-glass';
    backing.position.set((G.x0 + G.x1) / 2, (G.y0 + G.y1) / 2, -0.004);
    this.windshield.add(backing);
    const vw = A.x1 - A.x0;
    const vh = A.y1 - A.y0;
    const shape = new THREE.ShapeGeometry(roundedRect(vw, vh, Math.min(0.035, vh * 0.05)), 12);
    const pos = shape.getAttribute('position');
    const uv = shape.getAttribute('uv');
    for (let i = 0; i < pos.count; i += 1) uv.setXY(i, (pos.getX(i) + vw / 2) / vw, (pos.getY(i) + vh / 2) / vh);
    this.geometries.push(shape);
    const face = new THREE.Mesh(shape, this.pixels);
    face.name = 'live-display-surface';
    face.position.set((A.x0 + A.x1) / 2, (A.y0 + A.y1) / 2, 0);
    face.visible = !this.wallOnly;
    this.windshield.add(face);
    this.face = face;
    this.surfaceWidth = vw;
    this.surfaceHeight = vh;
    Object.assign(this.viewport, { x: layout.face.x, y: layout.face.y, width: layout.face.width, height: layout.face.height });
    this.camera.fov = CAB_FOV;
    this.camera.aspect = width / Math.max(1, height);
    this.camera.updateProjectionMatrix();
    this.pixels.uniforms.uSurfaceSize.value.set(this.viewport.width, this.viewport.height);
    this.target.setSize(Math.max(1, Math.round(this.viewport.width * pixelRatio)), Math.max(1, Math.round(this.viewport.height * pixelRatio)));
    const lightW = Math.max(48, Math.min(256, Math.round(this.viewport.width / 8)));
    const lightH = Math.max(24, Math.min(96, Math.round(this.viewport.height / 8)));
    this.filterTarget.setSize(lightW, lightH);
    this.emission.setSize(lightW, lightH);
    this.applyPower();
    this.updateProjection();
  }

  /** Mouse pressure is bounded and quadratic, with an exactly neutral centre: the eye leans. */
  setPointer(x: number, y: number): void {
    const px = THREE.MathUtils.clamp(x, -1, 1);
    const py = THREE.MathUtils.clamp(y, -1, 1);
    if (px === 0 && py === 0) {
      this.headTarget.set(0, 0);
      return;
    }
    this.headTarget.set(px * Math.abs(px) * HEAD_RANGE.x, -py * Math.abs(py) * HEAD_RANGE.y);
  }

  /** Instrument power: 'off' (dark, before the driver sits), 'on', or a boot started `elapsed` ms ago. */
  setBoot(state: 'off' | 'on' | number): void {
    if (state === 'off' || state === 'on') {
      this.boot = state;
      this.bootT = state === 'on' ? CAB_BOOT_MS : 0;
    } else if (state >= CAB_BOOT_MS) {
      this.boot = 'on';
      this.bootT = CAB_BOOT_MS;
    } else {
      this.boot = 'running';
      this.bootT = Math.max(0, state);
    }
    this.applyPower();
  }

  get bootState(): BootState {
    return this.boot;
  }

  get animating(): boolean {
    return this.boot === 'running' || Math.abs(this.motion.headX - this.headTarget.x) + Math.abs(this.motion.headY - this.headTarget.y) > 0.00001;
  }

  step(dt: number): void {
    const t = Math.min(0.5, Math.max(0, dt));
    if (this.boot === 'running') {
      this.bootT += t * 1000;
      if (this.bootT >= CAB_BOOT_MS) {
        this.boot = 'on';
        this.bootT = CAB_BOOT_MS;
      }
      this.applyPower();
    }
    const moving = Math.abs(this.motion.headX - this.headTarget.x) + Math.abs(this.motion.headY - this.headTarget.y) > 0.00001;
    if (!moving) return;
    // Exponential damping remains stable through slow GPU frames and settles in wall time.
    const k = 1 - Math.exp(-t * 10);
    this.motion.headX += (this.headTarget.x - this.motion.headX) * k;
    this.motion.headY += (this.headTarget.y - this.motion.headY) * k;
    if (Math.abs(this.motion.headX - this.headTarget.x) + Math.abs(this.motion.headY - this.headTarget.y) <= 0.00001) {
      this.motion.headX = this.headTarget.x;
      this.motion.headY = this.headTarget.y;
    }
    this.updateProjection();
  }

  private applyPower(): void {
    const t = this.boot === 'off' ? -1 : this.boot === 'on' ? CAB_BOOT_MS : this.bootT;
    this.cockpit.setPower(this.boot === 'off' ? 'off' : this.boot === 'on' ? 'on' : this.bootT);
    const image = t < 0 ? 0 : bootProgress(t, BOOT_IMAGE.start, BOOT_IMAGE.length);
    this.pixels.uniforms.uBoot.value = this.boot === 'on' ? 1 : image;
    this.lighting.setPower(this.boot === 'on' ? 1 : image);
    this.glass.uniforms.uPower.value = t < 0 ? 0 : bootProgress(t, BOOT_ACCENTS.start, BOOT_ACCENTS.length);
  }

  private updateProjection(): void {
    this.camera.position.set(this.motion.headX, this.motion.headY, CAB_EYE);
    this.camera.updateMatrixWorld(true);
    this.scene.updateMatrixWorld(true);
    if (!this.face) return;
    this.lighting.update(this.face.matrixWorld, this.surfaceWidth, this.surfaceHeight);
    const { width, height } = this.size;
    const vw = this.surfaceWidth;
    const vh = this.surfaceHeight;
    const project = (x: number, y: number) => {
      const p = new THREE.Vector3(x, y, 0).applyMatrix4(this.face!.matrixWorld).project(this.camera);
      return { x: (p.x + 1) * width / 2, y: (1 - p.y) * height / 2 };
    };
    const tl = project(-vw / 2, vh / 2);
    const tr = project(vw / 2, vh / 2);
    const bl = project(-vw / 2, -vh / 2);
    const transform = this.viewport.transform ??= { a: 1, b: 0, c: 0, d: 1, x: 0, y: 0 };
    Object.assign(transform, {
      a: (tr.x - tl.x) / this.viewport.width, b: (tr.y - tl.y) / this.viewport.width,
      c: (bl.x - tl.x) / this.viewport.height, d: (bl.y - tl.y) / this.viewport.height, x: tl.x, y: tl.y,
    });
    this.viewport.x = tl.x;
    this.viewport.y = tl.y;
  }

  render(renderer: THREE.WebGLRenderer, dt = 1 / 60, imageChanged = true): void {
    this.step(dt);
    if (!this.environment) {
      this.environment = cabEnvironment(renderer);
      this.scene.environment = this.environment.texture;
      this.scene.environmentIntensity = 0.9;
    }
    // Two small GPU-only passes extract and diffuse the actual image's emitted colors.
    if (imageChanged && !this.wallOnly) {
      const lw = this.emission.width;
      const lh = this.emission.height;
      this.filter.uniforms.uImage.value = this.target.texture;
      this.filter.uniforms.uDirection.value.set(2.2 / lw, 0);
      this.filter.uniforms.uExtract.value = 1;
      renderer.setRenderTarget(this.filterTarget);
      renderer.setClearColor(0x000000, 1);
      renderer.clear();
      renderer.render(this.filterScene, this.filterCamera);
      this.filter.uniforms.uImage.value = this.filterTarget.texture;
      this.filter.uniforms.uDirection.value.set(0, 2.2 / lh);
      this.filter.uniforms.uExtract.value = 0;
      renderer.setRenderTarget(this.emission);
      renderer.clear();
      renderer.render(this.filterScene, this.filterCamera);
    }
    renderer.setRenderTarget(null);
    renderer.setViewport(0, 0, this.size.width, this.size.height);
    renderer.setClearColor(0x07090d, 1);
    renderer.clear();
    renderer.shadowMap.enabled = false;
    renderer.render(this.scene, this.camera);
  }

  dispose(): void {
    for (const g of this.geometries) g.dispose();
    for (const m of [this.pixels, this.filter, this.glass]) m.dispose();
    this.filterGeometry.dispose();
    this.target.dispose();
    this.filterTarget.dispose();
    this.emission.dispose();
    this.environment?.dispose();
    this.cockpit.dispose();
    this.scene.clear();
    this.filterScene.clear();
  }
}
