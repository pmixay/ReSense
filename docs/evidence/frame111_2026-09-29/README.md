# The GO at `doubleT_obstacle` frame 111, re-checked on `main` — 29 September

> **Purpose:** whether the single GO at frame 111 (and the CAUTION at 117 and 197) that the 28.09
> judgement documented as a limitation of the sealed detector is still there on `main`, what removed
> it, and on what evidence.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-29 on `main` `6cafb28` (offline runs made here on the organizers'
> recording, node captures from the CI run of that commit) · **Status:** dated record

## Result

**It is fixed on `main`.** On `doubleT_obstacle` the detector reports STOP on 193 of 201 frames,
from frame 8 to the end, with no non-STOP frame after the first STOP; frames 111, 117 and 197 are
STOP (56.21, 56.14 and 56.15 m). The 27.09 detector, run in the same environment, gives 190 of 201
with the gaps at exactly 111, 117 and 197, as the judge recorded.

| run | STOP frames | non-STOP after the first STOP |
|---|---:|---|
| judge A's file, sealed 27.09 detector ([`judge_outputs_2026-09-28/`](../judge_outputs_2026-09-28/README.md)) | 190 / 201 | 111, 117, 197 |
| commit `464f5bc` (the 27.09 detector), re-run here, numpy path | 190 / 201 | 111, 117, 197 |
| `main` `6cafb28`, numpy path | 193 / 201 | none |
| `main` `6cafb28`, native kernels | 193 / 201 | none |
| `main` `6cafb28`, native, `tracking.stop_keep_low_s: 0` ([`no_keep.yaml`](no_keep.yaml)) | 190 / 201 | 111, 117, 197 |
| ROS node in Docker, CI run 36547463949 on `6cafb28`, cold-disk run | 193 / 201 results | none |
| ROS node in Docker, same run, warm-cache full-rate run | 193 / 201 results | none |

In both node runs frames 111, 117 and 197 are fresh results (`freshness.valid`). Only the start-up
results are not: the node is still catching up on the player's first burst, frames 0–21 in the cold
run and 0–12 in the warm run; those from frame 8 on are already STOP, the earlier ones FAULT or
CAUTION.

The obstacle-free control `roundT_doubleT` (252 frames) has no STOP on either detector, and the
same 173 frames with a warning (CAUTION) on both.

## Scored against the committed labels

The team's scorer on the same recording and the current detector
(`resense eval --bag <doubleT_obstacle> --gt labels/doubleT_obstacle.json --config configs/default.yaml
--text --labelled-only`):

| | |
|---|---|
| alarm frames / first alarm frame | 193 / 8 |
| alarm distance | 55.5 .. 56.6 m |
| false alarms | 0 frames, 0 events |
| person | 61 / 61 |
| object on the rail | 128 / 185 labelled frames on the raw recording; the gate on the compact frame cache has 129 / 185 and 126 / 126 from frame 75 ([`health_compare_counts/`](../cycle_2026-09-29/health_compare_counts/README.md)) |
| distance error | mean 0.04 m, max 0.24 m |

The labels were made with the team's own tools and are not independent ([`EVALUATION.md`](../../EVALUATION.md) §1).

## What removed it

The cause, found on 28.09 ([`cycle_2026-09-28/continuity/`](../cycle_2026-09-28/continuity/README.md)):
on the three lost frames the object's observed top is 0.093–0.096 m, just under
`lowobj.straddle_min_top` = 0.10 m, so the low-object stage forms no cluster, and
`tracking.hold_misses` = 1 covers only the first missed frame.

The fix that reached `main` in PR #27 is not the rejected global `hold_misses` 2 (ride 130 → 150 alarm
frames). It is a bounded continuation: with `tracking.stop_keep_low_s` = 0.3, a current straddle
blob that misses the height threshold by at most `lowobj.straddle_keep_height_margin` = 0.03 m may
continue an already reported low STOP for up to 0.3 s of sensor time. It cannot start a track or
confirm a new STOP. Setting `stop_keep_low_s` to 0 brings back exactly the 27.09 behaviour (last
row of the table).

## What this does not show

* **In-sample.** The rule was designed on this recording's three gaps, and this recording is the
  only one with a real obstacle. The result shows the gaps are closed, not that low objects that
  fade for longer than 0.3 s, or on other recordings, are held.
* **False alarms.** This check ran the two original recordings only. The cost on the ride and on
  the other recordings is the team's full-gate result
  ([`cycle_2026-09-29/health_compare_counts/`](../cycle_2026-09-29/health_compare_counts/README.md):
  ride 130 alarm frames / 32 events / 31 STOP episodes, person 61/61, rail object 126/126 from frame
  75; the seal is in [`DETECTOR_FREEZE.md`](../../DETECTOR_FREEZE.md)). That gate needs the 90 GB
  ride and was not repeated here.
* **Node runs are CI's.** The node captures come from the CI job `docker` of run 36547463949
  (artifact `p1-cold-dry-run-6cafb28…`, kept 30 days); the per-frame values are kept in
  [`per_frame.json`](per_frame.json) because the artifact expires. The node was not run here (no
  ROS 2 or Docker in the analysis sandbox); the offline runs use the same detector and give the
  same distances frame for frame.

## Reproduce

```bash
scripts/fetch_cold_bags.sh /data                 # the organizers' archive, sha256-checked (pins in scripts/cold_bags.sha256)
resense run --bag /data/for_hackathon/doubleT_obstacle --config configs/default.yaml --out main.jsonl --quiet
resense run --bag /data/for_hackathon/doubleT_obstacle --config docs/evidence/frame111_2026-09-29/no_keep.yaml \
  --out nokeep.jsonl --quiet                     # the ablation: 190 / 201 and the GO at 111 return
# STOP frame = the "obstacle" field of each line; 201 lines per run
```

The old detector: `git worktree add <dir> 464f5bc`, then the same command from a directory outside the
repository with `PYTHONPATH=<dir>` (a checkout of the current directory would otherwise be imported).
Environment of these runs: Python 3.11, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2 (the
Dockerfile's pins). `per_frame.json` holds the per-frame STOP flags and nearest distances of the four
offline runs and the decisions of the two node runs.
