// The driver's cab of a metro train (Moskva-2020 cues: light-grey moulded trim, a bonded black-frit
// windshield, a graphite desk with multifunction displays, physical push buttons, manometers and
// the driver's controller), built around the windshield, which carries the live LiDAR view.
// Coordinates are metres: the windshield (live display) plane is z = 0, the seated driver's eye
// looks down -z from (0, 0, CAB_EYE), y is up. The front (windshield, pillars, header, overhead
// panel, desk) is parametric on the measured display region, so the Player's view and the boarding
// animation's last frame are the same geometry. `full` adds what only the boarding animation sees:
// side walls, floor, the rear bulkhead with its sliding door and the driver's seat.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { roundedRect } from './screenGeometry';
import type { ScreenLighting } from './screenLighting';
import { BOOT_ACCENTS, BOOT_SCREENS, bootProgress } from './cabBoot';
import { CAB_VERTEX, MFI_FRAGMENT } from './cabShaders';

/** Vertical field of view of the seated view (degrees, over the Player canvas height). */
export const CAB_FOV = 50;
/** Distance of the seated eye from the windshield plane (m). */
export const CAB_EYE = 1.6;
export const CAB_FLOOR = -1.25;
export const CAB_CEILING = 1.18;
export const CAB_HALF_WIDTH = 1.42;
/** The rear bulkhead between the cab and the saloon (z, m). */
export const CAB_BULKHEAD = 2.6;
export const CAB_DOOR = { halfWidth: 0.5, top: 0.86 };

export interface CabRegion { height: number; top: number; width?: number; left?: number }
export interface PixelRect { x: number; y: number; width: number; height: number }
/** World rectangle on the windshield plane; y0 is the bottom edge. */
export interface WorldRect { x0: number; x1: number; y0: number; y1: number }

export interface CabLayout {
  /** canvas CSS size */
  width: number;
  height: number;
  /** metres per CSS pixel on the windshield plane */
  unit: number;
  /** the active (live image) area in canvas pixels */
  face: PixelRect;
  faceWorld: WorldRect;
  /** the windshield glass (the frit band runs between it and the active area) */
  glass: WorldRect;
  /** outer edge of the moulded trim around the windshield */
  frame: WorldRect;
}

const clamp = THREE.MathUtils.clamp;

/** Where the windshield sits for a canvas and its display region (CSS px relative to the canvas). */
export function cabLayout(width: number, height: number, region: CabRegion = { height, top: 0 }): CabLayout {
  const rw = region.width ?? width;
  const rl = region.left ?? (width - rw) / 2;
  const side = Math.max(56, rw * 0.1);
  const top = clamp(region.height * 0.085, 36, 60);
  const bottom = clamp(region.height * 0.045, 22, 32);
  const bezel = clamp(region.height * 0.024, 7, 14);
  const trim = clamp(rw * 0.016, 16, 28);
  const face = {
    x: rl + side + bezel,
    y: region.top + top + bezel,
    width: Math.max(1, rw - (side + bezel) * 2),
    height: Math.max(1, region.height - top - bottom - bezel * 2),
  };
  const unit = (2 * CAB_EYE * Math.tan(THREE.MathUtils.degToRad(CAB_FOV / 2))) / Math.max(1, height);
  const rect = (x0: number, y0: number, x1: number, y1: number): WorldRect => ({
    x0: (x0 - width / 2) * unit, x1: (x1 - width / 2) * unit, y0: (height / 2 - y1) * unit, y1: (height / 2 - y0) * unit,
  });
  const { x, y } = face;
  const r = x + face.width;
  const b = y + face.height;
  return {
    width, height, unit, face,
    faceWorld: rect(x, y, r, b),
    glass: rect(x - bezel, y - bezel, r + bezel, b + bezel),
    frame: rect(x - bezel - trim, y - bezel - trim, r + bezel + trim, b + bezel + trim),
  };
}

/** A material colour given as an sRGB hex: lit in linear light, then encoded (`encodePbr`). */
export const srgb = (hex: number): THREE.Color => new THREE.Color(hex).convertSRGBToLinear();

/** Compress and gamma-encode a PBR material's light: the cab shares the display-valued pipeline. */
export function encodePbr(material: THREE.MeshStandardMaterial): void {
  material.onBeforeCompile = shader => {
    shader.fragmentShader = shader.fragmentShader.replace('#include <opaque_fragment>',
      'outgoingLight = pow(outgoingLight / (vec3(1.0) + outgoingLight * .55), vec3(1.0 / 2.2));\n#include <opaque_fragment>');
  };
  material.customProgramCacheKey = () => 'cab-pbr-encoded';
}

interface ScreenSpec { kind: number; seed: number }
/** Fixed instrument set; the boot powers them in this order. */
const SCREENS: ScreenSpec[] = [
  { kind: 2, seed: 1 }, // left pillar: platform camera monitor
  { kind: 2, seed: 2 }, // right pillar: platform camera monitor
  { kind: 3, seed: 3 }, // overhead panel indicator LEDs
  { kind: 0, seed: 4 }, // desk: traction MFI
  { kind: 1, seed: 5 }, // desk: train diagnostics MFI
  { kind: 4, seed: 6 }, // desk: brake cylinder manometer
  { kind: 4, seed: 7 }, // desk: main reservoir manometer
  { kind: 1, seed: 8 }, // left wing MFI
  { kind: 3, seed: 9 }, // right wing indicator LEDs
];
type CapTone = 'white' | 'green' | 'amber' | 'red';

