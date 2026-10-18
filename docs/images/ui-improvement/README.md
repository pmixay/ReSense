# Pinned navigation and dimensional 16:9 player

Captured on 2026-10-18 from the production build served by the real ReSense web
backend, using Chromium with SwiftShader WebGL. These are rendered UI screenshots,
not mockups. The API generated and processed six-second `approach` and `crossing`
demos with stored point clouds. `capture.json` records the local run IDs and frame
positions used for each decision state; those IDs are specific to the capture stand.

## Review

Each view was captured at 1920×1080, 1280×720, 820×1180 and 390×844:

- `overview-*`: Raleway, metro-red actions, cool neutral surfaces, responsive overview.
- `upload-*`: source selector, upload controls and processing options beneath pinned navigation.
- `about-*`: system category and its navigation branch; the processing diagram becomes vertical on phones.
- `picker-*`: run selection inside the borderless, rounded player window.
- `player-clear-*`, `player-caution-*`, `player-stop-*`: real GO, CAUTION and STOP frames.

The complete cab is uniformly scaled from 1600×900 to its available container. Its
WebGL canvas is rendered at 1600×600 with the corresponding camera aspect; the glass,
HUD, curved console, five instrument panels and scrubber share that coordinate
system. There is no oversized canvas hidden behind a shorter viewport. The window
is a rounded rectangle with straight edges and no bezel, outline or raised surround.
The existing steel backdrop, top controls and instrument perspective remain.

The top bar and category rail remain outside the scrolling content on every route,
including the player picker, loading/error states and both real/fallback fullscreen.
Browser checks cover all ten page categories at the four sizes; player tests also
cover 1440×900 and 1280×800, playback, seeking, camera orbit, error recovery and fullscreen.

`web/demo/capture_gallery.py` was also run against the legacy dashboard into a
temporary review directory for clear, caution, stop, plan and recorded-data states.

## External references

The two JPG filenames from the request were searched after a full remote fetch and
fast-forward pull, including available history/reflogs, deleted-branch objects,
detached trees, hidden workspace files and the nested style archive. Neither image
was available. The current dimensional ReSense cab was therefore the available
visual baseline; direct comparison to those external references is still pending
the actual files or a commit/link containing them.
