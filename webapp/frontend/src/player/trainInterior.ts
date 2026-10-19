// A close view of a metro saloon wall: formed laminate, joints, a door reveal,
// stainless trim/grab rail and a louvered ceiling with a linear luminaire.
// Materials and installation details are modeled geometry, not a background photograph.
import * as THREE from 'three';
import { roundedRect } from './screenGeometry';

function materialGrain(): THREE.DataTexture {
  const side = 128;
  const data = new Uint8Array(side * side * 4);
  let seed = 9127;
  for (let i = 0; i < side * side; i += 1) {
    seed = (Math.imul(seed, 1664525) + 1013904223) | 0;
    const v = 170 + ((seed >>> 24) & 31);
    data.set([v, v, v, 255], i * 4);
  }
  const texture = new THREE.DataTexture(data, side, side);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(16, 6);
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.needsUpdate = true;
  return texture;
}

export interface WallOpening { width: number; height: number; radius: number; centerY: number }

export class TrainInterior {
  readonly group = new THREE.Group();
  readonly railings = new THREE.Group();
  private readonly grain = materialGrain();
  private readonly laminate = new THREE.MeshStandardMaterial({ color: 0xc6c8c0, roughness: 0.72, metalness: 0.03, bumpMap: this.grain, bumpScale: 0.0008 });
  private readonly ceiling = new THREE.MeshStandardMaterial({ color: 0xb7bdb9, roughness: 0.66, metalness: 0.1 });
  private readonly steel = new THREE.MeshStandardMaterial({ color: 0x9ba5ad, roughness: 0.32, metalness: 0.8, roughnessMap: this.grain });
  private readonly shadow = new THREE.MeshStandardMaterial({ color: 0x151a1c, roughness: 0.95 });
  private readonly rubber = new THREE.MeshStandardMaterial({ color: 0x282d2e, roughness: 0.92 });
  private readonly window = new THREE.MeshStandardMaterial({ color: 0x101b21, roughness: 0.25, metalness: 0.28 });
  private readonly light = new THREE.MeshBasicMaterial({ color: 0xf4f6e9 });
  private readonly joint = new THREE.MeshStandardMaterial({ color: 0x767d7c, roughness: 0.84 });
  private geometries: THREE.BufferGeometry[] = [];

  constructor() {
    this.group.name = 'train-wall-installation';
    this.railings.name = 'train-railings-layer';
  }

  private mesh(geometry: THREE.BufferGeometry, material: THREE.Material, x: number, y: number, z: number, name: string): THREE.Mesh {
    this.geometries.push(geometry);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, y, z);
    mesh.name = name;
    mesh.receiveShadow = true;
    mesh.castShadow = material !== this.light;
    this.group.add(mesh);
    return mesh;
  }

  private box(w: number, h: number, d: number, material: THREE.Material, x: number, y: number, z: number, name: string): THREE.Mesh {
    return this.mesh(new THREE.BoxGeometry(w, h, d), material, x, y, z, name);
  }

  setSize(width: number, height: number, opening: WallOpening | null): void {
    for (const g of this.geometries) g.dispose();
    this.geometries = [];
    this.group.clear();
    this.railings.clear();
    const w = width + 3;
    const h = height + 2;
    const { width: ow, height: oh, radius, centerY } = opening ?? { width: width * .7, height: height * .6, radius: .3, centerY: 0 };
    const wall = roundedRect(w, h, 0.1);
    const hole = roundedRect(ow + 0.16, oh + 0.16, radius + 0.08);
    if (opening) wall.holes.push(new THREE.Path(hole.getPoints().map(p => p.add(new THREE.Vector2(0, centerY))).reverse()));
    this.mesh(new THREE.ExtrudeGeometry(wall, { depth: 0.12, bevelEnabled: false, curveSegments: 18 }), this.laminate, 0, 0, -0.58, 'laminate-wall-with-display-aperture').castShadow = false;
    const mount = roundedRect(ow + 0.2, oh + 0.2, radius + 0.08);
    mount.holes.push(new THREE.Path(roundedRect(ow - 0.1, oh - 0.1, radius).getPoints().reverse()));
    if (opening) this.mesh(new THREE.ExtrudeGeometry(mount, { depth: 0.16, bevelEnabled: false, curveSegments: 18 }), this.rubber, 0, centerY, -0.49, 'recessed-mounting-gasket');

    // Vertical panels flank the device; their joints continue behind the ceiling and dado.
    for (const x of [-ow / 2 - 0.34, ow / 2 + 0.31]) {
      this.box(0.018, h, 0.02, this.joint, x, 0, -0.445, 'vertical-laminate-panel-joint');
      this.box(0.028, h, 0.018, this.ceiling, x + 0.025, 0, -0.43, 'panel-joint-highlight');
    }

    // Real door/window reveal and stainless grab rail remain visible at the crop's right edge.
    const doorX = width / 2 - 0.20;
    this.box(0.76, h, 0.18, this.steel, doorX, 0, -0.31, 'metro-door-aluminium-stile');
    this.box(0.56, h, 0.08, this.rubber, doorX + 0.04, 0, -0.18, 'door-window-rubber-seal');
    this.box(0.46, h, 0.04, this.window, doorX + 0.08, 0, -0.115, 'dark-door-window');
    this.box(0.022, h, 0.01, this.ceiling, doorX - 0.11, 0, -0.085, 'window-glass-reflection');
    const railX = -width / 2 + 0.27;
    this.railings.add(this.mesh(new THREE.CylinderGeometry(0.055, 0.055, h, 18), this.steel, railX, 0, -0.08, 'stainless-grab-rail'));
    for (const y of [-height * 0.32, height * 0.32]) {
      const boss = this.mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.22, 20), this.steel, railX, y, -0.28, 'grab-rail-wall-fixing');
      boss.rotation.x = Math.PI / 2;
      this.railings.add(boss);
    }

    const top = height / 2 - Math.min(0.20, height * 0.07);
    this.box(w, 0.16, 0.55, this.ceiling, 0, top, -0.25, 'formed-ceiling-valance');
    this.box(w, 0.035, 0.05, this.shadow, 0, top - 0.105, -0.13, 'ceiling-luminaire-recess');
    this.box(w - 0.9, 0.035, 0.025, this.light, -0.1, top - 0.095, -0.08, 'linear-saloon-light');
    for (let i = 0; i < 3; i += 1) {
      this.box(w, 0.016, 0.12, this.joint, 0, top + 0.10 + i * 0.07, -0.05, 'ceiling-ventilation-louver');
    }
    const bottom = -height / 2 + 0.11;
    this.box(w, 0.09, 0.17, this.steel, 0, bottom, -0.29, 'brushed-aluminium-wall-dado');
    this.box(w, 0.018, 0.04, this.shadow, 0, bottom + 0.06, -0.21, 'dado-contact-joint');

    for (const x of opening ? [-ow / 2 - 0.12, ow / 2 + 0.12] : []) {
      for (const y of [centerY - oh / 2 + 0.16, centerY + oh / 2 - 0.16]) {
        this.mesh(new THREE.CylinderGeometry(0.024, 0.024, 0.018, 12), this.steel, x, y, -0.44, 'flush-mounting-fastener').rotation.x = Math.PI / 2;
      }
    }
  }

  dispose(): void {
    for (const g of this.geometries) g.dispose();
    for (const m of [this.laminate, this.ceiling, this.steel, this.shadow, this.rubber, this.window, this.light, this.joint]) m.dispose();
    this.grain.dispose();
    this.group.clear();
    this.railings.clear();
  }
}
