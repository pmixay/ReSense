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

The Player is a code-led, inherited-world integration: the driver's cab of a metro train seen from the seat. The live LiDAR view is the windshield, in a black-bonded frit band and light-grey moulded trim, between A-pillars with platform-camera monitors and vent grilles, under a sun-visor housing and above a graphite desk with displays, manometers, push buttons and the driver's controller (Moskva-2020 cues, not a spaceship). The cab fills the Player beneath the shared metro-line station rail; head parallax, restrained live-image optics and taller views accompany stationary native-size controls over a feathered dock. Entering the Player is a walk from the saloon into this cab, and the cab boots its screens once the driver is seated. The Player's Operate contract lives in `.impeccable/surfaces/webapp-frontend-src-pages-player.md`.

**Key Characteristics:**
- Shared metro-line station navigation on Upload and Player, with grouped menus omitted on Player.
- Cool neutral work surfaces, saturated red actions and distinct decision colors.
- Native-size persistent bottom controls and button-toggled side telemetry around a clear central screen.
- A straight-at-rest Moskva-2020-style driver's cab around the live windshield, with head parallax, physical glass and restrained live-image optics.
- Full-viewport cab context beneath pinned chrome and a feathered, stationary control dock.
- Into the Player: a walk from the saloon into the cab and a short screen boot instead of the doors.
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

Player is a viewport-height workspace with a fixed cab layer and a bottom-anchored dock. Scenario, camera, height/fullscreen, play/pause, frame/event steps, seek, speed and loop remain visible at native CSS sizes. Telemetry starts hidden; tapping the centered «Телеметрия» button opens two compact side columns above the dock. Track map and decision sit left; distance, timing/rate and health sit right. The center remains unobstructed, and the cab, windshield, HUD and transport do not move or resize. Each side scrolls independently. Wheel/trackpad and swipes never toggle the panels. No whole-page scaling or fixed design-resolution stage is used.

`useDockHeight.ts` observes the responsive persistent dock, publishing `--player-dock-h`. The display region fills the remaining viewport, with an 8px upper margin and shared side gutters. The height toggle adds 36px to the region while keeping width and bottom controls fixed; the active image uses tighter physical top/bottom clearances. Expanded hardware remains within the viewport canvas rather than creating page scrolling. The hidden telemetry panel never contributes to the dock measurement.

The interface is desktop-only, with a 1280px minimum workspace width. Use the same desktop navigation, camera tools, telemetry columns and playback row across supported windows; retain full labels and icons. Side height is capped at 72% of the available display region, preserving the image center. Picker/loading/error content has its own scrollable region above measured bottom actions. Future interface work and captures follow this desktop-only scope.

The cab canvas spans exactly the non-scrolling Player viewport beneath the shared rail. `World.tsx` measures the DisplayRegion relative to the canvas, preserving hardware/HUD alignment. Mouse dragging still orbits the live visualization; wheel/trackpad does not zoom the physical Player. Touch scrolls an open side column and taps toggle its button. Pointer-pressure parallax is independent of telemetry and disabled for touch/reduced motion.

The pinned dock sits above the scene (z-index 2), with shared gutters and bottom safe-area padding. A clear-to-dark gradient and short feathered backdrop blur keep transport readable without blurring the display annotations. Supporting dock copy is white; telemetry/control surfaces retain their own ink. The shared «Телеметрия» button has `aria-expanded`/`aria-controls`, a focus ring and active red state. Hidden panels use native `hidden`; Escape closes them and returns focus to the toggle. Enter/Space toggle without reaching playback shortcuts. The scenario menu opens upward within the viewport.

## Elevation & Depth

The shared system combines neutral tonal layering with soft card, popover and primary-action shadows; it is not shadow-free. Card, popover and red-action shadow tokens, keyboard rings and shared CSS state transitions are preserved in the sidecar. CSS reduced-motion handling suppresses CSS animation/transition durations; Player pointer pressure also honors reduced motion independently of the existing camera/orbit behavior.

