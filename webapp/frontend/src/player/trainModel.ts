import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { brushedMetalTexture, createTrainEnvironment } from './trainMaterials';

/** A formed metro carriage for the outside cameras. Coordinates follow the track: X forward, Z up. */
export class TrainModel {
  readonly group = new THREE.Group();
  private readonly geometries = new Map<string, THREE.BufferGeometry>();
  private readonly brushed = brushedMetalTexture();
  private readonly environment: THREE.WebGLRenderTarget;
  private readonly paint = new THREE.MeshPhysicalMaterial({ color: 0xdce3e5, roughness: .3, metalness: .22, clearcoat: 1, clearcoatRoughness: .16 });
  private readonly graphite = new THREE.MeshPhysicalMaterial({ color: 0x101d29, roughness: .22, metalness: .45, clearcoat: 1, clearcoatRoughness: .1 });
  private readonly glazing = new THREE.MeshPhysicalMaterial({ color: 0x102b3a, roughness: .12, metalness: .52, clearcoat: 1, clearcoatRoughness: .07 });
  private readonly red = new THREE.MeshPhysicalMaterial({ color: 0xd7133b, roughness: .24, metalness: .3, clearcoat: 1, clearcoatRoughness: .15 });
  private readonly steel = new THREE.MeshPhysicalMaterial({ color: 0xa7b5c0, roughness: .38, metalness: .9, roughnessMap: this.brushed });
  private readonly rubber = new THREE.MeshStandardMaterial({ color: 0x111820, roughness: .87 });
  private readonly lamp = new THREE.MeshBasicMaterial({ color: 0xe8f5ff });
  private readonly marker = new THREE.MeshBasicMaterial({ color: 0xff3855 });

  constructor(renderer: THREE.WebGLRenderer, layer: number) {
    this.group.name = 'modern-metro-carriage';
    this.environment = createTrainEnvironment(renderer);
    for (const material of [this.paint, this.graphite, this.glazing, this.red, this.steel, this.rubber]) {
      material.envMap = this.environment.texture;
      material.envMapIntensity = .75;
      // The train shares a render target with display-valued LiDAR shaders. Bound and
      // encode only its PBR light, keeping the point cloud and decision colors exact.
      material.toneMapped = false;
      material.onBeforeCompile = shader => {
        shader.fragmentShader = shader.fragmentShader.replace('#include <opaque_fragment>',
          'outgoingLight = pow(outgoingLight / (vec3(1.0) + outgoingLight), vec3(1.0 / 2.2));\n#include <opaque_fragment>');
      };
      material.customProgramCacheKey = () => 'metro-pbr-display-v1';
    }
    const part = (w: number, d: number, h: number, radius: number, material: THREE.Material, x: number, y: number, z: number, name: string) => {
      const key = [w, d, h, radius].join(':');
      if (!this.geometries.has(key)) this.geometries.set(key, new RoundedBoxGeometry(w, d, h, 2, radius));
      const mesh = new THREE.Mesh(this.geometries.get(key)!, material);
      mesh.position.set(x, y, z);
      mesh.name = name;
      this.group.add(mesh);
      return mesh;
    };
    part(16, 2.7, 3.1, .22, this.paint, -8.8, 0, 1.65, 'formed-carriage-shell');
    part(15.8, 2.73, .28, .07, this.graphite, -8.8, 0, .35, 'graphite-underbody-skirt');
    part(15.7, 2.72, .16, .025, this.red, -8.8, 0, 1.12, 'metro-red-belt');
    part(15.7, 2.73, 1.1, .13, this.graphite, -8.85, 0, 2.15, 'continuous-glazing-surround');
    part(11.5, 1.7, .24, .1, this.steel, -9.6, 0, 3.25, 'roof-equipment-fairing');
    for (const y of [-1.19, 1.19]) part(15.5, .045, .045, .015, this.red, -8.8, y, 3.12, 'roof-edge-inlay');
    // A black wraparound cab mask, inset windshield, wipers and discrete LED light housings.
    part(.095, 2.46, 1.73, .16, this.graphite, -.775, 0, 2.05, 'rounded-cab-mask');
    part(.045, 2.18, 1.12, .14, this.glazing, -.71, 0, 2.24, 'laminated-cab-windscreen');
    part(.025, .028, 1.01, .008, this.graphite, -.68, 0, 2.24, 'windscreen-center-mullion');
    for (const y of [-.56, .56]) {
      const wiper = part(.025, .47, .025, .008, this.rubber, -.675, y, 1.84, 'windscreen-wiper');
      wiper.rotation.x = y < 0 ? -.12 : .12;
    }
    part(.12, 2.40, .24, .065, this.red, -.77, 0, 1.13, 'sculpted-red-front-apron');
    part(.12, 2.25, .27, .08, this.graphite, -.77, 0, .50, 'lower-front-valance');
    part(.3, .30, .15, .035, this.steel, -.62, 0, .38, 'recessed-automatic-coupler');
    for (const y of [-.93, .93]) {
      part(.09, .46, .22, .07, this.graphite, -.745, y, .85, 'headlight-recess');
      part(.035, .32, .065, .02, this.lamp, -.686, y, .88, 'led-running-light');
      part(.025, .12, .035, .012, this.marker, -.683, y, .78, 'red-marker-light');
    }
    for (const side of [-1, 1]) {
      for (const x of [-2.3, -6.7, -11.3]) {
        part(1.95, .035, .84, .1, this.glazing, x, side * 1.377, 2.15, 'individual-side-window');
      }
      for (const x of [-4.5, -9, -14]) {
        for (const offset of [-.32, .32]) {
          part(.62, .045, 2.45, .06, this.steel, x + offset, side * 1.387, 1.5, 'sliding-door-skin');
          part(.51, .025, 1.23, .08, this.graphite, x + offset, side * 1.42, 2.0, 'door-glazing-gasket');
          part(.43, .018, 1.12, .065, this.glazing, x + offset, side * 1.44, 2.0, 'door-safety-glass');
        }
        part(.022, .025, 2.43, .007, this.rubber, x, side * 1.42, 1.5, 'paired-door-center-seal');
        part(1.28, .08, .045, .012, this.steel, x, side * 1.4, .28, 'door-threshold');
      }
    }
    const wheel = new THREE.CylinderGeometry(.32, .32, .16, 20);
    this.geometries.set('wheel', wheel);
    for (const x of [-4, -13.1]) {
      part(2.15, 1.8, .30, .07, this.graphite, x, 0, .10, 'bogie-frame');
      for (const axle of [-.66, .66]) for (const side of [-1, 1]) {
        const mesh = new THREE.Mesh(wheel, this.steel);
        mesh.position.set(x + axle, side * 1.04, -.02);
        mesh.name = 'steel-wheel';
        this.group.add(mesh);
      }
    }
    const ambient = new THREE.HemisphereLight(0xdaeaff, 0x25303e, 1.3);
    ambient.position.set(0, 0, 1);
    const key = new THREE.DirectionalLight(0xf6f7ff, 2.0);
    key.position.set(6, -8, 15);
    this.group.add(ambient, key, key.target);
    this.group.traverse(object => object.layers.set(layer));
  }

  dispose(): void {
    for (const geometry of this.geometries.values()) geometry.dispose();
    for (const material of [this.paint, this.graphite, this.glazing, this.red, this.steel, this.rubber, this.lamp, this.marker]) material.dispose();
    this.brushed.dispose();
    this.environment.dispose();
    this.group.clear();
  }
}
