---
name: ReSense
description: The inherited «Линия» application system and its integrated LiDAR Player.
colors:
  red: "#D7133B"
  red-deep: "#A9092D"
  bg: "#EDF1F6"
  card: "#FFFFFF"
  well: "#E1E7EF"
  well-2: "#CBD5E1"
  well-3: "#F7F9FC"
  ink: "#111827"
  hair: "#D7DFE9"
  hair-2: "#B9C5D3"
  go: "#009F68"
  go-deep: "#007D4B"
  caution: "#FFB000"
  stop: "#D10C31"
  fault: "#7739C8"
  night: "#05070D"
  night-2: "#0B0E15"
  glass: "rgba(10, 12, 20, 0.66)"
  online: "#39D77C"
typography:
  title:
    fontFamily: "Raleway, system-ui, sans-serif"
    fontSize: "34px"
    fontWeight: 800
    lineHeight: 1.05
  card-title:
    fontFamily: "Raleway, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 700
  nav:
    fontFamily: "Raleway, system-ui, sans-serif"
    fontSize: "14.5px"
    fontWeight: 700
  body:
    fontFamily: "Raleway, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.35
  label:
    fontFamily: "Raleway, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 700
  meta:
    fontFamily: "Raleway, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 700
rounded:
  r-xs: "12px"
  r-sm: "16px"
  r-md: "20px"
  r-tile: "24px"
  r-lg: "28px"
  pill: "999px"
spacing:
  gut: "20px"
  pad: "clamp(16px, 2.5vw, 40px)"
components:
  button-primary:
    backgroundColor: "{colors.red}"
    textColor: "{colors.card}"
    rounded: "{rounded.pill}"
    height: "44px"
    padding: "0 20px"
  button-primary-hover:
    backgroundColor: "{colors.red-deep}"
  button-dark:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.card}"
    rounded: "{rounded.pill}"
    height: "44px"
    padding: "0 20px"
  button-outline:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "44px"
    padding: "0 20px"
  button-ghost:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "44px"
    padding: "0 20px"
  button-light:
    backgroundColor: "{colors.card}"
    textColor: "{colors.red}"
    rounded: "{rounded.pill}"
    height: "44px"
    padding: "0 20px"
  button-ghost-light:
    backgroundColor: "rgba(255, 255, 255, 0.14)"
    textColor: "{colors.card}"
    rounded: "{rounded.pill}"
    height: "44px"
    padding: "0 20px"
  text-input:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    rounded: "{rounded.r-xs}"
    height: "46px"
    padding: "0 14px"
  chip-well:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    typography: "{typography.meta}"
    rounded: "{rounded.pill}"
    height: "30px"
    padding: "0 12px"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.r-lg}"
    padding: "22px 24px"
  metro-navigation:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    height: "84px"
---

# Design System: ReSense

## Overview

**Creative North Star: "Линия"**

ReSense inherits a cool, compact engineering application: saturated metro-red chrome, a white station rail, pale continuous page ground and explicit emerald, amber, STOP-red and violet signal states. Self-hosted Raleway supports both Russian labels and tabular telemetry. The approved refinement strengthens color and control definition within this existing identity.

The Player is a code-led, inherited-world integration. Its onboard display sits exactly straight at rest in a Moscow-2020-inspired cool-gray saloon, with black glass, rounded industrial housing, a sharp copper-toned foreground post and red door-edge light. The train fills the Player beneath the shared metro-line station rail; pressure parallax, restrained live-image optics and taller views accompany stationary native-size controls over a feathered dock. The Player's Operate contract lives in `.impeccable/surfaces/webapp-frontend-src-pages-player.md`.

**Key Characteristics:**
- Shared metro-line station navigation on Upload and Player, with grouped menus omitted on Player.
- Cool neutral work surfaces, saturated red actions and distinct decision colors.
- Native-size controls and responsive, vertically flowing content.
- A straight-at-rest Moscow-2020-inspired scene with near-field railing parallax, physical glass and restrained live-image optics.
- Full-viewport train context beneath pinned chrome and a feathered, stationary control dock.
- Taller views at unchanged width and explicitly bounded physical-render effects.

