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
- Native-size persistent bottom controls and button-toggled side telemetry around a clear central screen.
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

One self-hosted variable Raleway serves headings, body, labels and numbers, with system-ui/sans-serif fallback. Body uses lining, tabular numerals; this is not a separate monospace instrument face. The frontmatter records shared roles, not a geometric scale. The user deferred Esh/Struve test variants after the exact font files were found unavailable; Raleway remains authoritative.

Shared page titles use the title role, card headings the card-title role, and navigation the nav role; the Player does not add a page title. Local Player distance values are bold (44px/800, unit 20px, tracking -0.035em), metric values (22px/800, tracking -0.025em), and telemetry headings (12px/700). Distance-bar labels are native DOM text (12px), outside the bar SVG. Existing smaller HUD metadata and compact decision chips are observed legacy exceptions, not a new shared label scale.

## Layout

AppShell is a viewport-height flex column with pinned route-level navigation above a scrolling main region. Ordinary routes keep TopBar (64px), the default LineRail (84px), shared fluid side padding and top/bottom padding (16px/28px). Player uses the same LineRail styling as Upload, including the red line and station rings; grouped TopBar menus and the System branch DOM stay omitted. ResizeObserver publishes actual chrome height as `--site-chrome-h`. Player uses zero main-region padding for its edge-to-edge backdrop; shared pages retain their grid, gutters and full navigation.

**The One Shell Rule.** Player uses the shared metro-line station rail as its only pinned navigation, styled like Upload, including fullscreen; grouped TopBar menus and the System branch are omitted on that route. Other routes keep their full shared chrome. No local Player logo, duplicate title, rail or back bar is added.

Player is a viewport-height workspace with a fixed train/display layer and a bottom-anchored dock. Scenario, camera, height/fullscreen, play/pause, frame/event steps, seek, speed and loop remain visible at native CSS sizes. Telemetry starts hidden; tapping the centered «Телеметрия» button opens two compact side columns above the dock. Track map and decision sit left; distance, timing/rate and health sit right. The center remains unobstructed, and the train, screen, HUD and transport do not move or resize. Each side scrolls independently. Wheel/trackpad and swipes never toggle the panels. No whole-page scaling or fixed design-resolution stage is used.

`useDockHeight.ts` observes the responsive persistent dock, publishing `--player-dock-h`. The display region fills the remaining viewport, with an 8px upper margin and shared side gutters. The height toggle adds 36px to the region while keeping width and bottom controls fixed; the active image uses tighter physical top/bottom clearances. Expanded hardware remains within the viewport canvas rather than creating page scrolling. The hidden telemetry panel never contributes to the dock measurement.

The interface is desktop-only, with a 1280px minimum workspace width. Use the same desktop navigation, camera tools, telemetry columns and playback row across supported windows; retain full labels and icons. Side height is capped at 72% of the available display region, preserving the image center. Picker/loading/error content has its own scrollable region above measured bottom actions. Future interface work and captures follow this desktop-only scope.

The train canvas spans exactly the non-scrolling Player viewport beneath the shared rail. `World.tsx` measures the DisplayRegion relative to the canvas, preserving hardware/HUD alignment. Mouse dragging still orbits the live visualization; wheel/trackpad does not zoom the physical Player. Touch scrolls an open side column and taps toggle its button. Pointer-pressure parallax is independent of telemetry and disabled for touch/reduced motion.

The pinned dock sits above the scene (z-index 2), with shared gutters and bottom safe-area padding. A clear-to-dark gradient and short feathered backdrop blur keep transport readable without blurring the display annotations. Supporting dock copy is white; telemetry/control surfaces retain their own ink. The shared «Телеметрия» button has `aria-expanded`/`aria-controls`, a focus ring and active red state. Hidden panels use native `hidden`; Escape closes them and returns focus to the toggle. Enter/Space toggle without reaching playback shortcuts. The scenario menu opens upward within the viewport.

## Elevation & Depth

The shared system combines neutral tonal layering with soft card, popover and primary-action shadows; it is not shadow-free. Card, popover and red-action shadow tokens, keyboard rings and shared CSS state transitions are preserved in the sidecar. CSS reduced-motion handling suppresses CSS animation/transition durations; Player pointer pressure also honors reduced motion independently of the existing camera/orbit behavior.

