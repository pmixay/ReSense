# F1 + Falcon false STOPs — protocol (registered 19.10 before any candidate is measured)

> **Lane:** P3 (detector), ordered by P1. **Branch:** `det/f1-false-alarms` from `main` `aec88d2`
> (1.2.0 candidate, seal `68dee667…`, 38 files). **Cut-off:** 21.10 09:00 UTC.
> **Why:** the organizers count a false alarm like a missed obstacle (Q&A 16.10, `organizers/answers.md` §10 #2).
> **Scope:** BACKLOG card F1 (near-field low-object false STOPs at the rail-head plane) and the false STOPs
> of the real Falcon Prime recording. **Out of scope:** what `CAUTION` means (card C1): CAUTION frames
> added/removed are reported, not optimised. No version, seal, README, CHANGELOG, BACKLOG or shared
> doc is changed here; P1 integrates and reseals.

## 1. Rules

* Every new behaviour sits behind a config switch in its own block of keys; **switch off ⇒ every
  output equal to `aec88d2`** except wall-clock timing fields (proved on the full gate's per-frame
  JSONL and on the whole Falcon recording, §4 A8).
* Candidate designs are registered in this file (or a dated amendment below, committed) **before**
  their measurement. Thresholds named here are not tuned afterwards on the acceptance data;
  a sweep named here (e.g. a margin 0.02 / 0.03 / 0.04) is reported in full.
* `CLAUDE.md`: every negative result ("0 false STOPs", "no change") is shown with a positive control
  (the same tool on the base run finds the base false STOPs); every cause label is read from the
  full detector state on every row (or a stated sample); instrumented runs must equal plain runs.
* Never the held-out G3 set. Evidence runs: `RESENSE_REPO=<checkout>`,
  `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`.

## 2. Data (container of 19.10: ~6 GB free disk, so nothing large is unpacked)

| set | source | how | check |
|---|---|---|---|
| six recordings, gate cache (int16, zstd) | `/data/dataset.zip` (Google Drive id `1WTlR2wD…`) | `scripts/stream_cache.py` (this folder): the archive streamed once, sqlite overflow chains recovered (`stream_falcon.Recover`, extended to the Pandar record layout), written exactly as `cache_frames.py --every 1 --int16 --stamps --zstd` | **positive control:** `roundT_doubleT` and `roundT_pressureGate_roundT` streamed vs caches of the unpacked bags made by `cache_frames.py` / `cache_decoded.py`: every array and every stamp equal; frame counts 201/345/252/268/545/877; `metadata.yaml` equal to `docs/evidence/bag_metadata/` |
| set O (`cloud_with_fake_obj`, 1,510) gate + node-decoded cache | Yandex `KpkG_yKoGk-vHQ` | same tool | frame count; set O labels match (`score_fake_objects`) |
| the ride `new_data` (11,271) | Yandex `N8IUpAyd7jyvow` | `scripts/cache_extended_ride.py` (compact16 zstd) | its own split validation and intake manifest (SHA-256 of the archive) |
| Falcon (4,443) | Yandex `SfBeRHbs8bNJAQ` | `scripts/stream_falcon.py` (one node replica, nothing stored but records; `--dump` frames for pictures) | the committed `falcon_full_v110.jsonl` reproduced decision by decision on the base |
| node-decoded `roundT_squareT_pressureGate_squareT` | dataset.zip | same tool (`cache_decoded.py` format) | positive control as above on `roundT_doubleT` |

## 3. Base measurements on `aec88d2` (first, before any candidate)

B1. Full gate (`scripts/regression_gate.py --jobs 2`, ride in 8 chunks) against the seal baseline
`docs/evidence/results/regression_baseline_2026-09-29_shell_off.json`: exit 0; its non-timing rows equal the
committed seal gate `docs/evidence/b4_merge_reseal_2026-10-18/gate.json` (ride 27 events / 30 episodes; five
empty 8 / 12; `doubleT_obstacle` 193 STOP frames; set O per object).
B2. **The ride through one detector in order** (as the judge and a jury playing the bag: `eval_real.run_piece`
over all 11,271 frames, receive stamps): every STOP episode (a run of STOP frames; a frame's decision as the node's,
STOP > FAULT > CAUTION > GO) with onset frame, distances, the kind/size/lateral/height of the reporting detection
and rail lock. **Low-kind episode:** an episode with a `kind == "low"` detection on its onset frame (also counted:
on any frame). The card's six (ride frames 2838, 4152, 5714, 5901, 7362; `roundT_pressureGate` 139) were measured
on v1.0.0 by the judge's node path; the base count on `aec88d2` is re-measured here and is the reference.
B3. Every base low-kind episode (ride and the five empty recordings) is traced from the full detector state on its
onset frame: the cluster's top above the model's rail-head plane, above the local rail-head line(s) (both rails,
X ± 5 m, measured from the raw points) and above the same lateral band's own line; rail slabs / rail score;
distance vs `template_range` / `rails_range`. A raw picture of each (top and side view of the points) is looked at.
B4. Falcon: the whole recording streamed through the base; all 4,443 decisions equal to `falcon_full_v110.jsonl`;
the 12 non-person STOP frames (159, 2312–2314 at ~115 m; 4394–4401 at ~9.4 m) re-identified; their mechanism
traced from the detector state on those frames (§5).
B5. Probes (judge tools, `docs/evidence/judgement_2026-10-13/scripts/`, unchanged): `range_test.py` on
`roundT_squareT_pressureGate_squareT` (background A, ICP odometry from `icp_odometry.py`) with
`--obj 0.3,0.3,0.15 --start 150 --d0 230 --end 340` (the judge's "rail-head box", 44.9 m) and the organizers'
10 cm box on each rail head (`--obj 0.3,0.3,0.1 --lat ±0.795`); set O through the node path (decoded cache,
`judge_runner.NodeReplica`), per object first STOP / STOP frames (`score_objects.py`).

## 4. Acceptance (all required for a "ship" recommendation; each reported pass/fail with numbers)

| id | criterion |
|---|---|
| A1 | ride (one detector, B2) low-kind false-STOP episodes: base → **≤ 1** (card F1 "6 → ≤ 1") |
| A2 | full gate **exit 0 without `--allow`** against the seal baseline; ride events / episodes ≤ base (27 / 30); five empty ≤ base (8 / 12) |
| A3 | `doubleT_obstacle`: 193 STOP frames, labelled hits per label and first alarm frame unchanged |
| A4 | set O: every inside object's STOP frames ≥ base and first STOP not nearer (gate); `small_on_rail` through the node path first STOP **48.0 ± 3 m** |
| A5 | rail-head box (`A_lowbox_rail`) first STOP **≥ 42 m**; the 10 cm box on either rail head: first STOP not nearer than base by more than one frame of travel |
| A6 | the whole test suite passes (base: 1,969 passed, 8 deselected), incl. the synthetic 30×30×10 cm box on a rail at 10/16/20/25/50 m |
| A7 | Falcon (whole recording, one detector): non-person STOP frames 12 → **0** (target; any reduction reported), **all 1,360 person-associated STOP frames kept**, first person STOP distance unchanged (±0.5 m) |
| A8 | every new switch off ⇒ all non-timing per-frame outputs equal to `aec88d2` (full gate JSONL incl. set F straight; Falcon 4,443 records) |
| A9 | X3 robustness battery (`scripts/robustness_battery.py`) against the 1.1.0 reference: pass — if the container's disk allows the four node-decoded caches; otherwise reported **not run** |
| A10 | (information) CAUTION frames added / removed per recording and on Falcon |
| A11 | independent review by a fresh agent: code + this protocol's criteria + the per-frame diffs (not my conclusions) |

## 5. Candidate designs registered now (F1, card tasks a–c)

All in `lowobj` (new keys, own block), default **off** in the class and both YAML copies until accepted.

* **F1a — local rail-head reference** (`lowobj.local_rail_margin` > 0, `local_rail_window` 5 m): for a low cluster,
  the rail-head line of each rail band (|dy ∓ rails_spacing/2| ≤ band half-width) is measured from the frame's raw
  points within X ± window, outside the cluster's own extent ± 0.3 m, as the median over 0.5 m along-track bins of
  each bin's highest return (≥ 2 returns per bin, ≥ 4 bins). The local reference at the cluster's lateral is the
  line of the nearer rail, or the linear interpolation between both lines across the bed. The cluster is kept only if
  its top ≥ reference + margin. No measurable line (too few rail returns): the existing rule is unchanged.
  Before the sweep: measure how far the ray-cast boxes (B5, synthetic tests) rise above their own rail's line; the
  margin keeps ≥ 1.5 cm headroom below the lowest such rise; sweep **0.02 / 0.03 / 0.04** and report all three.
* **F1b — same-band line to `range_max`** (`lowobj.rail_band_range` > 0): `mark_rail_line`'s test (the cluster's
  lateral band continues along the track at the same height: top ≤ band line + `rail_band_margin`) applied out to
  `rail_band_range` (≤ `range_max` 60 m) without the `rail_start_min_ref` condition; margin **0.03 / 0.05**.
  A marked cluster is dropped as rail geometry (not only withheld at start-up).
* **F1c — no rail pair** (`lowobj.no_rail_low_within` > 0, 15 m): on a frame with `track.rail_slabs == 0`, a low
  cluster farther than this is advisory (`reason = "no_rail_low"`), never a new STOP.

Falcon designs are registered in an amendment after B4's attribution, before their measurement.

## 6. Order

B1–B5 → commit base evidence → F1a–c measured on B2/B3 + probes (fast screen) → selected setting → full gate,
probes, Falcon, switch-off identity, X3 if possible → independent review → report to P1. A failed or partial
attempt is reported as such.

## Amendment 1 (19.10, ~09:35 UTC) — Falcon designs, registered after B4's attribution and before their measurement

**B4 result (base `aec88d2`, one stream, `scripts/falcon_trace.py`):** 4,443 / 4,443 decisions equal to
`falcon_full_v110.jsonl`; non-timing differences only in wall-clock latency lines (frames 10–19) and frame 0's
1.2.0 orientation-readiness message. Attribution from the traced state and the raw points of dumped frames:

* **9.4 m, frames 4394–4401 (8 STOP):** not a floor patch. The cluster's points are at z = +2.37…+2.54 m in the
  processed frame (the floor is at −2.0 m): **the tunnel ceiling**. After the walking person shadowed the near bed
  and the rail pair was lost, the track model's bed fit climbed (frame 4384: `floor_coef` [0, 0.0439, 1.4382],
  range 12–112.5 m; the whole recording before: [0, ~0, −1.98]), putting the ceiling 0.15–0.33 m above the
  modelled rail head. The 6.0 m STOPs of frames 4380–4382 are the person's upper body (1.6–1.8 m above the floor).
