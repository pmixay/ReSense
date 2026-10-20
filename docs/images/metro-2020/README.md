# Photo-led Moscow-2020 interior and door transitions

## References

The user supplied these photographs in main commit `7e38c01`:

- [`IMG_8349.jpeg`](../references/IMG_8349.jpeg): frontal doorway, black glazed leaves,
  formed off-white pillars, bronze handrails, gray individual bench seats.
- [`IMG_8350.jpeg`](../references/IMG_8350.jpeg): perspective saloon view, taupe woven
  upholstery, cantilevered shells, curved bronze bench-end armrests.
- [`1591221.jpeg`](../references/1591221.jpeg): exterior door proportions, dark framing,
  red door-edge illumination and brushed threshold.

The photographs guide modeled materials and geometry; their pixels do not ship as
the scene. Frosted navigation glass is explicitly requested by the user, unlike the
clear glazing in the train photographs. Screen, door and original foreground rail
anchors remain those of `4961e48`; exact source comparison and projection/clearance
tests verify the lock.

## Captures

`interior-{1366,1440,1920}.png` are native production-build screenshots from
Chromium/SwiftShader at `http://127.0.0.1:8000`, with neutral/reduced-motion pressure.
They retain the real dock and all controls. `capture.json` records route, synthetic
demonstration frame, viewport and measured display/transport bounds. The upper
bench is visible beneath the display; lower cushions sit behind the pinned dock.

`bench-inspection-1440.png` is a **diagnostic inspection view**, with only the dock's
visibility temporarily disabled. It exposes the modeled upholstery, cushions,
cantilever shells and bronze end armrests; it is not the default application state.

`doors-{closing,closed,opening}-1440.png` capture actual CSS door geometry
from the production build in Vite preview at `http://127.0.0.1:4173`.
The route goes from `/runs` to `/upload`. Browser time is held and native animation
interpolation is paused at 180ms into closing / 225ms into opening for repeatable
motion review. The closed capture occurs after the route commits, before revealing
the destination. These are runtime screenshots, not generated pictures or photo
composites.

## Implementation and verification

- `src/player/trainInterior.ts`: refined PBR materials, unchanged main anchors,
  two extra fixed-door trim details, individual piped backrests, contoured cushions,
  shells and end armrests. Shared procedural upholstery texture; explicit disposal.
- `src/components/AppShell/TrainDoors.tsx` and its CSS: paired dimensional leaves,
  close/covered/open routing phases, inert input, main focus restoration, bounded
  lazy-chunk wait/recovery and reduced-motion fade. Two frosted backdrop panes only
  during navigation; fully hidden at rest.
- Unit tests verify route timing, history, immediate within-Player URL edits,
  reduced motion, suspended chunks, anchor/seat clearance and resource lifetime.
- Browser scenarios cover pinned navigation, desktop door coverage, history,
  input/focus restoration, reduced motion, fullscreen/orbit, responsive layout and
  fixed-scene side telemetry.
- [`../player-workspace/interior-lighting-verification.json`](../player-workspace/interior-lighting-verification.json)
  is refreshed from the actual GPU black/RGB/split-image test. Source hue, black
  baseline, cached neutral return, stable resize resource counts and disposal pass.
  The 1200×800 diagnostic uses 75 draw calls and 21,562 triangles. Physical-render
  resolution bounds remain unchanged; no hardware-specific FPS claim is made.
- `frost-verification.json` checks actual rendered glass against uniform black/white
  backings and a 32px checkerboard. Removing frost/filter is the positive control:
  neighbor contrast is 121.60 unfiltered versus 0.92 through the pane (99.25%
  attenuation). This verifies optical diffusion, rather than just a computed CSS
  blur property. Flattened pane composition avoids Chromium's `preserve-3d`
  backdrop-filter suppression; perspective leaf motion and depth details remain.
