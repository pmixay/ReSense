---
version: 1
slug: "webapp-frontend-src-pages-player"
primary_target: "webapp/frontend/src/pages/Player"
related_targets: ["webapp/frontend/src/player/scene.ts"]
---

# Player workspace

Mode: Operate. Engineers inspect LiDAR recordings, decisions and telemetry, navigate events and compare camera views. Keep the existing playback engine, APIs, URL state, shared Raleway typography, metro-red navigation and signal semantics.

## Direction contract

THESIS: One ReSense workspace beneath the existing global navigation. Replace the scaled miniature cab and duplicate local navigation with normal responsive layout.

OWN-WORLD: Inherit the application's cool page ground, white telemetry surfaces, red actions and explicit decision colors. The display is an actual shallow Three.js model with rounded black glass and a thin silver housing, based on the supplied `images (1).jpg`.

STORY: Open a run, inspect the live point cloud on the modeled display, select another scenario/camera, read metrics, then seek or replay events. Every control stays readable at its native CSS size.

FIRST VIEWPORT: Fixed full-width visualization above persistent bottom scenario/camera and playback controls. Telemetry starts hidden; tapping its button opens left/right side columns while the image center remains clear. The renderer and HUD resize together through ResizeObserver without moving when telemetry opens. Continuous page background; no player logo, duplicated stage rail or artificial outer frame.

FORM: Brief-pinned engineering workspace; seed: none (user-pinned). Model materials and rounded housing follow the uploaded photograph; the live viewport adapts to available workspace dimensions.

DISPLAY OPTICS: The user requests a slight physical tilt, visible housing depth, image-driven light emission and individual RGB pixel structure. The HUD follows the projected active surface exactly. GPU-only light diffusion samples the live image, remains still when playback/camera are still, and keeps source point sampling continuous. Modernize the surrounding controls and telemetry through the shared radius/type system and stronger, contrast-checked brand and signal colors. Keep the single application shell and full Player functionality.

TRAIN INSTALLATION: The display must be installed in a believable metro saloon wall. Model a wall aperture, recessed gasket, industrial metal housing, laminate panel joints, door/window reveal, stainless grab rail, overhead linear lighting and ventilation details. Match the enclosure and wall angle, use real contact shadows, restrained content-driven spill and mild cover-glass reflections. The train context fills the Player beneath the pinned application chrome; below-display controls remain native application UI over a feathered dock.

POINTER PRESSURE: The scene rests exactly straight. Mouse displacement from the workspace center produces a bounded, damped lean in the pressed direction; foreground railings are independent geometry and move at 24% of the wall/display angle. Reset on leave/blur and honor reduced motion and touch. Reuse the existing render loop, cache unchanged LiDAR/emission during pointer-only motion, and stop rendering when settled. Extend the train wall edge-to-edge beneath the sole pinned application chrome, including behind native-size controls. A dark backdrop-filter layer under the controls fades and feathers toward the top; ordinary panels, controls and timeline remain legible and scrollable.

MOSKVA-2020 & PERFORMANCE: Use the inspected 81-775 saloon/touchscreen photos for cool-gray formed panels, black glass, warm metallic foreground posts and red door-edge lighting. Foreground rail geometry sits well in front of all wall/display geometry at every pressure extreme and now renders sharply, without a defocus target or composite pass. Keep antialiased analytic enclosure contact shading and a bounded physical-render pixel budget. Player uses the same metro-line station-rail styling as Upload, while Data/Analysis/System grouped navigation stays omitted. Keep the desktop display height and further height toggle preserving width, with controls reachable through native content scrolling.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

FIXED SCENE & BOTTOM CONTROLS (current user correction): Keep the screen, HUD and train interior fixed in the viewport during scrolling. Playback and all demo-affecting settings remain visible at the bottom at every supported width. Other information starts hidden in a lower overlay tray, revealed by wheel/trackpad, a native range slider or touch swipe; the tray alone scrolls. Preserve mouse orbit and existing pressure parallax. Center charging indicators on their pillar plate, terminate trim before the door, and remove artificial horizontal roof/vent/light bands above the screen. Retain off-camera ceiling lighting and content-derived emission. Esh/Struve screenshot variants are deferred at the user's request; keep Raleway.

SIDE TELEMETRY (latest correction, supersedes gesture reveal): Open/close telemetry only by tapping its button, with native keyboard support and Escape. Put map/decision left and distance/metrics/health right in compact independently scrollable side columns. Preserve the central 40% clear at all widths, keep most screen area visible, and leave the fixed scene and bottom controls unmoved. Wheel, trackpad and swipes must not toggle telemetry.

