# New LiDAR adaptation: registered acceptance protocol

Registered on 2026-10-18 before modified sealed-detector candidate runs.
Baseline: `9b92df56e802d9d63f83f2fc5e5b07374db669c7` (sealed 1.1.0 detector).
Work branch: `work/n5-labels-c2-acceptance` (continued on the previous branch at the user's request; registration commit47b42be retained). No release is authorized in this task.
This protocol records defects, hypotheses and acceptance tests; an implementation is not accepted merely because it exists.

## N2 — Falcon Prime

Defect: Pandar assumptions are not an adequate documented Falcon input contract; only a partial Falcon recording has been measured. The actual `/iv_points`, `seyond` recording uses ROS +x forward/+y left/+z up, unlike the sensor manual's native axes.

Test all 4,443 recording frames, with source hash and frame completeness, classify static warning/STOP causes and the moving person, report timing on this machine. Exercise 8 supported upright/inverted orientations plus explicit configurations for all 24 proper axis permutations; never report GO while orientation is pending. Exercise absent rings, single returns, intensity scales/types, padded/organized float32/float64 fields and input topic/frame changes. Compare Pandar baseline decisions, including 193 STOP frames on doubleT_obstacle, and a Falcon sampling proxy. Any degradation is quantified, not silently accepted. Sensor profiles must not silently apply Pandar small-object density to Falcon. Document a working Falcon replay command and same-node Pandar-to-Falcon reset.

## N4 — interactive playback

Defect: player keyboard controls and sequential bags need a supported, verified entry point. Test pause/resume and rate 0.5, two bags through one unchanged node process, input/state resets, and the Pandar/Falcon profile boundary. Keep batch playback supported. Exercise actual Docker/ROS transport and RViz under software rendering/Xvfb; retain logs and screenshot. Add the relevant local integration check to CI, distinguishing local success from unavailable hosted CI.

## N1 — honest, stable gauge

Defect: unbounded 250 m lines and per-frame marker replacement misrepresent trusted geometry and jitter. Draw the configured gauge box (2.1 m wide, rail-relative 0.12–3.0 m), bounded to trusted axis/monitored range. Display smoothing must not alter detector decisions. A held invalid outline must explicitly be invalid, with zero solid trusted range. Status exposes range, validity and hold state. On Set O, measure edge frame-change p90 at 40/80/120 m against limits 0.05/0.08/0.15 m; report availability and smoothing lag as well as jitter. Check no trusted solid segment exceeds axis_valid, no disappearance on valid GO/STOP, and replay obstacle plus curve with screenshot.

## N3 — dust stress

Defect: no labeled physical dust recording exists, and performance under volumetric returns plus occlusion is unmeasured. Add a deterministic generator that preserves clean truth and records seed, cloud geometry, return density, low-intensity distribution and distance-dependent attenuation. Predeclare low/medium/high return densities 0.1/1/10 per cubic metre in the forward cloud (x=2.5–60 m, y=-3–3 m, z=0.1–3.5 m above rail), extinction coefficients 0.0005/0.003/0.02 per metre. These are simulation stress settings, not measured dust physics. Keep the three levels and seeds fixed across candidates; include spatially concentrated and broad clouds if a generic-filter hypothesis needs controls.

Run clean and each density on five original empty recordings, doubleT_obstacle (real person), Set O and available set F backgrounds. At each level, empty-bag false STOP episodes may increase by at most one per recording. Low-density real-person first STOP distance must remain at least 90% of clean, with per-object STOP retention also reported. High density must be explicitly degraded, not silently GO. Any low-intensity filtering requires positive controls with low-reflectivity real objects and Falcon's intensity distribution; do not infer dust merely from low intensity. Prefer conservative health/range reporting over removal of obstacle evidence. Report all regressions and physical-data limitation.

## N6 — platform late person

Defect: synthetic_platform person is visible at ~249 m but first STOP is 44.01 m. Existing attribution identifies wall-loss frames113–238, capped45m axis and129 beyond_axis person demotions; synthetic motion is a separate limitation.

Hypothesis: independently observed, consistent paired rails can extend the trusted existing axis on wall-loss frames, without changing its shape or trusting an unobserved far polynomial. Measure current raw paired-rail support first. Require bounded rail gaps, gauge and residual checks. Do not enable the previously failing far-rail curvature refit or blindly raise a distance cap. Candidate acceptance: improve first STOP distance above44.01m (target at least60m), lose/delay/shorten no baseline person STOP, add no unmatched/outside-object STOP on the three labeled synthetic recordings, no new STOP on exact source Set O1308–1433 or five empty recordings. Report uncertain labels separately. Reject candidates that fail these controls.

## Integration and detector acceptance

Preserve the approved C2 conservative range policy and explicitly compare decisions, warnings, detections and range claims. Test input/reset contracts, focused unit tests and the complete available suite. Record hardware, commit, configurations, source/cache hashes and timings; this host has one exposed CPU and4GB RAM, not an8-core stand.

Before accepting a sealed change: reviewed patch and affected tests; commit measured code; full default regression gate with ride and set F, no waivers/missing rows; independent frame-level safety review (no STOP loss/delay/shortening on O, real obstacle, range and stress cases); reviewed new manifest and successful verify. A necessary baseline update must describe actual intended improvements and retain negative controls. Keep failed candidate evidence. Do not reseal an incomplete or failing gate. User's standalone work map stays outside the repository.

### N3 candidate registered after the first moderate-dust baseline

The first complete medium-density doubleT_platform measurement produced25 false STOP episodes versus0 clean. The candidate will recognize diffuse low-intensity returns only when they occupy at least45% of 5m×0.5m×0.5m cells across the trusted forward gauge interior (5–60m, lateral±1m, rail-relative0.3–2.7m), with at least6 longitudinal stations. Under that measured diffuse condition, inspect local distinct-point support for a detection: a distance-scaled radius of0.15m+range*tan(0.2deg), at least3 distinct returns, and at least2 supported returns in its box. A low-intensity unsupported detection may become an explicit advisory with a conservative range cap; its evidence must remain visible, never converted to silent GO. Retain mixed/strong returns and already-held detections when current raw support is unavailable. Pandar intensity ceiling5 is an explicit test setting, not automatically portable to Falcon. First prototype against archived results, then integrate only after low-reflectivity positive controls and frame-level STOP-retention checks. Reject a candidate that loses real labeled STOP or fails the registered dust/empty criteria; report coverage and false STOP frames as well as episodes.

### N6 candidate v3 after rejected empty-platform regression

Candidatev2 improved the person44.01→51.12m with no lost person STOP, but failed its first empty control: doubleT_platform gained6 low-object STOP frames30–35 after extended-range frames23–28 had admitted distant bed candidates. It is rejected. Revised hypothesis: paired rails support only lateral axis geometry, not farther low-bed anomaly trust. Preserve the exact pre-extension range for low-stage candidate admission/history while retaining observed lateral extension for above-rail objects. Test low-stage input/range parity with baseline and rerun complete platform/person/empty/SetO controls before any activation. Existing no-regression criteria remain unchanged.

The post-tracker N3 prototype is rejected: it reduced medium-platform STOP frames167→62 but fragmented alarms, increasing episodes25→33. The next candidate applies qualification **before** tracker confirmation, keeps1–2 distinct current returns as ambiguous sparse objects, protects any strong original echo before deduplication (both echo orders), protects held/no-current data and objects outside the examined clutter volume. Tests cover dark sparse/new objects10–200m, dense dark body, coincident strong/dim echoes, flat surface vs diffuse volume and severity preservation. These protections narrow the experiment; acceptance criteria stay unchanged.

Independent review further requires protecting up to3 distinct returns, a sampled line/plane (maximum best-plane residual≤0.10m), and excluding diffuse_low_support from near escalation; otherwise a dark thin cable could be demoted or the tracker could undo an advisory. New tests include3-return dark objects,4-return upright/diagonal cables and a planar box, plus10 tracker updates that must stay advisory for the new reason. These are conservative protections, not proof of physical dust performance.

### N2 bounded orientation-adoption replay candidate

The eight automatic orientation cases lose initial tracking evidence after adoption (first STOP around frame10 versus explicitly mapped frame8/193 STOP). The readiness guard prevents premature GO but does not recover this history. Candidate default-off calibration.orientation_replay_frames=4 buffers only initial unconfirmed inputs, with the current input included in the4-frame/32MiB maximum. Require finite strictly increasing timestamps and no gap>1s; reset, gap, overflow or late adoption disables replay. On validated discrete orientation adoption, initialize a fresh detector with that rotation explicitly installed/confirmed, replay the buffered real frames through unchanged thresholds, publish only the current result/stamp, and transfer state. No invented hits, old publications or recursive adoption replay. Unsupported instrumentation subclasses must be handled explicitly rather than silently bypassed. Measure full one-time wall/memory cost and completed-process latency including replay. Tests compare decisions/detections/193STOP and first STOP frame8 against explicit mappings for all8 automatic cases, exercise empty/fault/startup/reset/late-adoption/size boundaries, and preserve every existing STOP. Full gate and independent review remain required before enabling the default.

### N3 retained failure and health-only follow-up

The pre-tracker candidate406ffaa reduces medium doubleT_platform false STOP frames167→11 and episodes25→4, still failing the maximum1 extra episode. Residuals include strong far background104–110m, mixed near returns and2–3-return hanging shapes. Independent review rejects weakening sparse/strong protections: those shapes can be real cables. No suppression candidate is accepted for runtime. A separate health-only hypothesis addresses frame78's silent GO: the trusted axis shrank to20m, so the six-station diffuse observer stopped even though the clutter persisted. Measure broad60m observed-volume occupancy independently for health, retaining the trusted-range-bound qualifier only for the rejected advisory experiment. This health flag cannot remove detections or promote GO, must preserve error severity, and must be paired with clean/dark-object controls. Its sensor-specific intensity ceiling remains explicit; physical dust is not identified.

### N2 independent metadata-budget finding, 18 October 09:06 UTC

The independent reviewer reproduced an owned-storage limit violation in the startup buffer:
at a scaled 65,536-byte limit, 600 distinct five-item metadata lists were charged 64,736 bytes,
but their copied retained payload occupied 78,108 bytes. `deepcopy` can expand list storage;
counting the input containers is not a conservative bound for their copies. Ordinary decoded
metadata uses scalar counts, but the accepted public nested-metadata contract must also obey
the current-inclusive 32 MiB limit. The interrupted f5 full-gate attempt is retained and is
not acceptance evidence for a corrected implementation.

Before editing, register this narrow correction: reserve conservative copy-container capacity;
count independently copied XYZ/intensity/ring separately from the metadata deepcopy memo;
then independently check owned retained storage before accepting a snapshot. Preserve supported
plain metadata types and cycles, reset/overflow behavior, timestamps and replay semantics.
Test the nested-list reproduction, aliases shared between fields and metadata, and actual
owned-storage bounds. Require independent review, affected replay tests and a fresh full gate
on the committed corrected source. Do not waive the limit or relabel earlier source captures.

### N3 independent coordinate-frame finding, 18 October 09:21 UTC

Independent review found that the regular dust harness used a rail height from the clean
detector's calibrated model with configured-frame input points before that mount correction.
In the dark-person frame100 example, the vertical inconsistency is approximately 0.252 m
(estimated from the rounded recorded mount angles). Those captures remain reproducible
configured-coordinate stresses, but cannot claim the registered rail-relative cloud geometry.
Set F used its separate, pre-process legacy placement model for the rail height; the same
specific frame-mixing defect has not been demonstrated there. Its partial placement bank had
no evaluated dust levels and lacked the common auditable clean-frame transform contract.
Preserve the earlier regular captures and Set F bank under their original source hashes;
do not silently overwrite or promote partial runs.

Correct the harnesses, not the frozen production core: freeze the exact applied clean input-to-model
rotation and rail reference per frame, independently of every dusty detector. Perform attenuation
and cloud construction in that same clean reference frame, inverse-map only the new cloud returns,
and recover every retained source XYZ/intensity/ring exactly through its original index. Preserve
timestamps, clean labels, source identity, existing densities/extinction/seed and the identical
frozen Set F object placement across densities. Record the reference transform and verify its
source and per-frame identity. The rail reference must correspond to the actual applied transform,
including startup/adoption/reset behavior, rather than a later or rounded calibration estimate.

Before fresh complete batteries, test nonzero pitch/roll, exact retained source points, cloud
bounds after the round trip, deterministic replay and independence from dusty outputs. Strengthen
the Set F verifier to reconstruct decision/hit/count summaries from raw captures rather than
trusting aggregate counters. Rerun the seven recording/four density baseline and all30 fixed
Set F sequences with the corrected geometry; repeat dark-object and health-only controls where
their claimed conclusions depend on that geometry. Earlier acceptance failures remain recorded.