* **115 m, frames 159, 2312–2314 (4 STOP):** a support static in the sensor frame (centroid p5–p95 spread 8 cm
  along, 10 cm across, 4,246 hits) whose cluster is inside the strict gauge in 8.8 % of its hits (10–14 % of the
  100 hits before each STOP); the 10-hit vote reaches 6/10 by fluctuation of the axis/support.

**Designs (switches off by default):**

* **H — near-field height cross-check** (`cluster.mount_cross_tol` 0.5, `mount_cross_grade` 0.05,
  `mount_cross_range` 30 m): where the model's rail head at a gauge cluster's distance X differs from the
  calibrated mount's rail-head plane (z = −`MountCalibration.height`, final calibration only) by more than
  0.5 m + 0.05·X, the cluster stays an obstacle only if that plane puts some of its points within 0 … 3.0 m
  (the envelope's height band); otherwise advisory `height_conflict` (a signature; never near-escalated).
* **S — settled static scene** (`tracking.settle_min_hits` 50, `settle_window` 100, `settle_max_spread` 0.5 m,
  `settle_min_share` 0.5): a track whose last ≤ 100 ordinary hits (≥ 50) kept its centroid within 0.5 m per axis
  is an obstacle only while ≥ 50 % of those hits were inside the strict gauge; near escalation still wins.
  **Extra safety probes for S (registered now):** the judge's standing-train probes `S_person_{60,100,150}` and
  `S_cube05_{60,100,150}` (`range_test.py` on `squareT_platform_squareT_switch`, `--start 360 --end 620`) must not
  lose STOP frames against the base; doubleT_obstacle (standing train, static object on the rail) 193 STOP.
* Values above are fixed before measurement; if a value fails, the failure is reported, and any retry is a new
  amendment with its reason.
