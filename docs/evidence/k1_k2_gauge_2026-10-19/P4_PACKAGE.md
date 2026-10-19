# K2 / K1: the work package for P4 (P0, highest priority; set by the captain on 19.10)

> **Owner:** P4 (develop and measure). **Review:** P3 or a fresh agent, because P4 is the author of these changes
> and cannot review them. **Decides:** the captain. **Limit:** code stop 20.10 23:59 MSK; after that only
> measurements and documents.

## 1. What ships now (integration branch `claude/optimistic-mccarthy-z5nmwd`, `c9e8daa` and later)

**Variant B** = v5b without K1. The values are in `resense/config.py` and in both YAML files (`configs/default.yaml`,
`ros2_ws/src/resense_ros/config/detector.yaml`; keep them in sync with `scripts/sync_params.sh --check`):

```yaml
    axis_joint_fit: true               # K2: joint least-squares axis (rails + every tunnel-boundary segment)
    axis_joint_range: false            # its shape only; the trusted range keeps the base policy
    axis_joint_min_curvature: 0.0001   # the joint shape replaces the base axis only where the base estimator sees a curve
                                       # (write 0.0001: YAML reads "1e-4" as a string and the run crashes on frame 1)
    axis_joint_reach_cap: true         # on those frames the trusted range also ends where the walls stop following the axis
    walls_smoothing_distance: 0.0      # K1 (per-distance smoothing of the axis) OFF
```

How v5 works: [`V5.md`](V5.md) §1–§2. Code: `resense/track.py` (`estimate_track`, `joint_axis_fit`,
`_followed_reach`, the v5 block after the base estimate). Tests: `tests/test_k1_k2_axis.py` builds every variant from an
explicit all-off base (`OFF`, `_cfg`). `tests/test_late_candidates.py::test_shipped_k2_axis_in_the_station_scene`
checks the shipped axis in the station scene. The legacy station and hall tests pin the old axis (`_legacy()`).

## 2. What B gains and costs (measured)

Full gate on `cf58128` (F1a, H′, R3, L16/S3 on) with B's values as overrides
([`../integration_2026-10-19/runs/gate_k2B_cf58128.json`](../integration_2026-10-19/runs/gate_k2B_cf58128.json)).
The comparison is against the same configuration without K2 (`gate_int_11bb1ab_final.json`):

| row | without K2 | B |
|---|---|---|
| gate exit (seal baseline, no `--allow`) | 0 | **1**: 6 rows, all set O `small_center` |
| set O `small_center`: first STOP / held from / STOP frames / 50–100 m bin | 55.8 m / 60.8 m / 32 / 4 | **52.5 m / 57.5 m / 30 / 2** |
| ride STOP episodes (alarm events) | 24 (18) | **9 (7)**: 18 removed, 3 new (onsets at 24.1, 40.6, 91.8 m) |
| five empty recordings, STOP episodes | 11 | **0** |
| `squareT_platform_squareT_switch` STOP episodes | 11 | **0** |
| `doubleT_obstacle` obstacle on the rail, hits | 129 | 133 |
| set F cable recall 0–50 / 50–100 m | 50 / 49 % | 52 / 44 % |
| every other set O object and set F target, first STOP and held from | — | unchanged |

The captain accepted B with the `small_center` gate exception (19.10). The integration evidence lists the remaining
runs on the committed defaults: final gate, X3, the whole Falcon recording, the standing-person probes, and gate A
(B + K1). Each one is added there when it is measured
([integration README](../integration_2026-10-19/README.md)).

## 3. What to improve, in this order

