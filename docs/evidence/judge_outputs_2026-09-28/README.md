# Per-frame outputs of the sealed detector (independent judge A, 28.09)

> **Purpose:** the per-frame outputs of the sealed 27.09 detector made by an independent judge,
> so that its quality figures can be recomputed and not only read from aggregate files; the
> figures recomputed from them with the team's own counting, and where they agree or disagree
> with the documented ones.
> **Audience:** jury, team · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-28: every figure below recomputed with `recompute.py` (this folder) at
> `d359a06`; the offline outputs of `doubleT_obstacle` and `roundT_doubleT` re-made and compared ·
> **Status:** current

## Why this folder exists

Before 28.09 the 27.09 detector's quality figures (the five empty recordings, the ride, set O,
set F) were committed only as aggregate files ([the gate](../results/regression_gate_2026-09-27_quality.json),
[the cross-fitted ride](../results/quality_cycle_2026-09-27/opinion_crossfit_2x_margin.json)),
so a reader could not recompute them; judge B gave them no credit for that reason
([both reports](../results/rejudge_2026-09-28.json)). Judge A of the 28.09 re-judgement ran the
sealed detector on every recording he could obtain and kept its per-frame output. This folder
holds those outputs unchanged (gzip), his scripts and logs, and a script that recomputes the
figures with the team's counting.

## Provenance

* **Who, when:** judge A of the fresh re-judgement of 28.09 (an independent reviewer agent in its
  own session; [report](../results/rejudge_2026-09-28.json), `judges[0]`), 2026-09-28 between
  08:37 and 09:12 (file times of his working folder, container clock), on a 4-vCPU Intel Xeon
  2.1 GHz sandbox.
* **Code:** commit `806b6c4` of `claude/amazing-fermi-t67v8g`, host Python 3.11 with
  `pip install -e .` (the C++ kernels built). Its detector source equals the seal:
  `python3 scripts/detector_freeze.py verify` → `Detector freeze PASS: 31 files; source
  298da6cc4fcbea98e002a94e1fe616d9c139db0f413e5c016745a97aee1fe66f` (judge A at `806b6c4`; the
  same line at `d359a06`, where `resense/`, `native/` and `configs/` are unchanged since
  `806b6c4`). Config `configs/default.yaml`, sha256 `a5acd921…e5e8ff57f47` (the set F files
  record it as `config_sha256`; it is the gate's `config.file_sha256`).
* **Reproduced here:** `resense run` on the two original recordings at `d359a06` gives the same
  per-frame output as `offline/dto_offline.jsonl.gz` and `offline/rt_offline.jsonl.gz` on every
  field except the timing and health fields (201 and 252 frames compared: detections, warnings,
  obstacle, nearest distance, clear distance, track model, mount). The other recordings were not
  available on the machine that wrote this README.

## Files and the commands that made them

| file | data | command (judge A) |
|---|---|---|
| `offline/dto_offline.jsonl.gz`, `offline/rt_offline.jsonl.gz` | the organizers' `doubleT_obstacle` (201 frames) and `roundT_doubleT` (252), the original rosbag2 directories | `resense run --bag <bag dir> --config configs/default.yaml --out <file> --quiet` (the command that reproduces them exactly, above; his own command line is not in his files) |
| `offline/empty_<recording>.jsonl.gz` (four files) | `doubleT_platform`, `roundT_pressureGate_roundT`, `roundT_squareT_pressureGate_squareT`, `squareT_platform_squareT_switch`, the `.db3` of each streamed out of the organizers' six-recording archive (Google Drive link in [`DATASET.md`](../../DATASET.md)) | `resense run --bag <.db3> --config configs/default.yaml --out empty_<recording>.jsonl --quiet`, run by [`provenance/stream_empty_bags.py.txt`](provenance/stream_empty_bags.py.txt); log [`provenance/stream_empty.log.txt`](provenance/stream_empty.log.txt) |
| `offline/seto_offline.jsonl.gz` | the organizers' `cloud_with_fake_obj` (set O, 1 510 frames), unpacked from their Yandex Disk link by `scripts/unpack_dataset.py` ([log](provenance/unpack_seto.log.txt)) | `resense run --bag cloud_with_fake_obj --out seto_offline.jsonl --quiet` ([log](provenance/seto_offline.log.txt): 1 510 frames); the recording's rosbag2 directory, not the team's 1 cm frame cache |
| `offline/ride_46.jsonl.gz`, `offline/ride_68.jsonl.gz` | the ride `new_data`, split files 46–48 and 68–70 (153 frames each), streamed from the organizers' `new_data.zst` by [`provenance/fetch_newdata.py.txt`](provenance/fetch_newdata.py.txt) ([log](provenance/fetch_newdata.log.txt): archive sha256 `8124b627…ab99ec`) | `resense run --npy` over a frame cache of those files made with `scripts/cache_frames.py` (the frame ids are the cache's `new_data_46_0000.npy` …); **the cache flags and the exact command line are not recorded** in his files |
| `set_f/setf_*.json.gz` and `set_f/*.summary.txt` | synthetic objects of the team's generator on the same ride cache (**team synthetic**, set F) | `python3 scripts/far_range_eval.py --cache <cache> --files 46,68 --kinds person,box0.5,box1.0,cable --start 220 --frames 110 --lateral -0.6:0.6 --place bed --placement-mode anchored --seed 0` (and `--seed 1`; `--jobs 8`), and `--files 46 --kinds person,trolley,box1.0,cable` with `--placement-mode legacy` / `anchored` (`--jobs 4`): reconstructed from the `parameters` block every file records |
| `node_set_o/status.jsonl.gz`, `node_set_o/dry_run_output.txt` | set O through the ROS node in Docker (`resense:ci`, the reviewed image of `806b6c4`), `/resense/status` captured | [`provenance/dry.sh.txt`](provenance/dry.sh.txt): `SKIP_BUILD=1 IMAGE=resense:ci scripts/dry_run.sh <cloud_with_fake_obj>` |
| `*_judge_matcher_score.json` | judge A's own scores with his own matcher ([`provenance/score_objects.py.txt`](provenance/score_objects.py.txt)) | as in his report |
| `provenance/runs_summary.txt`, `provenance/node_dry_runs_checker_output.txt` | his summary and the `scripts/check_dry_run.py` output of his 18 node dry runs of the two original recordings (base / reviewed image, warm / cold); the raw status captures of those runs are not committed | he passed `--max-p95-e2e 100` to the checker: the `FAIL` lines are that threshold, every other criterion passed |