export interface CockpitOptions {
  lighting?: ScreenLighting;
  /** the boarding animation's whole cab (walls, floor, bulkhead door, seat) */
  full?: boolean;
}

export class CabCockpit {
  readonly group = new THREE.Group();
  /** sliding door leaves of the rear bulkhead (full cab only) */
  readonly doorLeaves: THREE.Object3D[] = [];
  private readonly full: boolean;
  private geometries: THREE.BufferGeometry[] = [];
  /** repeated parts queued during a build, drawn as one instanced mesh per geometry and material */
  private readonly batches = new Map<string, { geometry: THREE.BufferGeometry; material: THREE.Material; name: string; matrices: THREE.Matrix4[] }>();
  private instanced: THREE.InstancedMesh[] = [];
  private readonly shared = new Map<string, THREE.BufferGeometry>();
  private readonly trim = new THREE.MeshStandardMaterial({ color: srgb(0xc9cfd6), roughness: 0.58, metalness: 0.04, side: THREE.DoubleSide });
  private readonly trimShade = new THREE.MeshStandardMaterial({ color: srgb(0xa9b1ba), roughness: 0.6, metalness: 0.04, side: THREE.DoubleSide });
  /** walls behind the seated view, lit by the cab's own LED panel (never seen from the seat) */
  private readonly rearTrim = new THREE.MeshStandardMaterial({ color: srgb(0xc9cfd6), roughness: 0.58, metalness: 0.04, side: THREE.DoubleSide, emissive: srgb(0xc9cfd6), emissiveIntensity: 0.3 });
  private readonly black = new THREE.MeshStandardMaterial({ color: srgb(0x0b0d10), roughness: 0.9, metalness: 0.02, side: THREE.DoubleSide });
  private readonly desk = new THREE.MeshStandardMaterial({ color: srgb(0x272c33), roughness: 0.62, metalness: 0.14, side: THREE.DoubleSide });
  private readonly glare = new THREE.MeshStandardMaterial({ color: srgb(0x15181c), roughness: 0.95, metalness: 0.02, side: THREE.DoubleSide });
  private readonly aluminium = new THREE.MeshStandardMaterial({ color: srgb(0xb6bec7), roughness: 0.3, metalness: 0.85 });
  private readonly bronze = new THREE.MeshStandardMaterial({ color: srgb(0xbe9176), roughness: 0.24, metalness: 0.86 });
  private readonly upholstery = new THREE.MeshStandardMaterial({ color: srgb(0x2f3a4c), roughness: 0.92, metalness: 0.02 });
  private readonly seatInsert = new THREE.MeshStandardMaterial({ color: srgb(0x485569), roughness: 0.95, metalness: 0.0 });
  private readonly floorMat = new THREE.MeshStandardMaterial({ color: srgb(0x5b6169), roughness: 0.85, metalness: 0.05, side: THREE.DoubleSide });
  private readonly sideGlass = new THREE.MeshStandardMaterial({ color: srgb(0x070a0f), roughness: 0.1, metalness: 0.6, side: THREE.DoubleSide });
  private readonly paintRed = new THREE.MeshStandardMaterial({ color: srgb(0xd7133b), roughness: 0.4, metalness: 0.1 });
  private readonly yellow = new THREE.MeshStandardMaterial({ color: srgb(0xf2b400), roughness: 0.45, metalness: 0.05 });
  private readonly caps: Record<CapTone, THREE.MeshStandardMaterial> = {
    white: new THREE.MeshStandardMaterial({ color: srgb(0xe8ecf0), roughness: 0.4, emissive: srgb(0xdfe8ff) }),
    green: new THREE.MeshStandardMaterial({ color: srgb(0x1fa86b), roughness: 0.4, emissive: srgb(0x00d47e) }),
    amber: new THREE.MeshStandardMaterial({ color: srgb(0xe0a100), roughness: 0.4, emissive: srgb(0xffb000) }),
    red: new THREE.MeshStandardMaterial({ color: srgb(0xc8102e), roughness: 0.4, emissive: srgb(0xff1e3c) }),
  };
  /** cab LED lighting is on before the instruments boot */
  private readonly lamp = new THREE.MeshBasicMaterial({ color: 0xf4f8ff, toneMapped: false, side: THREE.DoubleSide });
  private readonly doorRed = new THREE.MeshBasicMaterial({ color: 0xff2448, toneMapped: false });
  private readonly screens: THREE.ShaderMaterial[];
  private readonly lit: THREE.MeshStandardMaterial[];

