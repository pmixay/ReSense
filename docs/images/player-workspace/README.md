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

The shared AppShell supplies the sole header and stage navigation. The Player has no
local logo, duplicate title, stage strip or back-navigation bar. Normal responsive
page layout owns the display, compact scenario/camera/status controls, five telemetry
panels and timeline/transport. Background comes from the application shell. There is
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
