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

## Player surface

The workspace presents the live 3D LiDAR view first, then compact scenario/camera
controls, system metrics and timeline/transport. Keep scenario switching, camera
presets and orbit/reset, seeking, speed, event stepping, looping, fullscreen,
keyboard operation and recovery from data/GPU failures.

The user-supplied `images (1).jpg` is the physical display reference: rounded black
glass, silver housing and shallow depth. The modeled display belongs to the primary
visualization, while surrounding controls inherit the application's shared design.
The display is installed into a believable modeled train wall, with restrained
internal illumination, cover-glass reflections and physical mounting details; the
environment fills the Player workspace beneath the existing navigation without becoming a
second app shell. Its neutral pose is straight; mouse pressure adds restrained parallax
with a slower railing layer, while a feathered dark control dock preserves readability.
The page must feel like another ReSense stage, with a continuous background and no
duplicate local logo, title, stage rail or standalone player header.
On Player the existing metro-line stage rail matches Upload and is the only pinned navigation; grouped
Data/Analysis/System chrome is omitted to recover display height. A height control
expands the live view at the same width. The interior follows inspected Moscow-2020
saloon material cues, with a sharp curved near-field rail, detailed formed panels and door fittings,
broad neutral ceiling LEDs, warm side coves and content-driven light on nearby surfaces.
The display and interior remain fixed in the viewport. Playback and demo-affecting controls
stay visible at the bottom. Tapping «Телеметрия» toggles compact left/right side panels;
the central image stays clear and most of the display remains visible. Scrolling affects only
open side-panel contents. Charging fittings align to the door pillar and wall
trim stops before the door; artificial roof bands are omitted from the close wall crop.
Raleway remains in use; the requested Esh/Struve comparison was deferred by the user.

The latest user-supplied photographs (`IMG_8349.jpeg`, `IMG_8350.jpeg`, and
`1591221.jpeg`, main commit `7e38c01`) guide the next material pass. Keep the existing
screen, door and foreground handrail anchors locked. Use warm bronze metalwork,
off-white molded paneling, layered black glazing surrounds and gray-taupe woven
cantilevered seating below the screen. Photos remain reference-only.

Changing application sections closes a paired, dimensional metro-door overlay,
then glides through the station order toward the selected tab. Targets to the left
enter from the left; targets to the right enter from the right. Every intervening
tab passes behind the glass in order, with stronger motion blur and one continuous
decelerating trajectory. Only the destination creates a browser-history entry.
The moving visuals are frozen before departure. Motion blur is baked into bounded
temporary bitmaps; a single compositor timeline moves the complete journey and
crossfades sharp endpoints. The doors reveal the page only after that animation
actually finishes, preventing slow-frame/timer races and mid-travel content shifts.
The leaves follow the supplied
Moskva-2020 photographs, with tall glazing, narrow black surrounds, center seals
and red edge LEDs. Glass is matte and blurred but transparent: broad page colors
and movement remain visible through the frost. Navigation
must remain reliable by mouse, touch, keyboard and browser history. Player frame,
camera and run URL changes remain immediate. Reduced motion uses a brief non-spatial
fade. The decorative doors contain no controls and release keyboard focus to the page.

The current user correction restores the Player interior from before the glossy
material pass: the original wall, copper-toned rails, door, seats, screen housing
and saloon lighting/reflections. Button highlights and shadows are restrained,
with their light/edge opacity reduced by roughly two thirds.
The outside-camera train is a rounded, detailed metro carriage. Navigation shows
only two full-height sliding leaves; the user's screen is the doorway frame, with
no added jambs, overhead header or threshold around the transition.

The interface is desktop-only with a minimum workspace width of 1280px. Build and
verify this single layout at 1280×720, 1366×768, 1440×900 and 1920×1080. Keep this
desktop-only scope for future changes, screenshots and documentation. Synthetic
capture runs demonstrate the UI and are not evaluation evidence.
