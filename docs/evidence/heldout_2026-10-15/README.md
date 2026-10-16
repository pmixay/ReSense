# G3 pre-registration — 15 October 2026

**Status: specification only; no detector run and no results.** This implements
[`BACKLOG.md` G3](../../BACKLOG.md) and the 15–16 / 21 October calendar.
The committed `spec.json` is the registration; the geometry rules below are part
of it. The final single batch belongs to **another fresh agent**, on the verified
final shipped seal around **21 October**, after this registration commit.

## 1. Claim, scope, and provenance

The holdout is **new synthetic placements / motion / perturbation probes**.
`new_data` is a real background ride already used in the regression gate and
other development. Neither these windows nor the ride become an independent
real dataset by this registration. The shapes are synthetic; this cannot measure
real-obstacle generalization or independently held-out real recall.

Read for this registration: BACKLOG G3 and calendar; DATASET/SENSOR input,
coordinate, timestamp, shape and cache documentation; judge harness **input
definitions / CLI / geometry plumbing**. No outcome files were opened, no old
CSV/JSON detector outputs were read, and no H1/H2/R1/R2 evidence was accessed.
**Disclosure:** an initial grep aimed at `docs/BACKLOG.md` unexpectedly expanded
to the docs tree and returned legacy measured-summary snippets. Those were
incidental exposure, were not followed up, and did not inform window or shape
selection. Consequently this record does not claim zero exposure to all legacy
outcome text. The permitted sensor/data documents also contain historical
measurement context. No detector, range probe, ICP or held-out case evaluation
was executed. This agent did not write or tune a detector.

Exclusions come from the **definitions** in
`docs/evidence/judgement_2026-10-13/scripts/run_range_matrix.sh`:

| Name | Recording | Insertion / replay end, zero-based |
|---|---|---|
| A | `roundT_squareT_pressureGate_squareT` | 150 / 340 exclusive (line 10) |
| B | `roundT_doubleT` | 50 / recording end (line 11) |
| C | `roundT_pressureGate_roundT` | 0 / recording end (line 12) |
| D | `squareT_platform_squareT_switch` | 100 / 420 exclusive (line 13) |
| S | `squareT_platform_squareT_switch` | 360 / 620 exclusive (lines 23–24) |

The harness warms up from the beginning; these are insertion intervals, not
claims that earlier frames were unused. We conservatively exclude **all frames
of all four recordings**, every other short bag, and set O. This also excludes
the A/E extra shape placements and whole-bag robustness probes. The three shell
input definitions have SHA-256 fingerprints in `input_metadata.json`; the
validator checks their identity and extracts the five interval definitions. No
outcome table was used to derive an exclusion.

## 2. Fixed windows, concrete cases, and input metadata

Global index = `51 * numeric_split + local_message_index`; numeric split order
is essential (`9` precedes `10`). All boundaries are **[start, end)**. Do not use
lexicographic DB3 ordering or a cache iterator's enumerated list position as the
global index. There are exactly 714 messages per window, the first 60 warm up
the detector, and insertion occurs at the index shown.

| Window | Global interval | Insert | Original split numbers | Input span (s) | Intended category, unconfirmed |
|---|---:|---:|---:|---:|---|
| w01 | [1020,1734) | 1080 | 20–33 | 71.306988 | switch candidate |
| w02 | [2550,3264) | 2610 | 50–63 | 71.312287 | station candidate |
| w03 | [6324,7038) | 6384 | 124–137 | 71.301521 | curvature candidate |
| w04 | [8823,9537) | 8883 | 173–186 | 83.007752 | second curvature candidate |

These fixed indices were selected from input scene hints in DATASET.md
(splits 22, 55, 129–134, 176–180), **not by observed geometry or detector output**.
The deterministic selection fallback is to retain these very same windows with
`unclassified_fixed_fallback` when the category rules cannot confirm a label.
No other windows may be searched, swapped in, extended, or cut shorter.

