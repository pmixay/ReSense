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
| F1a (`lowobj.local_rail_margin` 0.01, cross-rail off) | final gate and Falcon on `11bb1ab`: **pending** | ride low-kind false STOP episodes 4/6 → 1/1, gate exit 0 (`129415f`, with S2); review finding B1 open (accepted by the captain) |
| K2/K1 | **pending** (variant chosen from v3/v4/v5) | v3: gate exit 1, 12 rows; v4: gate exit 1, 19 rows ([handoff](../k1_k2_gauge_2026-10-19/HANDOFF.md)) |

Decisions: [`DECISIONS.md`](../../DECISIONS.md) rows 40–42; the plan per role: [`BACKLOG.md`](../../BACKLOG.md),
"Current plan".

## 4. Not done yet / not checked

- The final gate without `--allow`, X3 and the whole Falcon recording on the final commit (after K2).
- The organizers' dust (13 frames of the marked synthetic bags) on the final configuration.
- P4's independent review of everything that ships on.
- The reseal.
- The full test suite on the final commit. Only the targeted suites ran here: 311 feature/node tests after the
  merge, 271 after F1a.

## Files

- `runs/gate_*.json`: gate summaries (`base_aec88d2` from the F1 lane; `merged_b2c523a`; `int_3535947_off`;
  `int_3535947_hprime`).
- `runs/falcon_*.jsonl.xz`: per-frame Falcon records (`base_aec88d2`, `main_6be817a`, `off_b2c523a`).
- `runs/comparisons.txt`: every comparison above.
- `scripts/`: `run_gate.sh` (gate wrapper; paths are this session's), `cmp_frames.py` and `cmp_falcon.py` (copies of
  the F1 lane's).