The judge's own scripts are kept as `.txt` so that the repository's lint does not run on them.

## Recompute

```bash
python3 docs/evidence/judge_outputs_2026-09-28/recompute.py [--json out.json] [--bag <doubleT_obstacle dir>]
```

It applies `scripts/regression_gate.py`'s own counting (alarm frames; alarm events = distinct
confirmed track ids; STOP episodes; the labelled hits of `doubleT_obstacle` against
[`labels/doubleT_obstacle.json`](../../../labels/doubleT_obstacle.json); set O per object with
`scripts/score_fake_objects.py` against [`labels/cloud_with_fake_obj.json`](../../../labels/cloud_with_fake_obj.json))
to these files, and lists the non-STOP decisions after frame 75 in every committed node capture
of `doubleT_obstacle` (with `--bag`, also the two captures whose start-up skipped frames). It
needs no recording otherwise. Output, 28.09 (all **in-sample**: the team tuned the rules on
these recordings and on set O):

### Five obstacle-free recordings (real, 2 287 frames)

| recording | frames | alarm frames | events | STOP episodes | gate (1 cm cache), 27.09 |
|---|---|---|---|---|---|
| `doubleT_platform` | 345 | 3 | 1 | 1 | 2 / 3 / 1 |
| `roundT_doubleT` | 252 | 0 | 0 | 0 | 0 / 0 / 0 |
| `roundT_pressureGate_roundT` | 268 | 2 | 1 | 1 | 0 / 0 / 0 |
| `roundT_squareT_pressureGate_squareT` | 545 | 0 | 0 | 0 | 0 / 0 / 0 |
| `squareT_platform_squareT_switch` | 877 | 18 | 6 | 5 | 38 / 8 / 12 |
| **total** | 2 287 | **23** | **8** | **7** | **40 / 11 / 13** (the documented figure) |

The raw recordings give fewer false alarms than the team's cache (23 / 8 / 7 against
40 / 11 / 13), but not everywhere: `roundT_pressureGate_roundT` has a 2-frame STOP at 53.3–54.5 m
on the raw bag and none on the cache. Judge A's own count, 7 STOP episodes / 23 STOP frames
(1.0 % of frames), agrees with this recomputation.

### `doubleT_obstacle` (real)