The Player's depth is actual Three.js geometry seen through a perspective eye. `cockpit.ts` builds the driver's cab around the measured display region (`cabLayout`): the windshield plane is z = 0, the seated eye looks straight down −z from 1.6 m with a 50° vertical field over the Player canvas, so the live face projects affinely and the DOM HUD stays aligned. Around the active face run the windshield glass with its black ceramic frit band (shader, fading to dots), a black bonding bead and an extruded light-grey moulding with screws; the A-pillars flare back to the cab sides with seams, a vent grille, a bronze grab handle, a platform-camera monitor on an arm and the side window beyond; the header carries a sun-visor roller housing with a red line, the ceiling an LED panel and an overhead switch panel whose lower edge is computed to stay above the glass at every head position. Below the glass a matte glare shield with defroster slots leads to the sloping graphite desk: traction and diagnostics displays, two manometers, rows of backlit push buttons, toggle switches, the driver's controller with its red grip and reverser lock, the emergency stop and the radio handset, with angled wing panels. Most of the desk sits under the dock in the Player and is seen whole during the walk-in. The instrument faces (`cabShaders.ts`) are procedural and decorative in the application palette: they draw blocks, traces and dials, never a value that could be read as a measurement. No photograph pixels ship in the scene, and no factory-dimensional scan is claimed.

The opaque cab fills the Player background. Colours are sRGB values converted to linear light, lit, compressed and gamma-encoded in the material (`encodePbr`; the LiDAR target keeps its display values). Neutral ceiling LEDs, a soft windshield fill, a warm fill from the saloon side and a hemispheric bounce light the cab (`cabLights`, shared with the walk-in); a small procedural cab reflection probe (the windshield ahead, roof strips above) is prefiltered once per renderer and cached. Dynamic shadow maps stay disabled. Geometry is rebuilt on resize; repeated parts (push buttons, toggles, screws, defroster slats) are drawn as one instanced mesh per geometry and material, which keeps the cab to about 90 meshes instead of 235, and everything owned is disposed. Model checks verify the projection/HUD alignment, that no opaque cab part covers the live picture at any head position (with a positive control), the boot timeline and disposal.

Normalized mouse displacement sets a bounded quadratic head target: up to 6 cm sideways and 3.5 cm vertically. The eye translates and never rotates, so the windshield stays parallel to the screen (the HUD transform remains a pure translation) while nearer cab parts move more than farther ones. Exponential smoothing (10 per second, allowing up to .5s elapsed time per slow frame) settles to the exact target; centre, pointer leave and window blur return to exact neutral. Mouse pressure requires no held button; touch does not drive it, and reduced motion blocks new pressure and resets the pose. The canvas publishes the current offset as `data-head-x`/`data-head-y`.

**The Neutral Pressure Rule.** The cab rests exactly straight. Pressure leans the eye; native application controls remain stationary, and touch/reduced-motion interaction keeps the eye at rest.

`screenEffects.ts` retains continuous source sampling beneath a subtle simulated RGB aperture (approximately 1.85 CSS-pixel pitch), mild bloom and diffused emission; a boot uniform reveals the picture behind a scan line and is bypassed once steady. Two low-resolution GPU passes extract/filter changed images with hue-preserving compression. `screenLighting.ts` adds a bounded five-sample area-light approximation to the cab's PBR materials: four image-area samples plus a local edge sample, distance falloff in display coordinates, no light from a black source, and none while the display is powered down. Pointer-only frames reuse unchanged LiDAR/emission targets. PlayerEngine owns on-demand drawing for active runs; engine-less cab states use a bounded requestAnimationFrame sequence, and rendering stops when the eye and the boot have settled. No runtime CPU readback is added.

`displayQuality.ts` budgets physical-canvas resolution: at most 1.5 DPR, a nominal 2.6-million-pixel target and a 0.5 DPR floor; low-memory/core hints cap DPR at 1. World treats reported device memory of 4GB or less, or 1–4 logical cores, as constrained. The floor takes precedence on very large viewports. DOM controls and annotations retain native size/resolution; emission/extraction targets are separately bounded. Hardware-specific low-end FPS has not been measured.

**The Bounded Effects Rule.** Keep the cab a single direct scene pass without shadow maps or defocus passes, bound physical rendering by explicit resolution budgets, and preserve native DOM controls/HUD and on-demand settling. These bounds are not a device-specific FPS guarantee.

**The Content-Driven Light Rule.** Light from the windshield display on the trim, pillars, header and desk derives from the live image, retaining local hue and emitting nothing from black or from a powered-down display. Keep it restrained within the lit cab; environment and rendering constants stay local to the renderer.

### Photo-led interior refinement and section transitions

