# Integration of 19.10: four agent lanes merged, identity proof, the captain's switch decisions

> **Purpose:** the record of how 1.2.0's final source was assembled on 19.10. It covers the agent lanes K1/K2, F1,
> Falcon long range and N3, plus P3's L16/S3 and R3 from `main`. It shows that the merge changes nothing while the
> new switches are off, and what each switch the captain turned on does. **Owner:** P1 (integration), P4 (review)
> · **Branch:** `claude/optimistic-mccarthy-z5nmwd` · **Status:** in progress. The final-configuration rows
> (K2 variant, final gate, X3, Falcon, the organizers' dust) are added when they are measured.

## 1. What was merged

| source | head | content | default after the merge |
|---|---|---|---|
| `main` | `6be817a`, then `9621024` | P4's B4 review; P3's L16/S3 (ring-free orientation, bounded search); P3's R3 (cable confirmation) and the H1 diagnosis | L16/S3 and R3 **on** (as P3 shipped them) |
| `det/f1-false-alarms` | `0d93c3b` | F1a local rail reference, H/H′ mount cross-check, S/S2 settle, F1b/F1c | all off at the merge (`fbb64d7`) |
| `det/k1-k2-gauge` | `87d029d` | K2 joint axis fit (v3/v4), K1 distance-based smoothing, the viewers' curvature step | off (as committed) |
| `det/falcon-long-range` | `faac2d4` | `farrange` (far straight axis, crop 400 m, far rules) under the Falcon profiles; Falcon `small_target_limit` | `farrange` off; the Falcon clear-distance model is always on (`decision_policy.py`) |
| `det/n3-dust-robustness` | `b816534` | dust guard (`resense/dust_guard.py`) | off |

Conflicts: only the N3 merge, and they were additive. Both new config sections and both detector inits/resets were
kept. The track fit takes N3's filtered input (used only while the guard is on) and K1's `travel` argument (used only
with `walls_smoothing_distance` > 0). After the merge: `configs/default.yaml` equals the class defaults, the
parameter files are in sync, and the feature and node tests pass (311).

## 2. Identity with every new switch off

| check | method | result |
|---|---|---|
| full regression gate, per frame | `scripts/regression_gate.py` (seal baseline, no `--allow`) on `b2c523a`; [`cmp_frames.py`](scripts/cmp_frames.py) against F1's run of `aec88d2` | **exit 0; 15,269 rows, 0 differ** (101 differ only in the latency health level); set F equal. The 16 changed information rows are all latency |
| positive control of the comparison | the same comparator, F1's switched-on candidate `129415f` vs `aec88d2` | 2,716 rows differ: the comparator sees real changes |
| the whole Falcon recording (4,443 frames, one node replica, `falcon_trace.py`) | merged `b2c523a` vs `main` `6be817a` | **0 rows differ** (every non-timing field) |
| the same, vs `aec88d2` | merged vs `aec88d2`, and `main` vs `aec88d2` | 0 decision differences; one extra health message on frame 0 ("alternative orientation awaiting confirmation") in both, so it comes from L16/S3 in `main`, not from the agent lanes |

The gate covers the six Pandar recordings, set O, set F and the whole ride. So L16/S3 is also identical on the gate.
That agrees with P3's own check.

## 3. The switches that were turned on

| switch | measured here | measured by the lane (not re-run here) |
|---|---|---|
| R3 (on in `main`) | gate on `3535947` vs `b2c523a`: exit 0; 4 gated rows better (set O `thin_hanging`: STOP frames 15 → 18, first STOP 30.1 → 35.1 m, held from 31.8 → 40.0 m); set F cable recall 43 → 50 % (0–50 m), 47 → 49 % (50–100 m); information row `set_F_straight.cable.sustained_median_m` 34.2 → 17.8 m (worse, ungated); per frame 3 rows differ (set O frames 786–788) | P3: author acceptance PASS on `b14cfd0` ([R3/H1](../r3_h1_2026-10-19/README.md)) |
| H′ (`cluster.mount_cross_tol` 0.5) | gate on `3535947` with H′ vs without: **0 rows differ** | Falcon: the 8 STOP frames at 9.4 m (the tunnel ceiling under a floor fit that climbed) removed, all 1,360 person STOP frames kept |
| F1a (`lowobj.local_rail_margin` 0.01, cross-rail off) | see the final configuration below | ride low-kind false STOP episodes 4/6 → 1/1, gate exit 0 (`129415f`, with S2); review finding B1 open (accepted by the captain) |
| K2 variant B (v5b without K1; on since `c9e8daa`) | gate on `cf58128` with B's values as overrides ([`runs/gate_k2B_cf58128.json`](runs/gate_k2B_cf58128.json)): **exit 1, only set O `small_center`** (first STOP 55.8 → 52.5 m, held from 60.8 → 57.5 m, STOP frames 32 → 30; 6 gated rows; a gate exception accepted by the captain); against the configuration without K2: ride STOP episodes 24 → 9 (18 removed, 3 new), five empty recordings 11 → 0, `squareT_platform` 11 → 0, `doubleT_obstacle` rail-object hits 129 → 133, set F cable recall 50/49 → 52/44 %; every other obstacle row unchanged. Final gate on the committed defaults, X3, Falcon, standing-person probes and gate A (B + K1): **pending** | v3: gate exit 1, 12 rows; v4: 19; v5a: 12; v5b: 8 ([V5](../k1_k2_gauge_2026-10-19/V5.md)); improvement is P4's first P0 ([package](../k1_k2_gauge_2026-10-19/P4_PACKAGE.md)) |

### The configuration as decided, K2 still off (`11bb1ab`: F1a + H′ + R3 + L16/S3 on)

| check | result |
|---|---|
| full gate (seal baseline, no `--allow`) | **exit 0; 8 gated rows better, 0 worse.** Ride: alarm events 27 → 18, STOP episodes 30 → 24, alarm frames 126 → 102. Five empty recordings: events 8 → 7, episodes 12 → 11. `doubleT_platform`: its 1 STOP episode → 0. Set O `thin_hanging` as under R3. Information row `set_F_straight.cable.sustained_median_m` 34.2 → 17.8 m (R3) |
| real obstacles on the gate | of 50 obstacle rows (`doubleT_obstacle`, every set O object: STOP frames, first STOP, held from), only `thin_hanging` changed, and it improved. `doubleT_obstacle` has 1 STOP episode from frame 8, as before |
| whole Falcon recording vs `main` | 8 rows differ, all decisions STOP → CAUTION at frames 4394–4401 (the tunnel ceiling, H′). False STOP frames **12 → 4**; the remaining 4 (159, 2312–2314) are the static support at ~115 m that only S2 would remove (S2 off). Person: all 1,360 STOP frames kept, first STOP unchanged at 124.84 m. No new STOP frame. F1a and R3 change nothing on Falcon |

### K2 variant B (measured on `c9e8daa`; held off afterwards, [`DECISIONS.md`](../../DECISIONS.md) row 44)

| check | result |
|---|---|
| whole Falcon recording vs the same configuration without K2 (`11bb1ab`) | **the walking person: first STOP 124.84 m → 112.97 m (frame 2972 → 3070); person STOP frames 1,360 → 1,202 (158 lost, frames 2972–3065, 113–125 m)**. Cause in the records: at 113–125 m the person is seen on the axis (lateral 0.07–0.3 m) but only as a warning, beyond the trusted range, which the reach cap sets at 107–123 m (without K2 it was a STOP). The 4 remaining false STOP frames are gone; 9 new STOP frames not on the person (4373–4379 at 6.5 m, 4410–4411 at 3.0 m; not attributed, unverified); CAUTION 3,070 → 2,530 frames, GO 8 → 580. Decisions differ in 622 frames |
| the organizers' dust (13 frames of the marked synthetic bags) | no STOP, and no detection or warning at a dust box (the CAUTIONs come from warnings at 1.75–152 m, as with 1.1.0): **the dust guard stays off** (captain's decision 5) |
| STOP detections on the marked bags vs 1.1.0 | platform 187 / 187 on marked objects (1.1.0: 185 / 185); switch 150 / 151 (1.1.0: 133 / 142, the background STOPs at 147 m are gone); tunnels 107 / 111 (1.1.0: 120 / 128). Per marked object, the STOP frames are equal or more, except the **small cube right of `synthetic_tunnels` (marker id 19): 30 → 14**; at 30–55 m (frames 259–273) it is no longer a detection or a warning. Its marker is ~1.45 m right of the sensor axis, probably just outside the 2.1 m gauge (N5: "boundary uncertain"); not verified |