## Colors

### Primary
Metro red (`red`) carries the logo, header, navigation line and primary actions, plus Player camera/speed selection and primary transport. `red-deep` marks open navigation groups and red-button hover. The historically named red tints remain legacy neutral grays rather than the current well values.

### Secondary
Signals are semantic, not a second branding palette: `go` marks verified/healthy data and `go-deep` supports white decision text; `caution` uses ink text; `stop` uses white text, an octagon and diagonal hatching; `fault` marks invalid/unverified input. `online` is the brighter connectivity/envelope signal.

### Neutral
`bg` is the continuous page ground; `card` is the shared white surface; the wells distinguish controls and inset regions. Ink supplies text, shared default selected segments and dark actions; hairlines separate regions and outline local Player telemetry. Night surfaces and translucent glass support rendered views and their annotations. Shader/material colors remain local rendering constants, not shared UI palette tokens.

The sidecar's tonal ramps are synthesized OKLCH preview strips, not additional application colors; the frontmatter and source CSS remain authoritative.

**The Signal Separation Rule.** Keep brand red and STOP distinct in both token choice and meaning; retain decision words, icons and STOP hatching alongside color.

## Typography

One self-hosted variable Raleway serves headings, body, labels and numbers, with system-ui/sans-serif fallback. Body uses lining, tabular numerals; this is not a separate monospace instrument face. The frontmatter records shared roles, not a geometric scale.

Shared page titles use the title role, card headings the card-title role, and navigation the nav role. PageHeader titles become smaller (28px) below the shared compact breakpoint; the Player does not add a page title. Local Player distance values are bold (44px/800, unit 20px, tracking -0.035em), metric values (22px/800, tracking -0.025em), and telemetry headings (12px/700). Distance-bar labels are native DOM text (12px), outside the bar SVG. Existing smaller HUD metadata and compact decision chips are observed legacy exceptions, not a new shared label scale.

## Layout

AppShell is a viewport-height flex column with pinned route-level navigation above a scrolling main region. Ordinary routes keep TopBar (64px), the default LineRail (84px), shared fluid side padding and top/bottom padding (16px/28px). Player uses the same LineRail styling as Upload, including the red line and station rings; grouped TopBar menus and the System branch DOM stay omitted. ResizeObserver publishes actual chrome height as `--site-chrome-h`. Player uses zero main-region padding for its edge-to-edge backdrop; shared pages retain their grid, gutters and full navigation.

**The One Shell Rule.** Player uses the shared metro-line station rail as its only pinned navigation, styled like Upload, including fullscreen; grouped TopBar menus and the System branch are omitted on that route. Other routes keep their full shared chrome. No local Player logo, duplicate title, rail or back bar is added.

Player content retains the native-flow order: **upper modeled display region → compact scenario/camera/status controls → five telemetry regions → timeline/transport**. The controls, telemetry and transport share a dock with gaps (12px). Telemetry order is track map, decision, distance, latency/rate and health; the decision region is conditional on an available decision. Desktop columns use proportions (1.15 / 1 / 1.55 / 1.15 / 1.2). There is no fixed 1600×900 stage, whole-page scaling or CSS transform on the entire workspace.

The taller default desktop display uses `clamp(520px, calc(100dvh - var(--site-chrome-h, 84px) - 128px), 1200px)`. A local height toggle adds `data-expanded` and switches to `clamp(700px, calc((100dvh - var(--site-chrome-h, 84px) - 128px) * 1.34), 1600px)` without changing width. At 1440×900, the display region remains 1368px wide while its height grows from 688px to about 922px. The dock stays in normal flow, with lower controls reachable by normal scrolling in both modes.

