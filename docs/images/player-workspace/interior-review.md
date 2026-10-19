# Fixed-scene Player and door-alignment review

Disposition: **ship**

## Persistence

`PRODUCT.md`, `DESIGN.md`, the Player surface brief and design sidecar describe the
current fixed installation, persistent bottom transport and gesture-revealed telemetry.
PNG provenance is embedded. `capture.json` contains all four requested viewport
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
| Scroll / projection | Match | Wheel, trackpad, reveal slider and touch expose telemetry; physical screen/HUD and playback bounds remain identical |
| Persistent controls | Match | Playback, seek, scenario, camera, speed and loop remain visible; no overlapping or offscreen control rectangles at seven sizes including 320px and landscape |
| Type variants | Deferred | User explicitly said not to use Esh/Struve for now; Raleway retained |
| Parallax / geometry | Match | Neutral rest, 24% rail motion, active-surface and foreground-clearance checks at nine pressure poses across five viewport/height combinations |

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

Clear. Fixed during this pass: off-center charging fittings, invented ceiling bands,
wall seams crossing the door, playback/settings scrolling out of view, scene/HUD
moving with information, phone camera labels crowding fullscreen, and picker actions
overlapping its scrollable list. The reveal tray alone scrolls; transport never moves.

## Verification / keep

- Production TypeScript/Vite build passes.
- 339 frontend tests pass, including reveal-wheel/range/touch and geometry tests.
- 18 Player/navigation scenarios pass in the full browser suite; the new gesture
  scenario and picker regression pass in the focused post-fix run (19 distinct cases).
- Desktop 1366×768, 1440×900, 1920×1080 and mobile 390×844 captures reviewed,
  including expanded and pressure states.
- `interior-lighting-verification.json` records actual GPU receiver colors, stable
  geometry/texture counts across five resize cycles and resource disposal.
- Mechanical design scan has no findings; source diff has no whitespace errors.

Keep the sharp live image, native-size stationary controls, neutral resting scene,
reference-led lighting and bounded on-demand rendering. No hardware-specific low-end
FPS or universal defect-free guarantee is inferred from these checks.
