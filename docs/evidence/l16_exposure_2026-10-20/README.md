# T1: is any real start exposed to the L16/S3 open-air FAULT? (20.10)

> **For:** P3 (the fix of review A1) and Pavel · **From:** P4 data session of 20.10 (the handoff's T1,
> [`../p4_handoff_2026-10-20/HANDOFF.md`](../p4_handoff_2026-10-20/HANDOFF.md)) · **Detector code:** not touched ·
> **Tree:** `972d19a` (`claude/k2-refinement-ty1aya`; `resense/calibration.py` identical to `main` `0acb18c` and
> `cefd4c4`), all K2 switches off · **Environment:** Python 3.12, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2,
> native kernels built, `OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1`.

## Answer

**No real start in the data is near the bug.** The smallest share of returns above the sensor in the first 10 frames
of any recording is **28.3 %** (`roundT_pressureGate_roundT`); the cue fires below about **1.5–2 %**. And the bug can
only fire on a scan whose forward axis is not itself one-sided, i.e. a full-revolution scan: among the recordings that
is only `doubleT_obstacle` (5.9 % of returns behind the sensor), which starts with **30.9 %** above it and gives no
cue. Every other Pandar recording, the ride and the marked synthetic bags are cropped forward (0 returns with x < 0),
so +X is the one-sided axis and the cue is the correct +X. Falcon gives +Y under the default (Pandar) mapping, which
is its real forward; the orientation search confirms `forward=+y` from frame 1, as designed.

So nothing in the data shows the A1 FAULT; it stays a risk for a full-revolution jury bag that starts in open air
(< ~2 % of returns above the sensor), as the review says. When P3 commits the fix: gate + Falcon on that commit vs
`4cf8e27` (expected identical; no recording here takes the changed branch) and `scripts/fault_open_air.py` (expected
GO) are still to run.

## Per recording (first 10 frames)

Decoded as the jury runner does (`judge_runner.NodeReplica`: `fastcloud` decode, then `R_vs`), the cloud
`MountCalibrator.update` receives. Shares over all returns; "sample pos" is the per-axis share of positive values in
`directional_axes`' own sample (stride to ≤ 16,384, |p| > 1 m), the numbers its 98 % test sees; "1-sided max" its
largest max(p, 1 − p); "cue" `directional_axes(xyz)` per frame; "locked" the calibrator's cue after the frame;
"conflict" frames with `orientation_conflict` set.

```
recording                            z>0 min/max     x<0 min/max   sample pos min (x,y,z)  1-sided max  cue  locked conflict identity
doubleT_obstacle                     0.3087/0.3091   0.0594/0.0598   (0.939, 0.554, 0.305)    0.9421    none  none     0     identical (10 rows)
doubleT_platform                     0.2900/0.2974   0.0000/0.0000   (1.000, 0.495, 0.288)    1.0000     +X    +X      0     identical (10 rows)
roundT_doubleT                       0.2953/0.2959   0.0000/0.0000   (1.000, 0.492, 0.282)    1.0000     +X    +X      0     identical (10 rows)
roundT_pressureGate_roundT           0.2827/0.2995   0.0000/0.0000   (1.000, 0.493, 0.284)    1.0000     +X    +X      0     identical (10 rows)
roundT_squareT_pressureGate_squareT  0.2951/0.2975   0.0000/0.0000   (1.000, 0.486, 0.280)    1.0000     +X    +X      0     identical (10 rows)
squareT_platform_squareT_switch      0.2940/0.2999   0.0000/0.0000   (1.000, 0.446, 0.287)    1.0000     +X    +X      0     identical (10 rows)
cloud_with_fake_obj (set O)          0.2847/0.2911   0.0000/0.0000   (1.000, 0.448, 0.284)    1.0000     +X    +X      0     identical (10 rows)
ride, split new_data_0               0.3023/0.3057   0.0000/0.0000   (1.000, 0.454, 0.299)    1.0000     +X    +X      0     identical (10 rows)
falcon_test (seyond)                 0.4659/0.4680   0.5562/0.5575   (0.442, 1.000, 0.457)    1.0000     +Y    +Y      1     identical (10 rows)
marked synthetic tunnels             0.2979/0.3000   0.0000/0.0000   (1.000, 0.494, 0.290)    1.0000     +X    +X      0     identical (10 rows)
marked synthetic platform            0.2911/0.2984   0.0000/0.0000   (1.000, 0.479, 0.280)    1.0000     +X    +X      0     identical (10 rows)
marked synthetic switch              0.3082/0.3148   0.0000/0.0000   (1.000, 0.457, 0.305)    1.0000     +X    +X      0     identical (10 rows)
```

