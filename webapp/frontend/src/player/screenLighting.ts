import * as THREE from 'three';

/** GPU-only area-light approximation shared by wall, enclosure and foreground metal.
 * Positions are evaluated in display space, so independent parallax never detaches the light. */
export class ScreenLighting {
  readonly uniforms: Record<string, THREE.IUniform>;

  constructor(emission: THREE.Texture) {
    this.uniforms = {
      uScreenEmission: { value: emission },
      uScreenInverse: { value: new THREE.Matrix4() },
      uScreenHalfSize: { value: new THREE.Vector2(1, 1) },
    };
  }

  apply(material: THREE.MeshStandardMaterial, strength: number): void {
    material.onBeforeCompile = shader => {
      Object.assign(shader.uniforms, this.uniforms);
      shader.vertexShader = `varying vec3 vScreenWorldPosition;\n${shader.vertexShader}`.replace(
        '#include <project_vertex>',
        `#include <project_vertex>
        vec4 screenWorldPosition = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          screenWorldPosition = instanceMatrix * screenWorldPosition;
        #endif
        vScreenWorldPosition = (modelMatrix * screenWorldPosition).xyz;`,
      );
      shader.fragmentShader = `
        uniform sampler2D uScreenEmission;
        uniform mat4 uScreenInverse;
        uniform vec2 uScreenHalfSize;
        varying vec3 vScreenWorldPosition;
        ${shader.fragmentShader}
      `.replace('#include <opaque_fragment>', `
        vec3 screenPoint = (uScreenInverse * vec4(vScreenWorldPosition, 1.0)).xyz;
        vec2 screenUv = screenPoint.xy / (uScreenHalfSize * 2.0) + .5;
        vec2 outsideScreen = max(abs(screenPoint.xy) - uScreenHalfSize, vec2(0.0));
        float screenDistance = length(vec3(outsideScreen, screenPoint.z - .175));
        vec3 screenRadiance = vec3(0.0);
        for (int sy = 0; sy < 2; sy++) {
          for (int sx = 0; sx < 2; sx++) {
            screenRadiance += texture2D(uScreenEmission, vec2(.28 + float(sx) * .44, .28 + float(sy) * .44)).rgb * .25;
          }
        }
        vec3 edgeRadiance = texture2D(uScreenEmission, clamp(screenUv, .08, .92)).rgb;
        screenRadiance = mix(screenRadiance, edgeRadiance, .35);
        float screenFalloff = 1.0 / (1.0 + screenDistance * screenDistance * 1.8);
        // Broad LCD output: nearby surfaces receive the image's actual hue and energy.
        outgoingLight += screenRadiance * screenFalloff * ${strength.toFixed(3)} * (diffuseColor.rgb * .65 + .35);
        #include <opaque_fragment>
      `);
    };
    material.customProgramCacheKey = () => `screen-area-light-${strength}`;
  }

  update(displayMatrix: THREE.Matrix4, width: number, height: number): void {
    this.uniforms.uScreenInverse.value.copy(displayMatrix).invert();
    this.uniforms.uScreenHalfSize.value.set(width / 2, height / 2);
  }
}
