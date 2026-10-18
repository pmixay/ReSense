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
environment is confined to the visualization rather than becoming a second app shell.
The page must feel like another ReSense stage, with a continuous background and no
duplicate local logo, title, stage rail or standalone player header.

Target desktop review sizes are 1366×768, 1440×900 and 1920×1080, with mobile content
flowing vertically. Synthetic capture runs demonstrate the UI and are not evaluation evidence.
