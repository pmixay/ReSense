# J1 preparation — re-judge copy of the 13.10 tools and v1.0.0 dry run (16.10)

Status: **prepared; dry run PASS. The release J1 is not run** — it waits for H6/E1 (accepted CI,
merge, tag/image 1.1.0). The judge's 66/100 remains the **v1.0.0** score. Nothing here is a 1.1.0 score.

Protocol: [../p4_eval_1.1.0_2026-10-16/PROTOCOL.md](../p4_eval_1.1.0_2026-10-16/PROTOCOL.md) §D.

## Tool copy

`scripts/` is a byte copy of [`../judgement_2026-10-13/scripts/`](../judgement_2026-10-13/scripts/)
(`diff -r` empty at commit `058a451`); the 13.10 folder is never written. Runs use it with
`PYTHONPATH=<checkout>:<checkout>/ros2_ws/src/resense_ros` and **`RESENSE_REPO=<checkout>`** —
`judge_runner.py` reads `configs/default.yaml` from `RESENSE_REPO`, whose default
`/home/user/ReSense` is a real checkout path in this container; leaving it unset silently mixes
configurations.

## Dry run on exact 707ea9c (v1.0.0)

`judge_runner.py --bag <bag> --out <prefix>` on each of the six organizer bags, one detector per
bag, then `summarize_empty.py` on the five obstacle-free bags. Bags from the organizer ZIP
(SHA-256 `e2316680…68be`, matches the committed intake). Runtime: the Linux container of the
protocol (Python 3.10.12, numpy 1.26.4).

| anchor (BACKLOG J1 “done when”) | expected | measured | |
|---|---|---|---|
| `doubleT_obstacle` STOP frames / first STOP frame | 193 / 8 | **193 / 8** | PASS |
| five empty bags: STOP episodes / frames | 4 / 13 | **4 / 13** | PASS |

Per bag: roundT_pressureGate_roundT 2 frames / 1 episode (a low object at 54.5 m),
squareT_platform_squareT_switch 11 / 3 (147.6, 82.9, 139.9–145.8 m), the other three 0. All
episodes coincide with the 13.10 report's table. The 13.10 per-row CSVs (`raw.tar.xz`) are not
in Git or in the v1.0.0 release assets, so only these published anchors are compared.

## Pre-release 1.1.0 runner output (not a J1 result)

The same runner on the checkpoint checkout (`492e407`, sealed 1.1.0 detector tree) was run while
each bag was on disk, so the bags need not be extracted again. **Zero decisions differ** from
707ea9c in all 2,488 frames of the six bags (201, 345, 252, 268, 545, 877). Clear distance medians are lower (axis range cap of 1.1.0, as H5 measured on the gate path).
These are pre-release, unscored observations.

Files: [dryrun/dryrun.json](dryrun/dryrun.json) (counts, anchors, per-bag decision equality,
SHA-256 of every output incl. the external `.jsonl`), `dryrun/<tag>/<bag>.csv|.meta.json`.
The `.jsonl` records stay external (container `/home/user/rs-data/j1/`), indexed by hash.

## Pre-built for release day (16.10)

The judge's 37 range jobs ran on both versions: 707ea9c reproduces the 13.10 range table; 1.1.0 changes 2 jobs
(recording C, STOP now starts farther away: person 73.9 → 82.8 m, 1 m cube 73.9 → 85.7 m). What is left on
release day and how: [RELEASE_DAY.md](RELEASE_DAY.md).

## Remaining J1 work (after H6/E1)

On the accepted release commit / image: 8 per-recording CSVs (incl. Set O and the ride via
`stream_new_data.py`, ~14 GB peak disk), 31 range summaries (`run_range_matrix.sh`,
`run_range_extra.sh`; needs ICP odometry, built for X1 in this runtime), the X3 perturbation table,
the four Docker chain summaries on the release image, `detector_freeze.py verify` PASS in the run log,
then a fresh-context agent scores against the 13.10 rubric (`scores.json`) and writes `delta.md`.
S1 remains FAIL; the selected runtime is what is measured.
