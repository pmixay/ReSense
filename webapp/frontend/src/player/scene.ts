// The player's three.js scene (one WebGLRenderer per view): the stored point cloud as one
// preallocated BufferGeometry coloured on the GPU, the clearance envelope swept along the track
// model of the current frame, detections as red boxes and warnings as amber ones, a simple train
// for the outside cameras, the cab / top / chase camera presets with free orbit, and the «крупно»
// close-up rendered into a render target and drawn as a rounded inset.
//
// The owner drives it: setCloud / setFrame on a new frame (10 Hz × speed), setDrive every
// animation frame (the "live drive" glide), render(dt). Nothing is allocated per render; the HUD
// reads the screen positions of labels from `overlay` after each render (onOverlay).
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { DecodedCloud } from '../api/cloud';
import type { DetectionDict, FrameResultDict } from '../api/types';
import { ENVELOPE_PROFILE, centerY, defaultTrackModel, floorZ, railZ, type TrackModelDict, type Vec3 } from '../lib/track';
import {
  NO_OBSTACLE,
  TICK_LABELS,
  allocVertices,
  cameraPose,
  closeUpPose,
  envelopeSpan,
  fillPortal,
  fillTrackLines,
  fillTrackMesh,
  portalCapacity,
  trackLineCapacity,
  trackMeshCapacity,
  trackMeshIndex,
  type CamMode,
  type CamPose,
  type EnvelopeSpan,
  type VertexBuffers,
} from './geometry';
import { FLAT_FRAG, FLAT_VERT, INSET_FRAG, INSET_VERT, POINTS_FRAG, POINTS_VERT, TRACK_FRAG, TRACK_VERT } from './shaders';

// Colours are display values end to end (the inset render target must match the screen).
THREE.ColorManagement.enabled = false;

const srgbToLinear = (c: number): number => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
/** A hex colour as display values. */
const hex = (h: number): THREE.Vector3 => new THREE.Vector3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);
/** A hex colour darkened like the mockup's point colours (linearised, shown as is). */
const deep = (h: number): THREE.Vector3 => {
  const v = hex(h);
  return v.set(srgbToLinear(v.x), srgbToLinear(v.y), srgbToLinear(v.z));
};

const BG = 0x04060c;
const PIP_BG = 0x05070c;
const FOG = hex(BG);
const RAMP = [0x2e7fa8, 0x2f8fd0, 0x4fb0e6, 0x8fd3f5, 0xcdeafc, 0xf3f8ff].map(deep);
const HOT_RAMP = [0xff3347, 0xff8a5c, 0xffe3a8, 0xffffff].map(deep);
const GREEN = hex(0x2bd46f);
const RED = hex(0xff2a3c);
const WHITE = hex(0xdfe6f2);
const RED_RGB: Vec3 = [1, 0.33, 0.4];

export const MAX_DETECTIONS = 8;
export const MAX_WARNINGS = 12;
const BOX_PAD = 0.18;
const STEM = 1.3;
const EDGE_TH = 0.028;
const EDGE_OFFSETS: readonly [number, number][] = [
  [0, 0],
  [EDGE_TH, 0],
  [-EDGE_TH, 0],
  [0, EDGE_TH],
  [0, -EDGE_TH],
];
/** Ruler marks of the close-up (m above the bed). */
export const RULER_MARKS: readonly number[] = [0, 0.5, 1, 1.5, 2];

const LAYER_MAIN = 1;
const LAYER_PIP = 2;
/** Renders after a change while paused: the camera follow and the fades settle in about a second. */
const SETTLE_FRAMES = 60;

export interface ScreenPoint {
  visible: boolean;
  x: number;
  y: number;
}

export interface SceneOverlay {
  width: number;
  height: number;
  /** stem tops of frame.detections (same order) */
  detections: ScreenPoint[];
  /** tops of frame.warnings (same order) */
  warnings: ScreenPoint[];
  /** screen box around the nearest detection */
  bracket: { visible: boolean; x0: number; y0: number; x1: number; y1: number };
  /** labels of TICK_LABELS on the bed */
  ticks: ScreenPoint[];
  /** «габарит» tag anchor */
  envTag: ScreenPoint;
  /** close-up: shown, what it frames, ruler marks (y in inset px, RULER_MARKS) */
  pip: { visible: boolean; kind: 'detection' | 'warning' | null; index: number; x: number; ys: number[] };
}

export interface PipRect {
  x: number;
  y: number;
  w: number;
  h: number;
  radius: number;
}

export interface PlayerSceneOptions {
  /** light single-frame view: smaller points, no train, no inset */
  preview?: boolean;
  /** orbit with the mouse */
  interactive?: boolean;
  /** called when the user takes / gives back the camera */
  onFreeChange?: (free: boolean) => void;
  /** called after every render with the screen positions of the HUD anchors */
  onOverlay?: (ov: SceneOverlay) => void;
  /** a view that renders on demand asks for a new frame (orbit damping, camera tweens) */
  onInvalidate?: () => void;
}

const sp = (): ScreenPoint => ({ visible: false, x: 0, y: 0 });

function flatMaterial(color: number, opacity: number, uniforms: { uFogD: { value: number } }, opts: { vertexColors?: boolean; depthWrite?: boolean } = {}): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    vertexShader: FLAT_VERT,
    fragmentShader: FLAT_FRAG,
    uniforms: { uColor: { value: hex(color) }, uOpacity: { value: opacity }, uFog: { value: FOG }, uFogD: uniforms.uFogD },
    transparent: opacity < 1,
    depthWrite: opts.depthWrite ?? opacity >= 1,
    vertexColors: opts.vertexColors ?? false,
  });
}

interface BoxSlot {
  fill: THREE.Mesh;
  edges: THREE.LineSegments[];
  cx: number;
  cy: number;
  cz: number;
  sx: number;
  sy: number;
  sz: number;
  on: boolean;
}