INTERIOR DETAIL & LIGHTING: Follow the supplied saloon/touchscreen references for formed gray panels, recessed seams, black door glazing/seals, red diffuser, release fitting, charging sockets and polished copper-toned handrail. Keep the front-on installation and shared shell. Off-camera neutral ceiling lighting, warm fill, cached saloon reflections and GPU image light illuminate wall, trim, housing and rail; black emits no light and split sources retain local hue. Remove invented roof bands from the wall crop. Fit the screen above persistent controls at unchanged width and keep scene/HUD fixed. Check geometry at pressure extremes, responsive sizes and expanded height, preserving playback/recovery paths.

DESKTOP ONLY: Use one layout with a 1280px minimum workspace width. Verify 1280×720, 1366×768, 1440×900 and 1920×1080, all decision/error states, resize, orbit, run switching, fullscreen, speed, stepping and seeking. Future work, captures and documentation must follow this desktop-only scope. Preserve the established global design system; document the page architecture without replacing global design artifacts.

LATEST PHOTO PASS: `IMG_8349.jpeg`, `IMG_8350.jpeg` and `1591221.jpeg` from main
`7e38c01` pin warm off-white laminate, bronze rails, black enamel/glazing and taupe
individual moquette seats. Keep display, original handrail path and door anchors
unchanged. Add a cantilevered bench beneath the housing, never over the active view.
Keep the independent pressure layers and bounded renderer. The upper dock feather
is light enough to read the bench backs while preserving white control text.

GLOSSY MATERIALS (current refinement): Keep the current desktop scene composition
and anchors. Use clear-coated warm neutral panels, brushed aluminium, polished
bronze, glossy graphite enamel and reflective safety glass, contrasted with matte
woven seats. Outside cameras use the detailed rounded metro carriage. Navigation
shows only two full-height sliding leaves: the screen is the frame, with no added
header, jambs or sill. Keep frosted panes, route timing, reduced-motion fade and
on-demand rendering. Material tone mapping must not alter LiDAR/data colors.

LATEST CORRECTION: Restore the pre-gloss Player interior and display implementation
from `af2ecd8^`, including materials, geometry, original saloon lighting and screen
housing/rendering. Reduce button sheen, light edges and shadows by roughly two
thirds, including camera/speed and transport controls. Full-strength keyboard focus
rings remain. Current captures are in `docs/images/interior-restored/`.

MOSKVA-2020 TRANSITIONS (latest): Reconstruct the paired navigation leaves from
the uploaded train photographs: tall glazing, slim black enamel surrounds, center
seals, red LEDs and a small bottom bead. The viewport remains the frame. Matte
glass must stay transparent, transmitting broad page colors/movement through
20px diffusion and a 26–32% tint. Close, move the current page/chrome right with
motion blur, commit offscreen, immediately arrive from the left, then open. Use
one live route, brief bounded CSS effects, safe lazy-chunk waits and native focus
release. Reduced motion keeps the short non-spatial fade. Latest transition
captures and optical/motion evidence are in `docs/images/moskva-doors/`.

DIRECTIONAL STATION TRAVEL (latest): Use one continuous, decelerating page strip
following the shared LINE/BRANCH order. Left targets enter from the left, right
targets from the right; include every intermediate section behind the glass.
Increase motion blur to 32px at speed and clear it at rest. Preserve the outgoing
DOM/canvas appearance during the final route handover. Intermediate sections are
inert memory-route previews sharing cached data, without global shortcuts,
preference writes or additional Player/Live WebGL scenes. Only the selected route
enters history. Clean up previews/snapshots, retain reduced-motion fade and native
focus release. Evidence: `docs/images/directional-travel/`.

JITTER FIX (current): Freeze outgoing, passing and destination visuals before
movement. Bake the strong 32px blur into transient 640×400-capped bitmaps; move one
strip and crossfade sharp endpoints on the same native compositor timeline. The
real destination stays hidden at its final geometry. Unmount preview roots before
travel so live data/loading/layout cannot change moving pixels. Open doors from
actual animation completion, with bounded preparation/recovery and resize/hidden
tab cleanup. Current evidence: `docs/images/travel-stability/`.

STRICT FINAL-STOP RULE (latest): Current → every intermediate station in the
visible LINE/BRANCH order → final, both directions. Use explicit stage positions
and the actual destination offset, near-linear cruising, and two painted aligned
destination frames before reveal. Recovery finishes the journey instead of dropping
its strip. Close/open are 260/320ms; travel is 280 + 130ms per interval. Native
dropdowns and form affordances match the shared tokens. Evidence:
`docs/images/d1-controls-journey/`.
