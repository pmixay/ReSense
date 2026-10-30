// The boarding animation into the Player: you stand in the saloon looking out through the open side
// doors (the page you are leaving), turn right, walk the aisle to the cab, the cab door slides
// open, you step in and sit down; the last frame is exactly the Player's seated view with its
// instruments still dark (the Player then boots them). The page you leave is a CSS3D plane driven
// by the same camera, so the first frame is pixel-identical to the page and it swings away in
// true perspective. Coordinates are the cab's (cockpit.ts): metres, the seated eye at (0, 0, CAB_EYE).
import * as THREE from 'three';
import { CSS3DObject, CSS3DRenderer } from 'three/examples/jsm/renderers/CSS3DRenderer.js';
import { CabCockpit, CAB_BULKHEAD, CAB_EYE, CAB_FLOOR, CAB_FOV, cabLayout, encodePbr, srgb, type CabRegion } from './cockpit';
import { cabEnvironment, cabLights } from './screenDisplay';
import { CAB_VERTEX, GLASS_FRAGMENT } from './cabShaders';

/** The whole walk, from the first turn to settling in the seat (ms). */
export const ENTRY_MS = 3400;
export const SALOON = { halfWidth: 1.5, ceiling: 1.75, cove: 1.6, end: CAB_BULKHEAD + 8.6 };
/** Standing eye height over the seated eye (m). */
export const STAND = 0.45;
/** Where you stand at the portal (the page is the portal, `START.x + halfWidth` metres away). */
export const START = { x: 0.42, z: CAB_BULKHEAD + 4.8 };
/** The cab door slides open over this window (ms). */
export const DOOR = { start: 1650, length: 520 };

export interface EntryLayout {
  /** the overlay (the whole browser viewport), CSS px */
  viewport: { width: number; height: number };
  /** the Player's 3D canvas inside the viewport, CSS px */
  canvas: { left: number; top: number; width: number; height: number };
  /** the Player's display region relative to its canvas */
  region: CabRegion;
  pixelRatio: number;
}

export interface CameraPose { x: number; y: number; z: number; yaw: number; pitch: number; roll: number }

interface Key { t: number; x: number; y: number; z: number; yaw: number; pitch: number }
const KEYS: Key[] = [
  { t: 0, x: START.x, y: STAND, z: START.z, yaw: Math.PI / 2, pitch: 0 },
  { t: 720, x: START.x - 0.04, y: STAND, z: START.z - 0.42, yaw: 0.03, pitch: -0.02 },
  { t: 1950, x: 0.06, y: STAND, z: CAB_BULKHEAD + 0.9, yaw: 0, pitch: -0.03 },
  { t: 2380, x: 0.0, y: STAND - 0.01, z: CAB_BULKHEAD + 0.1, yaw: 0, pitch: -0.05 },
  { t: 2820, x: 0.46, y: STAND - 0.05, z: CAB_EYE + 0.28, yaw: 0.24, pitch: -0.15 },
  { t: 3250, x: 0, y: 0, z: CAB_EYE, yaw: 0, pitch: 0 },
];
const CHANNELS = ['x', 'y', 'z', 'yaw', 'pitch'] as const;
const smooth = (a: number, b: number, t: number) => THREE.MathUtils.smoothstep(t, a, b);

/** Time-keyed cubic Hermite with Catmull-Rom tangents; at rest at both ends. */
function channel(name: (typeof CHANNELS)[number], t: number): number {
  const last = KEYS.length - 1;
  if (t <= KEYS[0].t) return KEYS[0][name];
  if (t >= KEYS[last].t) return KEYS[last][name];
  let i = 0;
  while (KEYS[i + 1].t < t) i++;
  const a = KEYS[i];
  const b = KEYS[i + 1];
  const tangent = (k: number) => (k <= 0 || k >= last ? 0 : (KEYS[k + 1][name] - KEYS[k - 1][name]) / (KEYS[k + 1].t - KEYS[k - 1].t));
  const h = b.t - a.t;
  const u = (t - a.t) / h;
  const u2 = u * u;
  const u3 = u2 * u;
  return (2 * u3 - 3 * u2 + 1) * a[name] + (u3 - 2 * u2 + u) * h * tangent(i) + (-2 * u3 + 3 * u2) * b[name] + (u3 - u2) * h * tangent(i + 1);
}

