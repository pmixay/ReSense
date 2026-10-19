# Falcon long range: report (19.10)

Branch `det/falcon-long-range`, base `aec88d2`. Candidate code measured: `89e0f3b` (C1 + C3 redesigned + C5 + C6,
C4 off). Final commit only flips `farrange.with_falcon_profile` to **False** (Falcon long range off by default;
see §1). Protocol: [PROTOCOL.md](PROTOCOL.md) with amendments A1 and A2. Review:
[INDEPENDENT_REVIEW.md](INDEPENDENT_REVIEW.md) (first review + two re-reviews).

## 1. Recommendation to the captain

**Merge the code, ship it OFF.** No 300 m claim, and no 250 m claim either.

* The honest, safety-checked candidate (89e0f3b) gives on the real recording: first STOP on the person at
  **146 m instead of 127 m**, **0 false STOP episodes** (baseline 3), **0** STOP frames not on a person
  (baseline 18), CAUTION share **37 %** (baseline 68 %), all 1,369 baseline person-STOP frames kept.
* On the injected matrix (fresh seeds 10–12) it gives **no long-range gain**: approach first STOPs 112–117 m vs
  109–117 m baseline; no static target at ≥150 m is held. With one tunnel boundary the far axis cannot be
  trusted further than the near model already is (review R1); that removes the gain the earlier, unsafe
  versions showed (person STOP from 249–290 m, 2 m box from 292 m).
* Rule 5.1(b) **fails**: 9 STOP episodes vs 8 (whole recording). The Pandar gate and X3 were **not completed**
  in this container (§5). For these two reasons it must not be switched on before integration.
* To switch it on: `farrange.with_falcon_profile: true` (YAML/class), then the profiles `falcon_ros` /
  `falcon_native` enable it. With a route-map statement, `farrange.declared_straight_to` extends the trust
  (measured variant `map300`: first person STOP 205 m, 0 false episodes, 11 vs 8 STOP episodes).

## 2. What can be detected how far, and why not 300 m

| evidence | value |
|---|---|
| real person, returns per frame (far walk, raw labels, incl. empty frames) | 4.4 at 250–260 m, 3.1 at 260–270, 1.6 at 270–280, 0.3–0.6 at 280–310 m |
| injector, returns per frame at 300 m | person (front) 3.9, person (back, = real walker) 1.0, cube 20 % 3.9, 2 m box 20 % 23.8 |
| tunnel-boundary support of the far track on this recording | contiguous to ~190–200 m on one side (left wall); right side a sparse column row; a full-width structure at 248–252 m |

Blockers for 300 m, by kind:
1. **Sensor physics:** a dark person gives < 1 return per frame beyond ~280 m (real data), below any cluster
   minimum. A 2 m box at 20–50 % gives 24–29 returns at 300 m, so large objects are physically visible there.
2. **Missing data:** the track geometry beyond ~200 m is not observable (one wall, then the 250 m
   structure). A straight continuation is an assumption; a route map (`declared_straight_to`) or a second
   boundary is needed to trust a corridor there. Without it, an R 300 m curve can start unseen.
3. **Our code (fixed in the candidate, off by default):** the parabola axis is 2 m off at 150 m and 15 m at
   300 m on this recording (rails bend in the first 40 m); the 250 m crop; the Pandar-tuned height-reference
   rules (`far_min_height` 0.6, `far_max_length` 3.0); the conservative clear range 0 for Falcon.

## 3. What changed (files, switches, defaults)