The Player's depth is actual Three.js geometry: beveled rear and rounded housing sit in a real wall opening and recessed rubber gasket. `trainInterior.ts` supplies cool-gray panels, seams, fasteners, bevelled aluminium door reveals, rubber/glazing, red edge diffuser, release rosette and lit charging sockets. The charging plate and release share the pillar's centerline; paired indicators are centered within the plate. Horizontal dado/service seams terminate before the door. The previously invented ceiling valance, vent fins and horizontal light bands have been removed from this close wall crop; broad ceiling illumination and reflections remain off-camera. The sharp curved copper-toned post and collars retain independent 24% parallax. Model checks verify screen clearance, rail depth, centered charging geometry and trim/door separation.

`images (1).jpg` (commit `5118a17`) remains the physical display authority. The inspected Moscow-2020 saloon/touchscreen photographs cited in the gallery README inform cool-gray paneling, black surrounds, copper-toned rails and red door-edge lighting. These are reference-only material cues; no photograph pixels ship in the scene, and no factory-dimensional scan is claimed.

The opaque train-wall scene fills the Player background. Deterministic DataTexture grain supplies laminate bump and steel roughness without image assets. A neutral broad ceiling area light, cool overhead key, warm cove fill and dimmer lower hemispheric bounce reproduce the references' lighting hierarchy. A small procedural saloon reflection environment is prefiltered once per renderer and cached, giving copper/aluminium broad luminaire reflections rather than unlit metallic surfaces. The shared area-light lookup tables initialize once. Dynamic shadow maps remain disabled. An analytic rounded signed-distance contact shadow follows the enclosure at the wall plane, using `fwidth` antialiasing for a smooth penumbra. A transparent clear-coated MeshPhysicalMaterial cover plane remains above the live face (z .205 versus .175), with mild ceiling-light glare in the display shader.

The near-field handrail is rendered sharply in the same physical scene pass. Its separate depth and parallax layer remain, but the defocus shader, offscreen rail target and compositing pass have been removed.

Normalized mouse displacement sets a bounded quadratic pressure target: maximum pitch (0.035 radians), yaw (0.055 radians) and a tiny coupled roll (0.004 radians, opposite the horizontal displacement). Exponential smoothing (10 per second, allowing up to .5s elapsed time per slow frame) settles to the exact target; foreground railings use 24% of the background's rotation on all three axes. Center, pointer leave and window blur return to exact neutral after settling. Mouse pressure requires no held button; touch does not drive it, and reduced motion blocks new pressure and resets the pose.

**The Neutral Pressure Rule.** The train scene rests exactly straight. Pressure moves the modeled layers with foreground railings at 24% of the background rotation; native application controls remain stationary, and touch/reduced-motion interaction keeps pressure neutral.

`screenEffects.ts` retains continuous source sampling beneath a subtle simulated RGB aperture (approximately 1.85 CSS-pixel pitch), mild bloom and diffused emission. Two low-resolution GPU passes extract/filter changed images with hue-preserving compression. `screenLighting.ts` adds a bounded five-sample area-light approximation to PBR wall, enclosure, trim and rail materials: four image-area samples plus a local edge sample, distance falloff in display coordinates, and no light from a black source. The display inverse matrix updates with pressure so the independently moving rail receives coherent image light. The edge pool and black-glass emission also follow the texture. Pointer-only frames reuse unchanged LiDAR/emission targets. PlayerEngine owns on-demand drawing for active runs; engine-less wall states use a bounded requestAnimationFrame sequence, and pressure rendering stops when settled. No runtime CPU readback is added. Owned geometry, materials, procedural textures, reflection targets and instancing resources are disposed.

`displayQuality.ts` budgets physical-canvas resolution: at most 1.5 DPR, a nominal 2.6-million-pixel target and a 0.5 DPR floor; low-memory/core hints cap DPR at 1. World treats reported device memory of 4GB or less, or 1–4 logical cores, as constrained. The floor takes precedence on very large viewports. DOM controls and annotations retain native size/resolution; emission/extraction targets are separately bounded. Hardware-specific low-end FPS has not been measured.

**The Bounded Effects Rule.** Render foreground rails directly without defocus passes, keep enclosure contact shading analytic and antialiased, and bound physical rendering by explicit resolution budgets; preserve native DOM controls/HUD and on-demand settling. These bounds are not a device-specific FPS guarantee.

**The Content-Driven Light Rule.** Player emission, wall spill and reflected light on housing, trim and handrail derive from the live image, retaining local hue and emitting nothing from black. Keep them restrained within the lit saloon; environment and rendering constants stay local to the renderer.

### Photo-led interior refinement and section transitions