`input_metadata.json` materializes the available **input metadata only**:
56 timestamp-file hashes, 2,856 point-file presence checks, 56 original DB3
presence checks, exact first/insertion/last bag timestamps, timestamp-sequence
hashes, and the intake's declared archive identity. It does not hash/read point
payloads or independently reverify the large archive. At future scene generation,
hash the actual source point/DB3 payloads used and freeze the decoding manifest.

**Known input limitation:** w04 has four timestamp gaps above 0.25 s (maximum
4.396728 s). It stays registered; invalid motion spans / unavailable metrics
must be reported. The other three windows have no gap above 0.25 s. Supplied
`odometry/` contains only four short-bag ICP files, no `new_data` ICP. Their
contents were not inspected. No curve, station, switch, travel distance or rail
height is asserted as observed at registration.

`spec.json.cases` is the **complete concrete 84-row case list**, including
per-case IDs, lateral draws, crossing directions and seeds. For example,
`g3-w01-bed030-approach` has draw -221 mm and seed 2066470267. Each of four
windows has:

* 9 shape/side configurations × approach and crossing = 18 scene probes;
* 2 below-rail negative bed probes, paired with `bed030` placement/motion;
* 1 unmodified empty-background control.

There are **8 distinct classes**: lowbox on bed, lowbox on rail, 2×2 box, 5 cm
cable, plank, lying person, pole, trolley. Both pole sides remain separate rows.
All 84 cases receive all 11 fixed variants: **924 scheduled replays**, each with
a fresh detector and its own warm-up. Some bed probes may be nonhazards; the
independent envelope, not the desired outcome, determines that label.

The SHA-256 PRF in `spec.json` fixes all random draws across operating systems,
process order and Python hash seeds. Uniform integer lateral draws are in
[-900,+900] mm inclusive. Explicit placement constraints: rail lowbox chooses a
measured rail by draw sign; poles use ±0.8 m; plank divides its draw by 9 to
remain transverse across both rails. Other shapes use the draw unchanged.
No yaw randomization: cuboids align their registered L/W axes to the route;
the plank's width is transverse. Dimensions and approximations are assumptions
of these probes, never claims about real objects or catalogue substitutions.

## 3. Frozen geometry-only preparation and category rules

This section specifies a future **detector-free** scene builder. Do not run it
as part of registration. It may inspect background point geometry only, and
must finish/freeze all geometry and scenes **before any detector output**.
It must not instantiate a detector even for calibration or a baseline axis.
No scene-selection feedback, visual picking, hand-labelled rails, or model
threshold choice is permitted after registration.

### Decode, motion, and trajectory

1. Decode original DB3 PointCloud2 messages in numeric split order; preserve
   each global index, split/local index, bag receipt timestamp, original header
   timestamp, topic, frame ID, ring-presence flag and point count. Use the
   judge node decoder's input contract (`xyz` float32 sensor coordinates,
   `inten` float32, `ring` uint16, 2.5–250 m decode bounds). Keep scene cache names
   `f_<global:05d>.npz`; `meta.json` is a list with explicit global `i` and local
   `window_position`. A sparse global index must never index that list directly.
   Compact16 inputs are available for provenance, but are not a substitute for
   node-decoded precision for this ray-cast run. Record decoder identity/hashes.
2. Fixed basis `(X,Y,Z)=(-sensor_y,sensor_x,sensor_z)`. Implement the CPU
   point-to-plane ICP parameters and bad-pair conditions in `spec.geometry`.
   Sort input points lexicographically by coordinates before voxelization;
   use deterministic lexicographic voxel order. Run one CPU thread and record
   library versions. Geometry uses coordinates only, not intensity or detector
   features. The first pose is identity. Compose full transforms mapping each
   current cloud into the first cloud's world frame; retain rotation/translation,
   fitness, RMSE and validity for every pair. First-frame pair fitness is null.
   Invalid pairs break the trajectory; do not extrapolate across one.
