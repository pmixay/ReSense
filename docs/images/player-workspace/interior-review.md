# Moscow-2020 interior refinement review

Disposition: **ship**

## Persistence

`PRODUCT.md`, `DESIGN.md`, the Player surface brief and design sidecar describe the
current taller, natural-height installation and content-driven receiver lighting.
PNG provenance is embedded. `capture.json` contains all four requested viewport
sizes and no page errors. This is a code-led refinement of the existing installation.

## Fidelity

| Element | Result | Evidence |
| --- | --- | --- |
| Typography / shared shell | Match | Native Raleway, shared metro station rail, no grouped Player header |
| Materials | Match | Modeled laminate, clear cover glass, polished copper-toned rail, aluminium and black rubber/glazing |
| Ground / lighting | Adaptation | Neutral broad ceiling lighting, warm cove, red door diffuser and cached saloon reflections follow the supplied saloon/touchscreen photos |
| Interior fittings | Match | Formed seams, fasteners, ventilation fins, door release and paired lit charging sockets are visible in the desktop captures |
| Screen size | Match | 1368×688 default region at 1440×900; approximately 1368×922 expanded, unchanged width |
| Image-derived light | Match | Real black/RGB/split-color GPU diagnostic verifies wall and handrail hue, local split response and exact cached neutral return |
| Scroll / projection | Match | Canvas covers natural workspace height; native HUD and physical display scroll together; projection tests compare actual mesh vertices |
| Parallax / geometry | Match | Neutral rest, 24% rail motion, active-surface and foreground-clearance checks at nine pressure poses across five viewport/height combinations |

The wide responsive screen is an intentional adaptation of the supplied display
reference. The scene remains a close front-on installation rather than an aisle-wide
reproduction of the train photograph. The supplied photos guide materials and fittings;
they are not dimensional scans and no photograph pixels replace the live player.

## Ceiling

Broad reflected luminaires restore the metal hierarchy; actual formed/extruded parts
and a curved rail carry detail without obscuring the engineering visualization.
Vent fins use one instanced draw, emission uses two bounded filters and receiver
lighting uses five texture samples. No dynamic shadow maps or runtime pixel readback.

## Material fixes

Clear. Fixed during review: collars following the curved rail, socket plates hidden
behind the pillar, expanded hardware extending beyond a viewport-sized canvas,
HUD drift on scroll, slow-frame pressure settling, and cloud failures disappearing
when their request cooldown elapsed. Recovery checks wait for actual shader/API
readiness and retain injected failure until the retry action.

## Verification / keep

- Production TypeScript/Vite build passes.
- 338 frontend tests pass; final changed cache/engine/model checks pass (32 tests).
- 18 distinct Player/navigation browser scenarios pass across the initial suite and
  focused post-fix reruns; recovery's final run passes in 99 seconds.
- Desktop 1366×768, 1440×900, 1920×1080 and mobile 390×844 captures reviewed,
  including expanded and pressure states.
- `interior-lighting-verification.json` records actual GPU receiver colors, stable
  geometry/texture counts across five resize cycles and resource disposal.
- Mechanical design scan has no findings; source diff has no whitespace errors.

Keep the sharp live image, native-size stationary controls, neutral resting scene,
reference-led lighting and bounded on-demand rendering. No hardware-specific low-end
FPS or universal defect-free guarantee is inferred from these checks.
