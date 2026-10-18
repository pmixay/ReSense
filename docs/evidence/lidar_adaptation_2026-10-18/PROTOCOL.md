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
