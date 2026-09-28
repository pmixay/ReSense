# Detector Freeze

*На русском: [DETECTOR_FREEZE.ru.md](DETECTOR_FREEZE.ru.md).*

> **Purpose:** what is sealed, how the seal is verified, the gate that validates it, and how a
> detector change would be accepted.
> **Audience:** team, jury · **Owner:** P1 (seal), P3 (detector) · **Language:** EN
> **Last verified:** 2026-09-29: `python3 scripts/detector_freeze.py verify` PASS; the manifest's
> scope, gate and baseline against `scripts/detector_freeze.py`; the gate re-run of 28.09 ·
> **Status:** current; the detector is sealed and does not change before the submission

## What is sealed

The detector of the 27.09 quality cycle (detector `352ca13`, measured at `d572807`), sealed by
[`detector_freeze_2026-09-27.json`](evidence/detector_freeze_2026-09-27.json): the SHA-256 of its
31 files in `resense/` (the learned track opinion `resense/models/track_opinion.json` included),
`native/`, `configs/`, `ros2_ws/src/resense_ros/config/` and the build inputs `setup.py`,
`pyproject.toml`, `scripts/build_native.sh`; the configuration hashes, the measured commit, and the
validating gate and its baseline by path and hash. The ROS node code, launch file, Docker, CI and
docs are outside the seal, with their own checks.

## How to verify

`python3 scripts/detector_freeze.py verify` (standard library only; no data, packages or Git
checkout) fails if a sealed file is added, changed or removed, if `configs/default.yaml` and its ROS
copy differ, or if the gate or baseline named in the manifest changed or no longer records a full,
passing, waiver-free gate. CI runs it in job `checks` on every push. It replays no data, and a file
replaced together with its recorded hash passes: a change to the manifest is reviewed like code.

## The gate that validates it

[`regression_gate_2026-09-27_quality.json`](evidence/results/regression_gate_2026-09-27_quality.json):
every frame of the six recordings, set O, the whole ride and set F straight on the default
configuration, against [`regression_baseline_2026-09-26_ride_p3d.json`](evidence/results/regression_baseline_2026-09-26_ride_p3d.json):
PASS with no `--allow`, missing row or worse gated metric. The same run is the current baseline
[`regression_baseline_2026-09-27_quality.json`](evidence/results/regression_baseline_2026-09-27_quality.json);
re-run against it on the team VM on 28.09, identical but the informational latency rows
([`gate_2026-09-28/`](evidence/gate_2026-09-28/gate_table.txt)). Independent per-frame outputs:
[`judge_outputs_2026-09-28/`](evidence/judge_outputs_2026-09-28/README.md),
[`judgement_2026-09-28/`](evidence/judgement_2026-09-28/README.md). Measured quality and
limitations: [`SCORECARD.md`](SCORECARD.md), `docs/EXPERIMENTS.md`. The seal is an integrity
record, not a release, a deployment approval or a proof of safety.

## How a change would be accepted

None is planned before the submission. After it, a detector change needs, in order:

1. the defect and its acceptance test committed before any run; the patch reviewed, the affected
   tests passing, the detector committed;
2. the **full gate** on that commit (default configuration, the ride and set F cached as in
   [`VM_GUIDE.md`](VM_GUIDE.md) §2.3): exit 0, every gated metric identical or better, no
   `--allow`; a change meant to move the numbers commits its new baseline with it;
3. an **independent safety review** of the patch and its per-frame differences: no STOP lost,
   delayed or shortened on set O, the real obstacle, the range cases and the stress runs;
4. a **reseal**, reviewed: `create` refuses a gate with waivers, missing rows or overrides, or a
   sealed file that differs from the measured commit; then `DEFAULT_MANIFEST` in
   `scripts/detector_freeze.py` points at the new manifest and `verify` passes.

```bash
python scripts/regression_gate.py --cache /data/cache --jobs 4 \
  --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json \
  --out docs/evidence/results/regression_gate_<date>_<change>.json
python scripts/detector_freeze.py create --manifest docs/evidence/detector_freeze_<date>.json \
  --baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json \
  --evidence docs/evidence/results/regression_gate_<date>_<change>.json
```

Superseded P3d seals of 26.09: [`detector_freeze_2026-09-26.json`](evidence/detector_freeze_2026-09-26.json),
[`…_before_comment_correction.json`](evidence/detector_freeze_2026-09-26_before_comment_correction.json).
How the sealed detector came about: [`archive/QUALITY_CYCLE_2026-09-27.md`](archive/QUALITY_CYCLE_2026-09-27.md).
