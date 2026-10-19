# ReSense web — frontend

React 18 + TypeScript (strict) + Vite, react-router v6, TanStack Query v5; three.js (player) and
roslib (live) are lazy-loaded by the pages that need them. Design: «Линия»
([`../design/mockup/`](../design/mockup/README.md)). HTTP contract: [`../API.md`](../API.md).

## Install, run, build

```bash
npm ci                     # pinned versions from package-lock.json (Node 22)
npm run dev                # http://localhost:5173, /api (HTTP + WebSocket) proxied to 127.0.0.1:8000
npm run build              # tsc --noEmit (app + vite config) and vite build → dist/
npm run preview            # serves dist/ with the same /api proxy (http://localhost:4173)
npm test                   # vitest run (unit + jsdom component tests)
npm run lint               # type check only
```

Backend for development: `python -m resense_web --port 8000 --reload`. In production
`python -m resense_web` serves `dist/` itself (SPA fallback); `scripts/run_webapp.sh` builds `dist/`
when it is missing and starts the server on :8080. Without a backend every page still
renders: the top bar shows «бэкенд офлайн» and cards show empty / error states.

## Structure

```
src/
  main.tsx, App.tsx       QueryClient, router (every page lazy, inside the pinned AppShell)
  styles/                 fonts.css (local @font-face), tokens.css (all design tokens), base.css
  components/<Name>/      the UI kit: <Name>.tsx + <Name>.module.css (+ tests); barrel components/index.ts
  api/                    types.ts (API.md), client.ts (fetch → ApiError with the Russian detail),
                          hooks.ts (a react-query hook per endpoint), upload.ts (staged XHR upload with
                          progress / abort / folders), cloud.ts (RSC1 decoder), ws.ts (live sim URL),
                          rosbridge.ts (lazy roslib subscription to /resense/status)
  lib/                    format.ts (Russian numbers / units / dates), decisions.ts, track.ts (track
                          axis, bed, envelope from a result's track dict), nav.ts (site map),
                          useSize.ts (ResizeObserver size of an element)
  player/                 the 3D engine shared by the Player and the previews: scene.ts (three.js),
                          engine / clock / motion / frameStore / cloudCache, CloudPreview.tsx (lazy),
                          screenDisplay.ts (reference-based 3D housing and live render target)
  pages/<Name>/index.tsx  one module per route; page-only components, hooks and tests next to it
  pages/UiGuide           /_ui: the living style guide (every component and state; not in the nav)
screenshots/              local review screenshots (git-ignored)
```

Pages: `/` Overview · `/upload` · `/queue` · `/runs` · `/runs/:id` · `/player`, `/player/:runId`
(responsive display workspace, optional fullscreen) · `/compare` · `/live` · `/presets` · `/about` · `/_ui` · `*` NotFound. The Overview's
«Демо» generates a demo recording, queues it and opens `/queue`. Deep links into Загрузка:
`/upload?source=file|server|demo|list&rec=<recordingId>&preset=<presetId>` (source, chosen recording, preset).

## Conventions

- **Fonts.** Raleway (100–900), self-hosted with Latin and Cyrillic in `src/assets/fonts`;
  no network fonts. Use `var(--f-head)` / `var(--f-body)` and lining, tabular numerals.
- **Tokens.** Colours, radii, spacing and shadows come from `styles/tokens.css` — no raw hex in
  components except canvas / SVG drawing. Brand red (`--red`) is for chrome, the line and the one
  main call to action per page (`<Button variant="primary">`).
- **Safety colours.** GO `--go` (`--go-deep` under white text), CAUTION `--caution` with ink text,
  STOP `--stop` always with the white 45° hatch (`var(--hatch)`) and the octagon icon, FAULT
  `--fault`. STOP is never drawn in brand red. Use `DecisionChip`, `DecisionStrip`, `lib/decisions.ts`.
- **No grey text.** Text is ink `#171B20` or white. De-emphasise with weight and size, never with
  a grey colour or opacity; disabled controls switch to a `--well-2` fill with ink text.
