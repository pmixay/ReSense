# Integrated Player workspace

Latest material/seating and section-door review:
[`../metro-2020/`](../metro-2020/), based on the newly uploaded photographs in
`7e38c01`. That gallery supersedes these earlier captures for interior material
appearance while retaining the same display, door, rail and control layout.

Real production-build captures from the ReSense backend and Chromium with SwiftShader
WebGL. `clear-*`, `caution-*`, `stop-*` and `picker-*` cover 1366×768, 1440×900,
1920×1080. `capture.json` records the synthetic demo runs, exact frame
positions and measured workspace/display/transport bounds. These are UI demonstration
data from six-second approach/crossing runs, not detector evaluation evidence.

## Reference and implementation

The user supplied [`images (1).jpg`](../references/images%20%281%29.jpg) in commit `5118a17`:
a shallow display with rounded black glass, thin silver housing and recessed active
surface. [`screenDisplay.ts`](../../../webapp/frontend/src/player/screenDisplay.ts)
builds that form as actual extruded Three.js meshes with beveled edges and lit metal
and glass materials. Its active surface samples the live LiDAR render target.
The housing adapts parametrically to the workspace's aspect ratio; it is a
reference-based reconstruction rather than a photographic asset or a dimensional
scan. No reference-image pixels are used as the player UI.

## Moscow-2020-inspired train installation

The current display is mounted in a modeled metro interior. [`trainInterior.ts`](../../../webapp/frontend/src/player/trainInterior.ts)
builds a formed laminate wall with an actual opening, recessed rubber mounting gasket,
vertical/service-panel joints, flush fasteners and a curved warm-metal foreground handrail.
The door has beveled aluminium reveals, rubber seals, black glass with ceiling reflections,
a recessed red status diffuser and local spill, an emergency-release rosette, and illuminated
charging sockets when there is sufficient room. Both fittings share the pillar centerline;
the paired charging indicators are centered on their plate. Horizontal wall seams and dado
terminate before the door. The artificial roof/vent/light bands have been removed from
this close wall crop, while off-camera ceiling lighting and saloon reflections remain.
The wall and housing share
the same angle; there is no floating monitor on an abstract backdrop. The reference
photo informs the installation and materials; the environment is reconstructed 3D
geometry, not a claim that the app is rendering a photograph of a particular train.