| | raw bag, offline (these files) | ROS node on the raw bag (committed captures) | 1 cm cache, offline (the gate, 27.09; quoted until 28.09) |
|---|---|---|---|
| crossing person, frames inside the envelope | **61 of 61**, from frame 8 | 61 of 61 | 61 of 61 |
| object on the rail, frames 75–200 (after the person leaves) | **123 of 126**: no STOP at frames 111, 117, 197 | **123 of 126**: GO at 111, CAUTION at 117 and 197 | 125 of 126 |
| object on the rail, all its visible frames | 125 of 185 | — | 128 of 185 |
| alarm frames / STOP episodes | 190 / 4 | 190 STOP decisions | 192 / 2 |
| largest distance error (the gate's matching) | 0.24 m | — | 0.23 m |

The node column is the four 28.09 captures of the sealed detector in which the node processed all
201 frames ([`node_input_2026-09-28/`](../node_input_2026-09-28/README.md) `ab/base_obst_1`,
`ab/base_obst_2`, `ab/new_obst_2`, `cold_local/`; frame = the bag message index, `recompute.py`).
The CI capture of 27.09 [`cached_bags_run_36319767736`](../p1_p2_supported_playback_2026-09-27/cached_bags_run_36319767736/README.md)
(commit `2f23719`; by its person figures, 58 of 61 from frame 11, still the P3d detector) shows
the same GO at 111 and CAUTION at 117 and 197: the misses predate the 27.09 cycle. The two
captures whose start-up catch-up skipped frames (`ab/new_obst_1`, 191 frames; the first 27.09 CI
capture, 199) have STOP at 111 and 117 and CAUTION only at 197 (indexed with `--bag`): the misses
depend on the frames the detector has seen before. The cause is in the detector (documented, not
fixed: the detector is sealed): [`ALGORITHM.md`](../../ALGORITHM.md) §6 "Limitations of the
sealed 27.09 detector". The offline run on the raw bag and the node agree; the two offline runs
differ only in how the points are stored (the cache converts them to 1 cm int16,
`scripts/cache_frames.py --int16`; both use the bag's receive times as stamps), so the cache's
125 comes from that conversion.

### Set O (organizers' synthetic, 1 510 frames, in-sample)

| | raw bag, offline | through the node (judge A) | 1 cm cache, offline (the gate, 27.09) |
|---|---|---|---|
| STOP frames of the 8 inside objects / visible | **414 / 801** | **416 / 801** | 411 / 801 |
| inside objects with a STOP | 8 of 8 | 8 of 8 | 8 of 8 |
| 2 × 2 m box, first STOP | 98.0 m | 98.2 m | 98.0 m |
| 0.3 m cube on the rail: STOP frames, first STOP | 26, 48.0 m | 26, 48.0 m | 23, 42.7 m |
| plank across the rails, first STOP | 87.2 m | 89.0 m | 87.2 m |
| every other inside object | as the cache | as the cache | floating cube 55.8 m, edge cube 35.0 m, edge box 18.3 m by the scorer (its track from 28.7 m), box at the envelope top 111.4 m, hanging 30.1 m |
| false STOP frames on the outside 2 × 2 m box | **7** (from 142.3 m) | 7 | **6** (the documented figure) |
| background alarm frames | 0 | 0 | 0 |

**Why judge A counts 9 on the outside box:** his matcher accepts a STOP within 2.5 m laterally of
the box's centre (half its width + 1.5 m); `scripts/score_fake_objects.py` uses the evaluation
rule of [`EVALUATION.md`](../../EVALUATION.md) §2 (1 m laterally, one-to-one). The STOP
detections of frames 563–571 lie 0.7–1.0 m from the box's centre, except frames 569–570
(1.02–1.03 m): the team's scorer counts 7 of the 9, and on the cache 6. All three counts describe
one episode: a STOP at 126–142 m on the side of the box nearest the track.

### Ride segments and set F

* Ride `new_data` 46–48 and 68–70 (real, 306 frames, straight track): **0 alarm frames**, 2 and
  32 advisory frames. This is 306 of the ride's 11 271 frames; the 27.09 detector's full-ride
  figures (32 events in-sample, 37 on pieces the learned opinion never saw) still exist only as
  aggregates ([gate](../results/regression_gate_2026-09-27_quality.json),
  [cross-fit](../results/quality_cycle_2026-09-27/opinion_crossfit_2x_margin.json)); the per-frame
  ride output committed is the 26.09 (P3d) detector's
  ([`freeze_2026-09-26/gate_frames/`](../freeze_2026-09-26/gate_frames/)).
* Set F (team synthetic objects on those ride frames, anchored placement, 2 files × seeds 0 and
  1): person 4 of 4 approaches, first confirmed at 144–180 m, frames detected 82 of 100 at
  50–100 m, 65 of 94 at 100–150 m, 4 of 86 at 150–200 m; 1 m box 4 of 4, first 79–112 m; 3 cm
  hanging cable 4 of 4, first 46–88 m; 0.5 m box on the bed 2 of 4, first 42 and 64 m
  (`set_f/setf_anch_s*.summary.txt`). Not comparable with the gate's set F straight (six files,
  legacy placement, other kinds).

## Agreement with the documented figures

| documented figure (README, EXPERIMENTS, deck) | from these outputs | verdict |
|---|---|---|
| five empty recordings 11 events / 40 alarm frames / 13 STOP episodes (cache) | 8 / 23 / 7 on the raw recordings | the documented figure is the higher (worse) one; both are in-sample |
| object on the rail 125 of 126 | 123 of 126 on the raw bag, offline and through the node | **disagrees**: 125 is the cache replay only; the product path gives 123 with a GO at frame 111 |
| person 61 of 61 from frame 8 | 61 of 61 from frame 8 | agrees |
| set O inside STOP frames 411 of 801 | 414 (offline raw), 416 (node) | agrees within 5 frames; the documented one is the lowest |
| set O first STOP distances | the same except the cube on the rail (48.0 vs 42.7 m) and the plank through the node (89.0 vs 87.2 m) | agrees; the raw bag is slightly farther |
| outside box 6 false STOP frames | 7 (the team's scorer on the raw bag and the node), 9 (judge A's matcher) | **disagrees** by 1–3 frames of the same episode; the deck's 6 is the cache |
| ride 32 / 37 events | not recomputable (306 of 11 271 frames here, 0 alarms) | still aggregate only |
