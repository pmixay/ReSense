# L16 open-air repair acceptance on `main` `5fa865b` (20.10)

> **For:** P3 and the captain · **From:** P4 data session of 20.10 (handoff T1, second part,
> [`../p4_handoff_2026-10-20/HANDOFF.md`](../p4_handoff_2026-10-20/HANDOFF.md)) · **Detector code:** not touched ·
> **Candidate:** `main` `5fa865b` (P3's repair `4bf62f3`, merged after the F1a repair; committed source, clean tree,
> native kernels built) · **Reference:** `main` `99dab01`, the F1a-repaired main it was merged onto (the only detector
> difference is `resense/calibration.py`, 12 lines) · environment as in
> [`../f1a_acceptance_2026-10-20/README.md`](../f1a_acceptance_2026-10-20/README.md).

The handoff asks for gate + Falcon "vs `4cf8e27` (expected identical)". No commit `4cf8e27` exists in this repository;
the repair was merged onto `99dab01`, so that is the reference whose output must not change. `main` has since moved to
`111d613` (PR #44, evidence only: no file under `resense/`, `native/`, `configs/`, `ros2_ws/` or `scripts/` differs from
`5fa865b`).

## Answer

| check | expected | result |
|---|---|---|
| `fault_open_air.py`, correct full-revolution Pandar starting in open air (0.18 % of returns above the sensor), 450 frames | GO | **450 / 450 GO**, no directional cue, configured mapping confirmed ([`out/fault_open_air_l16.txt`](out/fault_open_air_l16.txt)) |
| the same, positive control on `99dab01` | FAULT | **450 / 450 FAULT**, false forward (0, 0, −1), conflict, fallback ([`out/fault_open_air_f1a.txt`](out/fault_open_air_f1a.txt)) |
| tunnel start (control), both trees | GO | 450 / 450 GO on both |
| gate against the seal baseline | pass | **PASS**, 8 gated rows better, none worse ([`out/gate_vs_seal.txt`](out/gate_vs_seal.txt)) |
| gate per frame against `99dab01` | identical | **15,269 rows, 0 differ** in any non-timing field (mount state included); 714 differ only in the latency health level; set F equal ([`out/identity_gate_99dab01_vs_5fa865b.txt`](out/identity_gate_99dab01_vs_5fa865b.txt)); the gate JSONs differ only in health ok / warn counts ([`out/gate_diff.txt`](out/gate_diff.txt)) |
| Falcon, the whole recording, against `99dab01` | identical | **4,443 rows, 0 differ**; track models byte-identical; 1,364 STOP rows ([`out/falcon_identity.txt`](out/falcon_identity.txt)) |
| X3 against `99dab01` | identical | **0 failed of 260**; all 40 cases equal in every row's decision, detections and warnings ([X3](#x3)) |

So the repair does what A1 asks on the review's scene and changes nothing on the recordings, set O, the ride, set F,
Falcon or X3.

## How it was checked

* The comparator finds a known difference: the same `cmp_frames.py` on `8c2bf51` vs `99dab01` (the F1a repair) reports
  2,087 differing rows, as in the F1a acceptance.
* `fault_open_air.py` is the review's script, unchanged, run on each tree with `PYTHONPATH=<tree>`; the reference run
  is its positive control (the bug fires there).
* The latency-only rows: the gate ran with 3 jobs beside the Falcon stream; the health level is clock-dependent and
  excluded by the comparator's registered normalisation, as in every gate identity here.

Not checked by P4: the first 10 frames of the three marked synthetic bags on the repaired code (no longer on this
machine; P3's T1 covers all 12 starts, [`../l16_open_air_2026-10-20/README.md`](../l16_open_air_2026-10-20/README.md));
a real recording that starts in open air (none in the data, T1).

## X3

`robustness_battery.py` on the clean `5fa865b` tree, MEASURED, exit 0 ([`out/x3_l16.json`](out/x3_l16.json)),
compared with the `99dab01` run ([`../f1a_acceptance_2026-10-20/out/x3_f1a.json`](../f1a_acceptance_2026-10-20/out/x3_f1a.json))
by [`../f1a_acceptance_2026-10-20/scripts/x3_compare.py`](../f1a_acceptance_2026-10-20/scripts/x3_compare.py)
([`out/x3_compare.txt`](out/x3_compare.txt)): the battery's comparison **0 failed of 260**; the raw probe records equal
in decision, detections and warnings in **40 of 40** cases, every row; the only other fields that differ are the
latency health level and message (88 / 92 rows). The same comparator found variant B's 6 failures (positive control,
F1a acceptance). Raw records: [`out/x3_raw_5fa865b.tar.xz`](out/x3_raw_5fa865b.tar.xz); the reference's are in the F1a
acceptance's `out/`.

## Files and reproduce

`out/`: the outputs named above, `gate_l16.json`, the per-frame rows `gatework_l16.tar.xz`, the X3 summary and raw records.

**Runs of the shipped source for reuse.** The detector source of `5fa865b` is byte-identical to the sealed `cc6226e`
(`git diff 5fa865b cc6226e -- resense native configs ros2_ws` is empty). A switch review of the final source therefore
needs only the switch-off runs; compare them against: the gate's per-frame rows `out/gatework_l16.tar.xz` (and
`out/gate_l16.json`), X3 `out/x3_l16.json` with its raw records `out/x3_raw_5fa865b.tar.xz` (unpack to
`/home/user/out/x3/`, the summary's `raw_path`), and the whole Falcon recording through
`docs/evidence/f1_false_alarms_2026-10-19/scripts/falcon_trace.py`: `out/falcon/l16.jsonl.xz` (per-frame records,
4,443 rows), `out/falcon/l16.x.jsonl.xz` (track model and each detection's cluster per frame) and `l16.meta.json`
(stream intake: 20,281,548,800 bytes, 4,443 frames found and kept, 0 lost).

```
export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1
cd <tree> && RESENSE_REPO=$PWD PYTHONPATH=$PWD python <repo>/docs/evidence/p4_review_shipping_2026-10-20/scripts/fault_open_air.py $PWD
python scripts/regression_gate.py --cache <cache> --jobs 3 --work <work> \
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json --out <gate.json>
python docs/evidence/integration_2026-10-19/scripts/cmp_frames.py <work 99dab01> <work 5fa865b>
```