Falcon's one conflict frame is frame 0 ("alternative orientation awaiting confirmation", decision FAULT for the view
check "6 of 6 central sectors without returns", as in the committed Falcon records); from frame 1 the message is
"sensor orientation found from the data: forward=+y left=-x up=+z" and the decisions are GO / CAUTION.

## How it was checked

| check | method | result |
|---|---|---|
| the probe does not change the runs | [`scripts/t1_probe.py`](scripts/t1_probe.py) wraps `MountCalibrator.update` / `directional_axes` read-only and runs the unmodified runner; a plain 10-frame run of the same runner beside it | 12 of 12 recordings: the probed run's records equal the plain run's in every field but timing ("identity" column) |
| the environment reproduces committed runs | Falcon's first 10 frames against the committed `integration_2026-10-19/runs/falcon_final_11bb1ab.jsonl.xz` | identical in every non-timing field (and later the whole recording, 4,443 rows: K2 v5c evidence) |
| positive control, synthetic | the review's [`cue_synthetic.py`](../p4_review_shipping_2026-10-20/scripts/cue_synthetic.py), re-run | full revolution, 0.2 % and 1 % above: forward (0, 0, −1); 3 %, 10 %: none; forward ±50°, 10 %: +X ([`out/cue_synthetic.txt`](out/cue_synthetic.txt)) |
| positive control, real cloud | [`scripts/t1_real_control.py`](scripts/t1_real_control.py): `doubleT_obstacle` frame 0 (full revolution), its returns above the sensor thinned at random to a given share | as recorded (30.9 %), 10 %, 5 %, 3 %, 2.5 %, 2 %: no cue; **1.5 %, 1 %, 0.5 %, 0.2 %: (0, 0, −1)** ([`out/real_control_doubleT_obstacle.txt`](out/real_control_doubleT_obstacle.txt)). So on the real scan geometry the bug fires below ~1.5–2 % |
| data are the originals | `Датасет.zip` sha256 against `scripts/cold_bags.sha256`; the six bags' `metadata.yaml` against `docs/evidence/bag_metadata/`; Yandex archives against the sha256 the public API reports; frame counts against VM_GUIDE §2.4 | all equal (set O 1,510, six recordings 201 / 345 / 252 / 268 / 545 / 877, ride 11,271) |

Not checked: how a real jury recording starts (the data has no open-air start at all); the fix itself (not committed
yet).

## Files and reproduce

`out/t1_table.txt` (the table above), `out/t1_runs.tar.xz` (per recording `<name>.t1.json` with every frame's numbers,
the probed and plain 10-frame records and their meta).

```
S=docs/evidence/p4_handoff_2026-10-20/scripts; T=docs/evidence/l16_exposure_2026-10-20/scripts
export RESENSE_REPO=$PWD PYTHONPATH=$PWD:$PWD/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
python $T/t1_probe.py <out>/<name> $S/judge_runner_set.py --bag <bag> --out <out>/<name>_probe --limit 10
python $S/judge_runner_set.py --bag <bag> --out <out>/<name>_plain --limit 10
# Falcon: the stream of falcon_test.zst on stdin, runner docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py /dev/stdin
python -I $T/t1_table.py <out> <name> ...
python $T/t1_real_control.py <doubleT_obstacle bag>
```
