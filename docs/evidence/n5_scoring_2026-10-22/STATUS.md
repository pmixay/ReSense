# N5 scoring: status (22.10, paused, nothing scored yet)

Base `f24d939`. No detector file touched. No result below comes from a point cloud; all of it is from reading the repo.

## Findings so far (read from the repo, not re-run)

* **The scorer's requirement.** `scripts/score_team_labels.py` lines 87-89 reject any annotation row whose `n_points` is not an int >= 0
  (`n_points must be a nonnegative integer`).
* **The 34 null rows.** All 34 `box_left_0` rows in `docs/evidence/n5_markers_2026-10-20/labels_n5_marker_supplement.json`
  (tunnels, marker id 18, frames 4-59) carry `n_points: null` and `n_unique_points: null`, so the scorer fails on the first one
  (`00004/box_left_0`). Reading the file confirms the nulls for the first rows; the count of 34 is from the file's own `_meta` and from P4.
  Not re-counted here.
* **Where P4's findings are.** `docs/evidence/p4_review_final_bundle_2026-10-20/README.md` section 6. The BACKLOG link `[p4-n5]`
  points at the `n5_markers_2026-10-20` README instead (a mistake in BACKLOG.md; left for the captain).
  P4's findings on the 12 flagged rows: 3 match under the STOP-matching rule (switch 328, 330; tunnels 346), 6 are real returns
  3.4-5.0 m in front of marker 13 (switch 521, 523-525, 528, 529), 3 have no marker nearby (switch 510, 526, 527).
  P4 says "drop when scoring against the markers" is too strong. These are P4's numbers, not yet re-checked by this lane.
* **P4's quick fix is not enough.** `n_points: 1` makes the file score but is only a lower bound. The task asks for counts computed from the clouds.
* **Data.** `Датасет.zip` (sha e2316680...) is the six real recordings (recorded in the repo as the original archive), not the synthetic bags.
  The marked synthetic bags are in `new_synth_data_with_markers.zst` (2,533,631,921 bytes, sha256 `04d176b49526e5da55a0481cf92d8442604dc0fb9f69c31680482b21d8682760`),
  from the organizers' public Yandex Disk folder, fetched by `docs/evidence/integration_1.3_2026-10-21/scripts/markers.sh`.
  Nothing was downloaded in this lane: the permission check refused the first download script, and the second request came only from another session.

## Plan (not started)

1. Get the three marked bags (markers.sh, foreground, check size and sha256).
2. Compute `n_points` / `n_unique_points` for the 34 rows the way the existing label builders do; check against the 1,684 existing rows as a positive control.
3. Re-adjudicate the 12 flagged rows one by one against the clouds (P4's three groups above).
4. Positive controls: the scorer still rejects a malformed row; a known-correct row scores as a hit.
5. Replay v1.2.0 (`3b73bbe`, separate worktree) and 1.3.0 (this base) on the three bags, with `RESENSE_REPO`, `OPENBLAS_CORETYPE=Haswell`, `OMP_NUM_THREADS=1`;
   score per object: first STOP, held STOP, misses, change between versions.
6. List which N5 conditions are met and which remain; ruff 0.15.8, `detector_freeze.py verify`, full suite, push to `claude/n5-scoring-1.3` only, record each CI job.

Unverified: everything in the plan.