### The final commit `4cf8e27` (K2 held off; F1a, H′, R3, L16/S3 on): for P4's review and the reseal

| check | result |
|---|---|
| full gate (seal baseline, no `--allow`) | **exit 0, 8 gated rows better, 0 worse** ([`runs/gate_final_4cf8e27.json`](runs/gate_final_4cf8e27.json)); per frame **identical to `11bb1ab`** (15,269 rows, 0 differ; latency level only in 1,427), so every number of "the configuration as decided" above holds |
| X3 robustness battery (40 cases, 260 comparisons, reference `aec88d2`) | **PASS, 0 failed** ([`runs/x3_final_4cf8e27.json`](runs/x3_final_4cf8e27.json)). 27 comparisons moved within tolerance: set O positive STOP frames +5 and the hanging cable's inside STOP rows 15 → 19 (R3) in every perturbation; set O unmatched STOP episodes +1 (e.g. 6 → 7; tolerance 1) |
| whole Falcon recording | **identical to `11bb1ab`** (4,443 rows, 0 differ): false STOP frames 12 → 4, all 1,360 person STOP frames kept, first STOP 124.84 m |
| organizers' dust and the marked synthetic bags (1,667 frames) | 13 dust frames: **no STOP, no detection or warning at a dust box** (the dust guard stays off). Against the committed 1.1.0 runs: **every decision and detection identical**; only the reported clear distance differs on 4 frames (platform 1, tunnels 3; switch identical in every field). So the 12 background false STOP frames of 1.1.0 (switch 7–14, tunnels 147–149 and 367) remain |
| full test suite | **2,140 passed, 0 failed**, 8 deselected (7 by default; `test_lidar_proxy_hook` is the container's environment failure, see below) |

Decisions: [`DECISIONS.md`](../../DECISIONS.md) rows 40–44; the plan per role: [`BACKLOG.md`](../../BACKLOG.md),
"Current plan".

## 4. Not done yet / not checked

- K2: held off; P4 resolves its problems ([package](../k1_k2_gauge_2026-10-19/P4_PACKAGE.md)).
- P4's independent review of everything that ships on.
- The reseal.
- The full test suite: on `4cf8e27` 2,140 passed, 0 failed (on `ff91d40` 2,133 passed), 8 deselected. 7 are
  deselected by default (local datasets). The 8th is
  `test_lidar_proxy_hook::test_child_process_inherits_hook_and_bad_source_fails_closed`, an environment failure of
  this container: it fails identically on untouched `aec88d2`, according to the F1 lane.

## Files

- `runs/gate_*.json`: gate summaries (`base_aec88d2` from the F1 lane; `merged_b2c523a`; `int_3535947_off`;
  `int_3535947_hprime`; `int_11bb1ab_final`).
- `runs/falcon_*.jsonl.xz`: per-frame Falcon records (`base_aec88d2`, `main_6be817a`, `off_b2c523a`, `final_11bb1ab`).
- `scripts/score_falcon.py`: the F1 lane's Falcon scorer (person frames from the N2 anchors, false STOP attribution).
- `runs/comparisons.txt`: every comparison above.
- `scripts/`: `run_gate.sh` (gate wrapper; paths are this session's), `cmp_frames.py` and `cmp_falcon.py` (copies of
  the F1 lane's).
