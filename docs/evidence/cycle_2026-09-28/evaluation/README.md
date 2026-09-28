# Detector evaluation protocol — 28 September 2026

`protocol.json` fixes development and reserved evaluation seeds, geometry, placements,
metrics and acceptance before this cycle's detector candidates are measured. It supplements
the existing real recordings. Synthetic results cannot establish real-world transfer.

The production concern is sustained output: a single STOP somewhere in a sequence does not
count as reliable detection. The protocol reports target-matched STOP frames, visible-frame
recall, confirmation delay, consecutive STOPs, missed intervals, false STOPs and differences
between float clouds and the same clouds quantized to centimetres.

The reserved split must be run only after candidate source/config hashes are fixed. Its
results may reject a candidate. If those results inform another change, the split has been
used for development and a later report must say so.

The existing `tests/fixtures/synthetic_lidar_v1` is development data. Automated tests consume
its arrays and masks without Open3D. The broader generated protocol uses the existing round
tunnel raycaster and varies only parameters that it models consistently. Grade is fixed at
zero because its rail and bench meshes do not follow a nonzero floor grade; geometry stops
returning points at 210 m. New point clouds stay outside Git; reports retain compact per-frame
metrics, seeds, code/config hashes and input digests.

## Commands

From a checkout with the development dependencies and native kernels:

```sh
python3 -m pytest -q tests/test_synthetic_sensitivity.py
python3 scripts/synthetic_sensitivity.py generate --split development \
  --output /cycle/synthetic/development
python3 scripts/synthetic_sensitivity.py evaluate --cache /cycle/synthetic/development \
  --config configs/default.yaml --output /cycle/synthetic/baseline-development.json
```

Run the evaluator from the candidate checkout against the same cache, adding
`--baseline /cycle/synthetic/baseline-development.json`. Its exit status is nonzero when any
registered case/encoding metric regresses or either report has an incomplete split. A report
says `complete_split: false` if only a subset was generated. `--cases` permits a named
development subset without renumbering seeds; those measurements cannot pass the strict gate.
Generation can resume an existing cache only if the protocol, generator script and raycaster
match; it checks existing file hashes. Evaluating always verifies every input hash.

When a container cannot resolve the host worktree's Git metadata, pass `--source-commit` with
the host's `git rev-parse HEAD`. The report labels this as a supplied commit and independently
hashes every detector source/model file, the evaluator, effective config and native binary.
No timing comparison is reported while other workers share the machine.

Reserved evaluation uses `--split evaluation` when generating and requires
`--candidate-freeze <file.json>` for generation and both replays. The freeze record must
contain `baseline` and `candidate` objects, each with `commit`, `detector_source_sha256` and
`config_sha256` from their development reports. Generation and evaluation refuse source/config
hash combinations that match neither frozen identity and report which identity is running.
Keep that exact record with the comparison. Baseline and candidate run
on identical saved float clouds; compact16 is derived from those clouds during each replay.
Do not regenerate a different scene for the second detector.

Per-frame reports retain detection IDs, full-precision distances/centres/sizes, kind/reason,
health and the offline decision policy alongside matched flags. A reviewer can therefore
recompute physical target matches. The decision excludes the ROS freshness watchdog; it is
not presented as a live node replay. The initial development cache was generated with the
first evaluator revision. Its original script hash remains in its manifest; subsequent
reports record both that generator hash and the current evaluator hash.

## Checks added

The stored-fixture tests require a sustained, correctly located rail-object STOP after
confirmation, continuity across one missing-return frame, recovery after two/three missing
frames, rejection of a single-frame target transient, and release within 0.3 seconds of a
real removal. Longer dropout tests allow improved continuity instead of preserving the
baseline's known failure. Metric tests independently verify that one detection does not count
as sustained, distinguish invisible frames from visible misses, and enforce each registered
regression condition for each input encoding.

## Development baseline measured

All 35 registered development cases completed on the unchanged baseline detector at evaluation
commit `0991251`. The 560 generated float clouds were replayed as float32 and as the same clouds
quantized to compact16: 1,120 detector frames altogether. The complete per-frame report is
[`baseline-development.json.gz`](baseline-development.json.gz); its hashes, source/config
identity and per-case counts are in [`baseline-summary.json`](baseline-summary.json).

| Metric | Float32 | Compact16 |
|---|---:|---:|
| Sustained positive sequences | 19/32 | 19/32 |
| Matched STOP / visible target frames, including confirmation | 228/512 | 228/512 |
| Positive cases with no target returns | 0 | 0 |
| Unmatched STOP frames in positive cases | 0 | 0 |
| STOP frames across three negative controls | 0/48 | 0/48 |
| Clear distance extends past a visible target by more than 1 m | 208/512 | 208/512 |

All cases that detect confirm at frame 4 and keep the STOP through frame 15. The missed cases
are the rail box, 0.3 m cube and 0.5 m box at both 100 m and 150 m, plus the 0.3 m edge cube at
50 m. Every missed case still has labelled target returns in every frame. Persons are sustained
at all four registered distances through 150 m. The two encodings disagree on zero matched-STOP
frames on these particular scenes; this does not resolve the raw/cache disagreements already
measured on real recordings.

