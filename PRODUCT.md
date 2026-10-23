# ReSense product context

ReSense is a Russian-language engineering application for inspecting LiDAR obstacle
detection along a metro train's clearance envelope. This context records the existing
project README and the user's Player brief; it introduces no new product claims.

## Primary workflow

Upload a recording or generate a synthetic scenario, process it with the existing
detector, inspect a run frame by frame, compare results and monitor telemetry.
Engineers use the Player to understand the point cloud, envelope, detected objects,
decision and distance at a selected moment, then seek, step events or replay it.

## Application commitments

- One shared ReSense header and stage-based navigation across the application.
- Existing Raleway typography, metro-red branding and explicit GO/CAUTION/STOP/FAULT semantics.
- Readable application controls and telemetry at native CSS sizes; responsive page flow.
- Russian UI copy and existing number/date/unit formatting.
- Preserve the detector, processing, data contracts, API behavior, playback clock and URL semantics.

## About surface

«О системе» is a reading surface: a concise description, a compact text workflow
and readable meanings for all four decisions come first. Measurements/conditions,
ROS commands, web launch/server details and team responsibilities open in native
disclosures. Documentation links stay directly reachable. Use one flowing desktop
layout with wrapping text and main-page scrolling; avoid forced viewport-height
cards, clipped labels, decorative icon grids and nested panel scrolling.

## Player surface

The workspace presents the live 3D LiDAR view first, then compact scenario/camera
controls, system metrics and timeline/transport. Keep scenario switching, camera
presets and orbit/reset, seeking, speed, event stepping, looping, fullscreen,
keyboard operation and recovery from data/GPU failures.

The Player is the driver's cab of a metro train, seen from the seat (user brief of
21.10, replacing the earlier screen installed in a saloon wall). The live LiDAR view
is the windshield; around it a realistic cab in the application's general style,
not a spaceship: a black-bonded windshield with its frit band and light-grey
moulded trim, A-pillars with platform-camera monitors, vent grilles and grab
handles, side windows, a sun-visor housing, an overhead switch panel, and a
graphite desk with displays, manometers, push buttons, the driver's controller,
emergency stop and radio (Moskva-2020 cues). Instrument faces are decorative and
never show values that could be read as measurements. The cab fills the Player
workspace beneath the existing navigation without becoming a second app shell. Its
neutral pose is straight; mouse pressure leans the seated eye (head parallax),
while a feathered dark control dock preserves readability. The page must feel like
another ReSense stage, with no duplicate local logo, title, stage rail or
standalone player header. On Player the existing metro-line stage rail matches
Upload and is the only pinned navigation; grouped Data/Analysis/System chrome is
omitted to recover display height. A height control expands the live view at the
same width. Light from the windshield display falls on nearby cab surfaces.
Playback and demo-affecting controls stay visible at the bottom. Tapping
«Телеметрия» toggles compact left/right side panels; the central image stays clear.
Raleway remains in use.

Entering the Player from another section plays no doors: you turn right from the
page (it swings away like the view through the open side doors), walk the saloon
aisle to the cab, its door slides open, you step in and sit down (the view lowers),
landing exactly on the Player. Then the cab's screens power up Iron Man-style and a
short initialization lists the run's facts before playback starts. Any key or click
skips the walk; reduced motion keeps the short fade and skips the boot.

The latest user-supplied photographs (`IMG_8349.jpeg`, `IMG_8350.jpeg`, and
`1591221.jpeg`, main commit `7e38c01`) guide the saloon of that walk: warm bronze
metalwork, off-white molded paneling, layered black glazing surrounds and gray-taupe
woven cantilevered seating. Photos remain reference-only.

Changing application sections (except entering the Player, above) closes a paired, dimensional metro-door overlay,
then glides through the station order toward the selected tab. Targets to the left
enter from the left; targets to the right enter from the right. Every intervening
tab passes behind the glass in order, with stronger motion blur and one continuous
decelerating trajectory. Only the destination creates a browser-history entry.
The moving visuals are frozen before departure. Motion blur is baked into bounded
temporary bitmaps; a single compositor timeline moves the complete journey and
crossfades sharp endpoints. The doors reveal the page only after that animation
actually finishes, preventing slow-frame/timer races and mid-travel content shifts.
The strict rule is current tab → every intermediate tab in bar order → final tab,
in either direction. Movement derives from the final stage's actual geometry and
must leave it centered for two painted frames before reveal. Closing/opening are
260/320ms; travel is 410–1320ms. Dropdown pickers and native form affordances use
the shared type, colors and control shapes.
The leaves follow the supplied
Moskva-2020 photographs, with tall glazing, narrow black surrounds, center seals
and red edge LEDs. Glass is matte and blurred but transparent: broad page colors
and movement remain visible through the frost. Navigation
must remain reliable by mouse, touch, keyboard and browser history. Player frame,
camera and run URL changes remain immediate. Reduced motion uses a brief non-spatial
fade. The decorative doors contain no controls and release keyboard focus to the page.

Button highlights and shadows are restrained, with their light/edge opacity reduced by
roughly two thirds.
The outside-camera train is a rounded, detailed metro carriage. Navigation shows
only two full-height sliding leaves; the user's screen is the doorway frame, with
no added jambs, overhead header or threshold around the transition.

The interface is desktop-only with a minimum workspace width of 1280px. Build and
verify this single layout at 1280×720, 1366×768, 1440×900 and 1920×1080. Keep this
desktop-only scope for future changes, screenshots and documentation. Synthetic
capture runs demonstrate the UI and are not evaluation evidence.
