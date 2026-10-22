# Dead-switch cleanup: status at pause (22.10)

> Lane: dead-switch cleanup, branch `claude/cleanup-switches-1.3`, base `f24d939`. Paused on P1's request
> (usage limits). **This commit is work in progress: the test suite fails (see below), no identity run, no
> reseal.** `detector_freeze.py verify` will fail on this commit (detector files changed, no new seal).

## Done

* Inventory of every config field with `scripts/inventory.py` (code default, `configs/default.yaml`, the ROS copy,
  effective value under the `pandar128`, `falcon_ros`, `falcon_native` profiles). Result on `f24d939`: the code
  defaults equal `default.yaml` everywhere; the only profile differences are the Falcon `farrange` block
  (`enabled`, ranges, `far_min_height` / `far_max_length`). So "never on in a shipped profile" = off in the code
  default. History (`git log -S`) and the full per-key table are **not written yet** (see next steps).
* Removed (code paths, config fields, `default.yaml` keys, ROS copy synced with `sync_params.sh`):

| group | keys | status evidence |
|---|---|---|
| bed far-bin rule | `track.floor_far_min_width`, `floor_far_from`, `floor_far_min_standing` | 25.09 P3 bed_bin, off, never shipped |
| far wall support | `track.walls_min_far_support`, `walls_far_support_max_curvature`, `walls_far_support_frames` | 25.09, off (EXPERIMENTS 1h) |
| far rail check | `track.rails_far_check_enabled`, `rails_far_rings` (+ `configs/experimental_far_rail_rings.yaml`) | experimental, fails the gate (CHANGELOG 29.09) |
| disagreement hold | `track.axis_disagree_hold` | 27.09 P4 history, off |
| old K2 variants | `track.axis_joint_range` (v3), `axis_joint_reach_cap` (v5b), `axis_joint_reach_dual` (v5c); the v4 / v5 code paths | user 22.10 (DECISIONS 57): replaced by K2 union |
| K1 | `track.walls_smoothing_distance`, `walls_smoothing_min_k`, `walls_smoothing_standstill_speed`, `walls_smoothing_standstill_max` | user 22.10 |
| edge margin² | `gauge.edge_margin_per_100m2` | opt-in, fails set O |
| sensor-axis union | `gauge.axis_union`, `axis_union_range`, `axis_union_max_offset`, `axis_union_max_curvature` | 26.09 not shipped (safety review); superseded by `gauge.reference` 3 |
| cross-ring | `cluster.weak_min_rings`, `weak_min_points_with_rings`, `tracking.far_min_ring_count` (+ experimental YAML) | experimental; `Cluster.ring_count` kept (track-opinion feature) |
| column free-top | `cluster.column_free_*` (6), `tracking.column_free_min_spares`; `top_is_free` and helpers | withdrawn after H4 (WITHDRAWAL.md); `FrameRays` kept (H1 collision core); `Cluster.spared` kept, always False (opinion record layout) |
| far both sides | `cluster.far_axis_both_sides` | 25.09 neither mode shipped |
| short signature | `cluster.short_signature_max_length`, `short_signature_max_distance` | no-go 25.09 |
| shell | `cluster.shell_*` (8) | off since the 29.09 night safety review |
| retro | `cluster.retro_*` (4) | off since v0.5 |
| P4 history | `tracking.zone_min_votes`, `start_clean` | 27.09, off |
| fresh-stop evidence | `tracking.fresh_stop_evidence` (+ window, min_hits; + experimental YAML) | experimental; the onset-gate state shared with `explained_run` / ego veto kept |
| start-up | `tracking.low_min_seen_distance`, `lowobj.pending_advisory`, `pending_advisory_within`, `min_model_age` | 26.09 tried, not shipped |
| settle (S2) | `tracking.settle_*` (5) | user 22.10 |
| near-bed path | `lowobj.near_*` (11), `lowobj.min_length` | "off for good" (CAPTAIN 25.09) |
| local support | `lowobj.local_support_*` (6) (+ experimental YAML) | experimental |
| F1 b / c / options | `lowobj.rail_band_range`, `rail_band_margin`, `local_rail_cross_tol`, `local_rail_advisory`, `no_rail_low_within` | 19.10 off; F1 (a) `local_rail_margin` kept (on) |
| calibration refine | `calibration.refine_min_deg`, `refine_raw_trigger`, `refine_confirm_obs`, `refine_max`, `provisional_per_axis` | off since 26.09 |
| health | `health.latency_affects_decision`, `clear_lost_model`, `clear_cap_margin`, `clear_cap_points` | off (v0.6 behaviour / cost limit failed / R1 variants) |
| far range | `farrange.confirm_*` (6, `FarConfirm`), `axis_union_separate` | measured 19.10 / 21.10, off |