/** The eye along the boarding path at `t` ms: turn, walk (with a step bob), enter, sit, settle. */
export function entryPose(t: number): CameraPose {
  const time = Math.min(ENTRY_MS, Math.max(0, t));
  const pose: CameraPose = { x: channel('x', time), y: channel('y', time), z: channel('z', time), yaw: channel('yaw', time), pitch: channel('pitch', time), roll: 0 };
  // walking: about three steps a second, a centimetre of bob and a hint of sway
  const walk = smooth(380, 700, time) * (1 - smooth(2150, 2450, time));
  const phase = ((time - 380) / 1000) * Math.PI * 2.9;
  pose.y -= walk * 0.012 * (0.5 - 0.5 * Math.cos(phase * 2));
  pose.roll = walk * 0.006 * Math.sin(phase);
  // sitting down: the head dips forward, then a small landing bounce in the seat
  const sit = THREE.MathUtils.clamp((time - 2820) / 430, 0, 1);
  // (bumps are exactly zero at their ends, so the last pose is the seated view to the bit)
  if (sit > 0 && sit < 1) pose.pitch -= 0.06 * Math.sin(Math.PI * sit);
  const land = THREE.MathUtils.clamp((time - KEYS[KEYS.length - 1].t) / (ENTRY_MS - KEYS[KEYS.length - 1].t), 0, 1);
  if (land > 0 && land < 1) pose.y -= 0.012 * Math.sin(Math.PI * land);
  return pose;
}

/** The saloon (Moskva-2020 cues): off-white panels, black glazing surrounds, taupe benches, bronze
 * poles, broad ceiling LEDs and the open side doors (the portal you leave by, red edge lights). */
class Saloon {
  readonly group = new THREE.Group();
  private geometries: THREE.BufferGeometry[] = [];
  private readonly wall = new THREE.MeshStandardMaterial({ color: srgb(0xd8dad6), roughness: 0.6, metalness: 0.03, side: THREE.DoubleSide });
  private readonly panel = new THREE.MeshStandardMaterial({ color: srgb(0xc4c8c6), roughness: 0.62, metalness: 0.03, side: THREE.DoubleSide });
  private readonly ceiling = new THREE.MeshStandardMaterial({ color: srgb(0xeceeeb), roughness: 0.55, metalness: 0.02, side: THREE.DoubleSide });
  private readonly surround = new THREE.MeshStandardMaterial({ color: srgb(0x111417), roughness: 0.5, metalness: 0.2, side: THREE.DoubleSide });
  private readonly floor = new THREE.MeshStandardMaterial({ color: srgb(0x70766f), roughness: 0.88, metalness: 0.02, side: THREE.DoubleSide });
  private readonly seat = new THREE.MeshStandardMaterial({ color: srgb(0x9a948b), roughness: 0.94, metalness: 0.0 });
  private readonly piping = new THREE.MeshStandardMaterial({ color: srgb(0x6f695f), roughness: 0.95, metalness: 0.0 });
  private readonly shell = new THREE.MeshStandardMaterial({ color: srgb(0xbebeb5), roughness: 0.42, metalness: 0.18 });
  private readonly bronze = new THREE.MeshStandardMaterial({ color: srgb(0xbe9176), roughness: 0.23, metalness: 0.86 });
  private readonly aluminium = new THREE.MeshStandardMaterial({ color: srgb(0xb3b8b6), roughness: 0.3, metalness: 0.83 });
  private readonly window = new THREE.MeshStandardMaterial({ color: srgb(0x0a0e12), roughness: 0.12, metalness: 0.6, side: THREE.DoubleSide });
  private readonly lamp = new THREE.MeshBasicMaterial({ color: 0xf3f7ff, toneMapped: false, side: THREE.DoubleSide });
  private readonly cove = new THREE.MeshBasicMaterial({ color: 0xf0d9b8, toneMapped: false, side: THREE.DoubleSide });
  private readonly red = new THREE.MeshBasicMaterial({ color: 0xe82a45, toneMapped: false, side: THREE.DoubleSide });