  constructor(options: CockpitOptions = {}) {
    this.full = !!options.full;
    this.group.name = 'driver-cab';
    this.lit = [this.trim, this.trimShade, this.rearTrim, this.black, this.desk, this.glare, this.aluminium, this.bronze, this.upholstery, this.seatInsert, this.floorMat, this.sideGlass, this.paintRed, this.yellow, ...Object.values(this.caps)];
    for (const m of this.lit) {
      if (options.lighting) options.lighting.apply(m, m === this.trim || m === this.trimShade ? 0.9 : 0.55, true);
      else encodePbr(m);
    }
    this.screens = SCREENS.map(s => new THREE.ShaderMaterial({
      vertexShader: CAB_VERTEX, fragmentShader: MFI_FRAGMENT, toneMapped: false,
      uniforms: { uPower: { value: 1 }, uSeed: { value: s.seed }, uKind: { value: s.kind }, uSize: { value: new THREE.Vector2(1, 1) } },
    }));
  }

  private add<T extends THREE.BufferGeometry>(geometry: T, material: THREE.Material, name: string, parent: THREE.Object3D = this.group, own = true): THREE.Mesh<T, THREE.Material> {
    if (own) this.geometries.push(geometry);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = name;
    parent.add(mesh);
    return mesh;
  }

  /** One geometry per distinct size, shared by repeated parts (buttons, slats, screws). */
  private part(key: string, make: () => THREE.BufferGeometry): THREE.BufferGeometry {
    let geometry = this.shared.get(key);
    if (!geometry) {
      geometry = make();
      this.shared.set(key, geometry);
    }
    return geometry;
  }

  private box(w: number, h: number, d: number, radius: number, material: THREE.Material, x: number, y: number, z: number, name: string, parent?: THREE.Object3D): THREE.Mesh {
    const r = Math.min(radius, w / 2, h / 2, d / 2);
    const geometry = this.part(`box:${w}:${h}:${d}:${r}`, () => (r > 0 ? new RoundedBoxGeometry(w, h, d, 2, r) : new THREE.BoxGeometry(w, h, d)));
    const mesh = this.add(geometry, material, name, parent, false);
    mesh.position.set(x, y, z);
    return mesh;
  }

