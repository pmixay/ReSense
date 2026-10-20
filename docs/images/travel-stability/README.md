# Stabilized motion-blur transitions

## Causes corrected

The previous version moved the destination and transit strip through separate
React roots with independent CSS animation starts. Intermediate pages could still
load or update while moving. Animated 32px DOM filters also required repeated
painting, and a wall-clock timer could remove the strip before the browser had
finished displaying the journey. A throttled baseline recorded up to 1067ms of
start skew between the two moving surfaces.

The corrected sequence prepares the complete journey before departure:

- Freeze outgoing, intermediate and destination views after layout/font settling.
- Unmount the intermediate React root before travel, preserving a stable image.
  Mount those views only after the doors close, so their initialization does not
  compete with the closing animation.
- Bake the strong 32px blur once into temporary bitmaps capped at 640×400.
  Self-hosted Raleway, actual project styles, canvas pixels and scroll crops are
  retained. Edge clamping avoids transparent gaps between neighboring pages.
- Move the **entire strip with one native animation**. Sharp endpoint crossfades
  use its exact timeline start; only transform and opacity animate.
- Keep the real destination hidden at its final geometry, so no moving live-page
  updates or independent animation can drift relative to the strip.
  Suspend the hidden Player renderer during travel while preserving playback/data,
  then reattach its scene on reveal.
- Open doors on actual animation completion, retaining a bounded recovery guard.
  Resize and tab visibility changes finish safely; preparation failure reveals the
  destination without starting a partial journey.

The Moskva-2020 leaves, translucent frost, navigation direction, intermediate
station order, original train interior, restrained controls, history and reduced
motion behavior remain the established design.

## Verification

`performance.json` compares real-time requestAnimationFrame sampling in headless
Chromium at 1440×900 with 4× CPU throttling, using the same launch configuration.
The short journey's worst sampled frame gap falls from **116.7ms to 83.5ms**; the
long journey falls from **133.3ms to 83.4ms**. The moving strip receives no DOM
mutations during the corrected runs. These are server-side throttled regression
measurements, not a claim of 60fps on a particular user's GPU.

Browser regressions verify the four desktop sizes, both directions, all six
intermediate sections in a long jump, nonempty copied Player pixels, fixed raster
bounds, immutable travel under a late destination update, native-completion timing,
resize cleanup, recovery after a one-time raster/font failure, hidden Player
renderer suspension, focus/history, and reduced motion. The production build,
all 352 frontend tests and ten focused browser scenarios pass.

## Capture provenance

`capture.json` records the frontend source fingerprint, exact route pair, native
animation sample, viewport, intermediate page, blur bitmap size/pixel, animated
properties, final alignment and cleanup. Screenshots come from the running
production build at `http://127.0.0.1:4181`, Chromium/SwiftShader, DPR 1, using the
existing local API. Browser clocks/native interpolation are held for inspection.
The rasters are transient runtime captures of the actual interface, not static
images substituted for live application pages.

- `runs-to-upload-queue-{1280,1366,1440,1920}.png` checks all four desktop sizes.
- Queue ↔ Player captures check both directions through Runs.
- Upload → Compare captures inspect Queue, Runs and Player as each passes center.
- `player-reveal-1440.png` checks the settled live Player beneath opening doors.
