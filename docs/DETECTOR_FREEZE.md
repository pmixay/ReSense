# Detector Freeze

> **Purpose:** what is sealed, how the seal is verified, the gate that validates it, and how a
> detector change would be accepted.
> **Audience:** team, jury · **Owner:** P1 (seal), P3 (detector) · **Language:** EN
> **Last verified:** 2026-09-28, experimental health source `ef71c9d`: source integrity and full default gate pass.
> **Status:** active user-authorized improvements; each detector change requires fresh acceptance and a replacement seal.

## What is sealed

**Current development reference:** `experiment/cross-ring-sparse-evidence`, combining
P3 work, validated low-object continuation and the exact-count health histogram optimization.
The [current seal](evidence/detector_freeze_2026-09-27.json) covers 34 detector,
configuration and build files, matching measured source `ef71c9d` with source digest
`c0273a13a67ab4872dab00154caa75f6b30f50416775062c591fbb47906a0fa4`.
The historical manifest filename is retained for CI.

The [full default gate](evidence/cycle_2026-09-28/health_histogram/default/README.md)
passes with all 208 compared metrics unchanged, including 146 enforced metrics, and no
waivers. All 15,269 real-frame payloads and 30 set F cases (3,060 actual rows) match the
combined P3 baseline outside verified timing effects. The
[previous P3 seal](evidence/cycle_2026-09-28/health_histogram/previous_p3_seal.json)
is preserved. This follows the user-authorized [improvement cycle](IMPROVEMENT_CYCLE_2026-09-28.md).

[Matched installed-image runtime](evidence/cycle_2026-09-28/health_histogram/runtime/README.md)
passes for the candidate: positive processing p95 105.15 → 76.32 ms, clear 77.33 → 60.51 ms;
all 201/252 original messages are processed and detections are identical.
Fresh positive availability improves from 0 to 170/201 frames, but current end-to-end p95
is 167.85 ms. This is one local warm pair, not target-hardware or cold-start acceptance.
The [previous experimental CI](evidence/cycle_2026-09-28/p3_sync/ci_25a218a/README.md)
is green in all four jobs; CI of the new health integration must be checked separately.

## How to verify

`python3 scripts/detector_freeze.py verify` (standard library only; no data, packages or Git
checkout) fails if a sealed file is added, changed or removed, if `configs/default.yaml` and its ROS
copy differ, or if the gate or baseline named in the manifest changed or no longer records a full,
passing, waiver-free gate. CI runs it in job `checks` on every push. It replays no data, and a file
replaced together with its recorded hash passes: a change to the manifest is reviewed like code.

## The gate that validates it

The [current health gate](evidence/cycle_2026-09-28/health_histogram/default/gate.json)
compares against the [combined P3 baseline](evidence/cycle_2026-09-28/p3_sync/default/gate.json):
all 208 compared metrics, including 146 enforced, are unchanged. Complete payload parity
covers 15,269 real frames and 30 set F cases. The node, launch, Docker and documentation
remain outside the seal and require their own checks. Main `059948a` changes the node;
the old-node health runtime must not be used as combined-node acceptance.

## How a change would be accepted

The user authorized continuing improvements on the experimental branch. A detector change needs, in order:

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
