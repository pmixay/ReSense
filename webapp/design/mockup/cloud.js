// d2 «Линия» — three.js point-cloud scene shared by the player and the preview cards.
import * as THREE from 'three';

export async function loadFrame(url = '../shared/sample_frame.json'){
  const r = await fetch(url); return r.json();
}

// wall / ceiling ramp by height above the rail bed (teal → sky → white)
const RAMP = [[0.00, 0x2e7fa8], [0.18, 0x2f8fd0], [0.42, 0x4fb0e6], [0.66, 0x8fd3f5], [0.86, 0xcdeafc], [1.00, 0xf3f8ff]];
function ramp(t){
  t = Math.min(1, Math.max(0, t));
  for (let i = 1; i < RAMP.length; i++) if (t <= RAMP[i][0]){
    const [t0, c0] = RAMP[i - 1], [t1, c1] = RAMP[i]; const k = (t - t0) / (t1 - t0);
    return new THREE.Color(c0).lerp(new THREE.Color(c1), k);
  }
  return new THREE.Color(RAMP[RAMP.length - 1][1]);
}
const clamp01 = v => Math.min(1, Math.max(0, v));

export function createView(canvas, data, o = {}){
  const W = o.width || canvas.clientWidth, H = o.height || canvas.clientHeight;
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, preserveDrawingBuffer: true, alpha: false});
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  const bg = new THREE.Color(o.bg ?? 0x04060c);
  const scene = new THREE.Scene(); scene.background = bg;
  const res = data.result, tr = res.track, fc = tr.floor_coef, C = tr.center;
  const floorZ = x => fc[0] * x * x + fc[1] * x + fc[2];
  const railZ = x => floorZ(x) + 0.16;

  // ---- points (o.crop keeps a box around the obstacle for close-ups)
  const crop = o.crop, all = data.points;
  const pts = crop ? all.filter(p => p[0] >= crop.x[0] && p[0] <= crop.x[1] && Math.abs(p[1] - C) <= crop.dy) : all, n = pts.length;
  const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), siz = new Float32Array(n);
  const hot = new THREE.Color(0xffe0e4);
  const HOT = [new THREE.Color(0xff3347), new THREE.Color(0xff8a5c), new THREE.Color(0xffe3a8), new THREE.Color(0xffffff)];
  const hotRamp = t => { t = clamp01(t) * 3; const i = Math.min(2, Math.floor(t)); return HOT[i].clone().lerp(HOT[i + 1], t - i); };
  const bedLo = new THREE.Color(0x1f6f8f), bedHi = new THREE.Color(0xa6eef4), railC = new THREE.Color(0xe6f6ff);
  const wallDim = o.wallDim ?? 0.5;
  for (let i = 0; i < n; i++){
    const [x, y, z, I, inC] = pts[i];
    pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z;
    let c;
    const hf = z - floorZ(x), ki = clamp01((I - 6.5) / 6.5);
    if (inC){ c = o.hotRamp ? hotRamp((I - 46) / 27) : hot; siz[i] = 2.2; }
    else if (hf < 0.32 && Math.abs(y - C) < 2.3){
      // track bed: ballast and sleepers lit by intensity, rail heads brightest
      const onRail = hf > 0.06 && Math.abs(Math.abs(y - C) - 0.8) < 0.12;
      c = onRail ? railC.clone() : bedLo.clone().lerp(bedHi, 0.15 + 0.75 * ki);
      c.multiplyScalar(onRail ? 1.1 : 0.9 + 0.35 * ki); siz[i] = onRail ? 1.35 : 1.1;
    } else {
      c = ramp((hf - 0.3) / 4.6 * 0.95 + ki * 0.12);
      c.multiplyScalar(0.72 + 0.38 * ki); siz[i] = 1;
      // tunnel walls and vault recede: half brightness, smaller points, so the track and the envelope lead
      if (hf > 0.6){ c.multiplyScalar(wallDim); siz[i] = 0.8; }
    }
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aCol', new THREE.BufferAttribute(col, 3));
  g.setAttribute('aSize', new THREE.BufferAttribute(siz, 1));
  const fov = o.fov || 30;
  const pxScale = H / (2 * Math.tan(fov * Math.PI / 360)) * (o.pointSize || 0.03);
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: {uScale: {value: pxScale}, uFog: {value: bg}, uFogD: {value: o.fog ?? 0.0085}, uMin: {value: o.minPx || 1.6}, uNear: {value: o.near ?? 16.0}},
    vertexShader: `attribute vec3 aCol; attribute float aSize; uniform float uScale; uniform float uFogD; uniform float uMin; uniform float uNear;
      varying vec3 vC; varying float vF;
      void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv;
        float d = max(0.5, -mv.z); gl_PointSize = clamp(uScale * aSize / d, uMin * aSize, 5.0 * aSize);
        vC = aCol * mix(0.55, 1.0, smoothstep(1.5, uNear, d)); vF = 1.0 - exp(-uFogD * uFogD * d * d); }`,
    fragmentShader: `uniform vec3 uFog; varying vec3 vC; varying float vF;
      void main(){ vec2 c = gl_PointCoord - 0.5; float r = dot(c, c); if (r > 0.25) discard;
        float a = smoothstep(0.25, 0.10, r); gl_FragColor = vec4(mix(vC, uFog, vF), a); }`
  });
  const cloud = new THREE.Points(g, mat); scene.add(cloud);

  // ---- clearance envelope 2,1 × 3,0 m along the track axis
  const envGroup = new THREE.Group(); if (o.envelope !== false) scene.add(envGroup);
  const GREEN = new THREE.Color(0x2bd46f), RED = new THREE.Color(0xff2a3c), WHITE = new THREE.Color(0xdfe6f2);
  const obs = res.detections[0], ox = obs.center[0];
  const xNear = ox - obs.size[0] / 2 - 0.15, xFar = ox + obs.size[0] / 2 + 1.2;
  // green up to the obstacle, red around it, a dim neutral outline beyond it (not monitored as clear)
  const envCol = x => x < xNear - 6 ? GREEN : x < xNear ? GREEN.clone().lerp(RED, (x - (xNear - 6)) / 6) : x <= xFar ? RED : WHITE;
  const fadeA = x => Math.exp(-Math.pow(x / 150, 2)) * (x > xFar ? 0.35 : 1);
  const halfW = 1.05, zb = x => railZ(x) + 0.12, zt = x => railZ(x) + 3.0;
  const lp = [], lc = [];
  const seg = (a, b, x1, x2, al) => { const c1 = envCol(x1), c2 = envCol(x2);
    lp.push(...a, ...b); lc.push(c1.r, c1.g, c1.b, al * fadeA(x1), c2.r, c2.g, c2.b, al * fadeA(x2)); };
  const X0 = o.envStart ?? 2, X1 = o.envEnd ?? 200;
  // longitudinal edges: bottom edges solid, top edges lighter; beyond the obstacle dashed
  for (let x = X0; x < X1; x += 1){
    const x2 = x + 1;
    if (x > xFar && (Math.floor(x) % 2)) continue;
    const nearA = clamp01((x - 3) / 10) * 0.7 + 0.3;
    for (const [dy, zf, a] of [[-halfW, zb, 0.95], [halfW, zb, 0.95], [-halfW, zt, 0.5], [halfW, zt, 0.5]])
      seg([x, C + dy, zf(x)], [x2, C + dy, zf(x2)], x, x2, a * nearA);
  }
  // portal frames: every 10 m from 15 m up to the obstacle, one full-strength frame at it; none beyond (not monitored as clear)
  const portals = [];
  for (let x = 15; x < xNear - 4; x += 10) portals.push([x, o.portalA ?? (o.preview ? 0.34 : 0.55)]);
  portals.push([xNear, 1]);
  // WebGL lines are 1 px: offset copies (in metres, so near frames read thicker) give a 2–3 px frame
  const tk = o.portalTh ?? 0.022, OFF = [[0, 0], [tk, 0], [-tk, 0], [0, tk], [0, -tk]];
  for (const [x, a] of portals){
    const p = [[C - halfW, zb(x)], [C + halfW, zb(x)], [C + halfW, zt(x)], [C - halfW, zt(x)]];
    for (const [dy, dz] of OFF)
      for (let k = 0; k < 4; k++){ const q = p[k], r = p[(k + 1) % 4]; seg([x, q[0] + dy, q[1] + dz], [x, r[0] + dy, r[1] + dz], x, x, a); }
  }
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.Float32BufferAttribute(lp, 3));
  lg.setAttribute('color', new THREE.Float32BufferAttribute(lc, 4));
  envGroup.add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({vertexColors: true, transparent: true, depthWrite: false})));
  // translucent floor ribbon + walls (up to the obstacle only)
  const fp = [], fcol = [], idx = [];
  let vi = 0;
  for (let x = X0; x < Math.min(X1, xFar); x += 1){
    const x2 = x + 1;
    const quads = [
      [[x, C - halfW, zb(x)], [x2, C - halfW, zb(x2)], [x2, C + halfW, zb(x2)], [x, C + halfW, zb(x)], o.floorA ?? 0.22],
      [[x, C - halfW, zb(x)], [x2, C - halfW, zb(x2)], [x2, C - halfW, zt(x2)], [x, C - halfW, zt(x)], 0.035],
      [[x, C + halfW, zb(x)], [x2, C + halfW, zb(x2)], [x2, C + halfW, zt(x2)], [x, C + halfW, zt(x)], 0.035],
    ];
    for (const q of quads){
      const al = q[4];
      for (let k = 0; k < 4; k++){ const xx = q[k][0]; const c = envCol(xx); const near = clamp01((xx - 4) / 12); fp.push(...q[k]); fcol.push(c.r, c.g, c.b, al * fadeA(xx) * near); }
      idx.push(vi, vi + 1, vi + 2, vi, vi + 2, vi + 3); vi += 4;
    }
  }
  const fg = new THREE.BufferGeometry();
  fg.setAttribute('position', new THREE.Float32BufferAttribute(fp, 3));
  fg.setAttribute('color', new THREE.Float32BufferAttribute(fcol, 4));
  fg.setIndex(idx);
  envGroup.add(new THREE.Mesh(fg, new THREE.MeshBasicMaterial({vertexColors: true, transparent: true, depthWrite: false, side: THREE.DoubleSide})));

  // distance ticks on the track bed + the two detected rail heads
  const tp = [], tc = [];
  for (let x = 10; x <= 150; x += 10){
    const z = railZ(x) + 0.02, a = (x % 50 === 0 ? 0.6 : 0.28) * fadeA(x);
    tp.push(x, C - 1.3, z, x, C + 1.3, z); tc.push(1, 1, 1, a, 1, 1, 1, a);
  }
  for (const s of [-0.8, 0.8]) for (let x = 2; x < 196; x += 2){
    const a = 0.8 * Math.exp(-Math.pow(x / 170, 2)) * clamp01((x - 2) / 6); tp.push(x, C + s, railZ(x), x + 2, C + s, railZ(x + 2)); tc.push(0.87, 0.91, 1, a, 0.87, 0.91, 1, a);
  }
  const tg = new THREE.BufferGeometry();
  tg.setAttribute('position', new THREE.Float32BufferAttribute(tp, 3));
  tg.setAttribute('color', new THREE.Float32BufferAttribute(tc, 4));
  if (o.envelope !== false || o.rails) scene.add(new THREE.LineSegments(tg, new THREE.LineBasicMaterial({vertexColors: true, transparent: true, depthWrite: false})));

  // ---- obstacle box: translucent fill + a thick edge (several offset copies of the edges)
  const [cx, cy, cz] = obs.center, [sx, sy, sz] = obs.size;
  const pad = 0.18;
  const bgeo = new THREE.BoxGeometry(sx + pad, sy + pad, sz + pad);
  const box = new THREE.Mesh(bgeo, new THREE.MeshBasicMaterial({color: 0xff2a3c, transparent: true, opacity: o.boxFill ?? 0.25, depthWrite: false}));
  box.position.set(cx, cy, cz); scene.add(box);
  const eg = new THREE.EdgesGeometry(bgeo), em = new THREE.LineBasicMaterial({color: 0xff5566});
  const th = o.edge ?? 0.028;
  for (const [dy, dz] of [[0, 0], [th, 0], [-th, 0], [0, th], [0, -th], [th, th], [-th, -th]]){
    const e = new THREE.LineSegments(eg, em); e.position.set(cx, cy + dy, cz + dz); scene.add(e);
  }
  // stem from box top to label
  const stemTop = new THREE.Vector3(cx, cy, cz + sz / 2 + (o.stem ?? 1.3));
  const sg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(cx, cy, cz + sz / 2 + pad / 2), stemTop]);
  if (o.stem !== 0) scene.add(new THREE.Line(sg, new THREE.LineBasicMaterial({color: 0xff5566})));

  // ---- camera
  const camera = new THREE.PerspectiveCamera(fov, W / H, 0.1, 400);
  camera.up.set(0, 0, 1);
  const cam = o.cam || {pos: [-1.2, C, 0.45], look: [70, C, -0.55]};
  camera.position.set(...cam.pos); camera.lookAt(new THREE.Vector3(...cam.look));
  if (o.viewOffsetY) camera.setViewOffset(W, H, 0, o.viewOffsetY, W, H);
  camera.updateProjectionMatrix();

  const project = v => { const p = (v.isVector3 ? v : new THREE.Vector3(...v)).clone().project(camera);
    return {x: (p.x + 1) / 2 * W, y: (1 - p.y) / 2 * H, z: p.z}; };
  // screen-space bounding box of the obstacle box (for HUD corner brackets)
  const bbox = () => { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const a of [-1, 1]) for (const b of [-1, 1]) for (const c of [-1, 1]){
      const p = project([cx + a * (sx + pad) / 2, cy + b * (sy + pad) / 2, cz + c * (sz + pad) / 2]);
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x); y1 = Math.max(y1, p.y); }
    return {x0, y0, x1, y1}; };
  const render = () => renderer.render(scene, camera);
  return {renderer, scene, camera, render, project, bbox, stemTop, C, railZ, floorZ, obs, THREE};
}