3. Route station is cumulative **horizontal** distance of consecutive valid
   world sensor origins. Interpolate origins linearly in station, and use the
   normalized horizontal segment tangent / world up to define route axes.
   For zero-length segments choose the next nonzero segment, then the previous
   one if none follows; no nonzero segment means `insufficient_motion`.
   A reversal (negative forward displacement >1 m for any pair) blocks that
   scene; never clip backward travel into forward motion. Orientations in SE(3)
   still carry pitch/roll for coordinate conversion.
4. The object's **front** station is `s(insert)+230.0` m and its centre station
   is front+L/2 (cylinder L=diameter). Its anchor tangent is the segment containing
   the centre station. Missing valid trajectory to that centre gives
   `incomplete_approach` / `geometry_blocked`; no straight-line invention or
   replacement window. For scoring, `d_gt(k)=s(front)-s(k)`, and also store the
   true Euclidean range to the surface. This arc-length start is explicitly not
   a promise of 230 m straight-line visibility on a curve.

### Rail and bed support (no detector track model)

Use the earliest valid source frame whose station is at least centre-15 m;
require the object centre to lie 5–25 m forward in that frame. If none exists,
support is unavailable. Transform the background to that frame's vehicle axes.
Use unique 1 cm xyz voxels (centroid, lexicographic voxel order), with
`5<=X<25`, `|Y|<=2`, `-2.0<=Z<=-0.3` m. Here z ranges are broad extraction
bounds, not an assumed mount height.

* Divide X into 1 m bins and Y into 0.025 m bins. Quantiles throughout this
  section use linear interpolation at index `(n-1)*q` in sorted values.
  In each X bin the floor reference is the 20th-percentile Z of all candidates.
  A Y bin with ≥3 voxels is a rail-ridge candidate if its 90th-percentile Z is
  0.15–0.50 m above that floor. Merge adjacent candidate Y bins into ridges
  only when their top heights differ by ≤0.05 m. Retain ridge width 0.025–0.20 m;
  ridge Y/Z are the medians of its candidate-bin Y centres / top heights.
* Enumerate all left/right ridge pairs in every X bin with separation
  1.45–1.70 m, midpoint |Y|≤0.40 m and head-height difference ≤0.06 m.
  Link pairs in adjacent X bins when both heads move ≤0.10 m laterally and
  ≤0.06 m vertically. Enumerate linked paths; rank by descending covered-bin
  count, then ascending summed squared lateral step, then lexicographic list
  of (X-bin,left-Y,right-Y). Choose first. Require ≥10 covered bins.
* Ordinary least squares, equal weight per covered bin, fits each head's
  `Y=a+bX` and `Z=c+dX`. Require each head's lateral and vertical residual RMS
  ≤0.04 m and predicted gauge at object X within 1.45–1.70 m. Otherwise
  `rail_geometry_missing`. No nominal gauge/height may be silently substituted.
  The two head positions evaluated at object X define the rail midpoint and
  mean rail height. Transform that midpoint into world; use its lateral/vertical
  offset from the ICP route centre as the frozen support correction. The
  tangent remains the independent ICP trajectory tangent. A rail-supported
  object rests at this plane, and `rail030`'s centre Y uses the chosen head.
* `bed030` uses the 20th-percentile Z from ≥10 unique background voxels within
  ±0.50 m longitudinal / ±0.25 m lateral of its anchor footprint, excluding
  points within 0.15 m of either fitted head. Its top may be below rail; compute
  and retain that fact. Missing support => `bed_geometry_missing`, not a made-up
  bed depth. Cable bottom is rail+0.20 m; other supports follow the spec.
* Crossing translates the object on its **frozen support plane**; it does not
  follow changing detector rails or vertically snap to every new floor bin.
  `bedneg` has rail-relative bottom -0.15 / top -0.05 m regardless of actual
  bed level: it is explicitly a negative synthetic geometry control.

The support extraction is an independent geometric rule, not ground-truth
certification of real rails. Preserve fits/residuals and flags so its limitations
are visible. If support is unavailable, retain all affected case rows as blocked;
empty-background controls can still run.

