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

The Player is a code-led, inherited-world integration. Its pinned physical display now reveals depth through a slight tilt, simulated pixels and light emitted from the live image; compact camera and transport controls remain in the shared application flow. The Player's Operate contract lives in `.impeccable/surfaces/webapp-frontend-src-pages-player.md`.

**Key Characteristics:**
- One shared header and metro navigation.
- Cool neutral work surfaces, saturated red actions and distinct decision colors.
- Native-size controls and responsive, vertically flowing content.
- A tilted modeled display with live-image pixel optics and content-driven light.

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

AppShell is a viewport-height flex column. Its sole TopBar and LineRail stay above a scrolling main region; the main region uses shared fluid side padding, with top/bottom padding (16px/28px). Desktop chrome is TopBar (64px) plus rail (84px); ResizeObserver publishes its actual height as `--site-chrome-h`. Shared pages retain their 12-column grid and shared gutter.

**The One Shell Rule.** The Player uses the full available main-region width and the existing global header/metro navigation, including fullscreen. It has no repeated logo, local Player title, miniature rail or back-navigation bar.

Player composition is a flowing column with gaps (12px): **modeled live scene → compact scenario/camera/status controls → five telemetry regions → timeline/transport**. Telemetry order is track map, decision, distance, latency/rate and health; the decision region is conditional on an available decision. Desktop columns use proportions (1.15 / 1 / 1.55 / 1.15 / 1.2). There is no fixed 1600×900 stage or whole-page scaling.

The display height responds to available viewport height (`clamp(280px, calc(100dvh - var(--site-chrome-h, 148px) - 342px), 720px)`). At widths up to 1100px, telemetry becomes three columns, navigation wraps into text destinations, and the timeline gets its own row. At widths up to 700px, telemetry becomes two columns with distance spanning both; view tools and transport wrap into additional rows. Narrow screens scroll vertically with native-size controls rather than shrinking the page.

## Elevation & Depth

The shared system combines neutral tonal layering with soft card, popover and primary-action shadows; it is not shadow-free. Card, popover and red-action shadow tokens, keyboard rings and state transitions are preserved in the sidecar. CSS reduced-motion handling suppresses CSS animation/transition durations; it does not imply all WebGL camera motion is disabled.

The Player's depth is actual Three.js geometry: beveled rear, thin silver housing and rounded black cover glass, with the live LiDAR render target mapped to the active face. A fixed body pitch/yaw (-0.075/-0.17 radians) and increased rear extrusion expose the sidewall without tilting application controls. The outer renderer remains transparent over the continuous application ground. `images (1).jpg` (introduced in commit `5118a17`) pins the material/form reference; the model is a parametric reconstruction, not a dimensional scan.

`screenEffects.ts` continuously samples the live source beneath a simulated RGB aperture (approximately 1.85 CSS-pixel pitch), local highlight bloom and diffused emission. Two low-resolution GPU passes extract/filter the image with hue-preserving compression; their emission map drives the screen, glass and surrounding light pool. Rendering stays on demand while paused, with no extra animation loop or runtime CPU pixel readback. Replaced geometry and all owned targets/materials are disposed.

**The Content-Driven Light Rule.** Player light spill and pixel optics derive from the live display texture; their rendering constants do not become shared UI colors or generic glow treatments.

## Shapes

Retain the inherited radius ladder: inputs use `r-xs`; selects/tooltips and local Player telemetry use `r-sm`; the intervening tile radii remain available; global Card uses `r-lg`. Shared Button, Chip and Segmented defaults remain pill-shaped. Player camera groups instead use `r-sm` with `r-xs` options; local tools, transport and picker play buttons are rounded squares using `r-xs`. Local telemetry's crisp hairline border (1px), smaller radius and flat white surface do not redefine global Card. The display's rounded housing is generated geometry, not a CSS card-radius token.

## Components

**Buttons.** Shared Button offers primary, dark (default), outline, ghost, light and ghost-light variants. Medium geometry is in frontmatter; small/large heights are (36px/54px). Primary Button and red IconButton hover use `red-deep`; other hover states change fill or inset stroke. Button active presses down (1px). Disabled uses a neutral well with ink. Keyboard focus uses the inherited ink/white ring, with a white/red treatment on red chrome.

**Fields, chips and cards.** TextInput is a neutral inset field with an ink focus-within stroke and fault-colored invalid stroke. Chip supports well/outline/ink/white/glass/on-red treatments; DecisionChip retains GO/CAUTION/STOP/FAULT words and icons. Global Card keeps its rounded, softly elevated default and existing dark/night/red/well variants; small padding is (16px 18px).

**Navigation.** TopBar owns the ReSense identity, grouped destinations and backend status; its logo's inner circle follows the shared red token. LineRail owns the station sequence and System branch. Current stations combine an enlarged ring, heavier label and red underline. Compact navigation wraps destinations while preserving the active underline; it is the same application navigation.

**Player display and annotations.** `World.tsx` observes available size and updates `PlayerScene`, the modeled surface/render targets, camera aspect, HUD bounds and close-up; MiniMap observes its own region. `screenDisplay.ts` rebuilds the housing aspect parametrically and exports the orthographic active face's exact affine projection. `Hud.tsx` applies that matrix to the annotation plane, including its close-up, so labels follow the tilted face rather than an axis-aligned approximation. The close-up reserves a ruler gutter (44px) and caption gutter (24px); adaptive caption detail never moves object pixels under those gutters.

**Player controls and data.** The compact run selector, locally styled shared camera Segmented, decision status and fullscreen control precede five single-level telemetry regions (minimum height 132px, padding 12px 14px). Camera options have icons, a neutral-well rounded-rectangle group and red selected state; speed selection and primary play/pause also use brand red. Tool/transport buttons retain native sizes with rounded-square local overrides. White telemetry uses crisp outlines; map and decision regions keep their dark/signal surfaces. The scene retains orbit and reset; timeline/transport retain seeking, frame/event stepping, speed, looping and keyboard operation. Picker, loading, errors, retry and lost-GPU recovery use the same page flow. The existing API hooks, detector contracts, PlayerEngine clock and URL position/speed/camera behavior remain authoritative.

## Do's and Don'ts

### Do:
- **Do** reuse AppShell, TopBar, LineRail and existing shared components/tokens.
- **Do** retain Raleway, Russian formatting and explicit decision semantics.
- **Do** resize the render targets, model projection, HUD and close-up together; keep map and distance labels responsive at native size.
- **Do** preserve global Card radii and typography when adding local compact panels.

### Don't:
- **Don't** add a second Player identity, header, stage rail or back bar.
- **Don't** scale the entire workspace or impose a fixed design-resolution canvas on application controls.
- **Don't** extend the modeled display housing into a separate instrument/cab mini-site.
- **Don't** substitute brand red for STOP or imply unverified distance is clear.

Evidence sources: `webapp/frontend/src/styles/{tokens,base,fonts}.css`, shared components, `lib/decisions.ts`, `pages/Player/{index.tsx,Player.module.css,World.tsx,Hud.tsx,ViewControls.tsx,Scrubber.tsx,Tiles.tsx}`, and `player/{screenDisplay,screenEffects,scene}.ts`. Reviewed captures: `.impeccable/review/{user-1366,desktop,user-1920,mobile}.png` and `docs/images/player-workspace/{caution-1366,clear-1440,picker-1440,app-overview-1440,app-upload-390}.png`. Provenance/architecture and measured optical checks remain in that directory's `README.md` and `optics-verification.json`.