The uploaded `IMG_8349.jpeg` / `IMG_8350.jpeg` saloon views and `1591221.jpeg`
exterior in main commit `7e38c01` remain the saloon/door material authority. Since
the Player became the driver's cab they dress the saloon of the boarding walk:
warm off-white panels, black glazing surrounds, individually piped gray-taupe
seats on cantilevered shells with bronze end armrests, curved bronze poles, broad
ceiling LED strips with warm coves, a metro-red line-map strip and red door-edge
lights at the open side doors.

Section navigation uses one authored paired-door sequence in AppShell: close in
260ms, settle until 270ms, capture the outgoing DOM/canvas appearance and commit
the selected destination offscreen. `navigationJourney.ts` follows `LINE` then
`BRANCH`: a left target enters from the left; a right target enters from the right.
Every intervening station is included in travel order. One native Web Animations
timeline translates a frozen strip containing outgoing, intermediate and
destination images. Its sharp outgoing/destination endpoint crossfades share
exactly the same document-timeline start time. Duration is 280ms plus 130ms per
station interval (410–1320ms), with near-linear cruising rather than an intermediate
stop. The 32px motion blur is baked once into temporary
bitmaps capped at 640×400; motion animates transform/opacity only. During the
closed-door slide, those bitmaps also cache the glass's existing 20px diffusion,
75% saturation and 94% contrast. Gaussian blur variances combine once, and each
endpoint's non-motion-blurred appearance reuses the same decoded source. All
moving surfaces are therefore small cached images rather than live DOM or
full-size backdrop-filter passes. The original endpoint DOM/live glass remains
in place until travel starts; closing, waiting, opening and raster-failure
fallback retain live optical sampling. Door tint/reflections stay in place.
A once-measured aperture clip avoids blending moving pixels behind opaque door
metal. Cached-mode skin paint ends at the inner glazing edge, preventing hard
overlap bands while preserving the leaf dimensions and all motion keyframes.
The real destination stays at its final layout geometry, hidden during travel.
Every stage has an explicit viewport-width offset in navigation order; movement
uses the actual final-stage offset. After finishing, that final offset is committed
and the destination must align for two painted frames before the leaves open in 320ms;
a delayed JS timer cannot cut the journey short. Preparation waits at most five
seconds (including cold font/chunk/image decoding), with a 12-second whole-sequence
recovery bound and a duration+2-second last-resort animation guard. Recovery finishes
the native journey instead of discarding its strip on an intermediate page. Failed
raster decoding still traverses the complete frozen stage sequence with CSS diffusion.
Query changes and navigation
within the same section (including Player run changes) are immediate. Browser
Back/Forward uses the same route blocker and direction. Only the selected route
enters browser history. A temporary outgoing DOM snapshot copies current form,
scroll and canvas appearance; `PlayerScene` refreshes its canvas synchronously
without advancing the playback clock before the pixel copy. Passing tabs use the
actual section components in isolated, inert memory routers sharing the query
cache only during preparation. After font/layout settling they are snapshotted
and their preview React root is unmounted before travel. Their global shortcuts,
Player title/fullscreen hooks and Live preferences are disabled. Passing Player/Live
avoid new WebGL scenes; the real destination retains the normal renderer. A native
SVG foreignObject capture embeds current project styles and the self-hosted font,
copies canvas pixels and bakes the blur with clamped edges. Three paint opportunities
warm the frozen surfaces before motion. No API/loading update can change the moving
images. Passing views mount only after the leaves have closed, preventing expensive
React work during door travel. The hidden destination Player temporarily detaches
only its renderer during frozen motion; its playback clock/data continue, and the
scene reattaches on reveal. Resize/visibility changes safely finish the journey; cancellation releases
native animations and pending preparation frames. Transit roots, snapshots and
temporary hints are released before the doors finish opening. Native focus/input is inert during
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
Earlier jitter-regression captures and CPU-throttled evidence are in
[`docs/images/travel-stability/`](docs/images/travel-stability/); the closed-door
compositing optimization is recorded in
[`docs/images/slide-performance/`](docs/images/slide-performance/README.md).

### Boarding the Player