  constructor() {
    this.group.name = 'saloon';
    for (const m of [this.wall, this.panel, this.ceiling, this.surround, this.floor, this.seat, this.piping, this.shell, this.bronze, this.aluminium, this.window]) encodePbr(m);
    // The brightly lit saloon: a soft bounce term on its own surfaces only (the cab keeps the
    // Player's exact lighting, so the walk ends on the Player's pixels).
    for (const [m, k] of [[this.wall, 0.36], [this.panel, 0.32], [this.ceiling, 0.62], [this.floor, 0.14], [this.seat, 0.16], [this.piping, 0.1], [this.shell, 0.2]] as const) {
      m.emissive.copy(m.color);
      m.emissiveIntensity = k;
    }
  }

  private mesh(geometry: THREE.BufferGeometry, material: THREE.Material, name: string): THREE.Mesh {
    this.geometries.push(geometry);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = name;
    this.group.add(mesh);
    return mesh;
  }

  private box(w: number, h: number, d: number, material: THREE.Material, x: number, y: number, z: number, name: string): THREE.Mesh {
    const mesh = this.mesh(new THREE.BoxGeometry(w, h, d), material, name);
    mesh.position.set(x, y, z);
    return mesh;
  }

  private quad(a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3, d: THREE.Vector3, material: THREE.Material, name: string): void {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute([...a.toArray(), ...b.toArray(), ...c.toArray(), ...d.toArray()], 3));
    geometry.setIndex([0, 1, 2, 0, 2, 3]);
    geometry.computeVertexNormals();
    this.mesh(geometry, material, name);
  }

  /** A rectangle in a side wall (x = ±halfWidth ∓ inset). */
  private side(sx: number, z0: number, z1: number, y0: number, y1: number, material: THREE.Material, name: string, inset = 0): void {
    const x = sx * (SALOON.halfWidth - inset);
    this.quad(new THREE.Vector3(x, y0, z0), new THREE.Vector3(x, y0, z1), new THREE.Vector3(x, y1, z1), new THREE.Vector3(x, y1, z0), material, name);
  }

  private tube(points: THREE.Vector3[], radius: number, material: THREE.Material, name: string): void {
    this.mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 32, radius, 12, false), material, name);
  }

  build(portal: { z: number; y: number; width: number; height: number }): void {
    for (const g of this.geometries) g.dispose();
    this.geometries = [];
    this.group.clear();
    const v = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
    const W = SALOON.halfWidth;
    const z0 = CAB_BULKHEAD + 0.12;
    const z1 = SALOON.end;
    this.quad(v(-W, CAB_FLOOR, z0), v(W, CAB_FLOOR, z0), v(W, CAB_FLOOR, z1), v(-W, CAB_FLOOR, z1), this.floor, 'saloon-floor');
    const cw = W - 0.34;
    this.quad(v(-cw, SALOON.ceiling, z0), v(cw, SALOON.ceiling, z0), v(cw, SALOON.ceiling, z1), v(-cw, SALOON.ceiling, z1), this.ceiling, 'saloon-ceiling');
    // two broad LED strips with a ventilation grille between them
    for (const x of [-0.55, 0.55]) this.quad(v(x - 0.09, SALOON.ceiling - 0.004, z0 + 0.1), v(x + 0.09, SALOON.ceiling - 0.004, z0 + 0.1), v(x + 0.09, SALOON.ceiling - 0.004, z1 - 0.1), v(x - 0.09, SALOON.ceiling - 0.004, z1 - 0.1), this.lamp, 'saloon-ceiling-led');
    for (let z = z0 + 0.6; z < z1 - 0.4; z += 0.9) this.quad(v(-0.18, SALOON.ceiling - 0.003, z), v(0.18, SALOON.ceiling - 0.003, z), v(0.18, SALOON.ceiling - 0.003, z + 0.5), v(-0.18, SALOON.ceiling - 0.003, z + 0.5), this.panel, 'saloon-ceiling-grille');
    for (const sx of [-1, 1]) {
      // roof cove between wall and ceiling, washed by a warm hidden strip
      this.quad(v(sx * W, SALOON.cove, z0), v(sx * cw, SALOON.ceiling, z0), v(sx * cw, SALOON.ceiling, z1), v(sx * W, SALOON.cove, z1), this.ceiling, 'saloon-roof-cove');
      this.quad(v(sx * (cw + 0.01), SALOON.ceiling - 0.006, z0), v(sx * (cw + 0.05), SALOON.ceiling - 0.03, z0), v(sx * (cw + 0.05), SALOON.ceiling - 0.03, z1), v(sx * (cw + 0.01), SALOON.ceiling - 0.006, z1), this.cove, 'saloon-warm-cove-light');
      // overhead grab rail on brackets
      this.tube([v(sx * 0.82, 1.4, z0 + 0.3), v(sx * 0.82, 1.4, z1 - 0.3)], 0.017, this.bronze, 'saloon-overhead-rail');
      for (let z = z0 + 0.8; z < z1 - 0.3; z += 1.8) this.box(0.02, 0.35, 0.02, this.bronze, sx * 0.82, 1.57, z, 'saloon-rail-bracket');
    }
    // Side walls: the left one opens at the portal, which is exactly the plane of the page you leave.
    const pz0 = portal.z - portal.width / 2;
    const pz1 = portal.z + portal.width / 2;
    const py0 = Math.max(CAB_FLOOR, portal.y - portal.height / 2);
    const py1 = Math.min(SALOON.cove, portal.y + portal.height / 2);
    for (const sx of [-1, 1]) {
      const runs: Array<[number, number]> = sx < 0 ? [[z0, pz0], [pz1, z1]] : [[z0, z1]];
      for (const [a, b] of runs) {
        if (b - a < 0.01) continue;
        this.side(sx, a, b, CAB_FLOOR, -0.1, this.wall, 'saloon-lower-wall');
        this.side(sx, a, b, 0.92, SALOON.cove, this.wall, 'saloon-upper-wall');
        // black glazing surrounds framing individual windows
        this.side(sx, a, b, -0.1, 0.92, this.surround, 'saloon-glazing-surround', 0.004);
        for (let z = a + 0.12; z + 0.5 < b - 0.12; z += 1.4) this.side(sx, z, Math.min(z + 1.24, b - 0.12), -0.02, 0.84, this.window, 'saloon-window', 0.008);
        this.side(sx, a, b, CAB_FLOOR + 0.12, CAB_FLOOR + 0.16, this.aluminium, 'saloon-kick-rail', 0.01);
        // line map strip above the windows: the metro-red line with its stations
        if (b - a > 1) {
          this.side(sx, a + 0.2, b - 0.2, 1.06, 1.2, this.surround, 'saloon-line-map', 0.006);
          this.side(sx, a + 0.3, b - 0.3, 1.122, 1.138, this.red, 'saloon-line-map-route', 0.008);
          for (let z = a + 0.35; z < b - 0.3; z += 0.28) this.side(sx, z - 0.012, z + 0.012, 1.118, 1.142, this.lamp, 'saloon-line-map-station', 0.009);
        }
      }
      if (sx < 0) {
        this.side(sx, pz0, pz1, CAB_FLOOR, py0, this.wall, 'portal-sill-wall');
        this.side(sx, pz0, pz1, py1, SALOON.cove, this.wall, 'portal-head-wall');
        // open doors: aluminium stiles with the red edge lights, just outside the page's edges
        for (const [za, zb] of [[pz0 - 0.08, pz0], [pz1, pz1 + 0.08]]) this.side(sx, za, zb, py0 - 0.02, py1 + 0.04, this.aluminium, 'portal-door-stile', 0.012);
        for (const z of [pz0 - 0.05, pz1 + 0.035]) this.side(sx, z, z + 0.015, py0, py1, this.red, 'portal-door-edge-light', 0.03);
        this.side(sx, pz0 - 0.08, pz1 + 0.08, py1, py1 + 0.06, this.surround, 'portal-header', 0.014);
        this.side(sx, portal.z - 0.35, portal.z + 0.35, Math.min(SALOON.cove - 0.12, py1 + 0.08), Math.min(SALOON.cove - 0.02, py1 + 0.18), this.surround, 'portal-info-display', 0.016);
      }
    }
    // Cantilevered benches with individual taupe seats, clear of the portal and the cab bulkhead.
    const benches: Array<[number, number, number]> = [
      [-1, z0 + 0.5, pz0 - 0.4], [-1, pz1 + 0.4, z1 - 0.3], [1, z0 + 0.5, z1 - 0.3],
    ];
    for (const [sx, a, b] of benches) {
      if (b - a < 0.6) continue;
      const len = b - a;
      const zc = (a + b) / 2;
      this.box(0.08, 0.66, len + 0.06, this.shell, sx * (W - 0.05), -0.42, zc, 'bench-back-shell');
      this.box(0.48, 0.07, len + 0.04, this.shell, sx * (W - 0.28), -0.86, zc, 'bench-seat-shell');
      const seats = Math.max(1, Math.round(len / 0.5));
      const sw = len / seats;
      for (let i = 0; i < seats; i++) {
        const z = a + sw * (i + 0.5);
        this.box(0.07, 0.56, sw - 0.03, this.piping, sx * (W - 0.11), -0.4, z, 'bench-seat-back-piping');
        this.box(0.08, 0.52, sw - 0.06, this.seat, sx * (W - 0.12), -0.4, z, 'bench-seat-back');
        this.box(0.44, 0.09, sw - 0.04, this.seat, sx * (W - 0.29), -0.78, z, 'bench-seat-cushion');
      }
      for (const z of [a - 0.04, b + 0.04]) this.tube([v(sx * (W - 0.02), -0.95, z), v(sx * (W - 0.46), -0.95, z), v(sx * (W - 0.5), -0.55, z), v(sx * (W - 0.02), -0.5, z)], 0.02, this.bronze, 'bench-end-armrest');
    }
    // Curved bronze poles by the benches, never between the start position and the portal.
    for (const [sx, z] of [[1, z0 + 1.3], [-1, z0 + 1.3], [1, z1 - 1.2], [-1, z1 - 1.2]] as const) {
      this.tube([v(sx * 0.9, CAB_FLOOR, z), v(sx * 0.9, 0.6, z), v(sx * 0.84, 1.2, z), v(sx * 0.82, 1.4, z)], 0.02, this.bronze, 'saloon-pole');
    }
    // the far end of the car: inter-car gangway
    this.quad(v(-W, CAB_FLOOR, z1), v(W, CAB_FLOOR, z1), v(W, SALOON.ceiling, z1), v(-W, SALOON.ceiling, z1), this.wall, 'saloon-end-wall');
    this.box(1.1, 2.0, 0.02, this.surround, 0, CAB_FLOOR + 1.0, z1 - 0.012, 'saloon-gangway');
    this.box(0.36, 0.05, 0.01, this.red, 0, CAB_FLOOR + 2.12, z1 - 0.02, 'saloon-gangway-sign');
  }

  dispose(): void {
    for (const g of this.geometries) g.dispose();
    for (const m of [this.wall, this.panel, this.ceiling, this.surround, this.floor, this.seat, this.piping, this.shell, this.bronze, this.aluminium, this.window, this.lamp, this.cove, this.red]) m.dispose();
    this.group.clear();
  }
}