* `tracking.explained_reasons` default `column,overhead,retro,shell` -> `column,overhead` (the two reasons can no
  longer occur; no output change expected, to be verified).
* K2: `axis_joint_fit` true now requires `axis_joint_union` true and `axis_joint_min_curvature` > 0
  (`config.check_joint_config`, called by `from_dict` and `estimate_track`); otherwise `ValueError`.
* Loader: unknown keys already raise `KeyError` (unknown top-level sections are ignored, as before); the message
  now names a key from `config.REMOVED_KEYS` as removed in the cleanup. **Test not written yet.**
* The four `configs/experimental_*.yaml` deleted (`git rm`).
* `ruff 0.15.8 check resense ros2_ws/.../resense_ros`: passes.

Kept on purpose (shipped-off but with a plan, or ambiguous), to be listed in the final README:
`track.rails_axis_extension` (N6 continues), `farrange.declared_straight_to` (route-map plan),
`calibration.orientation_replay_frames` (captain's explicit opt-in, lidar_adaptation_2026-10-18),
`accumulation.estimate_speed` (CLI / node option), `dust.*` (user: keep), `gauge.lateral_growth_per_100m`,
`gauge.edge_margin`, `voxel`, enum values of shipped-on switches (`gauge.reference` 0-2, `stop_keep_thin` 2),
and the "false = old behaviour" side of every shipped-on bool. The 1.3 track-opinion model
(`resense/models/track_opinion_1.3*.json`) is classified **dead** (DECISIONS 54 / 56: off, no out-of-sample gain,
no plan) but **not removed yet** (it has `tests/test_track_opinion_13.py` and is in the seal).

## In progress / not done

* **Tests: 348 failed, 25 errors** on this tree (vs 3 environment failures on `f24d939` in this container:
  `test_docker_fixtures`, `test_rail_start` needs the ride cache, `test_lidar_proxy_hook`). Every failure is a test
  of removed code or of removed signatures (`clear_cap_distance(clusters, tracks, hcfg)`, `estimate_axis_from_walls`
  7-tuple without `far_support_run`, `low_candidates` without `with_near`, `estimate_track` without
  `ring` / `travel`, `FrameRays(xyz, h, dy, track, track_cfg)`, `find_clusters` without `dy_alt` / `frame_ring`,
  `Tracker.update` without `low_ok`). To do: delete the tests of removed switches
  (`test_column_free_top.py`, `test_low_local_support.py`, `test_cross_ring.py`, `test_fresh_stop_evidence.py`,
  `test_shell_attachment.py`, `test_lowobj_near.py`, `test_h4_spare_rearm.py`, the far-rail-ring parts of
  `test_far_rail_yield.py`, the settle / far-support / bed-bin / far-both-sides parts of
  `test_late_candidates.py`, ...) and convert the rest to the new signatures; full failure list:
  rerun `pytest tests -n 3`.
* Docs not updated: `gitbook/reference/configuration.md` (§ "Изменения 29.09" lists shell, experimental
  profiles), `docs/ALGORITHM.md` §5, `docs/EXPERIMENT_*.md` (3), `docs/README.md` line 114, docstring of
  `scripts/far_rail_yield.py`. Captain's files (CHANGELOG, README, DECISIONS, BACKLOG, DETECTOR_FREEZE) untouched.
* Evidence scripts under `docs/evidence/*/scripts` use old APIs; they are historical (pinned to their commits)
  and are left as is.

## Next steps

1. Fix / delete tests; full suite green (except the 3 environment failures).
2. Loader test (removed key -> `KeyError` naming the cleanup; unknown section ignored; K2 variant -> `ValueError`)
   and the doc paragraph in `configuration.md`.
3. Decide and do the 1.3 model removal; write the full inventory table with `git log -S` history into README.md.
4. Identity runs, reference tree `/home/user/wt/ref` = `f24d939` (native built): strict gate without `--allow`
   on both trees + every row equal; X3; Falcon both paths (stream, `falcon_multi.py`); marked bags; positive
   control (one switch changed on a scratch copy).
5. Reseal (`detector_freeze.py create`), point `DEFAULT_MANIFEST` at it, lint / sync / verify, push, CI, `READY:`.

## Data state in this container (not committed)

* `/data/cache`: six recordings (201 / 345 / 252 / 268 / 545 / 877 frames, match VM_GUIDE; two bag SHA-256 OK),
  set O 1,510 frames; `/data/decoded`: five recordings + set O (for X3). Dataset zip SHA-256 verified
  (`e2316680…68be`), then deleted.
* Ride: **65 of 221 splits** cached in `/data/cache/new_data` (intake stopped at the pause;
  `cache_extended_ride.py` resumes and reuses validated splits).
* Tools in `/home/user/tools` (copies of the integration 1.3 scripts with paths for this container).

## Blockers

None, apart from the pause. Note for the resume: the gate needs the complete ride cache.