export class PlayerScene {
  readonly renderer: THREE.WebGLRenderer;
  readonly overlay: SceneOverlay;
  private readonly opts: PlayerSceneOptions;
  private readonly scene = new THREE.Scene();
  private readonly camera: THREE.PerspectiveCamera;
  private readonly pipCam: THREE.PerspectiveCamera;
  private readonly controls: OrbitControls | null = null;
  private readonly disposables: { dispose(): void }[] = [];

  // points
  private pointsGeo: THREE.BufferGeometry;
  private capacity = 0;
  private readonly points: THREE.Points;
  private readonly pipPoints: THREE.Points;
  private readonly pointsMat: THREE.ShaderMaterial;
  private readonly pipMat: THREE.ShaderMaterial;
  private pointSize: number;
  private minPx: number;

  // track (train-fixed)
  private readonly trainFixed = new THREE.Group();
  private readonly lineBuf: VertexBuffers;
  private readonly meshBuf: VertexBuffers;
  private readonly lineGeo = new THREE.BufferGeometry();
  private readonly meshGeo = new THREE.BufferGeometry();
  private readonly trackUniforms: Record<string, THREE.IUniform>;
  private readonly trainBody = new THREE.Group();
  private readonly grid = new THREE.Group();

  // world (glides back while driving)
  private readonly world = new THREE.Group();
  private readonly red: BoxSlot[] = [];
  private readonly amber: BoxSlot[] = [];
  private readonly stemGeo = new THREE.BufferGeometry();
  private readonly stemPos = new Float32Array(MAX_DETECTIONS * 2 * 3);
  private readonly portalBuf: VertexBuffers;
  private readonly portalGeo = new THREE.BufferGeometry();
  private readonly portal: THREE.LineSegments;

  // inset
  private readonly rt: THREE.WebGLRenderTarget;
  private readonly quadScene = new THREE.Scene();
  private readonly quadCam = new THREE.OrthographicCamera(0, 1, 1, 0, -1, 1);
  private readonly quad: THREE.Mesh;
  private pipRect: PipRect | null = null;
  private pip: { det: DetectionDict; kind: 'detection' | 'warning'; index: number; pose: ReturnType<typeof closeUpPose> } | null = null;

  // state
  private width = 1;
  private height = 1;
  private pixelRatio = 1;
  private track: TrackModelDict = defaultTrackModel();
  private span: EnvelopeSpan = { near: NO_OBSTACLE, far: NO_OBSTACLE, end: 200 };
  private frame: FrameResultDict | null = null;
  private mode: CamMode = 'cab';
  private free = false;
  private pose: CamPose;
  private readonly posePos = new THREE.Vector3();
  private readonly poseTarget = new THREE.Vector3();
  private readonly camPos = new THREE.Vector3();
  private readonly camTarget = new THREE.Vector3();
  private camFov = 24;
  private tween = { active: false, t: 0, fromPos: new THREE.Vector3(), fromTarget: new THREE.Vector3(), fromFov: 24 };
  private placed = false;
  private sWorld = 0;
  private sCloud = 0;
  private settle = SETTLE_FRAMES;
  private headX = 1;
  private headY = 0;
  private readonly tmp = new THREE.Vector3();
  private readonly tmp2 = new THREE.Vector3();
  private readonly corner: ScreenPoint = { visible: false, x: 0, y: 0 };
  private disposed = false;

