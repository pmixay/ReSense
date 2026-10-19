# H1 continuation: repaired initialization, unvalidated trajectory, main integrated locally

**Status: H1 OPEN. No validated far-axis/trajectory reference was obtained. No
push was performed.** This package preserves further reconstruction work and
checks of the locally integrated source. It does not relabel a reconstruction
as ground truth or claim closure from component tests.

## Source and integration

The remote advanced to `0acb18c` (PR #42). It was fetched and merged locally into
`det/h1-positive-core` as **`0f02b283a9a8ebeb8bccae76a7b12f23862206df`**.
The automatic merge had no textual conflicts, retained the H1 positive-core
implementation, and passed 252 affected H1/F1/K2/dust/far-range tests before
the complete gate. No production detector edits were made after that merge.
The organizer-marker intake was committed locally as `74a4990`.

The user authorizes pushing main **after actual blocker-free H1 closure**.
That condition is not met. Remote main and the local `main` branch were not
advanced by this continuation. The working H1 branch contains the fetched
remote changes, with source bytes pinned in execution receipts.

## Concrete error found in the earlier attempted reference

The earlier A sequence initialized geometric ICP at zero movement. Its first
step converged to about **0.335 m** and propagated a longitudinal alias through
the repetitive circular tunnel; the resulting pose chain reached about
**-40 degrees roll** by frame 100. Those poses were never accepted as truth.

An intensity-textured five-seed screen separates 0.341 m and 1.342 m solutions.
The latter has smaller raw intensity disagreement and a better joint score.
An **independent raw compact reflector**, selected at intensity >=100 in both
frames, shifts by **1.343043 m longitudinally**. This supports the 1.34 m mode
without trusting ICP. A reflector-centroid shift is not full SE3 ground truth.
See [reference amendment](REFERENCE_AMENDMENT.md).

## Reconstruction attempts and independent checks

The same **608 distinct real frames** are used: A 0–339 and C 0–267. None of
the reference tools imports detector state to select its reference geometry.

Full sequences were reconstructed by:

1. Generalized ICP initialized in the reflector-supported motion mode.
2. Intensity-textured, multi-resolution registration.
3. Generalized ICP after per-return timing compensation using the new motion.
4. Reflective-feature point-to-point registration.
5. Rolling scan-to-map generalized ICP, forward.
6. The same mapping backward, starting independently at the other end.

Their full trajectories, input hashes and per-step transforms are retained.
The initial longitudinal error is repaired, but the methods still disagree in
position and orientation. Backward A mapping loses capture again and is
explicitly rejected; the reflective per-step chain reaches implausible roll.
The plotted divergences are estimator failures, not asserted train motion.
`trajectory-methods.png` was inspected before drawing conclusions.

### Direct long-baseline validation

The fixed earlier frames are A 50/100/150/180/220/260 and C 0/25/50/75/100/125,
with requested rail stations 60/100/140 m. Future raw near-rail observations are
selected using the newly captured motion. The common physical crop is symmetric,
and registrations use three resolutions, two independent chain seeds and a
reverse solve.

**0/36 pass** the existing gates: projected seed agreement <=0.10 m, reverse
translation <=0.10 m, reverse rotation <=0.05 degree and common-region fitness
>=0.70. The independently recomputed **first failing gate** on every row is:

| Gate | Rows |
|---|---:|
| Seed disagreement | 4 |
| Reverse translation | 24 |
| Reverse rotation | 7 |
| Common-region fitness | 1 |

Positive control: an exact manufactured **80 m** rigid transform with partial
overlap passes this same validator from two perturbed seeds, with fitness 1.0.
The independent rotation-trace validator also accepts it, and rejects a planted
0.50 m transform error. A pre-control configuration using raw sample covariances
was found singular on exact planes; it is rejected and reproducible with
`--sample-covariances`. The final control and 36-row run use regularized GICP
plane covariances. Earlier rejected screen outputs are retained, not pooled
with the final validated tool configuration.

### Multi-view landmark bundle, separate validation tracks

The [registered landmark method](LANDMARK_BUNDLE.md) associates raw reflective
features without detector output and jointly fits poses and stationary landmark
positions. Every fifth retained complete track is excluded from optimization.

| Sequence | Training tracks | Validation tracks | Validation observations | Validation tracks with p95 consistency <=0.10 m |
|---|---:|---:|---:|---:|
| A | 109 | 28 | 685 | 13 |
| C | 106 | 27 | 500 | 16 |

An initial 100-evaluation solve did not converge. Both subsequent continued
solves reached the objective-change termination criterion, but validation still
fails on many tracks: p95 inconsistencies reach about **0.34 m on A** and
**0.33 m on C**. These are combined feature-association/centroid/reference-pose
errors, **not an independently measured pure pose-error distribution**.
All 1,185 validation observations and every reported percentile were recomputed
directly from raw observation coordinates and saved poses. Low training cost
does not turn this output into an accepted trajectory.

### Direct raw far-rail inspection

Registration-free bed cross sections were inspected on A frame 135 and C frame
55, in X slabs 15/30/60/90/120/150 m, each +-4 m, sensor-left +-7 m and raw Z
-3..-0.4 m. The same views show identified near-rail positive controls.
Distinct return counts are respectively:

* A: **5693 / 853 / 95 / 27 / 5 / 0**.
* C: **8205 / 1006 / 114 / 33 / 32 / 12**.

The inspected far views do not support a clear manually identified rail-head
pair at 120–150 m. This is a **two-frame inspection**, not proof that no possible
annotation or reconstruction from the whole dataset can work. The empty A150
slice is checked by the same path that finds thousands of near returns and
nonzero returns in the other far slices. The first proposed A180 positive
control lacked an accepted near pair, so it was replaced by the already
independently supported A135 sample; the failed attempt was not called a pass.

## Merged-source preservation checks

Execution receipts confirm unchanged source bytes for the gate, pytest and all
four critical probes. [Independent audit](audit-final.json) re-derives the facts.

| Check | Result |
|---|---|
| Complete original gate, no overrides/waivers | **PASS**, 15,269 ordinary frames plus Set F. All **208 non-timing metrics equal the published main integration gate**. Against the original seal: 190 same, 17 better, one worse informational row; no failing gated row |
| A-axis | **114/177**, every captured row identical to E; 63 visible unmatched rows remain |
| C-person | **55/153**, first STOP 82.77 m, every captured row identical to E |
| R3 E6 cable | **34/59**, first STOP 86.25 m, pooled held90 61.28 m; every row identical to E |
| Complete Falcon | **4443 frames**, 1372 ->1364 STOP frames relative to E; exactly frames **4394–4401** removed by main's H-prime ceiling filter, no added STOP and no other detection-payload change |
| Full pytest | **2276 passed +17 subtests**, **one inherited proxy-hook error-message failure**, eight external-data deselections, no skips |

The worse informational original-seal metric is Set F cable sustained median
(34.2 ->17.8 m), already present and documented in main's R3 integration. It is
not introduced by H1 or this merge. The full suite is **not all-green**: the
proxy-hook child exits the correct fail-closed code 86, but this environment
reports missing `resense` instead of the test's expected pinned-source message.
The failure and all raw logs are kept. X3 was not rerun on the merged source;
the earlier E X3 and main X3 do not certify the combined tree by themselves.

## Actual H1 status and required next evidence

The retained collision-core repair remains bounded by current observed rails
and validated geometry. A corrected first motion step, consistent seeds or an
optimizer convergence message do not establish the far rail axis. The remaining
63 A-axis misses, independent far-axis error budget, wrong-pair/no-rail limits
and independent final review are not closed by this work.

The next reference must have **independently verified spatial support** for the
100–150 m rail corridor, including curves. Neither obstacle-marker poses nor
unvalidated reconstructed poses provide it. These attempts do not prove that
all LiDAR-only methods are impossible; they document exactly why the available
outputs cannot yet be used to certify H1 or justify the conditional main push.

## Artifacts and reproduction

All exploratory and final outputs are in `/tmp/opencode/h1-trajectory/`.
`raw-evidence.tar.gz` and its per-member manifest retain them, including rejected
estimates, source snapshots and full gate/probe/test raw rows. `source.tar.gz`
pins the measured detector source and the final reference/audit tools.
`package.json` records runtime versions, input hashes and archive hashes;
archives are reopened and every member hash checked after creation.

Runtime: `/tmp/opencode/resense-b4-venv/bin/python`,
`RESENSE_REPO=/home/aiops/resense`, `PYTHONPATH=/home/aiops/resense`,
`OPENBLAS_CORETYPE=Haswell OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`,
`LD_LIBRARY_PATH=/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu`.

Tools in this folder accept explicit sequence/output arguments. Use fresh
output names. Example final direct check:

```bash
python docs/evidence/h1_trajectory_2026-10-19/direct_gicp.py \
  --new-seeds --out /tmp/opencode/h1-trajectory/direct-fresh.json
python docs/evidence/h1_trajectory_2026-10-19/validate_reconstruction.py
```

All inputs are real development recordings. No G3 set or new judging/release
run is used. Rejected trajectories are not installed in production or used
to tune the detector.
