# Button-toggled side telemetry review

Disposition: **ship**

## Persistence

`PRODUCT.md`, `DESIGN.md`, the Player surface brief and design sidecar describe the
current fixed installation, persistent bottom transport and button-toggled side telemetry.
PNG provenance is embedded. `capture.json` contains the three desktop viewport
sizes and no page errors. This is a code-led refinement of the existing installation.

## Fidelity

| Element | Result | Evidence |
| --- | --- | --- |
| Typography / shared shell | Match | Native Raleway, shared metro station rail, no grouped Player header |
| Materials | Match | Modeled laminate, clear cover glass, polished copper-toned rail, aluminium and black rubber/glazing |
| Ground / lighting | Adaptation | Neutral broad ceiling lighting, warm cove, red door diffuser and cached saloon reflections follow the supplied saloon/touchscreen photos |
| Interior fittings | Match | Charging indicators and release centered on the pillar; wall trim ends before the door; artificial roof/vent/light bands removed |
| Screen size | Match | Fills space above measured bottom dock; height toggle adds 36px at unchanged width, remaining inside the viewport canvas |
| Image-derived light | Match | Real black/RGB/split-color GPU diagnostic verifies wall and handrail hue, local split response and exact cached neutral return |
| Side telemetry | Match | Button opens map/decision left and distance/timing/health right; independent internal scrolling, no wheel/swipe toggle |
| Screen visibility | Match | The central 40% stays clear on desktop; bounded side height preserves most of the image |
| Scroll / projection | Match | Physical screen/HUD and playback bounds remain identical when panels open; button has native Enter/Space support and Escape restores focus |
| Persistent controls | Match | Playback, seek, scenario, camera, speed and loop remain visible at the supported desktop sizes |
| Type variants | Deferred | User explicitly said not to use Esh/Struve for now; Raleway retained |
| Parallax / geometry | Match | Neutral rest, 24% rail motion, active-surface and foreground-clearance checks at nine pressure poses across desktop viewport/height combinations |

The wide responsive screen is an intentional adaptation of the supplied display
reference. The scene remains a close front-on installation rather than an aisle-wide
reproduction of the train photograph. The supplied photos guide materials and fittings;
they are not dimensional scans and no photograph pixels replace the live player.

## Ceiling

Broad reflected luminaires restore the metal hierarchy; actual formed/extruded parts
and a curved rail carry detail without obscuring the engineering visualization.
Emission uses two bounded filters and receiver lighting uses five texture samples.
No artificial ceiling geometry, dynamic shadow maps or runtime pixel readback.

## Material fixes

Clear. Replaced gesture/range reveal and full-width bottom telemetry with a shared
tap-to-toggle button and left/right side columns. Native-size telemetry avoids
collisions. Open panels leave the live scene fixed and
preserve a clear image center. Bottom transport/settings never move.

## Verification / keep

- Production TypeScript/Vite build passes.
- 339 frontend tests pass, including button state, Escape/focus, ignored wheel/swipe
  input and geometry tests.
- Focused browser checks cover side placement, center clearance, button/keyboard
  operation, fixed scene/transport, resize, telemetry content and height switching.
- Desktop 1366×768, 1440×900 and 1920×1080 captures reviewed,
  including expanded and pressure states.
- `interior-lighting-verification.json` records actual GPU receiver colors, stable
  geometry/texture counts across five resize cycles and resource disposal.
- Mechanical design scan has no findings; source diff has no whitespace errors.

Keep the sharp live image, native-size stationary controls, neutral resting scene,
reference-led lighting and bounded on-demand rendering. No hardware-specific low-end
FPS or universal defect-free guarantee is inferred from these checks.
