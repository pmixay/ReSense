# Player as the driver's cab

The user asked (21.10) for the Player to stop being a screen on a saloon wall and become a
metro driver's cab, entered by walking into it: no door animation, you turn right, walk to
the driver's cab, its door opens, you enter, sit down (the view goes low), and the screens
then turn on Iron Man-style with a short initialization. A first spaceship styling was
corrected the same day: a cab close to a real train, in the site's general style, with more
detail. The cab follows Moskva-2020 cues (light-grey moulded trim, a black-bonded windshield
with its frit band, pillar camera monitors, vent grilles, a sun-visor housing, an overhead
switch panel and a graphite desk with displays, manometers, push buttons and the driver's
controller); the saloon of the walk uses the earlier saloon photographs' cues.

## Captures

Headless Chromium 1194 with SwiftShader (software WebGL), DPR 1, on the Vite dev server of
this checkout with a local backend and synthetic demo runs (`demo_approach` and
`demo_crossing` of 8 s, a `demo_approach` of 15 s for the README picture). UI demonstrations,
not detector evaluation evidence; the cab's instrument faces are decorative.

- `cab-{1280,1366,1440,1920}.jpg`: the Player on `demo_approach` at frame 30, at 1280×720,
  1366×768, 1440×900 and 1920×1080 (reduced motion: no boot, eye at rest).
- `picker-1440.jpg`: the run picker in the cab (no live picture).
- `walk-{0-page,1-turn,2-aisle,3-door,4-cab,5-seated}.jpg`: the walk into the Player from
  Прогоны (clicking a run's play link) at 1440×900, rendered frame by frame on Playwright's
  controlled clock (`page.clock`, 40 ms steps) with CSS animations pinned to the same clock: the
  first frame (the leaving page), the right turn, the aisle, through the open cab door, the cab
  with the seat, and the seated view with the instruments still dark.
- `boot-{1-init,2-scan,3-ready,4-playing}.jpg`: the Player's boot after the walk: brackets,
  reticle and the initialization log over the dark windshield; the scan line revealing the
  picture; «Система готова»; playback started after the boot.

The same frames at 25 frames per second were assembled into an 8.4 s review video that was sent
to the user and never committed; no capture script for it exists in the repository. How to
regenerate it: [`docs/evidence/webapp_cab_finish_2026-10-22/README.md`](../../evidence/webapp_cab_finish_2026-10-22/README.md#regenerating-the-review-video).

Checked: the first walk frame's leaving-page plane spans the viewport within 1.5 px at
1440×900 and 1280×720 (browser test), and a pixel diff against the page before the click
differs only in the fake clock's relative date text and single-glyph antialiasing.
