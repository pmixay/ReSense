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

The Player is a code-led, inherited-world integration. Its pinned onboard display sits exactly straight at rest in a modeled metro saloon wall, retaining rounded industrial metal housing, protective cover glass and restrained powered-LCD optics. The train environment fills the Player beneath the sole pinned application chrome; mouse pressure adds a small damped lean with slower foreground railings, while native-size controls remain stationary over a feathered dark dock. The Player's Operate contract lives in `.impeccable/surfaces/webapp-frontend-src-pages-player.md`.

**Key Characteristics:**
- One shared header and metro navigation.
- Cool neutral work surfaces, saturated red actions and distinct decision colors.
- Native-size controls and responsive, vertically flowing content.
- A straight-at-rest train-wall scene with independent railing parallax, physical glass and restrained live-image optics.
- Full-viewport train context beneath pinned chrome and a feathered, stationary control dock.

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

AppShell is a viewport-height flex column. Its sole TopBar and LineRail stay above a scrolling main region. Ordinary routes use shared fluid side padding and top/bottom padding (16px/28px); the Player-specific main-region override uses zero padding for the edge-to-edge train backdrop. Desktop chrome is TopBar (64px) plus rail (84px); ResizeObserver publishes its actual height as `--site-chrome-h`. Shared pages retain their 12-column grid and shared gutter.

**The One Shell Rule.** The Player fills the available main region beneath the existing pinned global header/metro navigation, including fullscreen. Its train backdrop extends behind native-flow controls without a repeated logo, local Player title, miniature rail or back-navigation bar.

Player content retains the native-flow order: **upper modeled display region → compact scenario/camera/status controls → five telemetry regions → timeline/transport**. The controls, telemetry and transport share a dock with gaps (12px). Telemetry order is track map, decision, distance, latency/rate and health; the decision region is conditional on an available decision. Desktop columns use proportions (1.15 / 1 / 1.55 / 1.15 / 1.2). There is no fixed 1600×900 stage, whole-page scaling or CSS transform on the entire workspace.

The display height responds to available viewport height (`clamp(280px, calc(100dvh - var(--site-chrome-h, 148px) - 342px), 720px)`). At widths up to 1100px, telemetry becomes three columns, navigation wraps into text destinations, and the timeline gets its own row. At widths up to 700px, telemetry becomes two columns with distance spanning both; view tools and transport wrap into additional rows. Narrow screens scroll vertically with native-size controls rather than shrinking the page.

The full train canvas spans the Player viewport below the measured chrome (`100dvh - --site-chrome-h`). A zero-height sticky scene anchor (top 0) keeps this background visible behind vertically scrolling mobile content. A separately measured DisplayRegion (width/left/height/top) preserves the hardware's original upper composition inside the full canvas; responsive margins reserve wall context around the device without turning application controls into scene geometry.

The native-flow control dock sits above the scene (z-index 2), with shared side padding and top/bottom padding (16px/24px). Its tint stays fully transparent through the first 64px, leaving the upper controls on the clear wall, then ramps gently with a 160px feather mask. Visible tint opacity stays between zero and 0.56; the near-black gradient stop is positioned 240px beyond the painted bottom edge, without adding scrollable space. A separate backdrop-blur layer (18px, saturation 0.85) starts only 32px above the dock and feathers across 64px, keeping the live display annotations sharp. Upper-row supporting copy and picker keyboard hints use ink on the clear wall; lower transport copy is white over the tint, and white controls/panels retain their own ink. DecisionStrip tick marks use the dock's white `--strip-axis-ink` override while retaining the shared ink fallback elsewhere.

## Elevation & Depth

The shared system combines neutral tonal layering with soft card, popover and primary-action shadows; it is not shadow-free. Card, popover and red-action shadow tokens, keyboard rings and shared CSS state transitions are preserved in the sidecar. CSS reduced-motion handling suppresses CSS animation/transition durations; Player pointer pressure also honors reduced motion independently of the existing camera/orbit behavior.

The Player's depth is actual Three.js geometry: a beveled rear and rounded metallic industrial housing sit in an extruded laminate wall's real opening, seated in a recessed rubber mounting ring. `trainInterior.ts` supplies panel joints, flush fasteners, a stainless grab rail and fixing bosses, aluminium door/window reveal with dark glazing, ceiling valance/louvers, a linear luminaire and lower dado trim. Wall and housing belong to `train-background-layer`; the grab rail and fixings form a separate foreground `railings` group, added independently to the scene. Both layers start at zero Euler rotation. `images (1).jpg` (introduced in commit `5118a17`) remains the material/form authority; this is a parametric reconstruction, not a photographic scan or a claim to depict a particular train.

The opaque train-wall scene fills the full Player background. Deterministic procedural DataTexture grain supplies subtle laminate bump and steel roughness without image assets. A warm directional key, hemispheric ambient light and cooler fill illuminate the interior; the housing casts real cached PCF soft contact shadows onto the wall. Shadow maps refresh after geometry/size changes and pressure-pose updates; unchanged poses reuse the cache. A transparent clear-coated MeshPhysicalMaterial cover plane sits above the live face (z 0.205 versus 0.175 in model coordinates), with low-amplitude ceiling-light glare in the display shader.

Normalized mouse displacement sets a bounded quadratic pressure target: maximum pitch (0.035 radians), yaw (0.055 radians) and a tiny coupled roll (0.004 radians, opposite the horizontal displacement). Exponential smoothing (10 per second) settles to the exact target; foreground railings use 24% of the background's rotation on all three axes. Center, pointer leave and window blur return to exact neutral after settling. Mouse pressure requires no held button; touch does not drive it, and reduced motion blocks new pressure and resets the pose.

