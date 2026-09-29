/* d2 «Линия» — shared helpers: icon sprite, decision sequences, strip renderer. Plain script (no build). */
(function(){
const P = {
  home:'<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  chev:'<path d="M6 9l6 6 6-6"/>',
  right:'<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
  left:'<path d="M19 12H5"/><path d="M11 6l-6 6 6 6"/>',
  upload:'<path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 002 2h12a2 2 0 002-2v-3"/>',
  download:'<path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M4 20h16"/>',
  play:'<path d="M8 5.5v13a1 1 0 001.5.9l10.4-6.5a1 1 0 000-1.8L9.5 4.6A1 1 0 008 5.5z" fill="currentColor" stroke="none"/>',
  pause:'<rect x="6" y="5" width="4" height="14" rx="1.5" fill="currentColor" stroke="none"/><rect x="14" y="5" width="4" height="14" rx="1.5" fill="currentColor" stroke="none"/>',
  stepb:'<path d="M6 5v14"/><path d="M18 6l-8 6 8 6z" fill="currentColor"/>',
  stepf:'<path d="M18 5v14"/><path d="M6 6l8 6-8 6z" fill="currentColor"/>',
  loop:'<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 014-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 01-4 4H4"/>',
  cam:'<path d="M3 8a2 2 0 012-2h2l2-2h6l2 2h2a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><circle cx="12" cy="13" r="3.5"/>',
  exitfs:'<path d="M9 4v5H4"/><path d="M15 4v5h5"/><path d="M9 20v-5H4"/><path d="M15 20v-5h5"/>',
  file:'<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M14 3v5h5"/>',
  folder:'<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>',
  server:'<rect x="4" y="4" width="16" height="7" rx="2"/><rect x="4" y="13" width="16" height="7" rx="2"/><path d="M8 7.5h.01M8 16.5h.01"/>',
  spark:'<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/>',
  check:'<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  x:'<path d="M6 6l12 12M18 6L6 18"/>',
  octa:'<path d="M8.2 3h7.6L21 8.2v7.6L15.8 21H8.2L3 15.8V8.2z"/><path d="M8 12h8" stroke-width="2.8"/>',
  tri:'<path d="M12 4l9 16H3z"/><path d="M12 10v4"/><path d="M12 17.2v.1"/>',
  go:'<circle cx="12" cy="12" r="9"/><path d="M8 12.3l2.8 2.8L16.3 9.5"/>',
  fault:'<circle cx="12" cy="12" r="9"/><path d="M6 18L18 6"/>',
  list:'<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
  compare:'<path d="M4 7h11"/><path d="M12 3l4 4-4 4"/><path d="M20 17H9"/><path d="M12 13l-4 4 4 4"/>',
  live:'<circle cx="12" cy="12" r="2.2"/><path d="M7.8 7.8a6 6 0 000 8.4M16.2 7.8a6 6 0 010 8.4M5 5a10 10 0 000 14M19 5a10 10 0 010 14"/>',
  sliders:'<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.5v.1"/>',
  cube:'<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  cpu:'<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  queue:'<rect x="3" y="4" width="18" height="5" rx="2"/><rect x="3" y="11" width="18" height="5" rx="2"/><path d="M7 20h10"/>',
  more:'<circle cx="5" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="19" cy="12" r="1.3" fill="currentColor"/>',
  menu:'<path d="M4 7h16M4 12h16M4 17h16"/>',
  train:'<rect x="5" y="3" width="14" height="14" rx="4"/><path d="M5 11h14"/><path d="M8.5 14h.01M15.5 14h.01"/><path d="M8 21l2-4M16 21l-2-4"/>',
  eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  rails:'<path d="M8 3L6 21M16 3l2 18"/><path d="M6.8 8h10.4M6.2 14h11.6"/>',
  target:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3"/>',
  trash:'<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/>',
  top:'<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M12 4v16"/>',
  back:'<path d="M3 17l9-10 9 10"/>',
  evb:'<path d="M10.5 7l-5 5 5 5"/><path d="M17 8l4 4-4 4-4-4z" fill="currentColor"/>',
  evf:'<path d="M13.5 7l5 5-5 5"/><path d="M7 8l4 4-4 4-4-4z" fill="currentColor"/>',
  zip:'<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M11 5h1M11 8h1M11 11h1"/><rect x="10" y="13" width="3" height="4" rx="1"/>'
};
let s = '<svg xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true">';
for (const k in P) s += `<symbol id="i-${k}" viewBox="0 0 24 24">${P[k]}</symbol>`;
s += '</svg>';
document.currentScript.insertAdjacentHTML('afterend', s);

/* ---- decision sequences (0 GO, 1 CAUTION, 2 STOP, 3 FAULT) ---- */
function rng(seed){ let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function synth(n, cautionFrames, stopEps, seed, opts={}){
  const r = rng(seed), a = new Uint8Array(n);
  let c = 0, guard = 0;
  const minL = opts.cMin || 4, maxL = opts.cMax || 40;
  while (c < cautionFrames && guard++ < 100000){
    const L = Math.min(cautionFrames - c, Math.floor(minL + r() * (maxL - minL)));
    const st = Math.floor(r() * (n - L));
    for (let i = st; i < st + L; i++) if (!a[i]) { a[i] = 1; c++; }
  }
  for (const [st, L] of stopEps) for (let i = st; i < st + L && i < n; i++) a[i] = 2;
  return a;
}
function doubleT(){ const a = new Uint8Array(201); for (let i = 8; i < 201; i++) a[i] = 2; a[111] = 0; a[117] = 1; a[197] = 1; return a; }
function spread(n, k, L, seed){ const r = rng(seed), out = []; for (let i = 0; i < k; i++){ const base = Math.floor((i + 0.15 + r() * 0.7) * n / k); out.push([base, typeof L === 'function' ? L(r) : L]); } return out; }
const RUNS = {
  doubleT_obstacle: doubleT,
  roundT_doubleT: () => synth(252, 173, [], 11, {cMin:6, cMax:30}),
  doubleT_platform: () => synth(345, 196, [[214, 3]], 12, {cMin:8, cMax:40}),
  roundT_pressureGate_roundT: () => synth(268, 119, [[150, 2]], 13),
  roundT_squareT_pressureGate_squareT: () => synth(545, 190, [], 14),
  squareT_platform_squareT_switch: () => synth(877, 443, [[120, 3], [301, 4], [488, 5], [612, 3], [790, 3]], 15, {cMin:10, cMax:60}),
  new_data: () => synth(11271, 4142, spread(11271, 30, r => 3 + Math.floor(r() * 5), 7), 16, {cMin:20, cMax:160}),
  cloud_with_fake_obj: () => { const a = synth(1510, 520, [], 17, {cMin:6, cMax:40});
      const eps = [[40, 208], [300, 56], [420, 52], [560, 34], [690, 30], [830, 22], [960, 26], [1120, 24]];
      for (const [st, L] of eps){ for (let i = st - 6; i < st; i++) a[i] = 1; for (let i = st; i < st + L; i++) a[i] = 2; }
      for (let i = 1300; i < 1340; i++) a[i] = 1; for (let i = 1420; i < 1450; i++) a[i] = 1; return a; }
};
const COL = ['#12A150', '#FFB300', '#D0001B', '#5B4E9C'];
/* SVG strip: merges runs, optional binning (max severity per bin) */
function strip(seq, {w = 600, h = 24, bins = 0, rx = 7, hatch = true, gap = 0} = {}){
  let s = seq;
  if (bins && seq.length > bins){ s = new Uint8Array(bins); const k = seq.length / bins;
    for (let b = 0; b < bins; b++){ let m = 0; const i0 = Math.floor(b * k), i1 = Math.max(i0 + 1, Math.floor((b + 1) * k)); let st = 0;
      for (let i = i0; i < i1; i++){ if (seq[i] === 2) st++; if (seq[i] === 1 && m < 1) m = 1; if (seq[i] === 3) m = 3; }
      s[b] = st ? 2 : m; } }
  const n = s.length, u = w / n, id = 'h' + Math.random().toString(36).slice(2, 8);
  let r = `<svg class="strip" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" preserveAspectRatio="none" style="border-radius:${rx}px">`;
  r += `<defs><pattern id="${id}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="${COL[2]}"/><rect width="3" height="8" fill="rgba(255,255,255,.22)"/></pattern></defs>`;
  let i = 0;
  while (i < n){ let j = i; while (j < n && s[j] === s[i]) j++;
    const fill = (s[i] === 2 && hatch) ? `url(#${id})` : COL[s[i]];
    r += `<rect x="${(i * u).toFixed(2)}" y="0" width="${((j - i) * u + 0.35).toFixed(2)}" height="${h}" fill="${fill}"/>`;
    if (gap && j < n) r += `<rect x="${(j * u - gap/2).toFixed(2)}" y="0" width="${gap}" height="${h}" fill="#fff"/>`;
    i = j; }
  return r + '</svg>';
}
window.D2 = { RUNS, strip, COL, rng,
  fill(sel, name, o){ document.querySelectorAll(sel).forEach(el => { el.innerHTML = strip(RUNS[name](), Object.assign({w: el.clientWidth || 400, h: el.clientHeight || 22}, o || {})); }); },
  icon(n, cls = ''){ return `<svg class="i ${cls}"><use href="#i-${n}"/></svg>`; }
};
})();
