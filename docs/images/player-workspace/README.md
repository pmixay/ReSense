# Integrated Player workspace

Real production-build captures from the ReSense backend and Chromium with SwiftShader
WebGL. `clear-*`, `caution-*`, `stop-*` and `picker-*` cover 1366×768, 1440×900,
1920×1080 and 390×844. `capture.json` records the synthetic demo runs, exact frame
positions and measured workspace/display/transport bounds. These are UI demonstration
data from six-second approach/crossing runs, not detector evaluation evidence.

## Reference and implementation

The user supplied [`images (1).jpg`](../../../images%20(1).jpg) in commit `5118a17`:
a shallow display with rounded black glass, thin silver housing and recessed active
surface. [`screenDisplay.ts`](../../../webapp/frontend/src/player/screenDisplay.ts)
builds that form as actual extruded Three.js meshes with beveled edges and lit metal
and glass materials. Its active surface samples the live LiDAR render target.
The housing adapts parametrically to the workspace's aspect ratio; it is a
reference-based reconstruction rather than a photographic asset or a dimensional
scan. No reference-image pixels are used as the player UI.

## Train-wall installation

The current display is mounted in a modeled metro interior. [`trainInterior.ts`](../../../webapp/frontend/src/player/trainInterior.ts)
builds a formed laminate wall with an actual opening, recessed rubber mounting gasket,
panel joints, flush fasteners, stainless grab rail, aluminium door/window reveal,
ceiling louvers, linear saloon light and lower wall trim. The wall and housing share
the same angle; there is no floating monitor on an abstract backdrop. The reference
photo informs the installation and materials; the environment is reconstructed 3D
geometry, not a claim that the app is rendering a photograph of a particular train.

The enclosure casts real cached contact shadows onto the wall. Material grain is a
deterministic small roughness/bump texture, and a physical clear-coated cover-glass
mesh sits above the active image. Internal brightness, bloom and wall spill are
restrained for a lit train interior; a mild ceiling-light reflection stays below the
contrast needed to read the live data. Shadow maps refresh on geometry/size and pose changes,
while screen emission follows the existing on-demand playback render loop.

[`installed-display-1440.png`](installed-display-1440.png) is a direct screenshot of
the full train-wall workspace beneath the header, including its control overlay.
The full-page captures also show the sole pinned site navigation.

## Neutral pose and pressure parallax

The wall and display rest perfectly straight. Mouse displacement from the workspace
center drives a bounded, quadratic, exponentially damped lean (maximum pitch .035 rad,
yaw .055 rad and coupled roll .004 rad). [`parallax-right-1440.png`](parallax-right-1440.png)
and [`parallax-left-1440.png`](parallax-left-1440.png) show the edge-pressure states.
The stainless rail and its fixings are a separate foreground geometry layer, moving
at 24% of the background's angles. Center, pointer leave and window blur reset the
pose; touch and reduced-motion mode keep a neutral scene.

The orthographic screen projection is exported as a live affine transform; the
HTML/SVG annotation surface applies that exact transform, including the close-up.
Projection tests compare real mesh vertices with the transformed HUD on desktop and
mobile, verify independent railing motion, neutral settling and full-height wall coverage.

The train backdrop fills the entire Player viewport beneath the shared top bar and
stage rail. It remains sticky behind vertically scrolling mobile content. The device
retains its original upper display region, while the wall and railings continue
behind telemetry and transport. A dark, backdrop-blurred control dock feathers to
transparent over 64px above the controls; its mask is shared with the blur so there
is no hard upper edge. Native-size controls stay stationary and usable.

Pointer-only frames reuse the unchanged LiDAR and emission textures. The existing
engine draws the physical scene until it settles; selection/error states use a
bounded on-demand renderer for the same wall. There is no permanent hover animation
loop or pointer-driven API/data update.

## Emission and pixel optics

[`screenEffects.ts`](../../../webapp/frontend/src/player/screenEffects.ts) adds a
fine RGB aperture, local highlight bloom, and light spill driven by the current
image. The source texture remains continuously sampled. Two small GPU filter passes
extract/diffuse the live image into an emission map used by the screen, glass and
surrounding light pool. Hue-preserving compression prevents a bright channel from
turning a green or blue source into the same color. No runtime pixel readback or
extra animation loop is required; the existing engine still renders on demand.

An isolated browser check filled the real display target with black/red/green/blue
frames and verified distinct matching emission colors, matching colored light on the
wall 3–18px outside the projected hardware relative to its unlit frame, and an aperture pattern on a uniform gray
source. Results are in `optics-verification.json`; diagnostic input colors are test
patterns, not screenshots of application data.

The shared palette now uses more saturated metro red, emerald, amber and violet.
Player camera/speed selection and primary transport use the brand accent, while
compact rounded-square tools and single-level telemetry keep the application hierarchy.

The shared AppShell supplies the sole header and stage navigation. The Player has no
local logo, duplicate title, stage strip or back-navigation bar. Normal responsive
page layout owns the display, compact scenario/camera/status controls, five telemetry
panels and timeline/transport. The Player uses a full-bleed train background; other
application sections retain their shared page ground. There is
no fixed 1600×900 composition or whole-page scaling.

ResizeObserver updates the canvas, offscreen target, camera aspect, annotation surface,
close-up and track map. Projection tests compare the actual screen mesh's projected
UV coordinates with HUD pixel bounds, and verify disposal of replaced GPU resources.
Browser tests cover playback, seeking, event stepping, speed, run switching, orbit,
fullscreen/fallback, loading, backend failures, FAULT and lost-context recovery.

The primary desktop sizes keep the complete workspace and transport in view. Narrow
layouts flow vertically with native-size controls and accessible scrolling panels.
Earlier Player galleries document previous revisions; this directory is the current
integrated layout.