**The Neutral Pressure Rule.** The train scene rests exactly straight. Pressure moves the modeled layers with foreground railings at 24% of the background rotation; native application controls remain stationary, and touch/reduced-motion interaction keeps pressure neutral.

`screenEffects.ts` retains continuous source sampling beneath a subtle simulated RGB aperture (approximately 1.85 CSS-pixel pitch), mild local highlight bloom and diffused emission. Brightness, glass emission and wall spill remain softened for a lit train interior. Two low-resolution GPU passes extract/filter changed images with hue-preserving compression; their emission map drives the screen, black glass and wall-local light pool. Pointer-only frames reuse unchanged LiDAR/emission targets. PlayerEngine owns on-demand drawing for active runs; engine-less wall states use a bounded requestAnimationFrame sequence, and pressure rendering stops when settled. No runtime CPU pixel readback is added. Replaced geometry and all owned materials, render targets, procedural textures and shadow resources are disposed.

**The Content-Driven Light Rule.** Player light spill and pixel optics derive from the live display texture and stay restrained within the lit train-wall scene; environment and rendering constants do not become shared UI colors or generic glow treatments.

## Shapes

Retain the inherited radius ladder: inputs use `r-xs`; selects/tooltips and local Player telemetry use `r-sm`; the intervening tile radii remain available; global Card uses `r-lg`. Shared Button, Chip and Segmented defaults remain pill-shaped. Player camera groups instead use `r-sm` with `r-xs` options; local tools, transport and picker play buttons are rounded squares using `r-xs`. Local telemetry's crisp hairline border (1px), smaller radius and flat white surface do not redefine global Card. The display's rounded housing is generated geometry, not a CSS card-radius token.

## Components

**Buttons.** Shared Button offers primary, dark (default), outline, ghost, light and ghost-light variants. Medium geometry is in frontmatter; small/large heights are (36px/54px). Primary Button and red IconButton hover use `red-deep`; other hover states change fill or inset stroke. Button active presses down (1px). Disabled uses a neutral well with ink. Keyboard focus uses the inherited ink/white ring, with a white/red treatment on red chrome.

**Fields, chips and cards.** TextInput is a neutral inset field with an ink focus-within stroke and fault-colored invalid stroke. Chip supports well/outline/ink/white/glass/on-red treatments; DecisionChip retains GO/CAUTION/STOP/FAULT words and icons. Global Card keeps its rounded, softly elevated default and existing dark/night/red/well variants; small padding is (16px 18px).

**Navigation.** TopBar owns the ReSense identity, grouped destinations and backend status; its logo's inner circle follows the shared red token. LineRail owns the station sequence and System branch. Current stations combine an enlarged ring, heavier label and red underline. Compact navigation wraps destinations while preserving the active underline; it is the same application navigation.

**Player display and annotations.** `World.tsx` observes the full background viewport and upper DisplayRegion separately, then updates `PlayerScene`, the modeled surface/render targets, camera aspect, HUD bounds and close-up; MiniMap observes its own region. `screenGeometry.ts` shares the rounded-rectangle construction between enclosure and wall aperture. `screenDisplay.ts` rebuilds the installation parametrically and mutates the live face's affine projection in place on resize and each pressure step. `Hud.tsx` applies that exact matrix to the annotation plane, including its close-up, so labels stay aligned through neutral and pressure poses. The close-up reserves a ruler gutter (44px) and caption gutter (24px); adaptive caption detail never moves object pixels under those gutters.

**Player controls and data.** The compact run selector, locally styled shared camera Segmented, decision status and fullscreen control precede five single-level telemetry regions (minimum height 132px, padding 12px 14px). Camera options have icons, a neutral-well rounded-rectangle group and red selected state; speed selection and primary play/pause also use brand red. Tool/transport buttons retain native sizes with rounded-square local overrides. White telemetry uses crisp outlines; map and decision regions keep their dark/signal surfaces. The scene retains orbit and reset; timeline/transport retain seeking, frame/event stepping, speed, looping and keyboard operation. Picker, loading and run-load-error states use the same full-height wall without active display hardware; retry and lost-GPU recovery remain in native page flow. The existing API hooks, detector contracts, PlayerEngine clock and URL position/speed/camera behavior remain authoritative.

## Do's and Don'ts

### Do:
- **Do** reuse AppShell, TopBar, LineRail and existing shared components/tokens.
- **Do** retain Raleway, Russian formatting and explicit decision semantics.
- **Do** resize the render targets, model projection, HUD and close-up together; keep map and distance labels responsive at native size.
- **Do** preserve global Card radii and typography when adding local compact panels.
- **Do** keep the default train pose exactly straight and the native control dock stationary during pressure parallax.

### Don't:
- **Don't** add a second Player identity, header, stage rail or back bar.
- **Don't** scale the entire workspace or impose a fixed design-resolution canvas on application controls.
- **Don't** extend the modeled display housing into a separate instrument/cab mini-site.
- **Don't** substitute brand red for STOP or imply unverified distance is clear.

Evidence sources: shared tokens/styles, AppShell, DecisionStrip, Player page/World/HUD and `player/{screenDisplay,screenEffects,screenGeometry,trainInterior,scene}.ts`. Current captures reviewed: `.impeccable/review/{desktop,user-1366,user-1920,mobile}.png` and `docs/images/player-workspace/{parallax-left-1440,parallax-right-1440,installed-display-1440,picker-1440,caution-1366}.png`. The installed-display capture now covers the full below-header workspace (1440×752), including the dock. That directory's `README.md` and `capture.json` record architecture, bounds and neutral/pressure poses; motion behavior is source-backed, with no motion video supplied. `optics-verification.json` remains earlier evidence for the unchanged pixel/emission pipeline, not a new readback measurement from this iteration.
