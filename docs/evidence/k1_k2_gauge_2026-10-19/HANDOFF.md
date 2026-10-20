# K1 / K2 handoff (19.10, ~13:55 UTC) — P3 lane stopped at P1's request; v4 continues in the coordinator's session

Branch `det/k1-k2-gauge`. The v3 report (`REPORT.md`, "ship off") stands. Everything below is v4 work in progress.

## Code state

| commit | what |
|---|---|
| `83c8894` | v3 code: `track.axis_joint_fit` (K2), `track.walls_smoothing_distance` (K1); both off by default |
| `7dbdd64` | **v4 code**: new `track.axis_joint_range` (default **true** = v3 behaviour). v4 candidate = `axis_joint_fit: true`, `axis_joint_range: false`, `walls_smoothing_distance: 1.5` (`results/candidate_config_v4.patch`) |
| `fa2bf69` | PROTOCOL.md revision 3 (§8): the v4 rows are the v3 rows, unchanged, pre-registered before measuring |
| `d58b93f` | viewers draw the curvature step: `webapp/frontend/src/lib/track.ts` (`centerY`, `headingAt`, type fields), `web/index.html` (two axis lambdas); webapp suite 324 passed, the new test fails on the old code |

Off identity (both switches off) re-proven on v4: full gate `off4` vs base 0 of 425 rows, 0 frames differ;
B6 `track` rows identical on all ten recordings.

**Where "base trust-range policy + joint shape only" lives** (`resense/track.py`, `estimate_track`):
* `if joint is not None:` block — the joint shape (center, yaw, curvature, curv_step EMA, `_STEP_ZERO`) is set there;
  v3 then computes its own sides / disagreement / reach (`fits`, `far_ok`, `_followed_reach`).
