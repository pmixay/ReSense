# Directional station travel behind the glass

## Current motion

The navigation order is the shared metro line followed by its system branch:
Главная → Загрузка → Очередь → Прогоны → Плеер → Сравнение → Прямой эфир →
Параметры → О системе.

- A target to the left enters from the left, while the outgoing page moves right.
- A target to the right enters from the right, while the outgoing page moves left.
- Every intermediate tab passes behind the closed translucent doors, in order.
- One continuous trajectory carries the outgoing view, intermediate pages and
  destination together. A 32px peak blur clears as the destination decelerates.
- Travel lasts 650–1700ms according to distance; door close/open timing remains
  350/450ms. Reduced motion keeps the short non-spatial fade.

For example, Queue → Player passes Runs; Player → Queue passes Runs in reverse.
Upload → Compare passes Queue, Runs and Player.

## Runtime and behavior

The outgoing view is a short-lived DOM snapshot of the actual page, including
current form values, scroll positions and freshly rendered canvas pixels. The
source Player refresh uses zero elapsed time, without advancing playback.
Intermediate sections use actual page components in inert, aria-hidden memory
routers sharing the query cache. They do not navigate the main browser, start
Player/Live WebGL scenes, install Player/Live global shortcuts or write Live
preferences. Native two-dimensional decision strips remain available.

Only the selected destination enters browser history. The live destination keeps
its normal renderer and behavior. Transit roots and snapshots are removed after
travel, and native focus is restored when the doors finish opening. Lazy chunks
are prefetched during closing, preparation is bounded, and there is no persistent
animation or preview renderer at rest.

## Capture provenance

`capture.json` records the frontend source fingerprint, exact route pair, viewport,
intermediate order, direction, native animation sample time, projected positions,
blur and history/cleanup checks. Screenshots come from the production build at
`http://127.0.0.1:4180`, Chromium/SwiftShader, DPR 1, using the live local API.

- `runs-to-upload-queue-{1280,1366,1440,1920}.png` centers the passing Queue at
  1280×720, 1366×768, 1440×900 and 1920×1080.
- `queue-to-player-runs-1440.png` and `player-to-queue-runs-1440.png` cover both
  directions through Runs.
- `upload-to-compare-{queue,runs,player}-1440.png` samples every intervening page
  as it crosses the viewport center.
- `queue-to-player-opening-1440.png` shows the doors opening over the live Player.

Native animation interpolation and browser timers are held for deterministic
inspection. These are real browser renders of the running UI, not photographic
composites or image replacements for application pages.

## Verification and visual review

- Production TypeScript/Vite build and all **352 frontend tests** pass.
- Seven focused browser scenarios pass, covering all four desktop sizes,
  direction/blur, history, reduced motion, live canvas copying and a long journey
  through all six intermediate sections between Upload and About.
- The passing pages never create intermediate history entries or alter stored
  preferences. Preview roots disappear, and main returns to an untransformed,
  sharp, focused state.
- The copied Player canvas sample is opaque and nonempty (RGB 215/218/216),
  verifying that the outgoing GPU image survives route disposal.
- Current captures have no page/console errors and no horizontal overflow.

Visual verdict: pass. The moving page silhouettes remain visible through the
frost, adjacent views meet on one continuous strip, and the stronger blur clears
before the destination is revealed. The existing frameless Moskva-2020 leaves
remain the fixed foreground reference for the motion.
