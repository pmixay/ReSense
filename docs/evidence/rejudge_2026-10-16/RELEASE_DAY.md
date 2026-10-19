# J1 on release day — runbook (pre-built 16.10)

> **Captain's note, 19.10:** 1.1.0 will not be released. J1 runs on the **final 1.2.0 seal** after the 21.10
> integration (and its release image once CI works). The identity check below must then compare against the 1.2.0
> manifest that P1 writes at the reseal (today's candidate: `docs/evidence/detector_freeze_2026-10-18_b4_merged.json`,
> digest `68dee667…`), not the 1.1.0 tree `db3f588d…`. Expected values: on Pandar data the 1.2.0 candidate equals
> 1.1.0 (gate and X3 identical); on the Falcon recording `aec88d2` reproduces the 1.1.0 run frame by frame
> ([check](../falcon_head_check_2026-10-19/README.md)). A detector change integrated on 21.10 moves these
> expectations: rebuild the pre-release numbers on the final seal before scoring.

The release J1 (BACKLOG J1) runs on the accepted 1.1.0 release: tag, archive, image. Everything that does
not need the release image is already run on the sealed 1.1.0 tree and on 707ea9c as a control
([prebuild/](prebuild/)). On release day, only the identity check and the steps marked **left** remain.
Use one runtime throughout and pin `OPENBLAS_CORETYPE=Haswell`
([P4 amendment 1](../p4_eval_1.1.0_2026-10-16/PROTOCOL.md)); always set `RESENSE_REPO` to the evaluated checkout.

| J1 deliverable | state | how |
|---|---|---|
| identity: release tag / commit / image = sealed tree `db3f588d…`; `detector_freeze.py verify` PASS in the run log | **left** | `git ls-tree -r <tag> -- resense native configs setup.py pyproject.toml ros2_ws/src/resense_ros/config` must equal the measured tree; image ID and archive SHA-256 from the release |
| 8 per-recording CSVs: six bags | **pre-built** (pre-release) on `492e407` | [dryrun/dryrun.json](dryrun/dryrun.json): 0 decisions differ from 707ea9c; the 707ea9c dry run reproduces the judge |
| 8 per-recording CSVs: Set O | **left** (cheap) | `judge_runner.py --bag <cloud_with_fake_obj> --out …` (~1,510 frames), then `score_objects.py`. The X3 nominal Set O metrics are already identical between versions |
| 8 per-recording CSVs: ride `new_data` | **left** (~1–2 h, ~14 GB peak disk) | `stream_new_data.py` streams the 17 GB archive from Yandex Disk |
| range summaries | **pre-built**: all 37 jobs of `run_range_matrix.sh` + `run_range_extra.sh`, both versions | [prebuild/range_table.md](prebuild/range_table.md), `prebuild_range.py`; re-run on the release checkout only if the identity check fails |
| perturbation table | **done** | X3 on 1.1.0, PASS, identical to v1.0.0 ([P4 report](../p4_eval_1.1.0_2026-10-16/README.md)) |
| 4 Docker chain summaries | **left** (needs the release image) | `scripts/docker/chain.sh <image> <bag dir> <bag> <label> [play options]` for the 13.10 conditions (its table has five runs: 360° and 120° each with README flags and with the literal default `ros2 bag play`, plus a renamed topic; the card asks for four summaries) |
| `scores.json`, `delta.md` | **left** | a fresh-context agent scores against the 13.10 rubric; S1 stays FAIL; the selected runtime is measured |

## Pre-built range result (16.10)

* **707ea9c reproduces the judge's 13.10 range table** (first STOP / held, metres): A person 218 / 222,
  with dropout 209 / 204, ±0.5 m 218 / 222; 1 m 151 / 163; 0.5 m 135 / 83; 0.3 m and the low box 45 / 49;
  B 52 / 50 / 50 / 41; C 74 / 74 / 75 / 42; D 106 / 106. Probes: crossing at 130 m, receding 96–97 m,
  pole off axis never STOP, cable 60 / 43 m. S at 100 / 150 m: the judge's 83 / 92 are STOP *decisions* while visible;
  matched STOP frames are 82 / 90. Both counts appear in the summaries.
* **1.1.0 changes 2 of 37 jobs, both on recording C:** person first STOP 73.9 → **82.8 m** (STOP frames
  49 → 55, held 81.3 → 91.6 m) and 1 m cube 73.9 → **85.7 m** (49 → 57). These match the H5-era probe
  C-person 82.77 m / 55 STOP. The pole on the axis stays 82 / 177 STOP frames in both, as the handoff's A-axis 82/177.