### Category confirmation and deterministic fallback

These tests assign descriptive **geometry-like** labels to the fixed windows;
they never select alternate windows. Use only pre-injection valid geometry.
Run all tests; retain multiple labels and all test inputs. No human relabelling.
For category tests use the canonical `box200` centre station
`s(insert)+231.0 m` and its support-frame rule, independent of each shape's
lateral draw. Thus category metadata is fixed once per window, not per case.

* **Curvature-like:** resample each continuous valid trajectory at integer-metre
  station; unwrap heading of each forward 5 m chord. Enumerate 100 m intervals
  starting at integer stations, regress heading on station, and confirm if an
  interval has `1/1500 <= abs(slope) <= 1/150` rad/m and heading residual RMS
  ≤1 degree. Choose the qualifying interval with earliest start for metadata.
* **Station-like:** at the same support frame, voxelize coordinates as above
  but keep `5<=X<40`, `1.4<=abs(Y)<=2.6` and height 0.6–1.4 m above fitted rail.
  Confirm if either side has ≥10 consecutive 1 m X bins with ≥10 unique voxels,
  within-bin Z MAD ≤0.05 m, and across-bin median Z range ≤0.10 m. Choose the
  left side before the right in a tie. This means platform-like geometry,
  not verified station identity or a detector's station state.
* **Switch-like:** repeat the ridge extraction over `5<=X<40`, `|Y|<=3`.
  Among ridges unused by the chosen main rail pair, link a third path with the
  same adjacency bounds and ≥15 covered bins. Its linear Y fit must have RMS
  ≤0.04 m, meet either main-head fit within 0.10 m at one covered-bin centre,
  and diverge by ≥0.40 m at another centre. Rank paths by covered-bin count,
  squared step, lexicographic coordinates as above. This is branching-rail-like
  geometry, not a claim of certified switch topology.
* No qualifying test, invalid trajectory, or missing supporting geometry =>
  `unclassified_fixed_fallback`. A window with other labels but without its
  requested category records `target_not_confirmed`; retain it unchanged.

All constants are frozen now. Any later modification must be an explicit
amendment before output; an outcome-informed change ends held-out status.

## 4. Visibility, perturbations, and metrics

`spec.json` fixes the exact shapes, 230 m front-station approach, 1 m/s crossing
centred at the first 100 m timestamp, sensor limits, occlusion, hazard envelope,
first-STOP and suffix held90 metrics, and every negative / missing / blocked row.
The cylinder is analytic, not a cuboid approximation. Use the lower median
observed elevation per ring and circular median phase modulo 0.1 degree per
frame (ties choose the smaller phase); generate only rings and azimuth columns
observed in that frame. Unique `(ring,column)` rays determine visibility;
duplicate echoes never inflate counts. Map observed azimuth to nearest column,
half ties toward smaller column. Canonical synthetic echo order is ring,
column, return index. Save the measured grid in the scene manifest.

Reference-visible means ≥1 unobstructed ray **before perturbation**, with a
separate ≥3-ray breakdown. Dropout cannot erase a miss from the denominator.
The 230–210 m blind segment and zero-ray scenes remain visible in reporting.
Keep negative bed controls below rail even if they produce points; bed height
is not automatically a hazard label. Do not label any global STOP as a hit
without the registered object match.

For held90, suffixes include **all** subsequent hazard frames, including zero-ray
frames. A hold crossing an actual source gap >0.25 s is invalid; a shorter valid
suffix after a gap may qualify if geometry itself remains valid. Cases with
insufficient motion or truncated approach/crossing keep explicit flags even
when an observed-prefix metric is available. Complete approach requires reaching
`d_gt<5 m`; complete crossing additionally requires passing both lateral
envelope boundaries. Always report the last scheduled hazard frame. No
distance-bin cherry-picking or short-suffix success without the registered
duration/frame-count conditions.

