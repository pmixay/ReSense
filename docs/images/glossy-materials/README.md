# Glossy materials and frameless door transitions

> **Superseded (22.10):** the saloon-wall interior shown here was replaced by the driver's cab on 21.10; current captures: [`../player-cab/`](../player-cab/README.md).

Historical material pass. The latest interior/button correction is documented in
[`../interior-restored/`](../interior-restored/).
The current reference-led translucent door sequence is in
[`../moskva-doors/`](../moskva-doors/).

This gallery supersedes the earlier metro-2020 material captures. It preserves
the existing desktop composition, display/door/rail anchors and application flows.

## Material direction

- Clear-coated warm off-white formed panels and brushed aluminium trim.
- Polished bronze railings with actual saloon-light reflections.
- Glossy graphite enamel, layered rubber seals and reflective safety glazing.
- Matte woven taupe seats to keep the finishes physically distinct.
- Full-height navigation leaves, recessed grips and brushed kick plates. The user's
  screen is the frame: no stationary header, jambs or sill.
- A rounded outside-camera carriage with individual windows and sliding doors,
  cab glazing, LED lights, wipers, roof equipment, bogies and wheels.

The uploaded photographs remain material references; no reference photograph is
used as a background or substituted for the rendered application.

## Screenshot provenance

`capture.json` records the frontend source fingerprint, capture time, route, demo
frame, viewport and actual display/playback bounds. Application screenshots come
from the production build served by Vite preview at `http://127.0.0.1:4175`, using
the live local API and headless Chromium/SwiftShader, DPR 1.

- `stop-{1280,1366,1440,1920}.png`: 1280×720, 1366×768, 1440×900 and 1920×1080.
- `clear-1440.png`, `caution-1440.png`, `stop-1440.png`: all three decision states,
  from existing synthetic demonstration runs. These are UI examples, not detector
  evaluation evidence.
- `telemetry-1440.png`: actual opt-in side panels above the persistent controls.
- `chase-1440.png`: the carriage in the existing outside-camera framing.
- `upload-1440.png`: shared chrome and glossy control/surface treatment.
- `keyboard-focus-1440.png`: final production-build keyboard-ring check at
  `http://127.0.0.1:4176`; `focus-verification.json` records computed focus styles
  after the material pass's explicit focus-ring refinement.
- `doors-{closing,closed,opening}-1440.png`: the real route transition from Runs to
  Upload. Browser time and native CSS animations are held at 180ms into closing,
  the covered route-commit phase and 225ms into opening for repeatable inspection.
- `carriage-inspection-1440.png`: **diagnostic perspective inspection**, rendering
  the actual `TrainModel` module in isolation through the development server. This
  exposes details outside the default LiDAR camera crop; it is not an application
  screenshot or a new camera preset. No image compositing is used.

Application captures use reduced-motion pressure to keep the train exactly neutral.
Door captures enable the authored spatial transition. `material-verification.json`
records actual GPU black/RGB/split-source lighting, renderer-state restoration,
cached neutral return, resize/disposal checks and rendered frosted-glass diffusion.
The physical diagnostic uses 78 draw calls and 41,606 triangles at 1280×800.
Five resizes keep 80 geometries and nine textures stable; disposal leaves only the
diagnostic quad and its texture. Frost attenuates the test checkerboard contrast
by 99.08%. These are bounded-render checks, not hardware-specific FPS measurements.

## Review

Check the full-height door coverage and clean window corners, consistent moving
leaf details, readable controls/telemetry at native size, visible material contrast,
and no page overflow at any of the four desktop sizes. Navigation tests cover
history, focus restoration and reduced motion. Player tests cover playback,
seeking, run/camera switching, orbit, fullscreen, resizing and error recovery.