* `if not cfg.axis_joint_range:` (right after the reach) — **v4**: overwrites `q, x_valid, n_sides, disagreement,
  x_valid_min, far_support_run` with the per-side fits' `est` (as without the joint fit), sets `one_wall = False` and
  keeps `model.curv_range` (EMA of `est`'s curvature).
* straight test: `bend = model.curv_range` when `joint is not None and not cfg.axis_joint_range`; the v3 hysteresis
  applies only with `axis_joint_range` true.
* new field `TrackModel.curv_range` (not serialised); config in `resense/config.py`, both YAMLs (`axis_joint_range`).
* test: `tests/test_k1_k2_axis.py::test_shape_only_mode_keeps_the_axis_shape_and_the_old_range_policy`.

## v4 results measured before the stop (`results/v4/`; X3, Falcon, display were NOT run)

| row | base | v3 | **v4** |
|---|---|---|---|
| K2-1 C wall error median 80/90/100/110/120 m | 0.72/1.03/1.39/1.90/3.43 | 0.40/0.47/0.51/0.52/0.56 | 0.40/0.47/0.51/0.52/0.56 (FAIL ≥ 100 m) |
| K2-2 C person first / held | 82.8 / 91.6 | 112.4 / 69.5 | 202.6 / 69.5 (FAIL held) |
| K2-3 B person first; 60–100 m | 51.8; 0/23 | 72.9; 8/13 | 72.9; 8/13 (FAIL) |
| K2-4 A person first / held | 218.4 / 221.8 | 165.2 / 179.6 | **218.4 / 221.8 (PASS)** |
| B6-2 roundT_doubleT off-track 90 m | 1.70 | 0.50 | **0.48 (PASS)** |
| B6-1 honesty > 1.05 m, worst | 30.8 % | 12.9 % | roundT_doubleT 9.1 %, synthetic_platform 16.4 %, roundT_squareT 9.6 %, synthetic_tunnels 7.2 % (FAIL) |
| B6-3 blinks | — | squareT 4→7 | roundT_doubleT 1→4, squareT 4→6, synthetic_tunnels 8→9 (FAIL) |
| K1-1 / K1-2 standing person 100 / 150 m | 82 / 90 | 255 / 78 | **255 / 197 (PASS both)** |
| K1-3 squareT false-STOP episodes (`probe.py`) | 3 | 0 | 3 (frames 309, 684, 705 at 147.8 / 146.8 / 144.3 m) (FAIL) |
| K1-4 doubleT_obstacle STOP frames | 193 | 188 | 188 (FAIL, first STOP 5 frames later) |
| K1-5 appear at 100 m, frames to STOP | 28 | 5 | 5 (PASS) |
| G-1 gate | exit 0 | exit 1, 12 rows | **exit 1, 19 rows**: set F first detections still worse (trolley 151.4 → 117.2, same as v3); ride events 27 → 32, episodes 30 → 35; roundT_squareT 0 → 3 STOP episodes; roundT_doubleT 0 → 1; set O background 0 → 14 alarm frames; `small_center` −2 |

Reading: v4 restores the trusted range (A person, standing 150 m) and keeps the curve accuracy, but **adds false
STOPs** on the moving recordings (ride +5 episodes, roundT_squareT +3, set O background +14 frames) — the old
range policy now extends trust over a curved axis shape whose far step is noisy on straight track (±2e-4 → up to
0.8 m at 150 m). Set F's first detections did not recover with the range; their cause is therefore not only the
trusted range (unexplained; check the set F per-sequence rows in `gate_cand4.json` against base).
Suggested next probe: zero the step unless its bend at 150 m exceeds a threshold, or require far support on both
walls for a step (review finding 4), then re-run the gate first (cheapest discriminating row).

## Commands (each tree = a worktree of the commit with the YAML switches set; `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`)

```bash
export RESENSE_REPO=$T PYTHONPATH=$T:$T/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1; cd $T
E=/home/user/ReSense/docs/evidence/k1_k2_gauge_2026-10-19
# gate (G-1), ~11 min with --jobs 2
python scripts/regression_gate.py --cache /data/cache --jobs 2 --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json --out out/gate.json --work out/gatework
python $E/scripts/gate_identity.py <base gate.json> out/gate.json <base gatework> out/gatework       # off identity
python $E/scripts/ride_episodes.py out/gatework                                                       # K2-5
# X3 (G-2): the tree must be committed (local commit of the YAML is enough)
python scripts/robustness_battery.py --repo $T --cache /data/decoded --out out/x3.json -j 2 --reference <base x3.json>
# B6 (B6-1/2/3, K1-3, K1-4): track + measure + probe + honesty per recording, then the table (both truths)
/opt/work/b6run.sh $T out/b6        # = gauge_stability.py track/measure + judgement probe.py + honesty, see scripts below
python $E/scripts/b6_table.py <base b6 dir> out/b6 <dir with poses_*.json and posesV_*.json> out/b6_table.json
python $E/scripts/k2_wall_error.py $E/results/k2wall/true_left.json 1 out/b6/track_roundT_pressureGate_roundT.json <base track json>   # K2-1
# range probes (K2-2/3/4, K1-1/2), ~20 min; ICP from icp_odometry.py on the decoded caches into /data/x1/icp
python $E/tools/prebuild_range.py --repo $T --tag cand --data /data --out out/range -j 1
# K1-5
python $E/tools/range_test.py out/range/cache_cand/squareT_platform_squareT_switch /data/x1/icp/icp_squareT_platform_squareT_switch.json out/K15 --obj 0.5,0.5,1.75 --start 450 --d0 100 --end 620 --appear 100
# Falcon (F-1), streamed ~5 min, nothing stored; wrapper adds the axis fields
python /opt/work/falcon_wrap.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out out/falcon
python $E/scripts/falcon_compare.py <falcon_full_v110.jsonl from falcon_full_2026-10-18/falcon_full_runs.tar.xz> <base falcon.jsonl> out/falcon.jsonl
python $E/scripts/falcon_person_match.py docs/evidence/n2_falcon_2026-10-18/raw_person_review/atlas_proposals.json out/falcon.jsonl
# display: docs/evidence/n1_n4_2026-10-18/replay_gauge.py --cache-root /data/decoded --rows out/disp/rows --reports out/disp <bags>
```

The helper scripts `/opt/work/*.{py,sh}` of this container (b6run, falcon_wrap, falcon_wrap_display, trackrun,
withcfg, capture) are not in the repo; `b6run.sh` = for each bag: `gauge_stability.py track <decoded> track.json`,
`measure track.json poses.json`, `docs/evidence/judgement_2026-10-13/scripts/probe.py <decoded> run`,
`honesty track.json poses.json run.jsonl`. `falcon_wrap.py` patches `judge_runner.record` to add
`k12 = {axis_valid, yaw, curv_step, y115, wall_drift}` and runs `scripts/stream_falcon.py`.
`posesV_*.json` = `b6_raw.tar.xz` poses with every ICP step of forward motion < −0.05 m set to `T: null`.

## Data (container starts empty; ~25 GB)

Originals: Google Drive id `1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu` → `scripts/unpack_dataset.py --only <bag>`, then both
`docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py <bag> /data/decoded/<bag>` (judge / B6 / range / X3)
and `scripts/cache_frames.py <bag> /data/cache/<bag> --every 1 --int16 --stamps` (gate); delete the bag.
Set O: `unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ`, same two caches. Synthetic: member
`new_synth_data.zst` of `https://disk.yandex.ru/d/SfBeRHbs8bNJAQ`, one bag at a time with `--only <bag>_cloud_only`
(the whole member is 13 GB), decoded cache only. Ride: `scripts/cache_extended_ride.py --cache /data/cache/new_data
--spool /data/.ride_spool --reserve-gib 3` (~17 min, resumable). ICP for the range probes:
`docs/evidence/rejudge_2026-10-16/scripts/icp_odometry.py /data/decoded/<bag> /data/x1/icp/icp_<bag>.json` (A, B, C, D).
Base B6 truth: `docs/evidence/gauge_stability_2026-10-18/b6_raw.tar.xz` (`poses_*`). Keep numpy 1.26.4 (a stray
`pip install matplotlib` upgraded it once; plot from a separate venv). Avoid `pkill -f` (matches your own shell).

## Open review items (`REVIEW.md`, `REVIEW_v3.md`), one line each

* **N1** — v3 range: take the reach after the rate limits and without the raw joint-fit floor (`max(joint x_max, …)`). Not used by v4.
* **N2** — K1: a stop before the axis has converged keeps a wrong, far-trusted axis for up to 60 s (rate limits at 5 %).
* **2** — v3 reach can rest on the raw joint `x_max` taken before the rate limits (partly fixed). Not used by v4.
* **3** — v3 one-wall cap applies only when the second wall ends ≤ ~54 m (partly fixed). Not used by v4.
* **4** — the curvature step is non-zero on most real frames: native kernels bypassed (latency) and far-axis noise ±2e-4 on straight track (likely v4's false STOPs).
* **7** — K1 at standstill: rate limits at 5 %, no age limit on the last confident speed, no trace of which branch fired.
* **8** — viewers: fixed in `d58b93f` (webapp, web); `detector_node.py:1063` radius text and `scripts/analyze_residual_events.py:288` still quadratic (text / analysis only).
