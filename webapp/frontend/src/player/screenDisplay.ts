// Parametric display modeled from the supplied images (1).jpg: shallow silver housing,
// rounded black cover glass, and the live LiDAR render target on the active display surface.
import * as THREE from 'three';
import { CONTACT_SHADOW_FRAGMENT, DISPLAY_FRAGMENT, DISPLAY_VERTEX, FILTER_FRAGMENT, FILTER_VERTEX, GLOW_FRAGMENT } from './screenEffects';
import { roundedRect } from './screenGeometry';
import { TrainInterior } from './trainInterior';

export interface DisplayTransform { a: number; b: number; c: number; d: number; x: number; y: number }
export interface DisplayMotion { sceneX: number; sceneY: number; sceneZ: number; railX: number; railY: number; railZ: number }
export interface DisplayViewport { x: number; y: number; width: number; height: number; transform?: DisplayTransform; motion?: DisplayMotion }
export interface DisplayRegion { height: number; top: number; width?: number; left?: number }

export class ScreenDisplay {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 50);
  readonly target = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: true });
  readonly emission = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: false });
  readonly viewport: DisplayViewport = { x: 0, y: 0, width: 1, height: 1 };
  private readonly body = new THREE.Group();
  private readonly background = new THREE.Group();
  private readonly interior = new TrainInterior();
  private readonly filterTarget = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: false });
  private readonly filterScene = new THREE.Scene();
  private readonly filterCamera = new THREE.Camera();
  private readonly filterGeometry = new THREE.PlaneGeometry(2, 2);
  private readonly filter = new THREE.ShaderMaterial({
    vertexShader: FILTER_VERTEX, fragmentShader: FILTER_FRAGMENT,
    uniforms: { uImage: { value: this.target.texture }, uDirection: { value: new THREE.Vector2() }, uExtract: { value: 0 } },
    depthTest: false, depthWrite: false,
  });
  private readonly contact = new THREE.ShaderMaterial({
    vertexShader: DISPLAY_VERTEX, fragmentShader: CONTACT_SHADOW_FRAGMENT, transparent: true, depthWrite: false,
    uniforms: { uSize: { value: new THREE.Vector2() }, uHalfSize: { value: new THREE.Vector2() }, uRadius: { value: .3 } },
  });
  private readonly mountShadow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), this.contact);
  private readonly metal = new THREE.MeshStandardMaterial({ color: 0xadb6bd, metalness: 0.7, roughness: 0.3 });
  private readonly glass = new THREE.MeshStandardMaterial({ color: 0x080b10, metalness: 0.12, roughness: 0.18 });
  private readonly cover = new THREE.MeshPhysicalMaterial({ color: 0xdfe9ed, transparent: true, opacity: 0.025, roughness: 0.14, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.1, depthWrite: false });
  private readonly rear = new THREE.MeshStandardMaterial({ color: 0x323940, roughness: 0.6 });
  private readonly pixels = new THREE.ShaderMaterial({
    vertexShader: DISPLAY_VERTEX, fragmentShader: DISPLAY_FRAGMENT, toneMapped: false,
    uniforms: { uImage: { value: this.target.texture }, uEmission: { value: this.emission.texture }, uSurfaceSize: { value: new THREE.Vector2() } },
  });
  private readonly glow = new THREE.ShaderMaterial({
    vertexShader: DISPLAY_VERTEX, fragmentShader: GLOW_FRAGMENT, transparent: true, depthWrite: false,
    uniforms: { uEmission: { value: this.emission.texture }, uFaceScale: { value: new THREE.Vector2() } },
  });
  private readonly lightPool = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), this.glow);
  private geometries: THREE.BufferGeometry[] = [];
  private size = { width: 0, height: 0, pixelRatio: 0, regionHeight: 0, regionTop: 0, regionWidth: 0, regionLeft: 0 };
  private readonly motion = { sceneX: 0, sceneY: 0, sceneZ: 0, railX: 0, railY: 0, railZ: 0 };
  private readonly pointerTarget = new THREE.Vector3();
  private surfaceWidth = 1;
  private surfaceHeight = 1;

  constructor(private readonly wallOnly = false) {
    this.camera.position.set(0, 0, 20);
    this.body.name = 'display-housing';
    this.background.name = 'train-background-layer';
    this.background.add(this.body, this.interior.group);
    this.body.visible = !wallOnly;
    this.mountShadow.name = 'antialiased-mount-contact';
    this.mountShadow.position.z = -.442;
    this.viewport.motion = this.motion;
    this.lightPool.name = 'content-driven-light';
    this.lightPool.position.set(0, 0, -0.415);
    this.filterScene.add(new THREE.Mesh(this.filterGeometry, this.filter));
    this.glass.emissive.set(0xffffff);
    this.glass.emissiveMap = this.emission.texture;
    this.glass.emissiveIntensity = 0.06;
    const key = new THREE.DirectionalLight(0xfff8e8, 1.35);
    key.position.set(-5, 10, 30);
    const fill = new THREE.DirectionalLight(0xdfe8f4, 0.7);
    fill.position.set(12, -4, 8);
    this.scene.add(this.background, this.interior.railings, new THREE.HemisphereLight(0xf1f4ed, 0x657079, 2.0), key, fill);
  }

  setSize(width: number, height: number, pixelRatio: number, region: DisplayRegion = { height, top: 0 }): void {
    const viewWidth = region.width ?? width;
    const viewLeft = region.left ?? (width - viewWidth) / 2;
    if (this.size.width === width && this.size.height === height && this.size.pixelRatio === pixelRatio && this.size.regionHeight === region.height && this.size.regionTop === region.top && this.size.regionWidth === viewWidth && this.size.regionLeft === viewLeft) return;
    Object.assign(this.size, { width, height, pixelRatio, regionHeight: region.height, regionTop: region.top, regionWidth: viewWidth, regionLeft: viewLeft });
    for (const g of this.geometries) g.dispose();
    this.geometries = [];
    this.body.clear();
    const units = 16 / width;
    const w = 16;
    const h = height * units;
    const side = Math.max(25, viewWidth * 0.065);
    const top = Math.min(72, Math.max(38, region.height * 0.16));
    const bottom = Math.min(56, Math.max(25, region.height * 0.12));
    const bezel = Math.min(22, Math.max(10, region.height * 0.045));
    Object.assign(this.viewport, { x: viewLeft + side + bezel, y: region.top + top + bezel, width: Math.max(1, viewWidth - (side + bezel) * 2), height: Math.max(1, region.height - top - bottom - bezel * 2) });
    const vw = this.viewport.width * units;
    const vh = this.viewport.height * units;
    const bodyW = (viewWidth - side * 2) * units;
    const bodyH = (region.height - top - bottom) * units;
    this.body.position.y = (height / 2 - region.top - region.height / 2 + (bottom - top) / 2) * units;
    this.body.position.x = (viewLeft + viewWidth / 2 - width / 2) * units;
    this.interior.setSize(w, h, this.wallOnly ? null : { width: bodyW, height: bodyH, radius: Math.min(0.42, bodyH * 0.12), centerY: this.body.position.y });
    const radius = Math.min(0.42, bodyH * 0.12);
    const shell = (sw: number, sh: number, r: number, depth: number, z: number, material: THREE.Material) => {
      const geometry = new THREE.ExtrudeGeometry(roundedRect(sw, sh, r), { depth, bevelEnabled: true, bevelSize: 0.035, bevelThickness: 0.035, bevelSegments: 3, steps: 1, curveSegments: 12 });
      const position = geometry.getAttribute('position');
      const uv = geometry.getAttribute('uv');
      for (let i = 0; i < position.count; i += 1) uv.setXY(i, (position.getX(i) + sw / 2) / sw, (position.getY(i) + sh / 2) / sh);
      this.geometries.push(geometry);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.z = z;
      mesh.castShadow = true;
      this.body.add(mesh);
    };
    shell(bodyW - 0.1, bodyH - 0.1, radius, 0.36, -0.48, this.rear);
    shell(bodyW, bodyH, radius, 0.11, -0.05, this.metal);
    shell(bodyW - 0.095, bodyH - 0.095, Math.max(0.05, radius - 0.04), 0.035, 0.09, this.glass);
    const face = new THREE.ShapeGeometry(roundedRect(vw, vh, Math.min(0.12, vh * 0.06)), 12);
    const pos = face.getAttribute('position');
    const uv = face.getAttribute('uv');
    for (let i = 0; i < pos.count; i += 1) uv.setXY(i, (pos.getX(i) + vw / 2) / vw, (pos.getY(i) + vh / 2) / vh);
    this.geometries.push(face);
    const screen = new THREE.Mesh(face, this.pixels);
    screen.name = 'live-display-surface';
    screen.position.z = 0.175;
    screen.castShadow = true;
    this.body.add(screen);
    const coverGeometry = new THREE.ShapeGeometry(roundedRect(bodyW - 0.1, bodyH - 0.1, Math.max(0.05, radius - 0.04)), 18);
    this.geometries.push(coverGeometry);
    const cover = new THREE.Mesh(coverGeometry, this.cover);
    cover.name = 'protective-cover-glass';
    cover.position.z = 0.205;
    cover.renderOrder = 2;
    this.body.add(cover);
    this.body.add(this.lightPool);
    this.mountShadow.geometry.dispose();
    this.mountShadow.geometry = new THREE.PlaneGeometry(bodyW + .6, bodyH + .6);
    this.contact.uniforms.uSize.value.set(bodyW + .6, bodyH + .6);
    this.contact.uniforms.uHalfSize.value.set(bodyW / 2, bodyH / 2);
    this.contact.uniforms.uRadius.value = radius;
    this.body.add(this.mountShadow);
    this.camera.left = -w / 2;
    this.camera.right = w / 2;
    this.camera.top = h / 2;
    this.camera.bottom = -h / 2;
    this.camera.updateProjectionMatrix();
    this.camera.updateMatrixWorld();
    this.surfaceWidth = vw;
    this.surfaceHeight = vh;
    this.updateProjection();
    this.pixels.uniforms.uSurfaceSize.value.set(this.viewport.width, this.viewport.height);
    this.lightPool.geometry.dispose();
    const poolW = bodyW + 0.9;
    const poolH = bodyH + 0.65;
    this.lightPool.geometry = new THREE.PlaneGeometry(poolW, poolH);
    this.glow.uniforms.uFaceScale.value.set(poolW / vw, poolH / vh);
    this.target.setSize(Math.max(1, Math.round(this.viewport.width * pixelRatio)), Math.max(1, Math.round(this.viewport.height * pixelRatio)));
    const lightW = Math.max(48, Math.min(256, Math.round(this.viewport.width / 8)));
    const lightH = Math.max(24, Math.min(96, Math.round(this.viewport.height / 8)));
    this.filterTarget.setSize(lightW, lightH);
    this.emission.setSize(lightW, lightH);
  }

  /** Mouse pressure is bounded and quadratic, with an exactly neutral center. */
  setPointer(x: number, y: number): void {
    const px = THREE.MathUtils.clamp(x, -1, 1);
    const py = THREE.MathUtils.clamp(y, -1, 1);
    if (px === 0 && py === 0) {
      this.pointerTarget.set(0, 0, 0);
      return;
    }
    // A tiny coupled roll makes pressure perceptible without distorting the live view.
    this.pointerTarget.set(py * Math.abs(py) * .035, px * Math.abs(px) * .055, -px * Math.abs(px) * .004);
  }

  get animating(): boolean {
    return Math.abs(this.background.rotation.x - this.pointerTarget.x) + Math.abs(this.background.rotation.y - this.pointerTarget.y) + Math.abs(this.background.rotation.z - this.pointerTarget.z) > 0.00001;
  }

  step(dt: number): void {
    if (!this.animating) return;
    const k = 1 - Math.exp(-Math.min(.1, Math.max(0, dt)) * 10);
    this.background.rotation.x += (this.pointerTarget.x - this.background.rotation.x) * k;
    this.background.rotation.y += (this.pointerTarget.y - this.background.rotation.y) * k;
    this.background.rotation.z += (this.pointerTarget.z - this.background.rotation.z) * k;
    if (!this.animating) this.background.rotation.set(this.pointerTarget.x, this.pointerTarget.y, this.pointerTarget.z);
    this.interior.railings.rotation.set(this.background.rotation.x * .24, this.background.rotation.y * .24, this.background.rotation.z * .24);
    Object.assign(this.motion, { sceneX: this.background.rotation.x, sceneY: this.background.rotation.y, sceneZ: this.background.rotation.z, railX: this.interior.railings.rotation.x, railY: this.interior.railings.rotation.y, railZ: this.interior.railings.rotation.z });
    this.updateProjection();
  }

  private updateProjection(): void {
    this.background.updateMatrixWorld(true);
    this.interior.railings.updateMatrixWorld(true);
    const { width, height } = this.size;
    const vw = this.surfaceWidth;
    const vh = this.surfaceHeight;
    const project = (x: number, y: number) => {
      const p = new THREE.Vector3(x, y, 0.175).applyMatrix4(this.body.matrixWorld).project(this.camera);
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
    renderer.setClearColor(0xb8c1bf, 1);
    renderer.clear();
    renderer.shadowMap.enabled = false;
    renderer.render(this.scene, this.camera);
  }

  dispose(): void {
    for (const g of this.geometries) g.dispose();
    for (const m of [this.metal, this.glass, this.cover, this.rear, this.pixels, this.glow, this.filter, this.contact]) m.dispose();
    this.lightPool.geometry.dispose();
    this.mountShadow.geometry.dispose();
    this.filterGeometry.dispose();
    this.target.dispose();
    this.filterTarget.dispose();
    this.emission.dispose();
    this.interior.dispose();
    this.scene.clear();
    this.filterScene.clear();
  }
}
