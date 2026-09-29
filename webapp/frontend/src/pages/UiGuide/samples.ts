// Synthetic decision strings for the style guide (the mockup's sequences, webapp/design/mockup/common.js).

function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function synth(n: number, cautionFrames: number, stopEps: [number, number][], seed: number, cMin = 4, cMax = 40): string {
  const r = rng(seed);
  const a = new Uint8Array(n);
  let c = 0;
  let guard = 0;
  while (c < cautionFrames && guard++ < 100000) {
    const L = Math.min(cautionFrames - c, Math.floor(cMin + r() * (cMax - cMin)));
    const st = Math.floor(r() * (n - L));
    for (let i = st; i < st + L; i += 1)
      if (!a[i]) {
        a[i] = 1;
        c += 1;
      }
  }
  for (const [st, L] of stopEps) for (let i = st; i < st + L && i < n; i += 1) a[i] = 2;
  return Array.from(a, (v) => 'GCSF'[v]).join('');
}

export const doubleT = (() => {
  const a = Array.from({ length: 201 }, (_, i): string => (i < 8 ? 'G' : 'S'));
  a[111] = 'G';
  a[117] = 'C';
  a[197] = 'C';
  return a.join('');
})();

export const roundT = synth(252, 173, [], 11, 6, 30);

export const newData = (() => {
  const r = rng(7);
  const eps: [number, number][] = [];
  for (let i = 0; i < 30; i += 1) eps.push([Math.floor(((i + 0.15 + r() * 0.7) * 11271) / 30), 3 + Math.floor(r() * 5)]);
  const s = synth(11271, 4142, eps, 16, 20, 160).split('');
  for (let i = 5200; i < 5230; i += 1) s[i] = 'F';
  return s.join('');
})();

export const doubleTLabels: boolean[] = Array.from({ length: 201 }, (_, i) => i >= 8);

export const sparkValues = Array.from({ length: 39 }, (_, i) => 8 + 12 * (0.5 + 0.5 * Math.sin(i / 3.2)) * (0.6 + ((i * 37) % 11) / 22) + (i > 30 ? 4 : 0));
