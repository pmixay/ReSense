# Restored interior and softer buttons

> **Superseded (22.10):** this gallery shows the saloon-wall display that the driver's cab replaced on 21.10; the current Player is documented in [`../player-cab/`](../player-cab/README.md). `trainInterior.ts` (removed in `7017a02`) no longer exists; the captures and `capture.json` stay as a historical record. See [`capture.note.md`](capture.note.md).

The user's follow-up restores the train interior from before the glossy pass and
reduces button highlight/shadow strength. `trainInterior.ts` (since removed) and `screenDisplay.ts`
match `af2ecd8^` exactly, including original geometry, material finishes, screen
housing, ceiling lights and saloon reflections.

Button sheen peaks at 5.5% white instead of 18%; light edges are 16% instead of
55%. Primary red shadows are reduced from 45% to 16%, with quieter icon, segmented
and speed controls. Keyboard focus keeps its original full white/ink ring.

## Captures

Real production-build screenshots from Chromium/SwiftShader, DPR 1, served at
`http://127.0.0.1:4177` with the existing live local API. `capture.json` records the
source fingerprint, routes, synthetic demonstration frames, viewport sizes,
display/playback bounds and computed control styles.

- `stop-{1280,1366,1440,1920}.png`: the single desktop layout at 1280×720,
  1366×768, 1440×900 and 1920×1080.
- `clear-1440.png`, `caution-1440.png`: the other decision states.
- `upload-1440.png`: shared controls in their normal page setting.

These are UI demonstrations, not detector evaluation evidence. Captures use
reduced motion for an exactly neutral scene. The production build and 19 targeted
projection, geometry/resource, render-budget, door-routing and telemetry tests
pass. Browser checks cover viewport fit, native-size controls, keyboard focus and
frame stepping; the interior restoration is also checked against Git source bytes.
