// A close view of a metro saloon wall: formed laminate, joints, a door reveal,
// stainless trim/grab rail. Ceiling illumination remains outside this close wall crop.
// Materials and installation details are modeled geometry, not a background photograph.
import * as THREE from 'three';
import { roundedRect } from './screenGeometry';
import type { ScreenLighting } from './screenLighting';

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
  texture.repeat.set(1.5, .75);
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}

/** Small, deterministic woven moquette tile, following the gray/taupe reference benches. */
function seatWeave(): THREE.DataTexture {
  const side = 128;
  const data = new Uint8Array(side * side * 4);
  for (let y = 0; y < side; y++) for (let x = 0; x < side; x++) {
    const weave = ((x + y) % 3 === 0 ? 13 : 0) - (x % 2 === 0 ? 7 : 0);
    const stitch = (x + y * 3) % 31 < 2;
    const i = (y * side + x) * 4;
    data.set(stitch ? [137, 116, 98, 255] : [156 + weave, 151 + weave, 143 + weave, 255], i);
  }
  const texture = new THREE.DataTexture(data, side, side);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(4, 3);
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}

export interface WallOpening { width: number; height: number; radius: number; centerY: number }

export class TrainInterior {
  readonly group = new THREE.Group();
  readonly railings = new THREE.Group();
  private readonly grain = materialGrain();
  private readonly weave = seatWeave();
  private readonly laminate = new THREE.MeshStandardMaterial({ color: 0xc9cdca, roughness: 0.64, metalness: 0.025, bumpMap: this.grain, bumpScale: 0.00012 });
  private readonly ceiling = new THREE.MeshStandardMaterial({ color: 0xe0e0d7, roughness: 0.48, metalness: 0.04 });
  private readonly steel = new THREE.MeshStandardMaterial({ color: 0xb3b6b3, roughness: 0.28, metalness: 0.83, roughnessMap: this.grain });
  private readonly copper = new THREE.MeshStandardMaterial({ color: 0xbe9176, roughness: 0.23, metalness: 0.86 });
  private readonly upholstery = new THREE.MeshStandardMaterial({ color: 0xd7d3cc, map: this.weave, bumpMap: this.weave, bumpScale: .008, roughness: .94 });
  private readonly piping = new THREE.MeshStandardMaterial({ color: 0x746e65, roughness: .97 });
  private readonly seatShell = new THREE.MeshStandardMaterial({ color: 0xbebeb5, roughness: .42, metalness: .18 });
  private readonly floor = new THREE.MeshStandardMaterial({ color: 0x777d78, roughness: .89, bumpMap: this.grain, bumpScale: .002 });
  private readonly doorLight = new THREE.MeshBasicMaterial({ color: 0xe82a45 });
  private readonly shadow = new THREE.MeshStandardMaterial({ color: 0x151a1c, roughness: 0.95 });
  private readonly rubber = new THREE.MeshStandardMaterial({ color: 0x282d2e, roughness: 0.92 });
  private readonly window = new THREE.MeshPhysicalMaterial({ color: 0x26332f, roughness: 0.32, metalness: 0.18, clearcoat: .75, clearcoatRoughness: .2 });
  private readonly socketLight = new THREE.MeshBasicMaterial({ color: 0xc3b5ff });
  private readonly reflection = new THREE.MeshBasicMaterial({ color: 0xaabec8, transparent: true, opacity: .13, depthWrite: false });
  private readonly doorWash = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader: 'varying vec2 vUv; void main(){float a=exp(-pow((vUv.x-.5)*5.0,2.0))*.20;gl_FragColor=vec4(1.0,.025,.09,a);}',
    transparent: true, depthWrite: false,
  });
  private readonly joint = new THREE.MeshStandardMaterial({ color: 0x767d7c, roughness: 0.84 });
  private geometries: THREE.BufferGeometry[] = [];

  constructor(lighting?: ScreenLighting) {
    this.group.name = 'train-wall-installation';
    this.railings.name = 'train-railings-layer';
    for (const m of [this.laminate, this.ceiling, this.steel, this.rubber, this.window, this.joint, this.upholstery, this.seatShell, this.floor]) lighting?.apply(m, .6);
    lighting?.apply(this.copper, 1.1);
  }

  private mesh(geometry: THREE.BufferGeometry, material: THREE.Material, x: number, y: number, z: number, name: string): THREE.Mesh {
    this.geometries.push(geometry);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, y, z);
    mesh.name = name;
    mesh.receiveShadow = true;
    mesh.castShadow = true;
    this.group.add(mesh);
    return mesh;
  }

  private box(w: number, h: number, d: number, material: THREE.Material, x: number, y: number, z: number, name: string): THREE.Mesh {
    return this.mesh(new THREE.BoxGeometry(w, h, d), material, x, y, z, name);
  }

  private panel(w: number, h: number, radius: number, depth: number, material: THREE.Material, x: number, y: number, z: number, name: string): THREE.Mesh {
    return this.mesh(new THREE.ExtrudeGeometry(roundedRect(w, h, Math.min(radius, w / 2 - .001, h / 2 - .001)), {
      depth, bevelEnabled: true, bevelSize: .018, bevelThickness: .012, bevelSegments: 2, curveSegments: 8,
    }), material, x, y, z, name);
  }

  private tube(points: THREE.Vector3[], radius: number, material: THREE.Material, name: string): THREE.Mesh {
    return this.mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 32, radius, 12, false), material, 0, 0, 0, name);
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

    // Recessed seams and formed edge panels follow the Moskva-2020 touchscreen bay.
    for (const x of [-ow / 2 - 0.34, ow / 2 + 0.16]) {
      this.box(0.018, h, 0.02, this.shadow, x, 0, -0.445, 'vertical-laminate-panel-joint');
      this.box(0.028, h, 0.018, this.ceiling, x + 0.025, 0, -0.43, 'panel-joint-highlight');
    }

    // Real door/window reveal and stainless grab rail remain visible at the crop's right edge.
    const doorX = width / 2 - .22;
    this.panel(.70, h, .10, .16, this.steel, doorX, 0, -.40, 'metro-door-aluminium-stile');
    this.panel(.50, h - .16, .14, .06, this.rubber, doorX + .08, 0, -.21, 'door-window-rubber-seal');
    this.panel(.40, h - .24, .12, .025, this.window, doorX + .09, 0, -.12, 'dark-door-window');
    this.box(.016, h, .012, this.ceiling, doorX - .20, 0, -.09, 'door-stile-machined-highlight');
    this.box(.045, h, .025, this.rubber, doorX - .30, 0, -.16, 'door-status-diffuser-channel');
    this.box(.025, h - .06, .018, this.doorLight, doorX - .30, 0, -.12, 'moskva-2020-door-edge-light');
    this.mesh(new THREE.PlaneGeometry(.25, h - .06), this.doorWash, doorX - .30, 0, -.083, 'red-door-diffuser-spill');
    for (const y of [-height * .31, height * .26]) {
      const streak = this.box(.32, .055, .008, this.reflection, doorX + .09, y, -.07, 'door-glass-ceiling-reflection');
      streak.rotation.z = -.16;
    }
    // Black enamel faces, a recessed glazing lip and a brushed sill give the fixed
    // doorway the same layered construction as the supplied 81-775 photographs.
    this.box(.026, h - .20, .018, this.shadow, doorX - .155, 0, -.065, 'black-enamel-door-glazing-lip');
    this.box(.34, .035, .025, this.steel, doorX + .09, -height / 2 + .20, -.07, 'door-bottom-glazing-bead');
    // Recessed door pillar, visible captive screws and emergency-release rosette.
    const pillarX = ow / 2 + .28;
    const pillarW = Math.max(.14, doorX - .40 - pillarX);
    const fittingX = pillarX + pillarW / 2;
    this.panel(pillarW, h - .45, .08, .045, this.ceiling, pillarX + pillarW / 2, 0, -.43, 'formed-door-pillar');
    if (pillarW > .22) {
      const releaseY = Math.min(height / 2 - 1.35, centerY + oh / 2 - .45);
      this.panel(.21, .30, .035, .015, this.steel, pillarX + pillarW / 2, releaseY, -.35, 'emergency-release-recess');
      const knob = this.mesh(new THREE.CylinderGeometry(.065, .065, .03, 20), this.rubber, pillarX + pillarW / 2, releaseY, -.30, 'emergency-release-rosette');
      knob.rotation.x = Math.PI / 2;
      const handle = this.box(.025, .09, .025, this.doorLight, pillarX + pillarW / 2, releaseY, -.27, 'emergency-release-handle');
      handle.rotation.z = -.35;
    }
    // The reference touchscreen bay has paired illuminated charging sockets.
    // Fit these only where the wall has enough physical room; never squeeze into the glass.
    const socketX = fittingX;
    if (pillarW >= .28) {
      this.panel(.23, .65, .045, .018, this.ceiling, socketX, centerY - .10, -.36, 'charging-socket-service-plate');
      for (const y of [centerY + .035, centerY - .235]) {
        this.panel(.12, .13, .025, .012, this.socketLight, socketX, y, -.325, 'charging-socket-backlight');
        this.panel(.087, .097, .018, .012, this.rubber, socketX, y, -.295, 'charging-socket-surround');
        this.box(.047, .018, .012, this.steel, socketX, y, -.265, 'charging-usb-port');
      }
    }
    const railX = -width / 2 + 0.50;
    const path = [
      new THREE.Vector3(railX, -h / 2, 1.8),
      new THREE.Vector3(railX, height * .05, 1.8),
      new THREE.Vector3(railX + .10, height * .30, 1.8),
      new THREE.Vector3(railX + .37, height * .43, 1.76),
      new THREE.Vector3(railX + .40, h / 2, 1.72),
    ];
    const rail = this.tube(path, .092, this.copper, 'stainless-grab-rail');
    rail.castShadow = rail.receiveShadow = false;
    this.railings.add(rail);
    // Collars follow the actual curved centerline rather than floating beside it.
    const railCurve = new THREE.CatmullRomCurve3(path);
    for (const t of [.16, .69]) {
      const point = railCurve.getPointAt(t);
      const collar = this.mesh(new THREE.CylinderGeometry(.105, .105, .055, 16), this.steel, point.x, point.y, point.z, 'foreground-post-collar');
      collar.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), railCurve.getTangentAt(t));
      collar.castShadow = collar.receiveShadow = false;
      this.railings.add(collar);
    }

    // The close wall crop does not include the roof: illumination comes from the
    // off-camera ceiling lights, without invented horizontal rails across the door.
    const wallRight = doorX - .40;
    const panelWidth = wallRight + w / 2;
    const panelCenter = (wallRight - w / 2) / 2;
    const bottom = -height / 2 + 0.11;
    this.box(panelWidth, 0.09, 0.17, this.steel, panelCenter, bottom, -0.29, 'brushed-aluminium-wall-dado');
    this.box(panelWidth, 0.018, 0.04, this.shadow, panelCenter, bottom + 0.06, -0.21, 'dado-contact-joint');

    // Horizontal service-panel joint stays below the display instead of cutting through it.
    const serviceY = Math.min(-height / 2 + .65, centerY - oh / 2 - .23);
    this.box(panelWidth, .022, .018, this.shadow, panelCenter, serviceY, -.444, 'lower-service-panel-joint');
    this.box(panelWidth, .018, .015, this.ceiling, panelCenter, serviceY - .025, -.43, 'service-panel-beveled-edge');

    // Cantilevered, individually upholstered bench seats below the locked display.
    // Their top follows the housing clearance, never the active image or the rail path.
    const benchLeft = -ow / 2 + .10;
    const benchRight = Math.min(ow / 2 - .12, wallRight - .12);
    const benchWidth = benchRight - benchLeft;
    const benchTop = opening ? centerY - oh / 2 - .20 : -height * .13;
    const seatCount = Math.max(2, Math.min(6, Math.round(benchWidth / 2.2)));
    const seatWidth = benchWidth / seatCount;
    const backHeight = Math.min(.88, Math.max(.48, height * .13));
    const seatY = benchTop - backHeight - .12;
    const benchCenter = (benchLeft + benchRight) / 2;
    this.box(panelWidth, Math.max(1, height), .05, this.floor, panelCenter, seatY - height / 2 - .34, -.38, 'speckled-saloon-floor');
    this.panel(benchWidth + .10, backHeight + .08, .16, .08, this.seatShell, benchCenter, benchTop - backHeight / 2, -.25, 'cantilever-bench-shell');
    this.box(benchWidth - .24, .11, .38, this.shadow, benchCenter, seatY - .12, -.07, 'bench-recessed-underframe');
    for (let i = 0; i < seatCount; i++) {
      const x = benchLeft + seatWidth * (i + .5);
      this.panel(seatWidth - .045, backHeight, .13, .09, this.piping, x, benchTop - backHeight / 2, -.14, 'bench-backrest-piping');
      const back = this.panel(seatWidth - .080, backHeight - .035, .12, .14, this.upholstery, x, benchTop - backHeight / 2, -.11, 'woven-individual-seat-back');
      back.rotation.x = -.055;
      const cushion = this.panel(seatWidth - .055, .68, .16, .18, this.upholstery, x, seatY, .02, 'contoured-seat-cushion');
      cushion.rotation.x = -Math.PI * .36;
      this.panel(seatWidth - .015, .18, .075, .12, this.seatShell, x, seatY - .15, .14, 'rounded-seat-front-shell');
    }
    // Armrests belong to the new bench, behind the original near-field rail layer.
    for (const x of [benchLeft - .06, benchRight + .06]) {
      this.tube([
        new THREE.Vector3(x, seatY - .20, -.22),
        new THREE.Vector3(x, seatY + .19, .29),
        new THREE.Vector3(x, seatY + .45, .32),
        new THREE.Vector3(x, seatY + .55, -.22),
      ], .035, this.copper, 'bench-bronze-end-armrest');
    }
    for (const x of opening ? [-ow / 2 - 0.12, ow / 2 + 0.12] : []) {
      for (const y of [centerY - oh / 2 + 0.16, centerY + oh / 2 - 0.16]) {
        this.mesh(new THREE.CylinderGeometry(0.024, 0.024, 0.018, 12), this.steel, x, y, -0.44, 'flush-mounting-fastener').rotation.x = Math.PI / 2;
      }
    }
  }

  dispose(): void {
    for (const g of this.geometries) g.dispose();
    for (const m of [this.laminate, this.ceiling, this.steel, this.copper, this.doorLight, this.shadow, this.rubber, this.window, this.socketLight, this.reflection, this.doorWash, this.joint, this.upholstery, this.piping, this.seatShell, this.floor]) m.dispose();
    this.grain.dispose();
    this.weave.dispose();
    this.group.clear();
    this.railings.clear();
  }
}