| # | problem | evidence | where to look |
|---|---|---|---|
| 1 | **set O `small_center` is confirmed 3.3 m later** (55.8 → 52.5 m, 2 STOP frames fewer). This is the only gate failure, so it is what keeps the gate exception | gate B above; the same in v3, v4 and v5a ([`V5.md`](V5.md) costs table) | the joint shape on the curve frames of set O. Trace which candidate rule demotes or delays it (`resense/detector.py` candidate reasons; `scripts/v5/` has the attribution helpers) |
| 2 | **standing person at 150 m in front of the standing train** (probe `S_person_150`, squareT platform): v5b 0 / 260 STOP frames, base 90 / 259. 65 of base's 90 matched a static structure, so base's real hits were ≤ 25 | [`V5.md`](V5.md) K1-2 row. B (K1 off) is being measured on the integration branch | v5b places the person on its own straight axis at Y ≈ −0.95 m; the candidates are demoted `beyond_axis` (reach cap) and `beyond_height_ref` |
| 3 | **X3 robustness:** v5b fails 10 of 260 comparisons (tilt, dropout, 5 Hz; STOP frames lost on real objects; 2 extra set O episodes at −2° pitch) | [`V5.md`](V5.md) G-2 row; X3 of B is being measured | `scripts/robustness_battery.py` |
| 4 | **curve accuracy not measured for v5**: K2-1 (C wall error 80–120 m), K2-2 / K2-3 (persons on curves), B6 honesty / blinks | v3/v4 values in [`REPORT.md`](REPORT.md) and [`HANDOFF.md`](HANDOFF.md). The v5 gate-row proxy puts it at v3/v4 level (unverified) | needs the decoded caches of recordings B and C ([`HANDOFF.md`](HANDOFF.md) "Data") |
| 5 | 3 new ride STOP episodes under B (onsets at 24.1, 40.6, 91.8 m) | gate B per frame (`/data/work_f1/gate_k2B_cf58128/new_data_{5,6,7}.jsonl` frames 317, 923, 354 in this session; repeat with the gate) | joint-shape frames, as in v5b ([`V5.md`](V5.md) §6) |
| 6 | **K1** (`walls_smoothing_distance`): standing train STOP at 100 m 82 → 255 / 260 and fast appearance (28 → 5 frames), but on its own it adds false STOPs on `doubleT_platform` | [`V5.md`](V5.md) §6; gate A (B + K1) on the integration branch | `resense/track.py` `estimate_track(travel=…)`, `resense/detector.py` `_travel` |
| 7 | open review items of the K2 code: N1 (take the reach after the rate limits), N2 (a stop before convergence keeps a wrong, far-trusted axis up to 60 s), 2, 3, 4, 7 | [`REVIEW_v3.md`](REVIEW_v3.md) | — |
| 8 | Falcon row F-1 with K2 on | being measured on the integration branch | `docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py` + `scripts/score_falcon.py` (copy in the integration evidence) |

## 4. How to work

- **Rules** ([`PROTOCOL.md`](PROTOCOL.md), `CLAUDE.md`):
  - register a dated revision with the rows before measuring a new variant;
  - keep the pre-registered rows as they are;
  - every new switch is off by default, and off must be identical to the current commit (gate per frame);
  - never use G3;
  - set `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1` and `RESENSE_REPO=<tree>`.
- **Cheapest discriminating check first:** the full gate (about 15 min with `--jobs 2`):
  `python scripts/regression_gate.py --cache <gate caches> --jobs 2 --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json --out <out>/gate.json --work <out>/work [--set track.k=v ...]`
  Per-frame comparison: `docs/evidence/integration_2026-10-19/scripts/cmp_frames.py <work A> <work B>`.
  Its positive control is F1's switched-on candidate, which gives 2,716 differing rows.
- **Other runs** (commands and data sources in [`HANDOFF.md`](HANDOFF.md) "Commands" and "Data"; v5 helpers in `scripts/v5/`):
  - X3: `scripts/robustness_battery.py --repo <tree> --cache <decoded caches> -j 2 --reference <base x3.json>`;
  - standing-train probes: `docs/evidence/f1_false_alarms_2026-10-19/scripts/measure_probe.py <decoded squareT_platform> <icp json> <out> --obj 0.5,0.5,1.75 --start 360 --d0 150 --end 620`, with `F1_SET="track.k=v;…"` for overrides;
  - the whole Falcon recording: `falcon_trace.py`.
- **Hand-over to the captain:** a variant with its switch values, the row table against the current commit (with
  the captain's switches), every worse row stated, and the review by P3 or a fresh agent. The captain decides; P1
  measures the final commit and reseals.
