import * as THREE from 'three';

/** Directional machining, shared by metal finishes rather than painted-on scratches. */
export function brushedMetalTexture(): THREE.DataTexture {
  const side = 128;
  const data = new Uint8Array(side * side * 4);
  let seed = 5729;
  for (let y = 0; y < side; y++) {
    seed = (Math.imul(seed, 1664525) + 1013904223) | 0;
    const line = 182 + ((seed >>> 24) & 31);
    for (let x = 0; x < side; x++) {
      const v = line + Math.round(Math.sin(x * .15 + y) * 3);
      data.set([v, v, v, 255], (y * side + x) * 4);
    }
  }
  const texture = new THREE.DataTexture(data, side, side);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(2, 6);
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}

/** A bounded HDR reflection probe: roof luminaires, dark glazing and warm saloon coves. */
export function createTrainEnvironment(renderer: THREE.WebGLRenderer): THREE.WebGLRenderTarget {
  const width = 256;
  const height = 128;
  const data = new Float32Array(width * height * 4);
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const v = y / height;
    const u = x / width;
    const roof = Math.exp(-Math.pow((v - .22) / .075, 4));
    const strip = Math.exp(-Math.pow((u - .18) / .018, 2)) + Math.exp(-Math.pow((u - .68) / .025, 2));
    const window = Math.exp(-Math.pow((v - .52) / .15, 8)) * (.5 + .5 * Math.cos(u * Math.PI * 8));
    const cove = Math.exp(-Math.pow((v - .43) / .025, 2));
    const base = (.065 + .13 * (1 - v)) * (1 - window * .8);
    const i = (y * width + x) * 4;
    data.set([base + roof * 1.55 + strip * 2.1 + cove * .65,
      base + roof * 1.64 + strip * 2.0 + cove * .42,
      base + roof * 1.75 + strip * 1.9 + cove * .24, 1], i);
  }
  const source = new THREE.DataTexture(data, width, height, THREE.RGBAFormat, THREE.FloatType);
  source.mapping = THREE.EquirectangularReflectionMapping;
  source.needsUpdate = true;
  const generator = new THREE.PMREMGenerator(renderer);
  const environment = generator.fromEquirectangular(source);
  source.dispose();
  generator.dispose();
  return environment;
}