At widths up to 1100px, normal display height uses `clamp(460px, 72dvh, 1000px)`, telemetry becomes three columns and the timeline gets its own row. At widths up to 700px, normal display height uses `clamp(380px, 105vw, 620px)`, telemetry becomes two columns with distance spanning both, and camera options occupy a full row before height/fullscreen tools. The expanded-height override remains available. Narrow screens scroll vertically with native-size controls rather than shrinking the page.

The train canvas spans the complete Player workspace, with an absolutely positioned scene anchor following its natural content height. The physical display and native HUD scroll together, preserving alignment and keeping the entire expanded housing inside the canvas. A separately measured DisplayRegion (width/left/height/top) preserves the hardware's upper composition and responds to the height toggle; responsive margins reserve wall context without turning application controls into scene geometry. Pointer pressure uses the visible main region's vertical center even when content is taller.

The native-flow control dock sits above the scene (z-index 2), with shared side padding and top/bottom padding (16px/24px). Its tint stays fully transparent through the first 64px, leaving the upper controls on the clear wall, then ramps gently with a 160px feather mask. Visible tint opacity stays between zero and 0.56; the near-black gradient stop is positioned 240px beyond the painted bottom edge, without adding scrollable space. A separate backdrop-blur layer (18px, saturation 0.85) starts only 32px above the dock and feathers across 64px, keeping the live display annotations sharp. Upper-row supporting copy and picker keyboard hints use ink on the clear wall; lower transport copy is white over the tint, and white controls/panels retain their own ink. DecisionStrip tick marks use the dock's white `--strip-axis-ink` override while retaining the shared ink fallback elsewhere.

## Elevation & Depth

The shared system combines neutral tonal layering with soft card, popover and primary-action shadows; it is not shadow-free. Card, popover and red-action shadow tokens, keyboard rings and shared CSS state transitions are preserved in the sidecar. CSS reduced-motion handling suppresses CSS animation/transition durations; Player pointer pressure also honors reduced motion independently of the existing camera/orbit behavior.

The Player's depth is actual Three.js geometry: beveled rear and rounded industrial housing sit in an extruded laminate wall's real opening, seated in a recessed rubber ring. `trainInterior.ts` supplies formed cool-gray panels, recessed vertical/service seams, captive fasteners, beveled aluminium door reveals, black rubber/glazing, ceiling reflections, a recessed red status diffuser with local spill, an emergency-release rosette, and illuminated charging sockets where width permits. The ceiling combines a broad segmented white diffuser, 150 instanced ventilation fins, an extruded cove lip and warm side strip. The valance is sized from available clearance so it cannot cross the enclosure. The curved warm-metal foreground post and collars form an independent `railings` group; wall and housing remain in `train-background-layer`. Both layers start at zero Euler rotation. The post uses radius .092 and nominal z 1.8; collars are positioned and oriented on its actual curved centerline. Model checks cover foreground/background separation and active-screen occlusion at nine pressure extremes across desktop, mobile and expanded dimensions.

`images (1).jpg` (commit `5118a17`) remains the physical display authority. The inspected Moscow-2020 saloon/touchscreen photographs cited in the gallery README inform cool-gray paneling, black surrounds, copper-toned rails and red door-edge lighting. These are reference-only material cues; no photograph pixels ship in the scene, and no factory-dimensional scan is claimed.

The opaque train-wall scene fills the Player background. Deterministic DataTexture grain supplies laminate bump and steel roughness without image assets. A neutral broad ceiling area light, cool overhead key, warm cove fill and dimmer lower hemispheric bounce reproduce the references' lighting hierarchy. A small procedural saloon reflection environment is prefiltered once per renderer and cached, giving copper/aluminium broad luminaire reflections rather than unlit metallic surfaces. The shared area-light lookup tables initialize once. Dynamic shadow maps remain disabled. An analytic rounded signed-distance contact shadow follows the enclosure at the wall plane, using `fwidth` antialiasing for a smooth penumbra. A transparent clear-coated MeshPhysicalMaterial cover plane remains above the live face (z .205 versus .175), with mild ceiling-light glare in the display shader.

