# P3 L16 / S3 author protocol — 19 October 2026

Base: `aec88d248fb1a48a275937607bd36c3587dc0dc9`, branch `det/l16-s3`,
Linux development VM `/home/aiops/resense`. Registered before candidate runs.
This is author development, not independent P4 acceptance, resealing or release.
No commits are authorized in this session; this saved protocol/test chronology
does not substitute for the committed-source acceptance required by the seal.

## Defect and hypotheses

L16: ring-free clouds do not supply B4 channel-axis evidence. A square tunnel
wall can satisfy the bed/rail check on a 90-degree remount. Forward sign
concentration alone cannot resolve roll about that same forward direction.
Evaluate a unique signed-forward axis (>98% same-sign finite returns), and
independently evaluate resolved broad/narrow angular coverage perpendicular to
that axis. Do not equate sign concentration with gravity. Ambiguous/degenerate
coverage must not supply a made-up up axis. Keep bed/rail checks and two votes;
never replace detections with a blanket pending-mount STOP suppression.

S3: transform/mask each candidate on a once-subsampled cloud of at most 60,000
points; normalize forward-count admission consistently with source sampling.
Bound evidence calculations, and avoid repeated expensive search when its
result has already been confirmed. Preserve supported recovery frame counts.

## Prospective checks

1. Reproduce current-source failure with ring-free real empty Pandar frames and
   available real Falcon inputs. Keep exact input/source hashes, transformations,
   old accepted mapping, decisions and raw examples. Full Falcon has real people
   and static alarms: it must NOT be labelled entirely empty.
2. Unit positive/negative controls: proper 24 rotations; signed-forward is
   rotation equivariant; forward sign does not resolve roll; balanced 360-degree,
   narrow pencil, one-sided/ambiguous coverage, invalid points and small inputs
   do not become independent up evidence. Preserve B4 channel-axis controls.
3. Ring-free Falcon ±90-degree and native-axis remounts vs explicit correct
   mapping; preserve positive person/object frames and first/last STOP. Report
   every added/lost frame and distinguish startup calibration shifts. Empty
   Pandar controls must gain no false STOPs. No broad closure without coverage.
4. S3 count every expensive candidate call on a >=350k input: <=60k points.
   Compare downsample admission with full forward counts. Search latency median
   of five calls on real doubleT_obstacle frame 50, 90-degree rotated: target
   <=60ms, label actual shared VM resources/load (no idle-4-vCPU claim).
5. Run affected calibration/health/replay tests, lint, and available full gate
   and X3. Uncommitted-author results are not relabelled committed acceptance.
   Record native/BLAS identity, input coverage and instrumentation parity.

Runtime: `RESENSE_REPO=/home/aiops/resense`, explicit PYTHONPATH, Haswell BLAS,
OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1. G3 is excluded.
