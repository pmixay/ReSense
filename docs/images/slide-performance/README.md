# Smooth closed-door tab travel

This is a rendering-only optimization of the existing navigation animation.
The native movement/crossfade keyframes, easing, duration, intermediate tab order,
direction, door phases, final alignment, history, focus and recovery rules retain
their existing implementation.

## Bottleneck and correction

The baseline trace spends most travel-frame time in compositing: two full-size
live glass backdrop passes and complex DOM endpoint surfaces remain in the moving
scene even though the intermediate pages are already bitmaps. There are no long
JavaScript tasks in the unthrottled baseline slide.

The same glass diffusion (20px), saturation (.75) and contrast (.94) are now baked
into every bounded travel bitmap. The 32px motion blur combines with glass blur
by Gaussian variance. Both endpoint appearances share their page's single SVG
decode, and the current loaded stylesheet is collected once per journey. Bitmap
dimensions remain capped at 640×400. Only the cached images move/crossfade.
The stationary closed-door aperture also supplies a single clip rectangle, so
crossfades avoid blending pixels hidden by the opaque crown, foot and stiles.
This clip is measured once at departure; no per-frame JavaScript is added.

Original endpoint DOM and live glass stay visible during preparation. At the
existing start of travel, the two endpoint images replace their DOM sources and
the already-baked glass replaces the panes' live backdrop passes. Tint, glazing
reflections, leaf geometry and all door animations retain their original styling.
Opening restores live glass sampling. The existing failed-raster path still
traverses every frozen stage with CSS diffusion and live glass.
The skin's overlapping paint is trimmed only in cached-glass mode so it cannot
show through the clear inner aperture as hard horizontal bands.

## Measurement and visual provenance

`performance.json` records before/after real-time requestAnimationFrame samples,
frame gaps, long tasks, preparation status, animation keyframes and trace cost
summaries. Both builds use the same headless Chromium executable/launch options,
DPR 1 and local API; each journey uses a fresh browser page. Four representative
route pairs cover short/long travel, both directions and a Player destination.
The 1440×900 comparison repeats each pair twice at ordinary speed and with 4×
CPU throttling. Other supported desktop sizes receive ordinary-speed samples.
No screenshots, other test suites or competing browser captures run during these
measurements. Server-side headless samples describe this run, not every client GPU.

### Final ordinary-speed measurements

| Desktop viewport | Mean frame interval | Approx. measured rate | Worst sampled interval |
| --- | ---: | ---: | ---: |
| 1280×720 | 16.72ms | 59.8fps | 33.4ms |
| 1366×768 | 16.78ms | 59.6fps | 33.3ms |
| 1440×900 | 16.70ms | 59.9fps | 33.4ms |
| 1920×1080 | 17.38ms | 57.5fps | 50.0ms |

All 20 ordinary-speed journeys prepare successfully. Per-journey 95th-percentile
frame intervals stay at 16.7–16.8ms. The 1440×900 baseline averages 55.55–61.27ms
per frame across the same route pairs, versus 16.67–16.79ms after optimization.
The long-journey trace's mean compositor draw drops from 63.70ms to 9.30ms;
travel-layout events drop from 22 to one and paint events from 44 to five.

The stress result is retained explicitly: two of eight final 4× CPU-throttled
samples hit the existing 1800ms raster-preparation limit and use the original
CSS/live-glass fallback. That software-rendered fallback is functional but does
not meet 60fps. The original guard and recovery/phase rules are preserved.

`capture.json` fingerprints the final frontend source and records inspected native
animation progress, route pairs, glass mode, bitmap sizes/pixel opacity, endpoint
alignment and cleanup. `before-*.png` come from the deployed parent build;
`after-*.png` come from the optimized production preview. Captures inspect the
same closed-door state at the beginning, mid-journey and destination, plus all
four desktop sizes and travel to/from Player. They show the actual runtime
snapshots; no static artwork replaces application pages.

## Acceptance

- The sliding phase animates the original transform and two opacity tracks only.
- Every prepared travel surface, including endpoints, is a bounded opaque bitmap;
  no full-size live backdrop filter runs during a successfully prepared slide.
- Native glass remains available while closing, preparing, opening and after
  an injected raster/font failure. Endpoint DOM is retained until motion starts.
- Regression checks cover the four desktop sizes, ordered intermediate tabs in
  either direction, destination alignment before opening, history/focus, resize,
  reduced motion, one-time preparation failure/recovery, renderer suspension,
  immutable travel images, cleanup and keyboard dropdown operation.
- Verification passed: TypeScript/Vite production build, 354 frontend tests,
  all 19 navigation/control browser scenarios, and 11 targeted final-build
  regressions after the aperture rendering refinement. Ruff and diff checks pass.
- Before/after native animation timing/keyframe objects match for every measured
  route pair. The movement/completion/alignment/recovery implementation after
  endpoint preparation, plus `TrainDoors.tsx`, `navigationJourney.ts` and
  `AppShell.tsx`, is byte-identical to the parent version.

Visual verdict: pass. Reviewed the rendered start, moving intermediate and final
views, including all desktop sizes and both Player directions. Corrected the
cached-mode metal overlap so the glazing remains continuous. Source fingerprints
and measured animation keyframes are retained with the captures; the ordinary
view has no added chrome, controls or content.
