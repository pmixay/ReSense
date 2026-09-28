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