Entering the Player from any other section (rail, links, Back/Forward) plays no
doors. `useTrainDoors` captures the leaving page exactly as it is (no closing
phase), enters `boarding` and commits the Player at once, hidden and inert under
the overlay so its layout can be measured; its renderer is detached while the walk
plays. `CabEntry.tsx` lazily loads `player/cabEntry.ts` (one temporary WebGL
renderer, disposed afterwards). The leaving page is a CSS3D plane standing in the
saloon's open side doors: a camera with the same focal length as the walk's,
centred on the Player canvas's principal point, makes the first frame identical to
the page. The time-keyed path (`entryPose`, 3.4 s) turns right by a quarter turn
(the page swings away to the left), walks the aisle with a small step bob, the cab
door slides open over 0.52 s, the eye steps past the seat and sits down (the view
lowers 0.45 m with a forward dip and a small landing bounce) and ends exactly in the
Player's seated pose over the same `cockpit.ts` geometry with its instruments dark.
The walk's camera is the Player's camera with a view offset that also covers the
pinned rail. The overlay then fades in 0.3 s and the Player boots. Any key or click
skips to the seat; keys are swallowed so the hidden Player never acts on them.
Failures (no WebGL, chunk error) reveal the Player at once; the 12 s watchdog
releases a walk that never finishes. Leaving the Player still uses the doors.
Reduced motion keeps the short fade. Initial loads do not play the walk.

**The boot.** The Player page boots its cab once per visit, when the walk has lifted
and the run (or picker/error) is there (`cabBoot.ts`, 2.1 s): button backlights and
the instrument faces strike with a flicker and draw in one after another, the
windshield shows a standby grid and a scan line reveals the live picture, and HUD
annotations fade in at 1.55 s. Over the windshield, `CabBoot.tsx` draws an
Iron Man-style initialization in the application's palette: a line of light opens
the screen, white brackets snap to the corners, a reticle with a metro-red arc
spins up and a short log types out the run's facts (name, frames, point clouds or
schematic mode, envelope, preset) before «Система готова». Controls stay usable;
autoplay waits for the boot; run switches keep the booted cab. Reduced motion and
passing previews skip it.

### Driver's cab and restrained controls

The wall-mounted display of earlier passes (`trainInterior.ts`) is gone: the user
asked for the Player to be a driver's cab instead of a screen on a wall, then
corrected a first spaceship styling to a realistic metro cab in the application's
general style, with more detail (see Elevation & Depth).


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
Captures of the previous wall installation stay in
[`docs/images/interior-restored/`](docs/images/interior-restored/); the cab, the walk-in and the boot are in
[`docs/images/player-cab/`](docs/images/player-cab/README.md).

## Shapes

Retain the inherited radius ladder: inputs use `r-xs`; selects/tooltips and local Player telemetry use `r-sm`; the intervening tile radii remain available; global Card uses `r-lg`. Shared Button, Chip and Segmented defaults remain pill-shaped. Player camera groups instead use `r-sm` with `r-xs` options; local tools, transport and picker play buttons are rounded squares using `r-xs`. Local telemetry's crisp hairline border (1px), smaller radius and flat white surface do not redefine global Card. The display's rounded housing is generated geometry, not a CSS card-radius token.

## Components

### About: reading hierarchy and progressive disclosure

`pages/About` uses a concise two-column overview: the existing purpose, a text-only
seven-stage workflow, and the four decision meanings. Small semantic GO/CAUTION/
STOP/FAULT labels retain their established colors and STOP hatch; explanations
wrap in full. The large illustrated metro pipeline, repeated question-mark help,
six competing KPI tiles and compressed four-column lower row are replaced by
quiet native disclosures. «Подробнее об обработке» exposes every original stage
explanation. Measurements retain their values and full conditions in one expanded
list, labelled as historical README data. ROS commands (including the UDP setup),
web launch/version/features and team descriptions each have their own expandable
section; commands stay copyable. Documentation is a plain list of links.

The default view contains no decorative icons. Only expanded copy controls use
icons. One desktop layout flows vertically at all supported widths; `main` owns
scrolling and opened detail grows naturally. No height fractions, forced local
scroll areas, ellipsis or nowrap constraints are used for content. Versions and
long commands wrap. Native summary controls expose expanded state and work with
Enter/Space, retain keyboard focus, and have restrained hover treatment.
Current captures and checks: [`docs/images/about-clean/`](docs/images/about-clean/).

