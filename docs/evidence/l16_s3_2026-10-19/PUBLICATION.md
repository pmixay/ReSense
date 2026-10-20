# P3 publication handoff — 19 October 2026

The user requested publication of the L16/S3 implementation, tests and results
to `main` after clarifying that P1's quoted message was the task assignment.
This is publication of the P3 candidate, not a claim of independent P4 approval.

Before publication the working branch was fast-forwarded to main
`b637756c76e128edc50ebd1eb44dae66652d9996`. Its net changes against measured base
`aec88d2` are three JPEG files; detector/config/native source did not change.
All **46 source/test/native members** of `candidate_source_manifest.json`
match the publication checkout byte for byte. The earlier measurements retain
their actual uncommitted-source identities; none was relabelled as a fresh run
on the publication commit.

## Delivered

* Ring-free directional-FOV orientation recovery, bounded newly supported
  startup history, and canonical float32 coordinate application.
* S3 candidate-loop input cap at 60,000 points with full winner validation.
* 226 passing affected tests, complete actual Falcon / B4 controls and an
  18,329-row author gate, with all 208 non-latency metrics equal.
* Exact source, raw rows, manifests, rejected attempts and explicit limitations.

## P1 / P4 follow-up

The current default detector seal is still the predecessor B4 manifest.
`python scripts/detector_freeze.py verify` was executed before publication and
reports exactly two changed frozen files:

```text
Detector freeze FAIL:
- changed detector file: resense/calibration.py
- changed detector file: resense/detector.py
```

That integrity check is **not passing for this candidate**. Its failure is not
hidden by changing the old manifest. Formal X3 on the actual committed source,
independent P4 review and P1's accepted-bundle reseal remain pending. The source
fingerprint is `aacfd664bac988dfde9e911997b84589d409709af471af4bd758187e73b59c85`.
The detailed scope and the unresolved general/physical-mount limitations are in
[README.md](README.md) and `author_acceptance.json`.