The uploaded `IMG_8349.jpeg` / `IMG_8350.jpeg` saloon views and `1591221.jpeg`
exterior in main commit `7e38c01` are the current material/seating/door authority.
Screen housing, right-hand door and foreground post positions stay locked to their
existing responsive geometry. Refine the wall toward warm off-white laminate,
polished bronze rails and brushed aluminium; add a black-enamel glazing lip and
lower bead to the fixed door. Below the housing, individually piped gray-taupe
woven backrests, contoured cushions, rounded shells and bronze end armrests form a
cantilevered bench. A shared 128×128 procedural weave/bump tile is disposed with the
interior. Seat geometry stays clear of the active display and behind the foreground
post at all pressure extremes. The dock blur is now 8px with a longer feather, so
the upper bench remains recognizable while controls retain their dark ground.

Section navigation uses one authored paired-door sequence in AppShell: close in
350ms, settle until 360ms, capture the outgoing DOM/canvas appearance and commit
the selected destination offscreen. `navigationJourney.ts` follows `LINE` then
`BRANCH`: a left target enters from the left; a right target enters from the right.
Every intervening station is included in travel order. One shared cubic-bezier
trajectory moves the outgoing/intermediate strip and the live destination together,
with no exit/entry gap. Duration is 500ms plus 150ms per station interval (650–1700ms);
motion blur peaks at 32px, then clears as the destination settles. Passing-page
blur is scoped to viewport-sized stages instead of one oversized filter target
spanning every station. The leaves open in 450ms after travel. Preparation waits
at most 1.2 seconds, with a six-second
whole-sequence recovery bound. Query changes and navigation
within the same section (including Player run changes) are immediate. Browser
Back/Forward uses the same route blocker and direction. Only the selected route
enters browser history. A temporary outgoing DOM snapshot copies current form,
scroll and canvas appearance; `PlayerScene` refreshes its canvas synchronously
without advancing the playback clock before the pixel copy. Passing tabs use the
actual section components in isolated, inert memory routers sharing the query
cache. Their global shortcuts, Player title/fullscreen hooks and Live preferences
are disabled. Passing Player/Live avoid new WebGL scenes; the live destination
retains the normal renderer. Transit roots, snapshots and temporary hints are
released before the doors finish opening. Native focus/input is inert during
the overlay, then main receives focus without scrolling.

The overlay is dimensional CSS geometry: only two full-viewport sliding leaves,
following the uploaded `IMG_8349.jpeg`, `IMG_8350.jpeg` and `1591221.jpeg`:
tall glazing occupying approximately 91% of the height, narrow black enamel
stiles, deep center seals, red edge strips and a small lower glazing bead. The
invented recessed grips and broad metal kick plates are removed. Every detail moves with
its leaf; the screen itself is the frame. No stationary header, side jamb or sill
is mounted. Each pane combines 20px backdrop diffusion, 75% saturation and a
26–32% warm neutral tint. This is genuinely transmitting frosted glass: page
light/color and lateral movement remain visible while fine text is diffused.
The matte finish is user-pinned relative to the clear photographed glazing.
Only the two panes backdrop-filter; brief blur on opaque door details and page
surfaces supplies motion blur without isolating the panes' backdrop sampling.
The overlay is `display:none` at rest
and adds no WebGL renderer, image download or animation dependency. Reduced motion uses a
75ms cover / 100ms reveal fade with no moving leaves. Initial page loads do not run
the sequence. Shared Raleway, navigation styling and all page controls are retained.
All temporary page transforms, filters and `will-change` hints end with the sequence.
Actual optical transmission/diffusion and outgoing/incoming projected directions
are recorded in [`docs/images/moskva-doors/`](docs/images/moskva-doors/). Current
directional/intermediate travel captures are in
[`docs/images/directional-travel/`](docs/images/directional-travel/).

### Restored interior and restrained controls

The latest user correction restores `trainInterior.ts` and `screenDisplay.ts`
byte-for-byte to the pre-gloss `af2ecd8^` implementation. Original wall/door/seat
geometry, copper-toned rails, material roughness, screen housing, ceiling lighting,
reflection probe and direct physical rendering are authoritative again. This also
restores the original screen/glass materials and removes the later ACES/sRGB pass.
The supplied photograph-led installation, woven bench and existing independent
pressure layers remain the visual reference.

`trainModel.ts` replaces the outside cameras' block carriage with rounded formed
shells, wraparound cab glazing, individual side panes, paired sliding leaves,
recessed LED running lights, wipers, roof equipment, bogie frames and steel wheels.
Repeated parts share geometry; model-owned materials, machining texture and
reflection target are disposed. Its PBR light is compressed and encoded locally
before joining the display-valued LiDAR target. Dedicated lights affect only the
outside-camera layer. Playback, camera framing and the clearance model retain
their existing coordinates.

