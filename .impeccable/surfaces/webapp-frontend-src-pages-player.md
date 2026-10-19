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

FIRST VIEWPORT: Full-width visualization first; a compact scenario/camera/status row below; five aligned telemetry panels; a timeline and playback row. The display renderer and HUD resize together through ResizeObserver. Continuous page background; no player logo, duplicated stage rail or artificial outer frame.

FORM: Brief-pinned engineering workspace; seed: none (user-pinned). Model materials and rounded housing follow the uploaded photograph; the live viewport adapts to available workspace dimensions.

DISPLAY OPTICS: The user requests a slight physical tilt, visible housing depth, image-driven light emission and individual RGB pixel structure. The HUD follows the projected active surface exactly. GPU-only light diffusion samples the live image, remains still when playback/camera are still, and keeps source point sampling continuous. Modernize the surrounding controls and telemetry through the shared radius/type system and stronger, contrast-checked brand and signal colors. Keep the single application shell and full Player functionality.

TRAIN INSTALLATION: The display must be installed in a believable metro saloon wall. Model a wall aperture, recessed gasket, industrial metal housing, laminate panel joints, door/window reveal, stainless grab rail, overhead linear lighting and ventilation details. Match the enclosure and wall angle, use real contact shadows, restrained content-driven spill and mild cover-glass reflections. The train context fills the Player beneath the pinned application chrome; below-display controls remain native application UI over a feathered dock.

POINTER PRESSURE: The scene rests exactly straight. Mouse displacement from the workspace center produces a bounded, damped lean in the pressed direction; foreground railings are independent geometry and move at 24% of the wall/display angle. Reset on leave/blur and honor reduced motion and touch. Reuse the existing render loop, cache unchanged LiDAR/emission during pointer-only motion, and stop rendering when settled. Extend the train wall edge-to-edge beneath the sole pinned application chrome, including behind native-size controls. A dark backdrop-filter layer under the controls fades and feathers toward the top; ordinary panels, controls and timeline remain legible and scrollable.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

Verify 1366×768, 1440×900, 1920×1080 and mobile, all decision/error states, resize, orbit, run switching, fullscreen, speed, stepping and seeking. Preserve the established global design system; document the page architecture without replacing global design artifacts.