- **Minimal text, explanations in «?».** Put explanations in `<Help>` (round «?» + tooltip): opens on
  hover and keyboard focus, click pins it, Escape closes, one open per screen, `aria-describedby`
  wires it to the button. `<Tooltip>` wraps any other focusable trigger.
- **Russian UI.** Every user-visible string (and every error shown to the user) is Russian; numbers
  go through `lib/format.ts` (comma decimals, thin-space groups: «11 271», «54,9 м», «20,4 с»,
  «4,5 ГБ», «сегодня 14:32»). Code, comments and identifiers are English.
- **Data.** Use the hooks in `api/hooks.ts`; they poll jobs every second while one is queued or
  running and the system every 5 s, and invalidate what a mutation changes. Errors are `ApiError`
  (`.message` is the backend's Russian `detail`, `.offline` when the backend cannot be reached);
  show them with `<ErrorBanner error={…} onRetry={…}/>`.
- **Layout.** 12-column bento (`.grid-12`), cards radius 28, the page fills 1600×1000 down to
  1440×900 without scrolling (`.fill-viewport` = `100vh − 256px`). A page on the line may add a sub
  label to its station with `useRailSub(name)`.
- **Pinned navigation.** The top bar and category rail stay above the independently scrolling
  page on every route, including loading/error states and the player. Fullscreen targets the
  shared shell so both bars remain accessible. Player uses normal page flow at the available
  width: a fixed modeled display and a pinned bottom dock with demo settings and transport.
  Telemetry starts hidden and rises over the scene through wheel/trackpad, a native range
  slider or touch swipe. Its canvas,
  offscreen render target, camera aspect, close-up and HUD resize together via ResizeObserver.
  The display housing is a real Three.js mesh based on the supplied `images (1).jpg`; only the
  Player enables this presentation, while existing CloudPreview views retain direct rendering.
  There is no scaled stage, duplicate local header or separate page background.
- **Display optics.** `screenDisplay.ts` tilts the housing and publishes the active-face affine
  projection for HUD alignment. `screenEffects.ts` samples the live image for a fine RGB pixel
  aperture, local bloom and GPU-diffused light emission. Two low-resolution filter targets are
  disposed with the display; no readback or independent animation loop is used.
- **Train installation.** `trainInterior.ts` builds a real wall aperture and recessed gasket,
  laminate panels, stainless grab rail and door reveal around the device. Charging indicators
  are centered on the pillar, trim ends before the door, and invented roof bands are omitted.
  The housing and wall share their angle, antialiased analytic contact shading anchors the enclosure, and a clear-coated
  physical cover glass sits above the live surface. Environment geometry, textures, materials and
  render targets are disposed with the display; UI controls still belong to the shared page.
- **Pressure parallax.** Player uses a fixed viewport train backdrop under the shared chrome,
  with an exactly aligned physical screen and HUD; only the information tray scrolls.
  The default pose is straight; bounded mouse pressure tilts the wall/display group and moves the
  separate foreground railings at 24% strength. The HUD uses the updated affine surface transform.
  Pointer-only renders reuse live image/emission textures, settle to rest, and respect reduced
  motion and touch. A clear-to-dark dock tint and short blur feather preserve label sharpness.
- **Player space/performance.** Player uses the shared metro-line destination rail, styled like Upload.
  Its height toggle expands the live display without narrowing it. Foreground rails sit ahead
  of the moving wall and render sharply in the physical scene without a defocus pass. The detailed
  Moskva-2020 bay has off-camera neutral ceiling illumination, warm fill and formed door fittings;
  a cached saloon reflection probe lights its metal. `screenLighting.ts` samples live emission on
  wall, trim, housing and rail without CPU readback. Scene and HUD remain fixed; a measured
  responsive dock keeps playback/settings visible while `TelemetryTray.tsx` reveals other data.
  Physical rendering
  is capped by `displayQuality.ts` (1.5×/2.6M pixels, 1× on constrained devices); DOM controls
  stay native-size. Dynamic shadow maps are disabled in favor of analytic contact shading.