The inherited UI gets a restrained material finish through shared `control-sheen`,
`surface-sheen` and `control-edge` tokens: shallow highlights on red actions,
selected camera/speed controls, chrome and pale surfaces. Control sheen now peaks
at 5.5% white, with a 16% light edge and 4% lower edge; primary red shadow opacity
is 16%. Selected segments/speed use 6% soft shadow and icon buttons use 16% bounded
drop shadow. Keyboard focus rings retain their full strength. Existing geometry,
Russian copy, semantic decisions and keyboard rings remain authoritative.
Current desktop captures and material provenance are in
[`docs/images/interior-restored/`](docs/images/interior-restored/).

## Shapes

Retain the inherited radius ladder: inputs use `r-xs`; selects/tooltips and local Player telemetry use `r-sm`; the intervening tile radii remain available; global Card uses `r-lg`. Shared Button, Chip and Segmented defaults remain pill-shaped. Player camera groups instead use `r-sm` with `r-xs` options; local tools, transport and picker play buttons are rounded squares using `r-xs`. Local telemetry's crisp hairline border (1px), smaller radius and flat white surface do not redefine global Card. The display's rounded housing is generated geometry, not a CSS card-radius token.

## Components

**Buttons.** Shared Button offers primary, dark (default), outline, ghost, light and ghost-light variants. Medium geometry is in frontmatter; small/large heights are (36px/54px). Primary Button and red IconButton hover use `red-deep`; other hover states change fill or inset stroke. Button active presses down (1px). Disabled uses a neutral well with ink. Keyboard focus uses the inherited ink/white ring, with a white/red treatment on red chrome.

**Fields, chips and cards.** TextInput is a neutral inset field with an ink focus-within stroke and fault-colored invalid stroke. Chip supports well/outline/ink/white/glass/on-red treatments; DecisionChip retains GO/CAUTION/STOP/FAULT words and icons. Global Card keeps its rounded, softly elevated default and existing dark/night/red/well variants; small padding is (16px 18px).

**Navigation.** Outside Player, TopBar retains the ReSense identity, grouped destinations and backend status, and LineRail retains its station rings and System branch. Player uses that same metro-line rail styling for Главная, Загрузка, Очередь, Прогоны, Плеер and Сравнение, retaining existing URLs and shared responsive wrapping. TopBar groups and System branch DOM are absent on Player. The sidecar's metro-navigation preview represents the shared rail used by both Upload and Player.

**Player display and annotations.** `World.tsx` observes the fixed background viewport and DisplayRegion separately, applies the physical-render budget, then updates `PlayerScene`, modeled targets, camera aspect, HUD bounds and close-up; MiniMap observes its own region. `screenDisplay.ts` rebuilds the installation parametrically and mutates the live face's affine projection in place on resize, height changes and pressure steps. `Hud.tsx` applies the exact matrix to the native annotation plane and close-up. The close-up reserves ruler/caption gutters (44px/24px); display labels and handrails are sharp. Toggling side telemetry changes no scene dimensions or projection.

**Player controls and data.** The run selector, camera Segmented, decision status, height/fullscreen tools and transport stay in the pinned bottom dock. Five telemetry regions live in the two side columns with a 132px minimum tile height. Height-toggle labels switch between «Увеличить высоту экрана» and «Обычная высота экрана». Camera, speed and primary play/pause retain red states; tools remain native-size rounded squares. White telemetry keeps crisp outlines/ink; map and decision regions keep dark/signal surfaces. Mouse orbit/reset, seeking, frame/event steps, speed, looping and keyboard operation remain. Picker/loading/run-load errors use the same wall with independently scrollable content above measured actions. Cloud-load failures persist until success independently of retry cooldown. API contracts, PlayerEngine clock and URL position/speed/camera behavior remain authoritative.

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

Evidence sources: shared tokens/styles, AppShell/LineRail, Player page/World/ViewControls/HUD and `player/{screenDisplay,screenLighting,screenEffects,displayQuality,trainInterior,scene}.ts`. Current captures: `.impeccable/review/{desktop,user-1366,user-1920}.png` and `docs/images/player-workspace/{taller-display-1440,parallax-right-1440,installed-display-1440,clear-1440,picker-1440}.png`. The installed-display capture covers the visible 1440×816 below-rail viewport. Gallery `README.md` and `capture.json` record reference sources, bounds and neutral/pressure poses. `interior-lighting-verification.json` records current real GPU black/RGB/split-color receiver checks and exact cached neutral return; `optics-verification.json` remains historical evidence for the pixel aperture. No hardware-specific low-end FPS measurement is claimed.
