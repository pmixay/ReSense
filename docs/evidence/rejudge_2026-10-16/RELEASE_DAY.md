# J1 on release day — runbook (pre-built 16.10 on 1.1.0, retargeted 20.10 to the 1.2.0 seal)

> **Retargeted 20.10 (P4).** 1.1.0 will not be released (captain, 19.10). J1 runs on the **final 1.2.0 seal**: the R3 reseal,
> main `f56ad5e` (measured `0a472d6`), manifest [`detector_freeze_2026-10-20_1.2.0_r3.json`](../detector_freeze_2026-10-20_1.2.0_r3.json),
> 40 files, seal digest `6d091081769104657ecc2c0b06f53049647d4f6c7327b7429bbda92673782452`; the git tree of the sealed paths
> (`resense native configs setup.py pyproject.toml ros2_ws/src/resense_ros/config`) hashes to
> `014ad8fd61f1a4b6962952505cc0274c95744f476c0d8d501a9c8cbe27873e54` (identical on `0a472d6`, `47b220c`, `f56ad5e` and the
> docs-only commits after it). **The run is one command** once the captain has accepted that seal:
>
> ```
> PY=<P4 runtime python> DATA=<decoded caches + x1/icp> BAGS=<six organizer bags + cloud_with_fake_obj> DATASET_ZIP=<organizers' archive> \
>   docs/evidence/rejudge_2026-10-16/release_day.sh <release checkout> <work dir> --run
> ```
>
> Without `--run` it checks the identity and prints the plan; a wrong tree or digest stops it (exit 2). The identity step is
> tested (pass on this tree, fail on a wrong value); the other steps were **not executed** in this retargeting (no recordings
> in the container) and are the existing tools called with the paths of this folder. If the accepted seal is a later
> reseal, give the new `EXPECT_TREE_SHA` / `EXPECT_DIGEST`. The Docker steps still wait for the release image
> (`scripts/docker/chain.sh`, below). **Everything below the table that says 1.1.0 or 707ea9c is the 16–18.10 pre-release
> record; what to expect on 1.2.0, and what differs from it, is the section "On the 1.2.0 seal".**

The release J1 (BACKLOG J1) runs on the accepted release: tag, archive, image. The 1.1.0-era pre-build ([prebuild/](prebuild/),
[dryrun/](dryrun/)) stays as the reference for 707ea9c and for what 1.1.0 did. On release day, only the identity check and the
steps marked **left** remain. Use one runtime throughout and pin `OPENBLAS_CORETYPE=Haswell`
([P4 amendment 1](../p4_eval_1.1.0_2026-10-16/PROTOCOL.md)); always set `RESENSE_REPO` to the evaluated checkout (the script does).

| J1 deliverable | state | how |
|---|---|---|
| identity: release tag / commit / image = sealed tree (tree sha `014ad8fd…3e54`, seal digest `6d091081…2452`); `detector_freeze.py verify` PASS in the run log | **left** (`release_day.sh`, step `identity`) | `git ls-tree -r <tag> -- resense native configs setup.py pyproject.toml ros2_ws/src/resense_ros/config | sha256sum` must equal the value above; image ID and archive SHA-256 from the release. The image must carry the same sources: compare `resense/*.py` in the image with the tag |
| 8 per-recording CSVs: six bags | **left** (cheap; `release_day.sh` step `sixbags`). The 1.1.0 pre-build on `492e407` does **not** stand in for 1.2.0 | [dryrun/dryrun.json](dryrun/dryrun.json) is 1.1.0 / 707ea9c (0 decisions differ from 707ea9c; the 707ea9c dry run reproduces the judge). 1.2.0 on the X3 nominal cases (node-decoded caches): `doubleT_obstacle` 193 STOP frames, first STOP frame 8, `squareT_platform_squareT_switch` 11 STOP frames / 3 episodes, `roundT_squareT_pressureGate_squareT` 0: the 707ea9c anchors. The other three bags are not in X3: **not measured on 1.2.0 in the judge-runner path** |
| 8 per-recording CSVs: Set O | **left** (cheap; step `seto`) | `judge_runner.py --bag <cloud_with_fake_obj> --out …` (~1,510 frames), then `score_objects.py`. **Set O is not identical to 1.1.0 any more:** X3 nominal 452 → 457 STOP frames, 8 → 9 episodes (R3: the labelled hanging cable, first STOP 35.1 m instead of 30.1 m) |
| 8 per-recording CSVs: ride `new_data` | **left** (~1–2 h, ~14 GB peak disk) | `stream_new_data.py` streams the 17 GB archive from Yandex Disk |
| range summaries | **left for 1.2.0** (step `ranges`, ~8 min at 2 workers): the pre-build is 1.1.0 / 707ea9c only | [prebuild/range_table.md](prebuild/range_table.md), `prebuild_range.py`. H1 and the later switches changed the detector after the pre-build; known moves: the pole on the axis 82 → 114 of 177 STOP frames (H1, measured on `0f02b28`); C person (82.77 m, 55 of 153) re-measured unchanged on `0f02b28` only; E6 (34 of 59) unchanged on `0f02b28` and `0a472d6`; the other jobs are unmeasured on 1.2.0 |
| perturbation table | **done on the sealed bytes**, repeated on the release (step `x3`) | X3 on 1.1.0 was PASS, identical to v1.0.0 ([P4 report](../p4_eval_1.1.0_2026-10-16/README.md)); on the 1.2.0 source (`0a472d6` bytes): 40 cases / 29,765 rows / 260 comparisons PASS against the base, re-derived 20.10 ([P4 review](../p4_review_final_bundle_2026-10-20/README.md)); against the 1.1.0 table 30 of 40 cases are identical in frames, STOP frames and episodes, the 10 Set O cases gain 1–7 STOP frames |
| 4 Docker chain summaries | **left** (needs the release image) | `scripts/docker/chain.sh <image> <bag dir> <bag> <label> [play options]` for the 13.10 conditions (its table has five runs: 360° and 120° each with README flags and with the literal default `ros2 bag play`, plus a renamed topic; the card asks for four summaries) |
| `scores.json`, `delta.md` | **left** | a fresh-context agent scores against the 13.10 rubric; S1 stays FAIL; the selected runtime is measured |