The cool-gray paneling, black display surround, copper-toned rails and red door-edge
lighting follow the inspected [Moskva-2020 saloon](https://commons.wikimedia.org/wiki/File:Москва-2020,_салон.jpg)
and [touchscreen installation](https://commons.wikimedia.org/wiki/File:Москва-2020,_салон_-_сенсорный_дисплей.jpg)
reference photographs. They are reference-only; no photograph is shipped as the background.

The enclosure uses analytic, antialiased rounded contact shading on the wall, replacing
the earlier dynamic shadow map. It has a smooth penumbra at any render resolution
and adds no shadow-map pass during pointer motion. Material grain is a
deterministic small roughness/bump texture, and a physical clear-coated cover-glass
mesh sits above the active image. Internal brightness, bloom and wall spill are
restrained for a lit train interior. Neutral overhead area/key light, warm cove fill,
lower hemispheric bounce and a cached procedural saloon reflection environment give
metalwork broad luminaire reflections. A mild ceiling-light reflection stays below the
contrast needed to read the live data. Screen emission follows the existing on-demand playback render loop.

[`installed-display-1440.png`](installed-display-1440.png) is a direct screenshot of
the visible train-wall viewport beneath the header, including its control overlay.
The full-page captures also show the sole pinned site navigation.

## Neutral pose and pressure parallax

The wall and display rest perfectly straight. Mouse displacement from the workspace
center drives a bounded, quadratic, exponentially damped lean (maximum pitch .035 rad,
yaw .055 rad and coupled roll .004 rad). [`parallax-right-1440.png`](parallax-right-1440.png)
and [`parallax-left-1440.png`](parallax-left-1440.png) show the edge-pressure states.
The handrail and its collars are a separate foreground geometry layer, moving
at 24% of the background's angles. They sit at least .5 scene units ahead of all
wall/housing geometry throughout the nine pressure extremes checked by the model tests.
Collars now sit on and align with the curved centerline instead of using guessed positions.
Additional raycast tests check the active surface against the interior at 45 combinations
of viewport/height and pressure. Tests also verify socket/pillar alignment and trim/door clearance.
The near handrail is now rendered sharply in the main physical scene, with the
dedicated blur target and composite pass removed. Center, pointer leave and window blur reset the
pose; touch and reduced-motion mode keep a neutral scene.

The orthographic screen projection is exported as a live affine transform; the
HTML/SVG annotation surface applies that exact transform, including the close-up.
Projection tests compare real mesh vertices with the transformed HUD on desktop and
verify independent railing motion, neutral settling and full-height wall coverage.

The train backdrop, physical display and native HUD stay fixed in the viewport beneath
the shared navigation. Playback, seeking, speed, loop, scenario, camera and fullscreen
controls are pinned at the bottom and always remain visible. A measured responsive dock
height reserves the live screen's space. Tapping the «Телеметрия» button opens compact
left/right columns: map/decision on the left, distance/timing/health on the right. Each
side scrolls independently; wheel/trackpad and swipes never toggle it. The central 40%
remains clear, with bounded column height preserving most of the live display. Opening
never moves the scene or transport. `telemetry-open-1440.png` captures the open state.
A short feathered backdrop blur and clear-to-dark tint keep controls readable.

Pointer-only frames reuse the unchanged LiDAR and emission textures. The existing
engine draws the physical scene until it settles; selection/error states use a
bounded on-demand renderer for the same wall. There is no permanent hover animation
loop or pointer-driven API/data update.

## Emission and pixel optics

[`screenEffects.ts`](../../../webapp/frontend/src/player/screenEffects.ts) adds a
fine RGB aperture, local highlight bloom, and light spill driven by the current
image. The source texture remains continuously sampled. Two small GPU filter passes
extract/diffuse the live image into an emission map used by the screen, glass and
surrounding light pool. `screenLighting.ts` adds a five-sample GPU area-light approximation
to wall, trim, enclosure and handrail materials. Light is evaluated in display coordinates,
so it remains attached while the rail moves independently. A black source emits no light.
Hue-preserving compression prevents a bright channel from
turning a green or blue source into the same color. No runtime pixel readback or
extra animation loop is required; the existing engine still renders on demand.

The current isolated browser check fills the real display target with black/red/green/blue,
gray and split-red/blue frames. It verifies source-colored emission on both wall and rail,
local hue on opposite sides of the split image, and pixel-identical cached neutral rendering
after pressure motion. Five resize cycles keep GPU texture/geometry counts constant;
disposal returns to only the diagnostic quad and shared renderer lookup textures.
Results are in `interior-lighting-verification.json`.
The earlier `optics-verification.json` retains historical aperture/edge-spill evidence.
Diagnostic input colors are test patterns, not screenshots of application data.

The shared palette now uses more saturated metro red, emerald, amber and violet.
Player camera/speed selection and primary transport use the brand accent, while
compact rounded-square tools and single-level telemetry keep the application hierarchy.

On Player, the destinations use the same red metro-line rail and station-ring styling as Upload.
The grouped Data/Analysis/System header is not mounted, and other application routes
retain their existing navigation. The Player has no
local logo, duplicate title, stage strip or back-navigation bar. Normal responsive
page layout owns the display, compact scenario/camera/status controls, five telemetry
panels and timeline/transport. The Player uses a full-bleed train background; other
application sections retain their shared page ground. There is
no fixed 1600×900 composition or whole-page scaling.

The display fills the space above the measured dock without reducing width. The height
toggle adds 36px while the canvas and bottom controls remain fixed; the live face uses
tighter physical margins. [`taller-display-1440.png`](taller-display-1440.png) captures
that mode. ResizeObserver resizes the actual live surface when toggled. Raleway remains
the application font: Esh/Struve test screenshots were deferred by the user.

## Rendering budget

The physical canvas is capped at 1.5× device scale and approximately 2.6 million
pixels; constrained devices are capped at 1×. DOM controls and annotations retain
their native resolution. Handrails render directly, avoiding a separate blur target
and composite pass. Dynamic shadow maps are disabled. The reflection probe is generated
once per renderer and cached. `interior-lighting-verification.json` records the current
draw/triangle counts and GPU resource lifetime. The pixel budget applies to the fixed
viewport canvas. This bounds the
added effects; it is not a hardware-specific FPS guarantee.

ResizeObserver updates the canvas, offscreen target, camera aspect, annotation surface,
close-up and track map. Projection tests compare the actual screen mesh's projected
UV coordinates with HUD pixel bounds, and verify disposal of replaced GPU resources.
Browser tests cover playback, seeking, event stepping, speed, run switching, orbit,
fullscreen/fallback, loading, backend failures, FAULT and lost-context recovery.

The display and transport fit the first viewport; telemetry is opt-in and overlays the
fixed scene. Alignment checks cover the supported desktop sizes. Controls retain native sizing.
Earlier Player galleries document previous revisions; this directory is the current
integrated layout.