| file | change | default |
|---|---|---|
| `resense/config.py` | new block `FarRangeConfig` (`farrange.*`) | `enabled=False`, `with_falcon_profile=False`, `confirm_enabled=False` |
| `resense/farline.py` (new) | far straight axis (contiguous support, curve lead, R 300 m unseen curvature, one-side divergence allowance, sigma ≤ 0.5 m trust, one-side cap at the near trust, `declared_straight_to`), far confirmation (C4, off) | only built when `farrange.enabled` |
| `resense/detector.py` | hooks: far laterals, strict-gauge shrink by sigma, trust never below near, accumulation buffer cleared on far-axis switch | inert when off |
| `resense/sensor.py` | `falcon_expected_points` (measured Falcon raster) | — |
| `ros2_ws/.../sensor_profiles.py` | Falcon profiles set `farrange.enabled`, crop/gauge/floor-verify 400 m, `far_min_height` 0.3, `far_max_length` 4.0 **only if** `with_falcon_profile` | off |
| `ros2_ws/.../decision_policy.py` | C5: `small_target_limit("falcon_prime")` = 48.2 m (0.3×0.3 m, 3 returns, outside-ROI raster 0.18°×0.235°) instead of unavailable | **active** for `falcon_prime` (not behind the flag; a model value, not a measured detection) |
| tests | `tests/test_farrange.py` (14, incl. the reviewer's curve / diverging / one-wall cases), `test_range_reporting.py`, `test_node.py` updated for C5 | — |

Not implemented: C2 (Falcon visibility prior) — measured offline: 6 % of detections would change score, all
near 25–30 m and only downwards (`scripts/`, report §4). C4 implemented, measured, off (no false alarm removed,
held fraction lower).

## 4. Before / after on the pre-registered rows

Real recording, `falcon_ros` ([falcon_recording_eval.json](falcon_recording_eval.json),
[falcon_recording_eval_final6.json](falcon_recording_eval_final6.json)); person association = N2 anchors +
far-walker raw labels (A1):

| row | baseline aec88d2 | candidate 89e0f3b | map300 variant |
|---|---|---|---|
| GO / CAUTION / STOP | 13 / 3,043 / 1,387 | 1,420 / 1,635 / 1,388 | 2,181 / 355 / 1,907 |
| STOP episodes (rule 5.1b, ≤ 8) | 8 | **9 (fail)** | 11 (fail) |
| STOP episodes with no person frame | 3 | 0 | 0 |
| STOP frames not on a person | 18 | 0 | 2 |
| frames 0–1700: STOP episodes / not-person STOP frames / CAUTION | 2 / 5 / 0.99 | 0 / 0 / 0.57 | 0 / 0 / 0.54 |
| baseline person-STOP frames lost | — | 0 | 0 |
| first STOP on the main person | 127.1 m | 146.3 m | 205.3 m |
| far walker 245–307 m (E4), STOP frames | 0 | 0 | 0 |

Injection matrix, seeds 10–12 ([matrix_tables_seeds10-12.md](matrix_tables_seeds10-12.md)): static targets
at 150–350 m — no STOP in the baseline; candidate only sporadic at 150 m (2 m box 2/3 seeds, 0.01 STOP
fraction); approach from 400 m at 10 m/s — first STOP baseline 109–117 m, candidate 112–117 m, held 1.0 both;
negative control `outside` never STOPped in either. Earlier versions (C1+C3, C1+C3+C6, seeds 0–2,
[matrix/](matrix/)) reached 290 m on approach, but they were shown unsafe on curves by the review (B1) and are
superseded.

Walk control on the candidate ([walk_control_candidate.json](walk_control_candidate.json)): real first STOP
146.5 m vs injected 121–127 m — **fails** the ±15 m criterion; per-band STOP fractions within ±0.25. Baseline
walk control passes (real 127.2 m vs injected 119.5–122 m, [walk_control_baseline.json](walk_control_baseline.json)).

## 5. Pandar identity (switch off vs aec88d2) and what was not completed

* Shown: with `farrange` off, the full Falcon recording replays row-identically to the archived N2 baseline
  (decision, detections, warnings, nearest, clear, monitored on all 4,443 frames; run `new_off`, on an earlier
  commit of this branch); the reviewer compared Pandar output with `aec88d2` on 200 frames of two bags:
  identical except the wall-clock latency message. Unit tests: 1,974 passed, 1 failed
  (`test_lidar_proxy_hook`, fails identically on a clean `aec88d2` checkout in this container).
* By construction: every detector change is behind `self.far is not None` / `farrange.enabled`; the effective
  config hash changes for Pandar because `to_dict()` now has a `farrange` section (review note 1).
* **Not completed:** full regression gate (ride cache stopped at 211/221 splits, disk full); X3 candidate
  (reference on `aec88d2` MEASURED; candidate run ended with "worker evaluation identities differ" because I
  committed evidence during the run — [x3_candidate_incomplete.log](x3_candidate_incomplete.log)); the
  map300 seeds 10–12 matrix; the coordinator's moving-target amendment (chaotic / receding targets) was
  received after the measurements and **not run**; a moving-train Falcon replay (only synthetic ego shift).

## 6. What was checked and how

* Cache vs node decode: 89/89 frames identical; replay rows identical to the archived N2 baseline (4,443
  frames, default and `falcon_ros`).
* Injector: raster leave-out (p99 0.024° az / 0.038° el), return counts vs the real person per band
  (within ~15 % 30–250 m, [count_control.json](count_control.json)), beam model, POD fall-off refitted on the
  real far walker 245–285 m (held-out odd frames), walk control (baseline passes, candidate fails §4).
* Discovery (A1): frames 0–1700 contain a person walking 253 → 307 → 245 m; labelled from raw points
  ([far_walker_labels.json](far_walker_labels.json), [far_walker.png](far_walker.png)), spot-checked by the reviewer.
* Independent review: 4 blocking issues in round 1 (curves, C6 post hoc, rule 5.1b, accumulation), fixed or
  reported; R1–R3 in round 2, fixed; round 3: acceptable as Falcon-profile-only candidate with conditions.

## HANDOFF

Environment: Python 3.12 venv (`numpy==1.26.4 scipy==1.11.4 scikit-learn==1.4.2 pyyaml rosbags zstandard
pytest open3d matplotlib==3.8.4`), `scripts/build_native.sh`,
`RESENSE_REPO=<checkout> PYTHONPATH=<checkout>:<checkout>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`.

```bash
E=docs/evidence/falcon_long_range_2026-10-19/scripts
# full-range Falcon cache (~12 min, 4.9 GB float32, node-identical decode to 600 m)
python $E/cache_falcon_full.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out /data/falcon
# replay (baseline: add --pre farrange.with_falcon_profile=false; candidate: --pre farrange.with_falcon_profile=true)
python $E/run_cache.py --cache /data/falcon --profile falcon_ros --pre farrange.with_falcon_profile=true --out out/cand
python $E/falcon_eval.py --base out/base.jsonl --cand out/cand.jsonl --out eval.json   # rule 5.1 rows
python $E/far_walker_eval.py out/cand.jsonl --out fw.json                                 # E4
# injection matrix (PROTOCOL §3 + A1): frames 1290+, seeds 10-12
python $E/matrix.py --name cand --out out/matrix --pre farrange.with_falcon_profile=true --seeds 10,11,12 --check-prefix
python $E/make_tables.py baseline=out/matrix/baseline_summary.json cand=out/matrix/cand_summary.json
# walk control
python $E/walk_control.py out/specs && python $E/run_cache.py --profile falcon_ros --frames 0:1211 --inject out/specs/walk_seed0.json --out out/walk0
```

Data and scripts: track reference [track_reference.json](track_reference.json); person model
[person_model.json](person_model.json), [person_calibration.json](person_calibration.json),
[far_calibration.json](far_calibration.json) (k = 3); raw replays [raw/replays_final6.tar.gz](raw/) (baseline,
candidate, map300, walk controls). Note: `matrix.py` and `run_cache.py` paths default to `/home/user/data/falcon`.
Pandar gate data: `VM_GUIDE.md` §2 (needs ~25 GB; this container ran out at 211/221 ride splits).

Open items, in order: (1) full regression gate and X3 on the final commit (paired with `aec88d2`), do not commit
during the X3 run; (2) moving / receding / random-walk targets in the matrix (coordinator amendment, not run);
(3) R1 residual: one-sided far axis inside the near model's trust (a straight wall beside a curve); (4) the
115 m left-wall structure is a gauge detection in a few candidate frames (baseline: warning); (5) a real
moving-train Falcon recording; (6) a route-map source for `declared_straight_to`; (7) P1 reseal (the freeze
manifest no longer matches: `resense/config.py`, `detector.py`, `sensor.py`, new `farline.py`).