**Native controls.** Shared Select retains native keyboard/typeahead/disabled
semantics. Supporting browsers use a Raleway, 16px-radius white `base-select`
picker, neutral hover and red selected/checkmark state; other browsers retain
the styled native fallback. Native accent/caret, scrollbar and file-button
treatments follow the shared tokens; number fields omit duplicate browser spin
buttons inside Stepper. Evidence: `docs/images/d1-controls-journey/`.

**Buttons.** Shared Button offers primary, dark (default), outline, ghost, light and ghost-light variants. Medium geometry is in frontmatter; small/large heights are (36px/54px). Primary Button and red IconButton hover use `red-deep`; other hover states change fill or inset stroke. Button active presses down (1px). Disabled uses a neutral well with ink. Keyboard focus uses the inherited ink/white ring, with a white/red treatment on red chrome.

**Fields, chips and cards.** TextInput is a neutral inset field with an ink focus-within stroke and fault-colored invalid stroke. Chip supports well/outline/ink/white/glass/on-red treatments; DecisionChip retains GO/CAUTION/STOP/FAULT words and icons. Global Card keeps its rounded, softly elevated default and existing dark/night/red/well variants; small padding is (16px 18px).

**Navigation.** Outside Player, TopBar retains the ReSense identity, grouped destinations and backend status, and LineRail retains its station rings and System branch. Player uses that same metro-line rail styling for Главная, Загрузка, Очередь, Прогоны, Плеер and Сравнение, retaining existing URLs and shared responsive wrapping. TopBar groups and System branch DOM are absent on Player. The sidecar's metro-navigation preview represents the shared rail used by both Upload and Player.

**Player display and annotations.** `World.tsx` observes the fixed background viewport and DisplayRegion separately, applies the physical-render budget, then updates `PlayerScene`, modeled targets, camera aspect, HUD bounds and close-up; MiniMap observes its own region. `screenDisplay.ts` rebuilds the cab parametrically and mutates the live face's affine projection in place on resize, height changes and head steps. `Hud.tsx` applies the exact matrix to the native annotation plane and close-up. The close-up reserves ruler/caption gutters (44px/24px); display labels and handrails are sharp. Toggling side telemetry changes no scene dimensions or projection.

**Player controls and data.** The run selector, camera Segmented, decision status, height/fullscreen tools and transport stay in the pinned bottom dock. Five telemetry regions live in the two side columns with a 132px minimum tile height. Height-toggle labels switch between «Увеличить высоту экрана» and «Обычная высота экрана». Camera, speed and primary play/pause retain red states; tools remain native-size rounded squares. White telemetry keeps crisp outlines/ink; map and decision regions keep dark/signal surfaces. Mouse orbit/reset, seeking, frame/event steps, speed, looping and keyboard operation remain. Picker/loading/run-load errors use the same cab (no live picture) with independently scrollable content above measured actions. Cloud-load failures persist until success independently of retry cooldown. API contracts, PlayerEngine clock and URL position/speed/camera behavior remain authoritative.

## Do's and Don'ts

### Do:
- **Do** reuse AppShell, LineRail and shared components/tokens; keep Player's stage-only navigation variant scoped to that route.
- **Do** retain Raleway, Russian formatting and explicit decision semantics.
- **Do** resize the render targets, model projection, HUD and close-up together; keep map and distance labels responsive at native size.
- **Do** preserve global Card radii and typography when adding local compact panels.
- **Do** keep the seated eye exactly at rest by default and the native control dock stationary during head parallax.

### Don't:
- **Don't** add a second Player identity, header, stage rail or back bar.
- **Don't** scale the entire workspace or impose a fixed design-resolution canvas on application controls.
- **Don't** let cab geometry cover the live picture at any head position, or let instrument faces show values that could be read as measurements.
- **Don't** substitute brand red for STOP or imply unverified distance is clear.

Evidence sources: shared tokens/styles, AppShell/LineRail/`CabEntry.tsx`, Player page/World/ViewControls/HUD/`CabBoot.tsx` and `player/{cockpit,cabEntry,cabShaders,cabBoot,screenDisplay,screenLighting,screenEffects,displayQuality,scene}.ts`. Current captures (SwiftShader software WebGL on synthetic demo runs, not evaluation evidence): [`docs/images/player-cab/`](docs/images/player-cab/README.md). Earlier galleries (`docs/images/player-workspace/`, `docs/images/interior-restored/`, `.impeccable/review/`) show the previous wall installation and are kept for the record. No hardware-specific low-end FPS measurement is claimed.