## On the 1.2.0 seal: what to expect, and what the checks will print (20.10)

Derived from the committed final-source records ([R3 raw archive](../r3_completion_2026-10-20/), P4's own runs on `f56ad5e`,
[the final-bundle review](../p4_review_final_bundle_2026-10-20/README.md)); nothing here is a J1 result.

| item | 1.2.0 expected | against the 1.1.0 record the comparators still hold |
|---|---|---|
| identity | tree sha `014ad8fd…3e54`, digest `6d091081…2452`, 40 files | — |
| synthetic bags, decisions (`run_probe.sh`) | platform 185 / 135 / 66, switch 142 / 294 / 300, tunnels 126 / 223 / 196 (STOP / CAUTION / GO), identical to 1.1.0 in all 1,667 frames | `PASS` ×3. Four frames differ in `clear` (platform 316; tunnels 45, 52, 291; F1a switch-on, no decision) — the comparator does not look at `clear` |
| synthetic platform, scored | person first STOP 44.0 m, edge box 86.8 m, 0 unmatched STOP | `PASS` (the 20.10 final-source replay equals 1.1.0 in every detection) |
| Falcon, whole recording | 4,443 frames; STOP 1,364 / CAUTION 3,070 / GO 8 / FAULT 1; 7 STOP episodes | **`DIFF` is expected, not a finding:** `Falcon whole recording decisions: 4435/4443 frames equal`. The 8 frames are rows 4394–4401, STOP → CAUTION: the tunnel-ceiling episode at 9.4 m that H′ removes (checked 20.10 against the committed 1.1.0 record: exactly these 8 rows; the other 3,169 rows differ only in `curv` at 1e-18). Any other difference is a finding |
| Falcon stream complete | 4,443 of 4,443, 0 lost | `PASS` |
| Pandar ↔ Falcon switch | the second bag equals its stand-alone run, both orders | `PASS` expected (the prefix is 100 frames, far from row 4394); not re-measured on 1.2.0 |
| gauge range and stability | not re-measured on 1.2.0 | unknown: report `PASS`/`DIFF` as printed; L16 and F1a touch calibration and the low-object reference |
| X3 | 40 cases PASS against `r3_completion_2026-10-20/x3-a-candidate.json` | the 10 Set O cases differ from the 1.1.0 table by +1…+7 STOP frames (nominal 452 → 457) |
| ride | gate-level counts of the seal: 23 events / 26 STOP episodes / 111 STOP frames (the gate path, not the judge-runner CSV) | the judge-runner CSV of the ride is not measured on 1.2.0 |

**Runtime sensitivity (found 20.10).** The same H1 physical replay on the same source moves its moving-body onset distance by
up to 6.6 m (three scans) between the P4 runtime and Python 3.13 / numpy 2.5 without the native kernels, and flips no stationary
hit ([review §3](../p4_review_final_bundle_2026-10-20/README.md)). Run J1, X3 and any comparison with the committed numbers in
the one pinned runtime; a number from another runtime is not a regression and not an improvement.

**Order on the day.** (1) `release_day.sh <checkout> <work>` without `--run` (identity, plan); (2) with `--run` (about 1 h plus
downloads, ride separately); (3) the Docker chain summaries on the release image; (4) a fresh-context agent scores against the
13.10 rubric (`scores.json`, `delta.md`); S1 stays FAIL.

## Pre-built range result (16.10, on 1.1.0 and 707ea9c; stale for 1.2.0)

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