export class CabEntryScene {
  readonly camera = new THREE.PerspectiveCamera(CAB_FOV, 1, 0.04, 60);
  /** CSS3DRenderer does not follow view offsets whose aspect differs from the camera's: the page
   * plane uses a symmetric camera with the same focal length, centred on the Player canvas. */
  private readonly cssCamera = new THREE.PerspectiveCamera(CAB_FOV, 1, 0.04, 60);
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly cssScene = new THREE.Scene();
  private readonly css = new CSS3DRenderer();
  private readonly page: CSS3DObject;
  private readonly cockpit = new CabCockpit({ full: true });
  private readonly saloon = new Saloon();
  private readonly windshield = new THREE.Group();
  private readonly glass = new THREE.ShaderMaterial({ vertexShader: CAB_VERTEX, fragmentShader: GLASS_FRAGMENT, toneMapped: false, uniforms: { uPower: { value: 0 }, uSize: { value: new THREE.Vector2(1, 1) }, uBand: { value: 0.03 } } });
  private readonly standby = new THREE.MeshBasicMaterial({ color: 0x010204, toneMapped: false });
  private geometries: THREE.BufferGeometry[] = [];
  private environment: THREE.WebGLRenderTarget | null = null;
  private key = '';

  constructor(canvas: HTMLCanvasElement, cssHost: HTMLElement, page: HTMLElement) {
    const gl = canvas.getContext('webgl2', { alpha: false, antialias: true, depth: true, stencil: false, powerPreference: 'high-performance' });
    if (!gl) throw new Error('WebGL 2 недоступен');
    this.renderer = new THREE.WebGLRenderer({ canvas, context: gl, antialias: true, powerPreference: 'high-performance' });
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.renderer.setClearColor(0x07090d, 1);
    this.cockpit.setPower('off');
    this.scene.add(this.cockpit.group, this.saloon.group, this.windshield, ...cabLights());
    const saloonLight = new THREE.DirectionalLight(0xf2f7ff, 0.55);
    saloonLight.name = 'saloon-roof-light';
    saloonLight.position.set(-0.6, 4, 7);
    this.scene.add(saloonLight);
    cssHost.append(this.css.domElement);
    this.css.domElement.style.position = 'absolute';
    this.page = new CSS3DObject(page);
    this.page.name = 'leaving-page';
    this.cssScene.add(this.page);
  }