* Per job: [prebuild/range_table.md](prebuild/range_table.md). Summaries `prebuild/summary_<tag>.json`
  (also in the P4 numeric export as stage `J1-range`). Every job output is in `prebuild/range_raw.tar.xz`
  (SHA-256 in `prebuild/SHA256SUMS`). Each version took ≈ 7.7 min at 2 workers on this container.

These are **pre-release** numbers; the judge score remains v1.0.0's 66/100 until the release J1 is scored.

## New recordings since 16.10 (added 18.10): run on the release too, reported separately

The 13.10 rubric does not cover these recordings, so they are **not part of the J1 score**. They are what the experts
announced for their own evaluation (criteria 1–3, second lidar), so they should be run on the release checkout with the
same runtime and reported next to J1 as observations. Every step below has been run on the 1.1.0 tree and 707ea9c.
Expected values are the pre-release ones; a difference on the release means the release is not the measured tree.

**One command does all of it** and checks the result against the committed evidence (frame by frame where there are
per-frame records):

```
PY=<python of the P4 runtime> DATASET_ZIP=<organizers' original archive> \
  docs/evidence/rejudge_2026-10-16/new_recordings/run_new_recordings.sh <release checkout> <work dir>
```

It ends with one line per check: `PASS`, `DIFF` (the release behaves differently: report it) or `MISSING`. Steps can
be run one by one (`... <work dir> synth score`), and disk peaks are in the script header. **Dry run 18.10** on the 1.1.0 tree
from a fresh work folder ([dryrun_2026-10-18_compare.txt](new_recordings/dryrun_2026-10-18_compare.txt)): **28 PASS,
0 DIFF, 0 MISSING**. It found and fixed two problems that would have broken release day: a broken download was
silently decoded (now retried and checked against each bag's message count), and the disk ran full (raw data is now
deleted as soon as it is decoded). The checker was tested with a doctored copy: it reports `DIFF` for one changed
frame out of 736. Fresh in that dry run: the seal check, the three synthetic downloads and decodes, the Falcon stream
and prefix, and `doubleT_obstacle` from the zip. Not fresh: the five other original bags and Set O (their caches were
linked; the same decoder, byte-identical in both versions).

What each step does and what it compares:

| step | command (release checkout `R`, the env of the P4 protocol) | pre-release result to compare | time |
|---|---|---|---|
| synthetic recordings, decisions | `docs/evidence/synthetic_labels_2026-10-17/scripts/run_probe.sh <tag> R <bag>` once per synthetic bag (judge `probe.py`, nominal, on the decoded caches under `/home/user/rs-data/decoded/`; [synthetic labels](../synthetic_labels_2026-10-17/README.md)) | STOP / CAUTION / GO: platform 185 / 135 / 66, switch 142 / 294 / 300, tunnels 126 / 223 / 196 | 1 min each |
| synthetic platform, scored (frames 0–314) | `score_objects.py` on the run restricted to frames 0–314 with `labels_synthetic_platform_0-314.json` | person first STOP **44.0 m**, edge box 86.8 m, outside box never; 0 unmatched STOP | seconds |
| Falcon, whole recording, one detector | `python scripts/stream_falcon.py https://disk.yandex.ru/d/SfBeRHbs8bNJAQ --out falcon_full` (streams 6.8 GB, stores nothing), then `check_b2.py` ([B2](../falcon_full_2026-10-18/README.md)) | 4,443 frames; CAUTION 3,062, STOP 1,372, GO 8, FAULT 1; person STOP from 124.8 m | ~5 min |
| Pandar ↔ Falcon switch in one node | `run_b3.sh` with `doubleT_obstacle` and the Falcon prefix ([B3](../falcon_switch_2026-10-18/README.md)) | second bag equals its stand-alone run on every decision, both orders | ~3 min |
| gauge range and stability | `scripts/gauge_stability.py track` per recording on R, then `measure` / `honesty` with the stored ICP poses ([B6](../gauge_stability_2026-10-18/README.md); poses in `b6_raw.tar.xz`) | identical track metrics; reported range p50 e.g. Set O 130 m; reported range > 1.05 m off: Set O 1.6 %, `roundT_doubleT` 40.1 % | ~20 min |

Disk: the synthetic caches are 1.8 GB; the Falcon run needs none. Record `detector_freeze.py verify` PASS with these
runs too.
