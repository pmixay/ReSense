// Parametric display modeled from the supplied images (1).jpg: shallow silver housing,
// rounded black cover glass, and the live LiDAR render target on the active display surface.
import * as THREE from 'three';

export interface DisplayViewport { x: number; y: number; width: number; height: number }

function roundedRect(w: number, h: number, r: number): THREE.Shape {
  const x = -w / 2;
  const y = -h / 2;
  const s = new THREE.Shape();
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y);
  s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h);
  s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r);
  s.quadraticCurveTo(x, y, x + r, y);
  return s;
}

export class ScreenDisplay {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 50);
  readonly target = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: true });
  readonly viewport: DisplayViewport = { x: 0, y: 0, width: 1, height: 1 };
  private readonly body = new THREE.Group();
  private readonly metal = new THREE.MeshStandardMaterial({ color: 0xc7cdd2, metalness: 0.45, roughness: 0.29 });
  private readonly glass = new THREE.MeshStandardMaterial({ color: 0x080b10, metalness: 0.12, roughness: 0.18 });
  private readonly rear = new THREE.MeshStandardMaterial({ color: 0x323940, roughness: 0.6 });
  private readonly pixels = new THREE.MeshBasicMaterial({ map: this.target.texture, toneMapped: false });
  private geometries: THREE.BufferGeometry[] = [];
  private size = { width: 0, height: 0, pixelRatio: 0 };

  constructor() {
    this.camera.position.set(0, 0, 20);
    const key = new THREE.DirectionalLight(0xffffff, 3.2);
    key.position.set(-8, 12, 14);
    const fill = new THREE.DirectionalLight(0xdfe8f4, 1.5);
    fill.position.set(12, -4, 8);
    this.scene.add(this.body, new THREE.HemisphereLight(0xffffff, 0x53616d, 1.9), key, fill);
  }

  setSize(width: number, height: number, pixelRatio: number): void {
    if (this.size.width === width && this.size.height === height && this.size.pixelRatio === pixelRatio) return;
    Object.assign(this.size, { width, height, pixelRatio });
    for (const g of this.geometries) g.dispose();
    this.geometries = [];
    this.body.clear();
    const units = 16 / width;
    const w = 16;
    const h = height * units;
    const outer = Math.min(12, width * 0.012);
    const bezel = Math.min(16, Math.max(8, height * 0.035));
    const inset = outer + bezel;
    Object.assign(this.viewport, { x: inset, y: inset, width: Math.max(1, width - inset * 2), height: Math.max(1, height - inset * 2) });
    const vw = this.viewport.width * units;
    const vh = this.viewport.height * units;
    const bodyW = w - outer * units * 2;
    const bodyH = h - outer * units * 2;
    const radius = Math.min(0.42, bodyH * 0.12);
    const shell = (sw: number, sh: number, r: number, depth: number, z: number, material: THREE.Material) => {
      const geometry = new THREE.ExtrudeGeometry(roundedRect(sw, sh, r), { depth, bevelEnabled: true, bevelSize: 0.035, bevelThickness: 0.035, bevelSegments: 3, steps: 1, curveSegments: 12 });
      this.geometries.push(geometry);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.z = z;
      this.body.add(mesh);
    };
    shell(bodyW - 0.1, bodyH - 0.1, radius, 0.22, -0.28, this.rear);
    shell(bodyW, bodyH, radius, 0.11, -0.05, this.metal);
    shell(bodyW - 0.095, bodyH - 0.095, Math.max(0.05, radius - 0.04), 0.035, 0.09, this.glass);
    const face = new THREE.ShapeGeometry(roundedRect(vw, vh, Math.min(0.12, vh * 0.06)), 12);
    const pos = face.getAttribute('position');
    const uv = face.getAttribute('uv');
    for (let i = 0; i < pos.count; i += 1) uv.setXY(i, (pos.getX(i) + vw / 2) / vw, (pos.getY(i) + vh / 2) / vh);
    this.geometries.push(face);
    const screen = new THREE.Mesh(face, this.pixels);
    screen.position.z = 0.175;
    this.body.add(screen);
    this.camera.left = -w / 2;
    this.camera.right = w / 2;
    this.camera.top = h / 2;
    this.camera.bottom = -h / 2;
    this.camera.updateProjectionMatrix();
    this.target.setSize(Math.max(1, Math.round(this.viewport.width * pixelRatio)), Math.max(1, Math.round(this.viewport.height * pixelRatio)));
  }

  render(renderer: THREE.WebGLRenderer): void {
    renderer.setRenderTarget(null);
    renderer.setViewport(0, 0, this.size.width, this.size.height);
    renderer.setClearColor(0x000000, 0);
    renderer.clear();
    renderer.render(this.scene, this.camera);
  }

  dispose(): void {
    for (const g of this.geometries) g.dispose();
    for (const m of [this.metal, this.glass, this.rear, this.pixels]) m.dispose();
    this.target.dispose();
    this.scene.clear();
  }
}