The cache is local at `/cycle/synthetic/development` in the shared development container
(`/home/likikikpa/ReSense-cycle-data/synthetic/development` on the host), roughly 1.1 GB. Its
generator script hash exactly matches `scripts/synthetic_sensitivity.py` at `871a105`; its
detector-source commit was recorded as `b9d2d4a` before the evaluator-only commit. The report
records both that generator hash and the revised `0991251` evaluator hash. The detector and
effective configuration did not change between those commits. Raw clouds are excluded from Git.

This is development evidence, with one simple stationary geometry per case. No reserved
evaluation clouds have been generated or scored. No detector improvement is claimed by this
baseline measurement.

## V1 geometry and stage audit

The historical positive labels above include boundary-contact cubes: a 0.30 m box on the bed
reaches exactly the canonical envelope floor because the synthetic rails are 0.18 m high.
The v1 development numbers are diagnostic and must not be read as an organizer-compliance
score. [The independent geometry/stage audit](diagnosis-v1.md) distinguishes physical body
intrusion from sampled returns and explains all 13 misses. It preserves the original protocol,
labels and results. All 448 traced outputs match the saved baseline after timing-only fields
are excluded.

## V2 registered before new generation

[`protocol_v2.json`](protocol_v2.json) is a separate prospective amendment. `protocol.json`
remains the CLI default so old commands reproduce v1; **pass `--protocol` explicitly for v2**.
No v2 cloud or detector outcome was observed before this amendment was committed.

Both low shapes now have 0.36 m height, giving 0.06 m of vertical envelope penetration above
the actual 0.18 m rails. `compact_box30` names the 0.30 × 0.30 m footprint; it is not a cube.
The reserved split scales these two footprints by 0.9 while preserving their height. The other
registered shape scaling, seeds, geometry and acceptance stay unchanged. Four negative controls
include a new central 0.30 × 0.30 × 0.10 m bed object whose top is 0.08 m below the rail head.
There are 36 sequences per split, 32 positive and four negative.

[`geometry-audit-v2.json`](geometry-audit-v2.json) records physical rail-head height, mesh top
and interior overlap for every case. Case expansion refuses positives without the registered
0.05 m minimum vertical overlap or a below-rail control that crosses the rail head. Generation
stores this audit in each case; evaluation additionally records per-frame counts of target
returns inside the known physical envelope, separately from all visible target returns.
No detector fit supplies those measurements. Auditing reserved parameter geometry does not
raycast reserved clouds or reveal detector outputs.

New development commands, to run only after the registration commit:

```sh
python3 scripts/synthetic_sensitivity.py generate --split development \
  --protocol docs/evidence/cycle_2026-09-28/evaluation/protocol_v2.json \
  --output /cycle/synthetic/development-v2
python3 scripts/synthetic_sensitivity.py evaluate \
  --protocol docs/evidence/cycle_2026-09-28/evaluation/protocol_v2.json \
  --cache /cycle/synthetic/development-v2 \
  --output /cycle/synthetic/baseline-development-v2.json
```

Reserved v2 generation remains prohibited until the exact baseline/candidate identities are
frozen and the full real regression gate passes. The existing `--candidate-freeze` source/config
guards apply to both generation and replay. A v1 report cannot be compared to v2: protocol
hashes differ. Reused development noise seeds and related synthetic shapes are not independent
trials or real holdout evidence.

To evaluate another frozen checkout without copying scripts into it, set
`RESENSE_DETECTOR_ROOT=/absolute/path/to/checkout`. The runner verifies the imported `resense`
package belongs to that checkout, hashes its detector/model/native sources, records its Git
commit, loads its default configuration and native library, and continues to use the runner's
own protocol/audit files. Plain `PYTHONPATH` is not an identity selector. For example:

```sh
RESENSE_DETECTOR_ROOT=/workspace/ReSense-continuity \
  python3 scripts/synthetic_sensitivity.py evaluate \
  --protocol docs/evidence/cycle_2026-09-28/evaluation/protocol_v2.json \
  --cache /cycle/synthetic/development-v2 \
  --baseline /cycle/synthetic/baseline-development-v2.json \
  --output /cycle/synthetic/candidate-development-v2.json
```


## Frozen candidate development results

The [complete development comparison](development-comparison.md) records the exact baseline
and `ef1d8f5` candidate on v1 and prospectively corrected v2. Both comparisons pass with no
regression **and no gain**; all public signals are identical (1,120 v1 and 1,152 v2 frame pairs).
V2 sustains 19/32 positive sequences, with 0/64 negative STOP frames per encoding. Its 13 missed
bodies do physically intersect the envelope; sampled-return visibility is reported separately.
The current candidate's continuity benefit is assessed by the separate dropout/real replay
checks, not these stationary sequences. Reserved data remain untouched.

The physical return counter now consumes the canonical profile stored in each generated case,
so future candidate profile changes cannot redefine independent truth. The documented profile
parity proof preserves all current v2 results and their original auditor hashes.