The near-field handrail is rendered sharply in the same physical scene pass. Its separate depth and parallax layer remain, but the defocus shader, offscreen rail target and compositing pass have been removed.

Normalized mouse displacement sets a bounded quadratic pressure target: maximum pitch (0.035 radians), yaw (0.055 radians) and a tiny coupled roll (0.004 radians, opposite the horizontal displacement). Exponential smoothing (10 per second, allowing up to .5s elapsed time per slow frame) settles to the exact target; foreground railings use 24% of the background's rotation on all three axes. Center, pointer leave and window blur return to exact neutral after settling. Mouse pressure requires no held button; touch does not drive it, and reduced motion blocks new pressure and resets the pose.

**The Neutral Pressure Rule.** The train scene rests exactly straight. Pressure moves the modeled layers with foreground railings at 24% of the background rotation; native application controls remain stationary, and touch/reduced-motion interaction keeps pressure neutral.

`screenEffects.ts` retains continuous source sampling beneath a subtle simulated RGB aperture (approximately 1.85 CSS-pixel pitch), mild bloom and diffused emission. Two low-resolution GPU passes extract/filter changed images with hue-preserving compression. `screenLighting.ts` adds a bounded five-sample area-light approximation to PBR wall, enclosure, trim and rail materials: four image-area samples plus a local edge sample, distance falloff in display coordinates, and no light from a black source. The display inverse matrix updates with pressure so the independently moving rail receives coherent image light. The edge pool and black-glass emission also follow the texture. Pointer-only frames reuse unchanged LiDAR/emission targets. PlayerEngine owns on-demand drawing for active runs; engine-less wall states use a bounded requestAnimationFrame sequence, and pressure rendering stops when settled. No runtime CPU readback is added. Owned geometry, materials, procedural textures, reflection targets and instancing resources are disposed.

`displayQuality.ts` budgets physical-canvas resolution: at most 1.5 DPR, a nominal 2.6-million-pixel target and a 0.5 DPR floor; low-memory/core hints cap DPR at 1. World treats reported device memory of 4GB or less, or 1–4 logical cores, as constrained. The floor takes precedence on very large viewports. DOM controls and annotations retain native size/resolution; emission/extraction targets are separately bounded. Hardware-specific low-end FPS has not been measured.

**The Bounded Effects Rule.** Render foreground rails directly without defocus passes, keep enclosure contact shading analytic and antialiased, and bound physical rendering by explicit resolution budgets; preserve native DOM controls/HUD and on-demand settling. These bounds are not a device-specific FPS guarantee.

**The Content-Driven Light Rule.** Player emission, wall spill and reflected light on housing, trim and handrail derive from the live image, retaining local hue and emitting nothing from black. Keep them restrained within the lit saloon; environment and rendering constants stay local to the renderer.

## Shapes

Retain the inherited radius ladder: inputs use `r-xs`; selects/tooltips and local Player telemetry use `r-sm`; the intervening tile radii remain available; global Card uses `r-lg`. Shared Button, Chip and Segmented defaults remain pill-shaped. Player camera groups instead use `r-sm` with `r-xs` options; local tools, transport and picker play buttons are rounded squares using `r-xs`. Local telemetry's crisp hairline border (1px), smaller radius and flat white surface do not redefine global Card. The display's rounded housing is generated geometry, not a CSS card-radius token.

## Components

**Buttons.** Shared Button offers primary, dark (default), outline, ghost, light and ghost-light variants. Medium geometry is in frontmatter; small/large heights are (36px/54px). Primary Button and red IconButton hover use `red-deep`; other hover states change fill or inset stroke. Button active presses down (1px). Disabled uses a neutral well with ink. Keyboard focus uses the inherited ink/white ring, with a white/red treatment on red chrome.