  /** A flat quad through four corners. */
  private quad(a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3, d: THREE.Vector3, material: THREE.Material, name: string, parent?: THREE.Object3D): THREE.Mesh {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute([...a.toArray(), ...b.toArray(), ...c.toArray(), ...d.toArray()], 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 1], 2));
    geometry.setIndex([0, 1, 2, 0, 2, 3]);
    geometry.computeVertexNormals();
    return this.add(geometry, material, name, parent);
  }

  /** An instrument face with its black housing, facing +z of `holder` (placed by the caller). */
  private screen(index: number, w: number, h: number, holder: THREE.Object3D, name: string, depth = 0.035): void {
    this.box(w + 0.034, h + 0.034, depth, 0.01, this.black, 0, 0, -depth / 2, `${name}-housing`, holder);
    const face = this.add(new THREE.PlaneGeometry(w, h), this.screens[index], name, holder);
    face.position.z = 0.0008;
    this.screens[index].uniforms.uSize.value.set(w, h);
  }

  private holder(position: THREE.Vector3, rotation: THREE.Euler, parent: THREE.Object3D = this.group): THREE.Group {
    const g = new THREE.Group();
    g.position.copy(position);
    g.rotation.copy(rotation);
    parent.add(g);
    return g;
  }

  /** Queue one copy of a repeated part at a position (and rotation) in `parent`. */
  private repeat(geometry: THREE.BufferGeometry, material: THREE.Material, name: string, parent: THREE.Object3D, position: THREE.Vector3, rotation = new THREE.Euler()): void {
    parent.updateWorldMatrix(true, false);
    this.group.updateWorldMatrix(true, false);
    const local = new THREE.Matrix4().compose(position, new THREE.Quaternion().setFromEuler(rotation), new THREE.Vector3(1, 1, 1));
    const matrix = this.group.matrixWorld.clone().invert().multiply(parent.matrixWorld).multiply(local);
    const key = `${geometry.uuid}:${material.uuid}`;
    let batch = this.batches.get(key);
    if (!batch) this.batches.set(key, batch = { geometry, material, name, matrices: [] });
    batch.matrices.push(matrix);
  }

  private repeatBox(w: number, h: number, d: number, radius: number, material: THREE.Material, x: number, y: number, z: number, name: string, parent: THREE.Object3D = this.group, rotation?: THREE.Euler): void {
    const r = Math.min(radius, w / 2, h / 2, d / 2);
    const geometry = this.part(`box:${w}:${h}:${d}:${r}`, () => (r > 0 ? new RoundedBoxGeometry(w, h, d, 2, r) : new THREE.BoxGeometry(w, h, d)));
    this.repeat(geometry, material, name, parent, new THREE.Vector3(x, y, z), rotation);
  }

  /** Draw every queued repeated part: one instanced mesh per geometry and material. */
  private flushRepeats(): void {
    for (const { geometry, material, name, matrices } of this.batches.values()) {
      const mesh = new THREE.InstancedMesh(geometry, material, matrices.length);
      matrices.forEach((m, i) => mesh.setMatrixAt(i, m));
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
      mesh.name = name;
      this.group.add(mesh);
      this.instanced.push(mesh);
    }
    this.batches.clear();
  }

  /** A push button: dark collar and a coloured, backlit cap. */
  private button(parent: THREE.Object3D, x: number, y: number, tone: CapTone, size = 0.026): void {
    this.repeatBox(size + 0.012, size + 0.012, 0.006, 0.003, this.black, x, y, 0.003, 'desk-button-collar', parent);
    this.repeatBox(size, size, 0.012, 0.004, this.caps[tone], x, y, 0.008, 'desk-button', parent);
  }

  build(layout: CabLayout): void {
    for (const g of this.geometries) g.dispose();
    for (const g of this.shared.values()) g.dispose();
    for (const m of this.instanced) m.dispose();
    this.instanced = [];
    this.geometries = [];
    this.shared.clear();
    this.group.clear();
    this.doorLeaves.length = 0;
    const F = layout.frame;
    const G = layout.glass;
    const v = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
    const fw = F.x1 - F.x0;
    const fh = F.y1 - F.y0;
    const fcx = (F.x0 + F.x1) / 2;
    const fcy = (F.y0 + F.y1) / 2;
    const gw = G.x1 - G.x0;
    const gh = G.y1 - G.y0;
    const gcx = (G.x0 + G.x1) / 2;
    const gcy = (G.y0 + G.y1) / 2;
    const glassRadius = Math.min(0.06, gh * 0.08);

    // Windshield: black bonding bead, then the light-grey moulded trim with a shadow gap.
    const ring = (outer: THREE.Shape, inner: THREE.Shape, dx = 0, dy = 0) => {
      outer.holes.push(new THREE.Path(inner.getPoints(10).map(p => p.add(new THREE.Vector2(dx, dy))).reverse()));
      return outer;
    };
    const bead = this.add(new THREE.ExtrudeGeometry(ring(roundedRect(gw + 0.03, gh + 0.03, glassRadius + 0.015), roundedRect(gw, gh, glassRadius)), { depth: 0.012, bevelEnabled: false, curveSegments: 10 }), this.black, 'windshield-bonding-bead');
    bead.position.set(gcx, gcy, 0);
    const trimShape = ring(roundedRect(fw, fh, Math.min(0.14, fh * 0.16)), roundedRect(gw + 0.022, gh + 0.022, glassRadius + 0.011), gcx - fcx, gcy - fcy);
    const moulding = this.add(new THREE.ExtrudeGeometry(trimShape, { depth: 0.03, bevelEnabled: true, bevelSize: 0.012, bevelThickness: 0.01, bevelSegments: 3, curveSegments: 10 }), this.trim, 'windshield-moulded-trim');
    moulding.position.set(fcx, fcy, 0.004);
    // the moulding's screws along the top, as on the reference cab trim
    for (let i = 0; i < 7; i++) {
      this.repeat(this.part('screw', () => new THREE.CylinderGeometry(0.006, 0.006, 0.004, 10)), this.aluminium, 'trim-screw', this.group,
        v(F.x0 + 0.12 + (fw - 0.24) * (i / 6), F.y1 - 0.016, 0.046), new THREE.Euler(Math.PI / 2, 0, 0));
    }

    // A-pillars: light-grey panels flaring back to the cab sides, with seams, a vent grille,
    // a bronze grab handle, the platform camera monitor and the side window beyond.
    const zp = 0.95;
    for (const sx of [-1, 1]) {
      const xi = sx < 0 ? F.x0 : F.x1;
      const xo = sx * CAB_HALF_WIDTH;
      const normal = new THREE.Vector3(-sx * zp, 0, Math.abs(xo - xi)).normalize();
      const at = (s: number, y: number, lift = 0) => v(xi + (xo - xi) * s, y, zp * s).addScaledVector(normal, lift);
      const patch = (s0: number, s1: number, y0: number, y1: number, material: THREE.Material, name: string, lift = 0.002) =>
        this.quad(at(s0, y0, lift), at(s1, y0, lift), at(s1, y1, lift), at(s0, y1, lift), material, name);
      patch(0, 1, CAB_FLOOR, CAB_CEILING + 0.5, this.trim, sx < 0 ? 'left-pillar' : 'right-pillar', 0);
      patch(0.0, 0.01, F.y0 - 0.3, F.y1 + 0.3, this.black, 'pillar-shadow-gap', 0.001);
      for (const y of [F.y1 + 0.02, fcy + 0.33, F.y0 + 0.04]) patch(0.01, 1, y - 0.003, y + 0.003, this.trimShade, 'pillar-panel-seam', 0.0012);
      // side window beyond the narrow pillar
      patch(0.12, 1, F.y0 + 0.02, F.y1 + 0.01, this.black, 'side-window-surround', 0.0015);
      patch(0.135, 1, F.y0 + 0.045, F.y1 - 0.015, this.sideGlass, 'side-window', 0.002);
      // air vent grille low on the pillar
      const vy = F.y0 + 0.2;
      patch(0.025, 0.1, vy - 0.07, vy + 0.07, this.black, 'pillar-vent-recess', 0.002);
      for (let i = 0; i < 5; i++) {
        const y = vy - 0.052 + i * 0.026;
        patch(0.028, 0.097, y - 0.004, y + 0.004, this.trimShade, 'pillar-vent-slat', 0.006);
      }
      // grab handle running up the pillar
      this.add(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
        at(0.3, fcy - 0.3, 0.004), at(0.3, fcy - 0.28, 0.05), at(0.3, fcy + 0.28, 0.05), at(0.3, fcy + 0.3, 0.004),
      ]), 24, 0.012, 10), this.bronze, 'pillar-grab-handle');
      // platform camera monitor on an arm from the pillar, angled to the driver
      const foot = at(0.06, fcy + 0.2, 0);
      const mount = at(0.07, fcy + 0.2, 0.045);
      const arm = this.add(new THREE.CylinderGeometry(0.008, 0.008, foot.distanceTo(mount), 8), this.black, 'camera-monitor-arm');
      arm.position.copy(foot).add(mount).multiplyScalar(0.5);
      arm.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), mount.clone().sub(foot).normalize());
      const monitor = this.holder(mount, new THREE.Euler(0, -sx * 0.9, 0));
      this.screen(sx < 0 ? 0 : 1, 0.1, 0.15, monitor, sx < 0 ? 'left-camera-monitor' : 'right-camera-monitor', 0.03);
    }

    // Header: the sun-visor roller housing along the windshield top, then the ceiling with an
    // LED panel and the overhead switch panel, kept clear of the glass at every head position.
    const visorZ = 0.085;
    this.box(fw - 0.14, 0.075, 0.11, 0.025, this.trim, fcx, F.y1 + 0.03, visorZ, 'sun-visor-housing');
    this.box(fw - 0.2, 0.006, 0.05, 0, this.black, fcx, F.y1 - 0.0075, visorZ + 0.005, 'sun-visor-slot');
    this.box(0.12, 0.022, 0.03, 0.008, this.black, fcx, F.y1 - 0.02, visorZ + 0.03, 'sun-visor-pull');
    this.box(0.16, 0.006, 0.004, 0, this.paintRed, fcx, F.y1 + 0.03, visorZ + 0.057, 'sun-visor-red-line');
    const zc = 1.25;
    const ceilingY = (z: number) => F.y1 + 0.07 + (CAB_CEILING - F.y1 - 0.07) * (z / zc);
    this.quad(v(-2, ceilingY(0), 0), v(2, ceilingY(0), 0), v(2, CAB_CEILING, zc), v(-2, CAB_CEILING, zc), this.trim, 'cab-ceiling');
    const panelAt = (x: number, z: number) => v(x, ceilingY(z) - 0.004, z);
    this.quad(panelAt(-0.42, 0.95), panelAt(0.42, 0.95), panelAt(0.42, 1.2), panelAt(-0.42, 1.2), this.lamp, 'cab-ceiling-led-panel');
    const eye = CAB_EYE;
    const margin = 10 * layout.unit;
    const zFar = 0.38;
    const zNear = 0.86;
    // the panel's far lower edge must project above the glass for head heights ±0.05 m
    const clear = Math.max(...[-0.05, 0.05].map(hy => hy + (eye - zFar) * ((G.y1 - hy) / eye + margin / eye)));
    const y0 = Math.max(clear, ceilingY(zFar) - 0.3);
    const y1 = Math.max(y0 + 0.08, ceilingY(zNear) - 0.24);
    const hw = 0.42;
    this.quad(v(-hw, y0, zFar), v(hw, y0, zFar), v(hw, y1, zNear), v(-hw, y1, zNear), this.desk, 'overhead-panel-face');
    this.quad(v(-hw, y0, zFar), v(-hw, ceilingY(zFar), zFar), v(hw, ceilingY(zFar), zFar), v(hw, y0, zFar), this.trimShade, 'overhead-panel-front');
    for (const sx of [-1, 1]) {
      const x = sx * hw;
      this.quad(v(x, y0, zFar), v(x, y1, zNear), v(x, ceilingY(zNear), zNear), v(x, ceilingY(zFar), zFar), this.trimShade, 'overhead-panel-side');
    }
    // switch plate on the panel's face, which looks down and back at the seat
    const faceDir = new THREE.Vector3(0, y1 - y0, zNear - zFar).normalize();
    const faceNormal = new THREE.Vector3(0, -faceDir.z, faceDir.y);
    const overhead = new THREE.Group();
    overhead.position.set(0, (y0 + y1) / 2, (zFar + zNear) / 2).addScaledVector(faceNormal, 0.002);
    overhead.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(new THREE.Vector3(1, 0, 0), faceDir.clone().negate(), faceNormal));
    this.group.add(overhead);
    const ledFace = this.add(new THREE.PlaneGeometry(0.4, 0.04), this.screens[2], 'overhead-indicator-leds', overhead);
    ledFace.position.set(0, 0.17, 0.0008);
    this.screens[2].uniforms.uSize.value.set(0.4, 0.04);
    const tones: CapTone[] = ['white', 'white', 'green', 'white', 'amber', 'white', 'white', 'red'];
    for (let i = 0; i < 8; i++) {
      this.button(overhead, -0.3 + i * 0.086, 0.06, tones[i], 0.03);
      this.button(overhead, -0.3 + i * 0.086, -0.04, 'white', 0.03);
    }

    // Desk: a matte glare shield with defroster slots under the glass, then the sloping
    // instrument face (displays, manometers, buttons, controller, emergency stop, radio).
    const shieldY = F.y0 - 0.014;
    const lipZ = 0.34;
    this.quad(v(-1.6, shieldY, 0.0), v(1.6, shieldY, 0.0), v(1.6, shieldY, lipZ), v(-1.6, shieldY, lipZ), this.glare, 'glare-shield');
    for (let i = 0; i < 4; i++) {
      const w = (fw - 0.5) / 4 - 0.06;
      const x = F.x0 + 0.25 + (w + 0.06) * (i + 0.5);
      this.quad(v(x - w / 2, shieldY + 0.001, 0.05), v(x + w / 2, shieldY + 0.001, 0.05), v(x + w / 2, shieldY + 0.001, 0.09), v(x - w / 2, shieldY + 0.001, 0.09), this.black, 'defroster-vent');
      for (let k = 0; k < 4; k++) this.repeatBox(w, 0.004, 0.003, 0, this.desk, x, shieldY + 0.003, 0.056 + k * 0.01, 'defroster-vent-slat');
    }
    this.box(3.2, 0.04, 0.04, 0.018, this.desk, 0, shieldY - 0.012, lipZ, 'desk-lip');
    const deskTop = shieldY - 0.03;
    const deskNear = 1.0;
    const deskLow = -0.88;
    this.quad(v(-1.6, deskTop, lipZ), v(1.6, deskTop, lipZ), v(1.6, deskLow, deskNear), v(-1.6, deskLow, deskNear), this.desk, 'desk-instrument-face');
    const down = new THREE.Vector3(0, deskLow - deskTop, deskNear - lipZ);
    const slope = down.length();
    down.normalize();
    const deskNormal = new THREE.Vector3(0, down.z, -down.y);
    const deskFrame = new THREE.Group();
    deskFrame.position.set(0, deskTop, lipZ).addScaledVector(deskNormal, 0.001);
    deskFrame.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(new THREE.Vector3(1, 0, 0), down.clone().negate(), deskNormal));
    this.group.add(deskFrame);
    const on = (s: number) => -s * slope;
    // displays in black bezels, set into the face
    this.screen(3, 0.4, 0.24, this.holder(v(-0.08, on(0.24), 0.012), new THREE.Euler(), deskFrame), 'desk-traction-display', 0.03);
    this.screen(4, 0.4, 0.24, this.holder(v(0.4, on(0.24), 0.012), new THREE.Euler(), deskFrame), 'desk-diagnostics-display', 0.03);
    for (const [i, x] of [[5, -0.62], [6, -0.4]] as const) {
      const g = this.holder(v(x, on(0.22), 0.01), new THREE.Euler(), deskFrame);
      const dial = this.add(this.part('dial', () => new THREE.CircleGeometry(0.085, 40)), this.screens[i], 'desk-manometer', g, false);
      dial.position.z = 0.004;
      this.screens[i].uniforms.uSize.value.set(0.17, 0.17);
      const rim = this.add(this.part('dial-rim', () => new THREE.TorusGeometry(0.088, 0.009, 10, 40)), this.aluminium, 'desk-manometer-rim', g, false);
      rim.position.z = 0.006;
    }
    // push buttons in rows beneath the displays
    const rows: CapTone[][] = [
      ['white', 'white', 'green', 'white', 'white', 'amber', 'white', 'white', 'white', 'red'],
      ['white', 'green', 'white', 'white', 'amber', 'white', 'white', 'green', 'white', 'white'],
      ['amber', 'white', 'white', 'red', 'white', 'white', 'green', 'white', 'white', 'white'],
    ];
    rows.forEach((row, r) => row.forEach((tone, c) => this.button(deskFrame, -0.22 + c * 0.075, on(0.5 + r * 0.075), tone)));
    for (let i = 0; i < 6; i++) {
      this.repeatBox(0.03, 0.05, 0.012, 0.004, this.black, 0.6 + i * 0.06, on(0.56), 0.006, 'desk-toggle-base', deskFrame);
      this.repeatBox(0.008, 0.008, 0.045, 0.003, this.aluminium, 0.6 + i * 0.06, on(0.56) + 0.008, 0.03, 'desk-toggle-lever', deskFrame, new THREE.Euler(-0.4, 0, 0));
    }
    // driver's controller (traction / brake) at the left hand, reverser lock beside it
    const km = this.holder(v(-0.72, on(0.62), 0), new THREE.Euler(), deskFrame);
    this.box(0.16, 0.34, 0.05, 0.012, this.black, 0, 0, 0.025, 'controller-housing', km);
    this.box(0.02, 0.26, 0.006, 0.003, this.aluminium, 0, 0, 0.052, 'controller-gate', km);
    const lever = this.box(0.026, 0.026, 0.17, 0.01, this.black, 0, 0.04, 0.12, 'controller-lever', km);
    lever.rotation.x = 0.32;
    this.box(0.15, 0.04, 0.045, 0.018, this.paintRed, 0, 0.068, 0.205, 'controller-grip', km);
    this.box(0.05, 0.05, 0.02, 0.008, this.aluminium, -0.17, 0.12, 0.01, 'reverser-lock', km);
    // emergency stop and the radio handset at the right hand
    const stop = this.holder(v(0.98, on(0.34), 0), new THREE.Euler(Math.PI / 2, 0, 0), deskFrame);
    this.add(this.part('stop-ring', () => new THREE.CylinderGeometry(0.055, 0.055, 0.012, 28)), this.yellow, 'emergency-stop-collar', stop, false).position.y = 0.006;
    this.add(this.part('stop-cap', () => new THREE.CylinderGeometry(0.04, 0.036, 0.035, 28)), this.caps.red, 'emergency-stop', stop, false).position.y = 0.03;
    const radio = this.holder(v(1.12, on(0.66), 0), new THREE.Euler(), deskFrame);
    this.box(0.12, 0.24, 0.03, 0.012, this.black, 0, 0, 0.015, 'radio-cradle', radio);
    this.box(0.07, 0.2, 0.045, 0.022, this.desk, 0, 0, 0.05, 'radio-handset', radio);
    // wing panels angled towards the seat
    for (const sx of [-1, 1]) {
      const wing = this.holder(v(sx * 1.2, deskTop - 0.12, 0.55), new THREE.Euler(-0.72, -sx * 0.62, 0, 'YXZ'));
      this.box(0.46, 0.34, 0.05, 0.02, this.desk, 0, 0, -0.025, 'wing-panel', wing);
      if (sx < 0) {
        this.screen(7, 0.24, 0.15, this.holder(v(0, 0.05, 0.002), new THREE.Euler(), wing), 'left-wing-display', 0.02);
        for (let i = 0; i < 5; i++) this.button(wing, -0.16 + i * 0.08, -0.11, i === 4 ? 'red' : 'white');
      } else {
        const strip = this.holder(v(0, 0.12, 0.002), new THREE.Euler(), wing);
        const face = this.add(new THREE.PlaneGeometry(0.36, 0.035), this.screens[8], 'right-wing-indicator-leds', strip);
        face.position.z = 0.0008;
        this.screens[8].uniforms.uSize.value.set(0.36, 0.035);
        for (let r = 0; r < 2; r++) for (let i = 0; i < 5; i++) this.button(wing, -0.16 + i * 0.08, 0.02 - r * 0.08, r === 1 && i === 0 ? 'green' : 'white');
      }
    }

    if (this.full) this.buildRear();
    this.flushRepeats();
  }

  /** The cab behind the seated view: walls, floor, ceiling, rear bulkhead and door, seat. */
  private buildRear(): void {
    const v = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
    const w = CAB_HALF_WIDTH;
    const back = CAB_BULKHEAD;
    for (const sx of [-1, 1]) {
      const x = sx * w;
      this.quad(v(x, CAB_FLOOR, 0.9), v(x, CAB_FLOOR, back), v(x, CAB_CEILING, back), v(x, CAB_CEILING, 0.9), this.rearTrim, 'cab-side-wall');
      const gx = x - sx * 0.004;
      this.quad(v(gx, -0.12, 1.0), v(gx, -0.12, 2.3), v(gx, 0.66, 2.3), v(gx, 0.66, 1.0), this.black, 'cab-side-window-surround');
      const hx = x - sx * 0.006;
      this.quad(v(hx, -0.08, 1.04), v(hx, -0.08, 2.26), v(hx, 0.62, 2.26), v(hx, 0.62, 1.04), this.sideGlass, 'cab-side-window');
      this.box(0.03, 0.5, 0.03, 0.012, this.bronze, x - sx * 0.05, 0.25, 2.42, 'cab-side-grab-handle');
    }
    this.quad(v(-w, CAB_CEILING, 1.2), v(w, CAB_CEILING, 1.2), v(w, CAB_CEILING, back), v(-w, CAB_CEILING, back), this.rearTrim, 'cab-rear-ceiling');
    this.quad(v(-0.45, CAB_CEILING - 0.004, 1.5), v(0.45, CAB_CEILING - 0.004, 1.5), v(0.45, CAB_CEILING - 0.004, 2.3), v(-0.45, CAB_CEILING - 0.004, 2.3), this.lamp, 'cab-rear-led-panel');
    this.quad(v(-w, CAB_FLOOR, -0.2), v(w, CAB_FLOOR, -0.2), v(w, CAB_FLOOR, back), v(-w, CAB_FLOOR, back), this.floorMat, 'cab-floor');
    this.quad(v(-1.6, -0.88, 1.0), v(1.6, -0.88, 1.0), v(1.6, CAB_FLOOR, 0.82), v(-1.6, CAB_FLOOR, 0.82), this.desk, 'desk-knee-panel');
    // Rear bulkhead (spans the wider, taller saloon behind it) with the door opening.
    const t = 0.12;
    const zb = back + t / 2;
    const dw = CAB_DOOR.halfWidth;
    const sideW = 1.6 - dw;
    for (const sx of [-1, 1]) this.box(sideW, 3.0, t, 0, this.rearTrim, sx * (dw + sideW / 2), CAB_FLOOR + 1.5, zb, 'rear-bulkhead');
    this.box(dw * 2, 3.0 - (CAB_DOOR.top - CAB_FLOOR), t, 0, this.rearTrim, 0, (CAB_DOOR.top + CAB_FLOOR + 3.0) / 2, zb, 'rear-bulkhead');
    for (const sx of [-1, 1]) this.box(0.05, CAB_DOOR.top - CAB_FLOOR, t + 0.02, 0.01, this.aluminium, sx * (dw + 0.025), (CAB_DOOR.top + CAB_FLOOR) / 2, zb, 'cab-door-frame');
    this.box(dw * 2 + 0.1, 0.05, t + 0.02, 0.01, this.aluminium, 0, CAB_DOOR.top + 0.025, zb, 'cab-door-frame');
    this.box(0.44, 0.09, 0.012, 0.01, this.paintRed, 0, CAB_DOOR.top + 0.17, back + t + 0.008, 'cab-door-sign');
    for (const sx of [-1, 1]) {
      const leaf = new THREE.Group();
      leaf.name = 'cab-door-leaf';
      leaf.position.set(sx * dw / 2, (CAB_DOOR.top + CAB_FLOOR) / 2, back + t + 0.03);
      leaf.userData.side = sx;
      this.group.add(leaf);
      const lh = CAB_DOOR.top - CAB_FLOOR;
      this.box(dw, lh, 0.04, 0.012, this.trimShade, 0, 0, 0, 'cab-door-panel', leaf);
      this.box(dw - 0.12, lh * 0.4, 0.012, 0.012, this.black, 0, lh * 0.18, 0.022, 'cab-door-window-surround', leaf);
      this.box(dw - 0.16, lh * 0.36, 0.012, 0.01, this.sideGlass, 0, lh * 0.18, 0.026, 'cab-door-window', leaf);
      this.box(0.012, lh - 0.1, 0.012, 0, this.doorRed, -sx * (dw / 2 - 0.01), 0, 0.026, 'cab-door-edge-light', leaf);
      this.doorLeaves.push(leaf);
    }
    // Driver's seat: pedestal and slide rails, contoured cushion, a bolstered back with a lighter
    // insert, a separate headrest on two rods, and armrests.
    const seatZ = 2.02;
    const seat = this.holder(v(0, CAB_FLOOR, seatZ), new THREE.Euler());
    this.box(0.4, 0.03, 0.46, 0.01, this.aluminium, 0, 0.08, 0, 'seat-slide-rails', seat);
    this.box(0.12, 0.34, 0.12, 0.03, this.aluminium, 0, 0.27, 0, 'seat-pedestal', seat);
    this.box(0.54, 0.1, 0.5, 0.045, this.upholstery, 0, 0.48, -0.02, 'seat-cushion', seat);
    this.box(0.36, 0.02, 0.4, 0.01, this.seatInsert, 0, 0.535, -0.03, 'seat-cushion-insert', seat);
    for (const sx of [-1, 1]) this.box(0.08, 0.08, 0.46, 0.035, this.upholstery, sx * 0.25, 0.54, -0.02, 'seat-cushion-bolster', seat);
    const backrest = this.holder(v(0, 0.56, 0.24), new THREE.Euler(-0.14, 0, 0), seat);
    this.box(0.46, 0.66, 0.1, 0.045, this.upholstery, 0, 0.33, 0, 'seat-back', backrest);
    this.box(0.3, 0.5, 0.02, 0.01, this.seatInsert, 0, 0.34, -0.052, 'seat-back-insert', backrest);
    for (const sx of [-1, 1]) this.box(0.08, 0.6, 0.14, 0.035, this.upholstery, sx * 0.25, 0.32, -0.02, 'seat-back-bolster', backrest);
    for (const sx of [-1, 1]) this.box(0.014, 0.08, 0.014, 0.005, this.aluminium, sx * 0.08, 0.7, 0.01, 'seat-headrest-rod', backrest);
    this.box(0.3, 0.16, 0.09, 0.04, this.upholstery, 0, 0.82, -0.005, 'seat-headrest', backrest);
    for (const sx of [-1, 1]) {
      this.box(0.06, 0.05, 0.36, 0.022, this.black, sx * 0.33, 0.72, 0.0, 'seat-armrest', seat);
      this.box(0.03, 0.18, 0.04, 0.01, this.black, sx * 0.33, 0.62, 0.14, 'seat-armrest-post', seat);
    }
  }

  /** Door opening 0…1 (full cab only). */
  setDoor(open: number): void {
    const o = clamp(open, 0, 1);
    for (const leaf of this.doorLeaves) leaf.position.x = (leaf.userData.side as number) * (CAB_DOOR.halfWidth / 2 + CAB_DOOR.halfWidth * 1.02 * o);
  }

  /** Instrument power: 'off', 'on', or the boot clock in ms since the driver sat down. */
  setPower(state: 'off' | 'on' | number): void {
    const t = state === 'off' ? -1 : state === 'on' ? Infinity : state;
    const backlight = t < 0 ? 0 : bootProgress(t, BOOT_ACCENTS.start, BOOT_ACCENTS.length);
    for (const m of Object.values(this.caps)) m.emissiveIntensity = 0.06 + 0.5 * backlight;
    this.screens.forEach((m, i) => {
      m.uniforms.uPower.value = t < 0 ? 0 : bootProgress(t, BOOT_SCREENS.start + i * BOOT_SCREENS.step, BOOT_SCREENS.length);
    });
  }

  dispose(): void {
    for (const g of this.geometries) g.dispose();
    for (const g of this.shared.values()) g.dispose();
    for (const m of this.instanced) m.dispose();
    this.instanced = [];
    this.geometries = [];
    this.shared.clear();
    for (const m of [...this.lit, this.lamp, this.doorRed, ...this.screens]) m.dispose();
    this.group.clear();
  }
}
