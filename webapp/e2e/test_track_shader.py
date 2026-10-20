"""Exercise the actual point shader on WebGL: rail coloring follows the piecewise axis."""
from pathlib import Path

import pytest


def test_piecewise_axis_rail_colors_on_gpu(browser):
    source = (Path(__file__).parents[1] / "frontend/src/player/shaders.ts").read_text()
    vertex = source.split("export const POINTS_VERT = /* glsl */ `", 1)[1].split("`;", 1)[0]
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    try:
        colors = page.evaluate("""source => {
            const gl = document.createElement('canvas').getContext('webgl2');
            if (!gl) throw new Error('WebGL2 is required');
            const compile = (type, text) => {
                const shader = gl.createShader(type);
                gl.shaderSource(shader, text); gl.compileShader(shader);
                if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS))
                    throw new Error(gl.getShaderInfoLog(shader));
                return shader;
            };
            const program = gl.createProgram();
            gl.attachShader(program, compile(gl.VERTEX_SHADER,
                '#version 300 es\\nprecision highp float;\\nin vec3 position;\\n' +
                'uniform mat4 modelViewMatrix; uniform mat4 projectionMatrix;\\n' +
                source.replaceAll('attribute ', 'in ').replaceAll('varying ', 'out ')));
            gl.attachShader(program, compile(gl.FRAGMENT_SHADER,
                '#version 300 es\\nprecision highp float; out vec4 color; void main(){color=vec4(1);}'));
            gl.transformFeedbackVaryings(program, ['vC'], gl.INTERLEAVED_ATTRIBS);
            gl.linkProgram(program);
            if (!gl.getProgramParameter(program, gl.LINK_STATUS))
                throw new Error(gl.getProgramInfoLog(program));
            gl.useProgram(program);
            const loc = name => gl.getUniformLocation(program, name);
            const identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
            for (const name of ['modelViewMatrix', 'projectionMatrix'])
                gl.uniformMatrix4fv(loc(name), false, identity);
            gl.uniform1f(loc('uCeil'), 99);
            gl.uniform1f(loc('uMinPx'), 1);
            gl.uniform1f(loc('uMaxPx'), 5);
            gl.uniform2f(loc('uFloorR'), 0, 200);
            gl.uniform3f(loc('uRail'), 1, 1, 1);
            // Give non-rail points a distinct color; only geometric rail classification is tested.
            gl.uniform3f(loc('uBedLo'), 0, 0, 1);
            gl.uniform3f(loc('uBedHi'), 0, 0, 1);
            const input = gl.createBuffer();
            gl.bindBuffer(gl.ARRAY_BUFFER, input);
            const position = gl.getAttribLocation(program, 'position');
            gl.enableVertexAttribArray(position);
            gl.vertexAttribPointer(position, 3, gl.FLOAT, false, 0, 0);
            const output = gl.createBuffer();
            gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, output);
            gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER, 12, gl.STREAM_READ);
            gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, output);
            gl.enable(gl.RASTERIZER_DISCARD);
            const sample = (step, x, y) => {
                gl.uniform2f(loc('uAxisStep'), step, 60);
                gl.bindBuffer(gl.ARRAY_BUFFER, input);
                gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([x, y, .2]), gl.STREAM_DRAW);
                gl.beginTransformFeedback(gl.POINTS);
                gl.drawArrays(gl.POINTS, 0, 1);
                gl.endTransformFeedback();
                const rgb = new Float32Array(3);
                gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER, 0, rgb);
                return Array.from(rgb);
            };
            // At 100 m a ±.001 step at 60 m displaces the axis by ±.8 m.
            const samples = [[0,100,.795], [-.001,20,.795], [-.001,60,.795],
                [-.001,100,-.005], [.001,100,1.595], [0,100,-.005], [0,100,1.595]];
            const result = samples.map(args => sample(...args));
            if (gl.getError() !== gl.NO_ERROR) throw new Error('WebGL feedback failed');
            gl.getExtension('WEBGL_lose_context')?.loseContext();
            return result;
        }""", vertex)
    finally:
        page.close()
    assert colors[0][0] > 0.5, colors  # a genuine rail point is bright, not a zero-output pass
    for color in colors[1:5]:
        assert color == pytest.approx(colors[0], abs=1e-5)
    for color in colors[5:]:
        assert color[0] < 0.1  # the displaced rail locations are bed under the legacy model