**Fields, chips and cards.** TextInput is a neutral inset field with an ink focus-within stroke and fault-colored invalid stroke. Chip supports well/outline/ink/white/glass/on-red treatments; DecisionChip retains GO/CAUTION/STOP/FAULT words and icons. Global Card keeps its rounded, softly elevated default and existing dark/night/red/well variants; small padding is (16px 18px).

**Navigation.** Outside Player, TopBar retains the ReSense identity, grouped destinations and backend status, and LineRail retains its station rings and System branch. Player uses that same metro-line rail styling for Главная, Загрузка, Очередь, Прогоны, Плеер and Сравнение, retaining existing URLs and shared responsive wrapping. TopBar groups and System branch DOM are absent on Player. The sidecar's metro-navigation preview represents the shared rail used by both Upload and Player.

**Player display and annotations.** `World.tsx` observes the full background viewport and upper DisplayRegion separately, applies the physical-render budget, then updates `PlayerScene`, modeled targets, camera aspect, HUD bounds and close-up; MiniMap observes its own region. `screenDisplay.ts` rebuilds the installation parametrically and mutates the live face's affine projection in place on resize, height changes and pressure steps. `Hud.tsx` applies the exact matrix to the native annotation plane and close-up. The close-up reserves ruler/caption gutters (44px/24px); display labels and handrails are sharp.

**Player controls and data.** The run selector, camera Segmented, decision status, height toggle and fullscreen control precede five single-level telemetry regions (minimum height 132px, padding 12px 14px). Height-toggle tooltip/accessibility labels switch between «Увеличить высоту экрана» and «Обычная высота экрана». Camera, speed and primary play/pause retain red states; tools retain native sizes and local rounded-square overrides. White telemetry keeps crisp outlines/ink; map and decision regions keep dark/signal surfaces. Orbit/reset, seeking, frame/event stepping, speed, looping and keyboard operation remain. Picker/loading/run-load errors use the full-height wall without active hardware; retry and GPU recovery remain native-flow states. A cloud-load failure remains visible until that cloud loads successfully, independently of its retry cooldown, so slow shader compilation cannot erase the error into an indefinite spinner. API hooks, detector contracts, PlayerEngine clock and URL position/speed/camera behavior remain authoritative.

## Do's and Don'ts

### Do:
- **Do** reuse AppShell, LineRail and shared components/tokens; keep Player's stage-only navigation variant scoped to that route.
- **Do** retain Raleway, Russian formatting and explicit decision semantics.
- **Do** resize the render targets, model projection, HUD and close-up together; keep map and distance labels responsive at native size.
- **Do** preserve global Card radii and typography when adding local compact panels.
- **Do** keep the default train pose exactly straight and the native control dock stationary during pressure parallax.

### Don't:
- **Don't** add a second Player identity, header, stage rail or back bar.
- **Don't** scale the entire workspace or impose a fixed design-resolution canvas on application controls.
- **Don't** extend the modeled display housing into a separate instrument/cab mini-site.
- **Don't** substitute brand red for STOP or imply unverified distance is clear.

Evidence sources: shared tokens/styles, AppShell/LineRail, Player page/World/ViewControls/HUD and `player/{screenDisplay,screenLighting,screenEffects,displayQuality,trainInterior,scene}.ts`. Current captures: `.impeccable/review/{desktop,user-1366,user-1920,mobile}.png` and `docs/images/player-workspace/{taller-display-1440,parallax-right-1440,installed-display-1440,clear-1440,picker-1440}.png`. The installed-display capture covers the visible 1440×816 below-rail viewport. Gallery `README.md` and `capture.json` record reference sources, bounds and neutral/pressure poses. `interior-lighting-verification.json` records current real GPU black/RGB/split-color receiver checks and exact cached neutral return; `optics-verification.json` remains historical evidence for the pixel aperture. No hardware-specific low-end FPS measurement is claimed.