  /** Fit the overlay and rebuild the cab when the Player's measured layout changes. */
  setLayout(entry: EntryLayout): void {
    const { viewport, canvas, region } = entry;
    const key = JSON.stringify([viewport, canvas, region, entry.pixelRatio]);
    if (key === this.key) return;
    this.key = key;
    this.renderer.setPixelRatio(entry.pixelRatio);
    this.renderer.setSize(viewport.width, viewport.height, false);
    const cx = canvas.left + canvas.width / 2;
    const cy = canvas.top + canvas.height / 2;
    const cssWidth = 2 * Math.max(cx, viewport.width - cx);
    const cssHeight = 2 * Math.max(cy, viewport.height - cy);
    this.css.setSize(cssWidth, cssHeight);
    this.css.domElement.style.left = `${cx - cssWidth / 2}px`;
    this.css.domElement.style.top = `${cy - cssHeight / 2}px`;
    const focal = canvas.height / 2 / Math.tan(THREE.MathUtils.degToRad(CAB_FOV / 2));
    this.cssCamera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(cssHeight / 2 / focal));
    this.cssCamera.aspect = cssWidth / cssHeight;
    this.cssCamera.updateProjectionMatrix();
    // The Player's camera, widened so the overlay also covers the pinned chrome above its canvas.
    this.camera.fov = CAB_FOV;
    this.camera.aspect = canvas.width / Math.max(1, canvas.height);
    this.camera.setViewOffset(canvas.width, canvas.height, -canvas.left, -canvas.top, viewport.width, viewport.height);
    this.camera.updateProjectionMatrix();
    const layout = cabLayout(canvas.width, canvas.height, region);
    this.cockpit.build(layout);
    this.cockpit.setPower('off');
    for (const g of this.geometries) g.dispose();
    this.geometries = [];
    this.windshield.clear();
    const G = layout.glass;
    const A = layout.faceWorld;
    const glass = new THREE.PlaneGeometry(G.x1 - G.x0 + 0.02, G.y1 - G.y0 + 0.02);
    const face = new THREE.PlaneGeometry(A.x1 - A.x0, A.y1 - A.y0);
    this.geometries.push(glass, face);
    this.glass.uniforms.uSize.value.set(G.x1 - G.x0 + 0.02, G.y1 - G.y0 + 0.02);
    this.glass.uniforms.uBand.value = G.x1 - A.x1 + 0.01;
    const backing = new THREE.Mesh(glass, this.glass);
    backing.position.set((G.x0 + G.x1) / 2, (G.y0 + G.y1) / 2, -0.004);
    const dark = new THREE.Mesh(face, this.standby);
    dark.name = 'windshield-display-standby';
    dark.position.set((A.x0 + A.x1) / 2, (A.y0 + A.y1) / 2, 0);
    this.windshield.add(backing, dark);
    // The leaving page exactly fills the first frame, standing in the portal of the left wall.
    this.pose(0);
    const d = START.x + SALOON.halfWidth;
    const p = this.camera.projectionMatrix.clone().invert();
    const corner = (nx: number, ny: number) => {
      const v = new THREE.Vector3(nx, ny, -1).applyMatrix4(p);
      return v.multiplyScalar(d / -v.z);
    };
    const tl = corner(-1, 1);
    const br = corner(1, -1);
    const centre = tl.clone().add(br).multiplyScalar(0.5).applyMatrix4(this.camera.matrixWorld);
    const width = br.x - tl.x;
    const height = tl.y - br.y;
    this.page.element.style.width = `${viewport.width}px`;
    this.page.element.style.height = `${viewport.height}px`;
    this.page.position.copy(centre);
    this.page.rotation.set(0, Math.PI / 2, 0);
    this.page.scale.setScalar(width / viewport.width);
    this.saloon.build({ z: centre.z, y: centre.y, width, height });
  }

  private pose(t: number): void {
    const p = entryPose(t);
    this.camera.position.set(p.x, p.y, p.z);
    this.camera.rotation.set(p.pitch, p.yaw, p.roll, 'YXZ');
    this.camera.updateMatrixWorld(true);
  }

  /** Draw the walk at `t` ms. */
  frame(t: number): void {
    if (!this.environment) {
      this.environment = cabEnvironment(this.renderer);
      this.scene.environment = this.environment.texture;
      this.scene.environmentIntensity = 0.9;
    }
    this.pose(t);
    this.cockpit.setDoor((t - DOOR.start) / DOOR.length < 0 ? 0 : THREE.MathUtils.smootherstep(t, DOOR.start, DOOR.start + DOOR.length));
    // the page plane is only drawn while any of it can be in front of the eye
    this.page.visible = t < 1400;
    this.renderer.render(this.scene, this.camera);
    this.cssCamera.position.copy(this.camera.position);
    this.cssCamera.quaternion.copy(this.camera.quaternion);
    this.cssCamera.updateMatrixWorld(true);
    this.css.render(this.cssScene, this.cssCamera);
  }

  /** Compile every program before the clock starts, so the first step does not stall. */
  warm(): void {
    this.renderer.compile(this.scene, this.camera);
  }

  dispose(): void {
    for (const g of this.geometries) g.dispose();
    this.glass.dispose();
    this.standby.dispose();
    this.cockpit.dispose();
    this.saloon.dispose();
    this.environment?.dispose();
    this.scene.clear();
    this.cssScene.remove(this.page);
    this.css.domElement.remove();
    const lost = this.renderer.getContext().isContextLost();
    this.renderer.dispose();
    if (!lost) this.renderer.forceContextLoss();
  }
}