Background randomness is keyed by window/variant/ray and shared across paired
cases; synthetic randomness is keyed by case/variant/ray. All eleven variants
are one-factor, including complete-cloud rotations, return dropout, radial
noise, 5 Hz with original timestamps, deduplication and the explicit dark-target
model assumption. Freeze geometry once; no re-fitting for a more favourable
variant. A case's `seed` is an audit identifier; all actual random draws use the
documented master-seed/tag PRF, never an implicit random generator state.

Publish per-case and class/motion/variant first-STOP and held90 distances, nulls,
every missed hazard frame, blocked/unobservable/incomplete cases, all negative
and empty STOPs, and paired variant deltas. Results must distinguish full
scheduled denominators from geometry-valid, hazardous and visible subsets.
No aggregate pass threshold or gain is invented after seeing results.

## 5. Validate the registration now (safe, no evaluation)

From this worktree, in PowerShell:

```powershell
& "C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe" -B "docs/evidence/heldout_2026-10-15/validate.py" --check-inputs --self-test
```

The standard-library validator implements structural/semantic schema checks,
regenerates **all** concrete IDs/draws/seeds, rejects missing/duplicate/changed
cases, window/exclusion overlap, missing shapes/perturbations, bad dimensions,
duplicate JSON keys and nonfinite numbers. Its mutation checks exercise those
failure paths. It reads only this registration, the three shell input definitions,
intake and timestamp input metadata; it checks point/DB3 filename existence.
It imports no project modules and writes no files. `--print-cases` and
`--print-metadata` emit proposals for review/apply_patch, not detector output.
Repeat in fresh processes with different `PYTHONHASHSEED` to check process-level
determinism. The validator deliberately refuses a registration already containing
`results.json` or `run_final/`; future agents validate **before** creating them.

## 6. Handoff for the single final batch (~21 October)

1. Another fresh-context agent, with no detector tuning, reads the committed
   registration and records its full Git commit. Confirm chronology relative to
   1.2.0 tuning independently: this agent has not read other worktrees, branches
   or tuning evidence and cannot attest to their activity. Do not silently claim
   the spec predates work that was already underway.
2. Validate registration and timestamp fingerprints. Build/freeze independent
   geometry, category metadata, scenes and full source hashes as specified.
   Record environment/dependency versions and thread settings. No detector calls
   are allowed during this preparation, including through helper imports.
3. Implement/audit an **external evaluation adapter** against these immutable
   inputs; commit its code and scene manifest before any detector result. The
   stock `range_test.py` uses `baseline()` and detector track geometry; the stock
   `icp_odometry.py` constructs `NodeReplica` just to obtain a coordinate matrix.
   Do not run either unchanged for geometry. Reuse their input/ray-cast/detection
   contracts through an adapter with the fixed basis, full ICP and injected GT;
   do not create/read `*_baseline.json`. Probe perturbations likewise use this
   registration, not a new search matrix. No native or sealed file edits.
4. Bind **the actual final** seal manifest, commit/tag and image digest. Run and
   archive `python scripts/detector_freeze.py verify --manifest <FINAL_MANIFEST>`
   with PASS before the first detector invocation. The old default seal is not
   a substitute. The schema/metadata checks in this commit are not seal checks.
5. One write-once final batch, in lexicographic `(case_id,variant_id)` order;
   one invocation per scheduled replay. The range and robustness probe lanes
   form this one batch, not repeated runs with outcome-driven edits. No parameter
   tuning, retries, adaptive early exits, substitutions or overwrite. A technical
   failure remains a failure row; unexecuted rows remain `not_executed`.
6. Verify the same final seal again. Only then create `results.json`,
   `results.md`, the 924-row table and frame/miss/control artifacts named in the
   spec. Record both verify logs, all input/scene/runner identities, every miss,
   all denominators and limitations. Later tuning makes this battery development
   data; this protocol must not be reused for another held-out headline.

Remaining preparation is explicit: point geometry/category confirmation,
detector-free ICP/scene adapter and final-seal execution are **future work**.
This commit contains no `results.json` and makes no range/recall claim.
