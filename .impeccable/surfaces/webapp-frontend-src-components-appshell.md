---
version: 1
slug: "webapp-frontend-src-components-appshell"
primary_target: "webapp/frontend/src/components/AppShell"
related_targets: ["webapp/frontend/src/App.tsx"]
---

# Section navigation doors

Mode: Operate. Retain the shared metro navigation and native page behavior.

USER-PINNED MOMENT: A pair of dimensional Moscow-2020 sliding train doors closes
over the departing page, hides the route swap behind matte frosted glass, then
opens over the destination. Use uploaded `docs/images/references/IMG_8349.jpeg` and `docs/images/references/IMG_8350.jpeg` for
the black enamel leaves, tall rounded glazing, bronze/metal surrounds and seals.
Frost is explicitly requested even though the reference train has clear glass.

CONTINUITY: Block cross-section navigation until leaves are shut. Keep initial
loads and same-section URL edits immediate. Preserve mouse/touch, keyboard,
Back/Forward and fullscreen. A reduced-motion fade replaces spatial movement.

BUDGET: CSS transform animation and two bounded backdrop-filter panes, mounted
once in AppShell and fully hidden at rest. No third WebGL scene or new dependency.
Glass has an opaque-tint fallback. Native input stays inert only during the cycle,
and main regains focus afterward. Bound suspension/recovery delays.

PERFORMANCE CORRECTION: Target a smooth 60Hz closed-door slide. Preserve all
animation phases, tab order/direction, durations/easing, endpoint crossfades,
alignment/recovery and door geometry. Cache the existing glass diffusion/color
optics in bounded travel bitmaps, including the endpoints; use the live panes
for closing, waiting, opening and failed-raster fallback. Keep the slide to
composited transform/opacity with no per-frame backdrop filtering or live DOM.