  constructor(canvas: HTMLCanvasElement, opts: PlayerSceneOptions = {}) {
    this.opts = opts;
    this.pointSize = opts.preview ? 0.024 : 0.028;
    this.minPx = opts.preview ? 1.25 : 1.6;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.renderer.autoClear = false;

    this.camera = new THREE.PerspectiveCamera(24, 1, 0.5, 600);
    this.camera.up.set(0, 0, 1);
    this.camera.layers.set(0);
    this.camera.layers.enable(LAYER_MAIN);
    this.pipCam = new THREE.PerspectiveCamera(27, 1, 0.5, 120);
    this.pipCam.up.set(0, 0, 1);
    this.pipCam.layers.set(0);
    this.pipCam.layers.enable(LAYER_PIP);

    const fogD = { value: 0.0072 };
    this.pose = cameraPose('cab', this.track, 1);

    // ---- points
    const common = {
      uScale: { value: 1 },
      uMinPx: { value: 1.6 },
      uMaxPx: { value: 5 },
      uFogD: fogD,
      uNearDim: { value: 12 },
      uCeil: { value: 99 },
      uWallDim: { value: 0.5 },
      uHot: { value: 0 },
      uCrop: { value: new THREE.Vector4(0, -1, 0, 0) },
      uFloorC: { value: new THREE.Vector3(0, 0, -1.5) },
      uFloorR: { value: new THREE.Vector2(3, 120) },
      uAxis: { value: new THREE.Vector4(-0.1, 0, 0, 0.35) },
      uRamp: { value: RAMP },
      uBedLo: { value: deep(0x1f6f8f) },
      uBedHi: { value: deep(0xa6eef4) },
      uRail: { value: deep(0xe6f6ff) },
      uObj: { value: hex(0xff4a5c) },
      uWarn: { value: hex(0xffb300) },
      uCor: { value: deep(0xffe0e4) },
      uHotRamp: { value: HOT_RAMP },
      uFog: { value: FOG },
    };
    this.pointsMat = new THREE.ShaderMaterial({ vertexShader: POINTS_VERT, fragmentShader: POINTS_FRAG, uniforms: common, transparent: true, depthWrite: false });
    // the close-up shares the track uniforms but has its own scale / crop / fog / colouring
    this.pipMat = new THREE.ShaderMaterial({
      vertexShader: POINTS_VERT,
      fragmentShader: POINTS_FRAG,
      uniforms: {
        ...common,
        uScale: { value: 1 },
        uMinPx: { value: 2.4 },
        uMaxPx: { value: 6 },
        uFogD: { value: 0 },
        uNearDim: { value: 1.5 },
        uCeil: { value: 99 },
        uHot: { value: 1 },
        uCrop: { value: new THREE.Vector4(0, -1, 0, 0) },
      },
      transparent: true,
      depthWrite: false,
    });
    this.pointsGeo = this.makePointsGeometry(opts.preview ? 30000 : 36000);
    this.points = new THREE.Points(this.pointsGeo, this.pointsMat);
    this.points.frustumCulled = false;
    this.points.layers.set(LAYER_MAIN);
    this.points.renderOrder = 0;
    this.pipPoints = new THREE.Points(this.pointsGeo, this.pipMat);
    this.pipPoints.frustumCulled = false;
    this.pipPoints.layers.set(LAYER_PIP);
    this.scene.add(this.points, this.pipPoints);

    // ---- track lines + envelope surfaces (train-fixed)
    this.trackUniforms = {
      uSpan: { value: new THREE.Vector3(NO_OBSTACLE, NO_OBSTACLE, 200) },
      uGreen: { value: GREEN },
      uRed: { value: RED },
      uWhite: { value: WHITE },
      uFog: { value: FOG },
      uFogD: fogD,
      uGain: { value: 1 },
    };
    const trackMat = new THREE.ShaderMaterial({ vertexShader: TRACK_VERT, fragmentShader: TRACK_FRAG, uniforms: this.trackUniforms, transparent: true, depthWrite: false });
    const trackMeshMat = new THREE.ShaderMaterial({
      vertexShader: TRACK_VERT,
      fragmentShader: TRACK_FRAG,
      uniforms: this.trackUniforms,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    this.lineBuf = allocVertices(trackLineCapacity());
    this.meshBuf = allocVertices(trackMeshCapacity());
    this.initVertexGeometry(this.lineGeo, this.lineBuf);
    this.initVertexGeometry(this.meshGeo, this.meshBuf);
    this.meshGeo.setIndex(new THREE.BufferAttribute(trackMeshIndex(), 1));
    const lines = new THREE.LineSegments(this.lineGeo, trackMat);
    const mesh = new THREE.Mesh(this.meshGeo, trackMeshMat);
    for (const o of [lines, mesh]) {
      o.frustumCulled = false;
      o.layers.set(LAYER_MAIN);
    }
    mesh.renderOrder = 1;
    lines.renderOrder = 2;
    this.trainFixed.add(mesh, lines);
    if (!opts.preview) {
      this.buildTrain(fogD);
      this.buildGrid(trackMat);
    }
    this.scene.add(this.trainFixed);

    // ---- world: boxes, stems, the obstacle portal
    const unitBox = new THREE.BoxGeometry(1, 1, 1);
    const unitEdges = new THREE.EdgesGeometry(unitBox);
    const redFill = flatMaterial(0xff2a3c, opts.preview ? 0.22 : 0.25, { uFogD: fogD });
    const redEdge = flatMaterial(0xff5566, 1, { uFogD: fogD });
    const amberFill = flatMaterial(0xffb300, 0.16, { uFogD: fogD });
    const amberEdge = flatMaterial(0xffc940, 1, { uFogD: fogD });
    this.disposables.push(unitBox, unitEdges, redFill, redEdge, amberFill, amberEdge, trackMat, trackMeshMat, this.pointsMat, this.pipMat);
    for (let i = 0; i < MAX_DETECTIONS; i += 1) this.red.push(this.makeBox(unitBox, unitEdges, redFill, redEdge));
    for (let i = 0; i < MAX_WARNINGS; i += 1) this.amber.push(this.makeBox(unitBox, unitEdges, amberFill, amberEdge));
    this.stemGeo.setAttribute('position', new THREE.BufferAttribute(this.stemPos, 3).setUsage(THREE.DynamicDrawUsage));
    this.stemGeo.setDrawRange(0, 0);
    const stems = new THREE.LineSegments(this.stemGeo, redEdge);
    stems.frustumCulled = false;
    stems.layers.set(LAYER_MAIN);
    this.portalBuf = allocVertices(portalCapacity());
    this.initVertexGeometry(this.portalGeo, this.portalBuf);
    this.portal = new THREE.LineSegments(this.portalGeo, trackMat);
    this.portal.frustumCulled = false;
    this.portal.layers.set(LAYER_MAIN);
    this.portal.renderOrder = 3;
    this.world.add(stems, this.portal);
    this.scene.add(this.world);

    // ---- inset
    this.rt = new THREE.WebGLRenderTarget(16, 16, { depthBuffer: true, samples: 4 });
    const quadMat = new THREE.ShaderMaterial({
      vertexShader: INSET_VERT,
      fragmentShader: INSET_FRAG,
      uniforms: { uTex: { value: this.rt.texture }, uSize: { value: new THREE.Vector2(1, 1) }, uRadius: { value: 26 } },
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });
    const quadGeo = new THREE.PlaneGeometry(1, 1);
    this.quad = new THREE.Mesh(quadGeo, quadMat);
    this.quadScene.add(this.quad);
    this.disposables.push(quadMat, quadGeo, this.rt, this.lineGeo, this.meshGeo, this.stemGeo, this.portalGeo);

    this.overlay = {
      width: 1,
      height: 1,
      detections: Array.from({ length: MAX_DETECTIONS }, sp),
      warnings: Array.from({ length: MAX_WARNINGS }, sp),
      bracket: { visible: false, x0: 0, y0: 0, x1: 0, y1: 0 },
      ticks: TICK_LABELS.map(sp),
      envTag: sp(),
      pip: { visible: false, kind: null, index: -1, x: 22, ys: RULER_MARKS.map(() => 0) },
    };

    if (opts.interactive) {
      const c = new OrbitControls(this.camera, canvas);
      c.enableDamping = true;
      c.dampingFactor = 0.12;
      c.rotateSpeed = 0.6;
      c.zoomSpeed = 0.8;
      c.minDistance = 2;
      c.maxDistance = 400;
      // never under the track bed: the camera stays above the pivot's horizon
      c.maxPolarAngle = Math.PI / 2 - 0.03;
      c.addEventListener('start', this.onControlStart);
      c.addEventListener('change', this.onControlChange);
      canvas.addEventListener('dblclick', this.onDblClick);
      this.controls = c;
    }
    this.setTrack(this.track);
    // compile every program now (hidden boxes, the inset, the train included): the first obstacle
    // of a run must not stall the drive while its shaders compile
    this.renderer.compile(this.scene, this.camera);
    if (!opts.preview) {
      // programs are keyed by the render target too: the close-up's variants
      this.renderer.setRenderTarget(this.rt);
      this.renderer.compile(this.scene, this.pipCam);
      this.renderer.setRenderTarget(null);
      this.renderer.compile(this.quadScene, this.quadCam);
    }
  }

  // ---------------------------------------------------------------- public API

  /** CSS size of the canvas and the device pixel ratio to render at (≤ 2). */
  setSize(width: number, height: number, pixelRatio: number): void {
    this.width = Math.max(1, Math.round(width));
    this.height = Math.max(1, Math.round(height));
    this.pixelRatio = Math.min(2, Math.max(0.5, pixelRatio));
    this.renderer.setPixelRatio(this.pixelRatio);
    this.renderer.setSize(this.width, this.height, false);
    this.camera.aspect = this.width / this.height;
    this.camera.updateProjectionMatrix();
    this.quadCam.right = this.width;
    this.quadCam.top = this.height;
    this.quadCam.updateProjectionMatrix();
    this.overlay.width = this.width;
    this.overlay.height = this.height;
    this.updatePose();
    this.layoutPip();
    this.touch();
  }

  /** The inset's place in the canvas (CSS px), or null for none. */
  setPipRect(rect: PipRect | null): void {
    this.pipRect = rect;
    this.layoutPip();
    this.touch();
  }

  /** Preallocate the point buffers for the run's cloud budget (GET /clouds `points`). */
  reserve(points: number): void {
    if (Number.isFinite(points) && points > this.capacity) this.grow(Math.ceil(points * 1.05));
  }

  /** Upload a cloud (null = schematic mode: no points). `track` is the model of the cloud's frame. */
  setCloud(cloud: DecodedCloud | null, track?: TrackModelDict | null): void {
    this.touch();
    if (!cloud || cloud.n === 0) {
      this.pointsGeo.setDrawRange(0, 0);
      return;
    }
    const n = cloud.n;
    if (n > this.capacity) this.grow(Math.ceil(n * 1.2));
    const pos = this.pointsGeo.getAttribute('position') as THREE.BufferAttribute;
    const inten = this.pointsGeo.getAttribute('aInt') as THREE.BufferAttribute;
    const flags = this.pointsGeo.getAttribute('aFlag') as THREE.BufferAttribute;
    (pos.array as Float32Array).set(cloud.positions.subarray(0, n * 3));
    (inten.array as Uint8Array).set(cloud.intensity.subarray(0, n));
    (flags.array as Uint8Array).set(cloud.flags.subarray(0, n));
    for (const [a, k] of [
      [pos, 3],
      [inten, 1],
      [flags, 1],
    ] as const) {
      a.clearUpdateRanges();
      a.addUpdateRange(0, n * k);
      a.needsUpdate = true;
    }
    this.pointsGeo.setDrawRange(0, n);
    this.setPointTrack(track ?? this.track);
  }

  /** Colour the cloud on screen along the track model of its frame (it may arrive after the cloud). */
  setCloudTrack(track: TrackModelDict): void {
    this.setPointTrack(track);
    this.touch();
  }

  /** The frame under the playhead: envelope along its track, boxes, the obstacle, the close-up. */
  setFrame(frame: FrameResultDict | null): void {
    this.touch();
    this.frame = frame;
    const track = frame?.track ?? this.track;
    if (frame?.track) this.setTrack(track);
    const dets = frame?.detections ?? [];
    const warns = frame?.warnings ?? [];
    for (let i = 0; i < this.red.length; i += 1) this.placeBox(this.red[i], dets[i]);
    for (let i = 0; i < this.amber.length; i += 1) this.placeBox(this.amber[i], warns[i]);
    // stems above the detections
    let k = 0;
    for (let i = 0; i < Math.min(dets.length, MAX_DETECTIONS); i += 1) {
      const d = dets[i];
      const top = d.center[2] + d.size[2] / 2 + BOX_PAD / 2;
      this.stemPos.set([d.center[0], d.center[1], top, d.center[0], d.center[1], top + STEM], k * 6);
      k += 1;
    }
    const sa = this.stemGeo.getAttribute('position') as THREE.BufferAttribute;
    sa.needsUpdate = true;
    this.stemGeo.setDrawRange(0, k * 2);
    const nearest = dets[0] ?? null;
    // FAULT: the input is unusable, nothing ahead is verified — the envelope is drawn as unverified
    const unverified = !nearest && frame?.decision === 'FAULT';
    this.span = envelopeSpan(nearest, unverified ? 0 : frame?.clear_distance, track.axis_valid);
    if (nearest) {
      fillPortal(this.portalBuf, track, this.span.near, RED_RGB, ENVELOPE_PROFILE);
      this.uploadVertices(this.portalGeo, this.portalBuf);
    }
    this.portal.visible = !!nearest;
    // close-up subject: the nearest detection, else the nearest warning
    let w = -1;
    for (let i = 0; i < warns.length; i += 1) if (w < 0 || warns[i].distance < warns[w].distance) w = i;
    const subject = nearest ?? (w >= 0 ? warns[w] : null);
    this.pip = subject
      ? { det: subject, kind: nearest ? 'detection' : 'warning', index: nearest ? 0 : w, pose: closeUpPose(subject.center, subject.size, track) }
      : null;
    this.updatePose();
  }

  /** The drive: the world (boxes) and the cloud glide back along the track by these metres. */
  setDrive(sWorld: number, sCloud: number): void {
    if (sWorld === this.sWorld && sCloud === this.sCloud) return;
    this.touch();
    this.sWorld = sWorld;
    this.sCloud = sCloud;
    this.world.position.set(-sWorld * this.headX, -sWorld * this.headY, 0);
    this.points.position.set(-sCloud * this.headX, -sCloud * this.headY, 0);
    this.pipPoints.position.copy(this.points.position);
  }

  setMode(mode: CamMode, animate = true): void {
    const changed = mode !== this.mode || this.free;
    this.mode = mode;
    this.trainBody.visible = mode !== 'cab';
    this.grid.visible = mode === 'top';
    if (changed) this.startTween(animate);
    this.touch();
    if (this.free) {
      this.free = false;
      this.opts.onFreeChange?.(false);
    }
    this.updatePose();
  }

  /** Back to the preset after an orbit (double-click). */
  resetView(): void {
    if (!this.free) return;
    this.free = false;
    this.startTween(true);
    this.updatePose(); // the preset's fog / vault / walls again
    this.touch();
    this.opts.onFreeChange?.(false);
    this.opts.onInvalidate?.();
  }

  get isFree(): boolean {
    return this.free;
  }

  /** Is the camera still moving (a tween or orbit damping)? On-demand views keep rendering then. */
  get animating(): boolean {
    return this.tween.active || this.free || !this.placed;
  }

  /** Would a render draw something new (a change not yet settled, a moving camera)? */
  needsRender(): boolean {
    return this.settle > 0 || this.animating;
  }

  render(dt: number): void {
    if (this.disposed) return;
    if (this.settle > 0) this.settle -= 1;
    this.updateCamera(Math.min(0.1, Math.max(0, dt)));
    const pr = this.pixelRatio;
    const u = this.pointsMat.uniforms;
    u.uScale.value = ((this.height * pr) / (2 * Math.tan((this.camera.fov * Math.PI) / 360))) * this.pointSize;
    // an orbited camera looks from afar: far points would shrink to specks
    u.uMinPx.value = (this.free ? this.minPx * 1.4 : this.minPx) * pr;
    u.uMaxPx.value = 5 * pr;
    this.trackUniforms.uSpan.value.set(this.span.near - this.sWorld, this.span.far - this.sWorld, this.span.end);

    const r = this.renderer;
    r.setRenderTarget(null);
    r.setClearColor(BG, 1);
    r.clear();
    r.render(this.scene, this.camera);

    const pipOn = !!(this.pip && this.pipRect && !this.opts.preview);
    if (pipOn && this.pip && this.pipRect) {
      this.updatePipCamera();
      const pm = this.pipMat.uniforms;
      pm.uScale.value = ((this.pipRect.h * pr) / (2 * Math.tan((this.pipCam.fov * Math.PI) / 360))) * 0.04;
      pm.uMinPx.value = 2.4 * pr;
      pm.uMaxPx.value = 7 * pr;
      r.setRenderTarget(this.rt);
      r.setClearColor(PIP_BG, 1);
      r.clear();
      r.render(this.scene, this.pipCam);
      r.setRenderTarget(null);
      r.render(this.quadScene, this.quadCam);
    }
    this.computeOverlay(pipOn);
    this.opts.onOverlay?.(this.overlay);
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    if (this.controls) {
      this.controls.removeEventListener('start', this.onControlStart);
      this.controls.removeEventListener('change', this.onControlChange);
      this.controls.dispose();
    }
    this.renderer.domElement.removeEventListener('dblclick', this.onDblClick);
    this.pointsGeo.dispose();
    for (const d of this.disposables) d.dispose();
    this.scene.clear();
    this.quadScene.clear();
    this.renderer.dispose();
    this.renderer.forceContextLoss();
  }

  // ---------------------------------------------------------------- internals

  private onControlStart = (): void => {
    if (!this.free) {
      this.free = true;
      this.tween.active = false;
      // pivot on the obstacle (else 30 m ahead) along the current view ray: the view does not jump,
      // and dragging turns around what the jury wants to inspect instead of a point 60 m away
      const d = this.frame?.detections?.[0];
      const cam = this.camera;
      const dist = d ? Math.hypot(d.center[0] - cam.position.x, d.center[1] - cam.position.y, d.center[2] - cam.position.z) : 30;
      cam.getWorldDirection(this.tmp);
      this.controls?.target.copy(cam.position).addScaledVector(this.tmp, Math.min(120, Math.max(8, dist)));
      this.opts.onFreeChange?.(true);
    }
  };

  private onControlChange = (): void => {
    this.touch();
    this.opts.onInvalidate?.();
  };

  private touch(): void {
    this.settle = SETTLE_FRAMES;
  }

  private onDblClick = (): void => this.resetView();

  private makePointsGeometry(capacity: number): THREE.BufferGeometry {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(capacity * 3), 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aInt', new THREE.BufferAttribute(new Uint8Array(capacity), 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aFlag', new THREE.BufferAttribute(new Uint8Array(capacity), 1).setUsage(THREE.DynamicDrawUsage));
    g.setDrawRange(0, 0);
    this.capacity = capacity;
    return g;
  }

  /** A cloud larger than the buffers (a frame with many flagged points): new buffers, once. */
  private grow(capacity: number): void {
    const old = this.pointsGeo;
    const n = Math.min(old.drawRange.count, capacity);
    this.pointsGeo = this.makePointsGeometry(capacity);
    // the cloud on screen stays on screen
    if (n > 0 && Number.isFinite(n)) {
      for (const [name, k] of [
        ['position', 3],
        ['aInt', 1],
        ['aFlag', 1],
      ] as const) {
        const from = old.getAttribute(name) as THREE.BufferAttribute;
        const to = this.pointsGeo.getAttribute(name) as THREE.BufferAttribute;
        (to.array as Float32Array | Uint8Array).set((from.array as Float32Array | Uint8Array).subarray(0, n * k));
        to.needsUpdate = true;
      }
      this.pointsGeo.setDrawRange(0, n);
    }
    this.points.geometry = this.pointsGeo;
    this.pipPoints.geometry = this.pointsGeo;
    old.dispose();
    this.touch();
  }

  private initVertexGeometry(g: THREE.BufferGeometry, b: VertexBuffers): void {
    g.setAttribute('position', new THREE.BufferAttribute(b.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aCol', new THREE.BufferAttribute(b.col, 4).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aKind', new THREE.BufferAttribute(b.kind, 1).setUsage(THREE.DynamicDrawUsage));
    g.setDrawRange(0, 0);
  }

  private uploadVertices(g: THREE.BufferGeometry, b: VertexBuffers): void {
    for (const [name, k] of [
      ['position', 3],
      ['aCol', 4],
      ['aKind', 1],
    ] as const) {
      const a = g.getAttribute(name) as THREE.BufferAttribute;
      a.clearUpdateRanges();
      a.addUpdateRange(0, b.count * k);
      a.needsUpdate = true;
    }
    if (!g.index) g.setDrawRange(0, b.count);
  }

  private setTrack(t: TrackModelDict): void {
    this.track = t;
    fillTrackLines(this.lineBuf, t);
    this.uploadVertices(this.lineGeo, this.lineBuf);
    fillTrackMesh(this.meshBuf, t);
    this.uploadVertices(this.meshGeo, this.meshBuf);
    this.meshGeo.setDrawRange(0, (this.meshBuf.count / 4) * 6);
    const h = Math.atan(Math.tan(t.yaw ?? 0));
    this.headX = Math.cos(h);
    this.headY = Math.sin(h);
    this.placeTrain();
  }

  private setPointTrack(t: TrackModelDict): void {
    for (const m of [this.pointsMat, this.pipMat]) {
      const u = m.uniforms;
      const c = t.floor_coef ?? [0, 0, -1.5];
      const n = c.length;
      (u.uFloorC.value as THREE.Vector3).set(n >= 3 ? c[n - 3] : 0, n >= 2 ? c[n - 2] : 0, n >= 1 ? c[n - 1] : -1.5);
      (u.uFloorR.value as THREE.Vector2).set(t.floor_range?.[0] ?? 3, t.floor_range?.[1] ?? 120);
      (u.uAxis.value as THREE.Vector4).set(t.center ?? 0, Math.tan(t.yaw ?? 0), t.curvature ?? 0, t.rail_offset ?? 0.35);
    }
  }

  private makeBox(geo: THREE.BufferGeometry, edgeGeo: THREE.BufferGeometry, fillMat: THREE.Material, edgeMat: THREE.Material): BoxSlot {
    const fill = new THREE.Mesh(geo, fillMat);
    fill.visible = false;
    fill.renderOrder = 4;
    this.world.add(fill);
    const edges = EDGE_OFFSETS.map(() => {
      const e = new THREE.LineSegments(edgeGeo, edgeMat);
      e.visible = false;
      e.renderOrder = 5;
      this.world.add(e);
      return e;
    });
    return { fill, edges, cx: 0, cy: 0, cz: 0, sx: 0, sy: 0, sz: 0, on: false };
  }

  private placeBox(b: BoxSlot, d: DetectionDict | undefined): void {
    b.on = !!d && Array.isArray(d.center) && Array.isArray(d.size);
    b.fill.visible = b.on;
    for (const e of b.edges) e.visible = b.on;
    if (!d || !b.on) return;
    b.cx = d.center[0];
    b.cy = d.center[1];
    b.cz = d.center[2];
    b.sx = Math.max(0.05, d.size[0]) + BOX_PAD;
    b.sy = Math.max(0.05, d.size[1]) + BOX_PAD;
    b.sz = Math.max(0.05, d.size[2]) + BOX_PAD;
    b.fill.position.set(b.cx, b.cy, b.cz);
    b.fill.scale.set(b.sx, b.sy, b.sz);
    b.edges.forEach((e, i) => {
      const [oy, oz] = EDGE_OFFSETS[i];
      e.position.set(b.cx, b.cy + oy, b.cz + oz);
      e.scale.set(b.sx, b.sy, b.sz);
    });
  }

  /** A simple train nose for the outside cameras: body, windscreen, red stripe, headlights. */
  private buildTrain(fogD: { value: number }): void {
    const shaded = (w: number, d: number, h: number, color: number): THREE.Mesh => {
      const g = new THREE.BoxGeometry(w, d, h).toNonIndexed();
      const nrm = g.getAttribute('normal');
      const col = new Float32Array(nrm.count * 3);
      for (let i = 0; i < nrm.count; i += 1) {
        const s = 0.72 + 0.26 * nrm.getZ(i) + 0.1 * nrm.getX(i) - 0.04 * Math.abs(nrm.getY(i));
        col.set([s, s, s], i * 3);
      }
      g.setAttribute('color', new THREE.BufferAttribute(col, 3));
      const m = flatMaterial(color, 1, { uFogD: fogD }, { vertexColors: true, depthWrite: true });
      this.disposables.push(g, m);
      const mesh = new THREE.Mesh(g, m);
      mesh.layers.set(LAYER_MAIN);
      return mesh;
    };
    const part = (w: number, d: number, h: number, color: number, x: number, y: number, z: number): THREE.Mesh => {
      const m = shaded(w, d, h, color);
      m.position.set(x, y, z);
      this.trainBody.add(m);
      return m;
    };
    const L = 16;
    const xc = -0.8 - L / 2;
    part(L, 2.7, 3.1, 0xf2efea, xc, 0, 1.55); // body
    part(L - 1.2, 2.76, 0.95, 0x1c1f28, xc - 0.3, 0, 1.95); // side window band
    part(L - 0.2, 2.74, 0.2, 0xe4000d, xc, 0, 1.12); // brand stripe
    part(L - 4, 1.7, 0.3, 0xcfc8be, xc - 1, 0, 3.25); // roof equipment
    for (const y of [1.22, -1.22]) part(L - 0.6, 0.16, 0.05, 0xe4000d, xc + 0.1, y, 3.12); // brand lines along the roof
    part(0.08, 2.3, 1.2, 0x1c1f28, -0.78, 0, 2.2); // windscreen
    part(0.08, 2.72, 0.2, 0xe4000d, -0.78, 0, 1.12); // front band
    for (const y of [0.9, -0.9]) part(0.08, 0.36, 0.16, 0xfff4d6, -0.76, y, 0.72); // headlights
    this.trainBody.visible = false;
    this.trainFixed.add(this.trainBody);
  }

  /** A faint plan grid for the top view: across every 10 m (brighter every 50 m), along every 5 m. */
  private buildGrid(mat: THREE.Material): void {
    const xs: number[] = [];
    for (let x = 0; x <= 200; x += 10) xs.push(x);
    const ys = [-25, -20, -15, -10, -5, 5, 10, 15, 20, 25];
    const b = allocVertices((xs.length + ys.length) * 2);
    const put = (x: number, y: number, z: number, a: number) => {
      const i = b.count;
      b.pos.set([x, y, z], i * 3);
      b.col.set([1, 1, 1, a], i * 4);
      b.kind[i] = 2;
      b.count = i + 1;
    };
    const z = -1.4;
    for (const x of xs) {
      const a = x % 50 === 0 ? 0.13 : 0.06;
      put(x, -26, z, a);
      put(x, 26, z, a);
    }
    for (const y of ys) {
      put(-20, y, z, 0.05);
      put(200, y, z, 0.05);
    }
    const g = new THREE.BufferGeometry();
    this.initVertexGeometry(g, b);
    this.uploadVertices(g, b);
    const lines = new THREE.LineSegments(g, mat);
    lines.frustumCulled = false;
    lines.layers.set(LAYER_MAIN);
    lines.renderOrder = 1;
    this.grid.add(lines);
    this.grid.visible = false;
    this.disposables.push(g);
    this.trainFixed.add(this.grid);
  }

  private placeTrain(): void {
    // the body stands on the rails at the train (x ≈ 0)
    this.trainBody.position.set(0, centerY(this.track, 0), railZ(this.track, 0) + 0.3);
    this.grid.position.set(0, centerY(this.track, 0), railZ(this.track, 0) + 1.4);
  }

  private focusX(): number | null {
    const d = this.frame?.detections?.[0];
    return d ? d.center[0] : null;
  }

  /** Recompute the preset pose (on a new frame, mode or size — not per render). */
  private updatePose(): void {
    this.pose = cameraPose(this.mode, this.track, this.camera.aspect || 1, this.focusX());
    this.posePos.set(...this.pose.pos);
    this.poseTarget.set(...this.pose.target);
    const u = this.pointsMat.uniforms;
    u.uFogD.value = this.pose.fog;
    u.uNearDim.value = this.pose.nearDim;
    u.uCeil.value = this.pose.ceil;
    u.uWallDim.value = this.pose.wallDim;
    this.pipMat.uniforms.uCeil.value = 99;
    if (this.camera.near !== this.pose.near || this.camera.far !== this.pose.far) {
      this.camera.near = this.pose.near;
      this.camera.far = this.pose.far;
      this.camera.updateProjectionMatrix();
    }
  }

  private startTween(animate: boolean): void {
    if (!animate || !this.placed) {
      this.tween.active = false;
      this.placed = false;
      return;
    }
    this.tween.active = true;
    this.tween.t = 0;
    this.tween.fromPos.copy(this.camera.position);
    this.tween.fromTarget.copy(this.camTarget);
    this.tween.fromFov = this.camera.fov;
  }

  private updateCamera(dt: number): void {
    const cam = this.camera;
    if (this.free && this.controls) {
      this.controls.update();
      this.camTarget.copy(this.controls.target);
      // above the vault the tunnel roof would hide the track: drop it, as the top / chase presets do
      const above = cam.position.z - floorZ(this.track, cam.position.x) > 4;
      const u = this.pointsMat.uniforms;
      u.uCeil.value = above ? 3.6 : this.pose.ceil;
      u.uWallDim.value = 1;
      u.uFogD.value = Math.min(this.pose.fog, 0.004);
      return;
    }
    if (!this.placed) {
      this.camPos.copy(this.posePos);
      this.camTarget.copy(this.poseTarget);
      this.camFov = this.pose.fov;
      this.placed = true;
    } else if (this.tween.active) {
      this.tween.t = Math.min(1, this.tween.t + dt / 0.55);
      const t = this.tween.t;
      const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
      this.camPos.lerpVectors(this.tween.fromPos, this.posePos, e);
      this.camTarget.lerpVectors(this.tween.fromTarget, this.poseTarget, e);
      this.camFov = this.tween.fromFov + (this.pose.fov - this.tween.fromFov) * e;
      if (t >= 1) this.tween.active = false;
    } else {
      // follow the track model gently (it is re-estimated every frame)
      const k = 1 - Math.exp(-dt * 5);
      this.camPos.lerp(this.posePos, k);
      this.camTarget.lerp(this.poseTarget, k);
      this.camFov += (this.pose.fov - this.camFov) * k;
    }
    cam.position.copy(this.camPos);
    cam.lookAt(this.camTarget);
    if (Math.abs(cam.fov - this.camFov) > 1e-4) {
      cam.fov = this.camFov;
      cam.updateProjectionMatrix();
    }
    if (this.controls) this.controls.target.copy(this.camTarget);
  }

  private layoutPip(): void {
    const r = this.pipRect;
    if (!r) return;
    const pr = this.pixelRatio;
    this.rt.setSize(Math.max(1, Math.round(r.w * pr)), Math.max(1, Math.round(r.h * pr)));
    this.quad.scale.set(r.w, r.h, 1);
    this.quad.position.set(r.x + r.w / 2, this.height - (r.y + r.h / 2), 0);
    const u = (this.quad.material as THREE.ShaderMaterial).uniforms;
    (u.uSize.value as THREE.Vector2).set(r.w, r.h);
    u.uRadius.value = r.radius;
    this.pipCam.aspect = r.w / r.h;
    this.pipCam.updateProjectionMatrix();
  }

  private updatePipCamera(): void {
    if (!this.pip) return;
    const p = this.pip.pose;
    const ox = this.world.position.x;
    const oy = this.world.position.y;
    this.pipCam.position.set(p.pos[0] + ox, p.pos[1] + oy, p.pos[2]);
    this.tmp.set(p.target[0] + ox, p.target[1] + oy, p.target[2]);
    this.pipCam.lookAt(this.tmp);
    if (this.pipCam.fov !== p.fov) {
      this.pipCam.fov = p.fov;
      this.pipCam.updateProjectionMatrix();
    }
    (this.pipMat.uniforms.uCrop.value as THREE.Vector4).set(p.crop[0], p.crop[1], p.crop[2], p.crop[3]);
  }

  /** World point (in the world group's frame when `inWorld`) → CSS px of the canvas. */
  private toScreen(out: ScreenPoint, x: number, y: number, z: number, inWorld: boolean, margin = 40): ScreenPoint {
    const v = this.tmp2.set(x, y, z);
    if (inWorld) v.add(this.world.position);
    v.project(this.camera);
    out.x = ((v.x + 1) / 2) * this.width;
    out.y = ((1 - v.y) / 2) * this.height;
    out.visible = v.z > -1 && v.z < 1 && out.x > -margin && out.x < this.width + margin && out.y > -margin && out.y < this.height + margin;
    return out;
  }

  private computeOverlay(pipOn: boolean): void {
    const ov = this.overlay;
    const dets = this.frame?.detections ?? [];
    const warns = this.frame?.warnings ?? [];
    for (let i = 0; i < ov.detections.length; i += 1) {
      const d = dets[i];
      if (!d) {
        ov.detections[i].visible = false;
        continue;
      }
      this.toScreen(ov.detections[i], d.center[0], d.center[1], d.center[2] + d.size[2] / 2 + BOX_PAD / 2 + STEM, true);
    }
    for (let i = 0; i < ov.warnings.length; i += 1) {
      const d = warns[i];
      if (!d) {
        ov.warnings[i].visible = false;
        continue;
      }
      this.toScreen(ov.warnings[i], d.center[0], d.center[1], d.center[2] + d.size[2] / 2 + BOX_PAD / 2 + 0.25, true);
    }
    // brackets around the nearest detection box
    const b = ov.bracket;
    const box = this.red[0];
    b.visible = false;
    if (box.on) {
      let x0 = Infinity;
      let y0 = Infinity;
      let x1 = -Infinity;
      let y1 = -Infinity;
      let ok = true;
      const q = this.corner;
      for (let c = 0; c < 8; c += 1) {
        this.toScreen(q, box.cx + ((c & 1) - 0.5) * box.sx, box.cy + (((c >> 1) & 1) - 0.5) * box.sy, box.cz + (((c >> 2) & 1) - 0.5) * box.sz, true, 400);
        if (!q.visible) ok = false;
        x0 = Math.min(x0, q.x);
        y0 = Math.min(y0, q.y);
        x1 = Math.max(x1, q.x);
        y1 = Math.max(y1, q.y);
      }
      if (ok && x1 - x0 < this.width * 0.6) {
        b.visible = true;
        b.x0 = x0;
        b.y0 = y0;
        b.x1 = x1;
        b.y1 = y1;
      }
    }
    // distance ticks: greedy, a label too close to the previous one is hidden
    const t = this.track;
    let lx = -1e9;
    let ly = -1e9;
    for (let i = 0; i < TICK_LABELS.length; i += 1) {
      const m = TICK_LABELS[i];
      const p = this.toScreen(ov.ticks[i], m, centerY(t, m) + 1.75, railZ(t, m) + 0.02, false, 0);
      const beyond = m > this.span.end + 5;
      if (p.visible && !beyond && Math.hypot(p.x - lx, p.y - ly) > 30) {
        lx = p.x;
        ly = p.y;
      } else p.visible = false;
    }
    this.toScreen(ov.envTag, 13, centerY(t, 13) - 1.05, railZ(t, 13) + 0.12, false, 0);
    ov.envTag.visible = ov.envTag.visible && this.mode !== 'top' && !this.free;
    // the close-up ruler: heights above the bed at the object, in inset px
    const pip = ov.pip;
    pip.visible = pipOn;
    pip.kind = this.pip?.kind ?? null;
    pip.index = this.pip?.index ?? -1;
    if (pipOn && this.pip && this.pipRect) {
      const d = this.pip.det;
      const fz = floorZ(this.track, d.center[0]);
      for (let i = 0; i < RULER_MARKS.length; i += 1) {
        const v = this.tmp2.set(d.center[0] + this.world.position.x, d.center[1] + this.world.position.y, fz + RULER_MARKS[i]).project(this.pipCam);
        pip.ys[i] = ((1 - v.y) / 2) * this.pipRect.h;
      }
    }
  }
}
