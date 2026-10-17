# P4 evaluation of sealed 1.1.0 — protocol (registered before measurement)

Continues [P4_HANDOFF](../integration_2026-10-16/P4_HANDOFF.md) §3 A–D. G3 (§3 E) is not touched.

## Identity

| item | value |
|---|---|
| harness branch | `ccr-027997e8-kqywat` (the session's assigned branch; plays the role of the handoff's `p4/eval-1.1.0-20261016`), started at checkpoint `492e407b76d9dee7852f9e1884200e27939f0fca` = `origin/integration/2026-10-15-16` |
| evaluated 1.1.0 | detached clean checkout of `492e407`; `detector_freeze.py verify` (default manifest = 1.1.0) **PASS**, 36 files, digest `db3f588d…d751`, also after native build. Its tracked detector tree (`resense native configs setup.py pyproject.toml ros2_ws/src/resense_ros/config`) is identical to measured commit `5211565` (equal `git ls-tree -r` listings), so this measures the sealed 1.1.0 detector |
| control | detached clean checkout of exact `707ea9cda051369326fb9407c42488c1033dad76` (v1.0.0) |
| native | `python setup.py build_ext --inplace` with the committed Linux flags (`-O3 -g0 -std=c++17 -ffp-contract=off -fno-fast-math`), g++ 13.3.0; both checkouts produce the same `.so` bytes |

Runtime: claude.ai cloud Linux container (x86-64, 4 vCPU, 15 GB RAM, kernel 6.18), not the
team Windows computer, not the H3/H5 tools image `sha256:5e2659e8…`, not the specified 4-vCPU
team VM. To keep arithmetic comparable with H5 the Python stack matches the H5 Linux runs:
CPython **3.10.12**, numpy **1.26.4**, scipy **1.13.1**, scikit-learn **1.5.2**, PyYAML.
`PYTHONPATH`/`RESENSE_REPO` pin each checkout; one BLAS/OpenMP thread per worker; at most two
replay workers. Timings are reported as measured in this container, informational only.

## A. Data intake

Organizer archives are downloaded from the public links in `docs/DATASET.md` and must match the
SHA-256/sizes committed in [p4_start provenance](../p4_start_2026-10-15/provenance.json):
`Датасет.zip` 3,940,746,006 B `e2316680…68be`; `cloud_with_fake_obj.zst` 1,746,145,824 B
`d41c2fb2…96e9` (both already verified at intake, before this protocol). The ride is not needed.

Node float32 caches are built with the unmodified judge `cache_decoded.py` under the 707ea9c
checkout's imports, exactly as H0 built Set O. Disk is limited, so each raw bag is extracted,
used, and deleted. `scripts/p4_linux_intake.py` then must show, for all 7 recordings, that
`meta.json` is **byte-identical** to the Windows H0 inventory and that every frame's arrays
re-serialized as the Windows tool wrote them (Python ≥ 3.11 `zipfile`, zip `create_system=0`)
have the **exact committed Windows NPZ SHA-256**. NPZ file bytes themselves legitimately differ
across platforms (zip headers only). Any mismatch stops X3/X1 and is reported.

## B. X3 on 1.1.0

Driver: committed `scripts/robustness_battery.py` (SHA-256 `9c599e3f…7783`, identical to the
driver of the v1.0.0 baseline); judge scripts from `judgement_2026-10-13/scripts` (LF bytes; the
Windows hashes in the baseline are of CRLF bytes of the same content — verified by converting).
Four recordings × ten variants, `-j 2`, rules of the [P4 X3 protocol](../p4_start_2026-10-15/PROTOCOL.md).

1. **Linux control** on 707ea9c, `--judge-reference`. *Comparability* to the committed Windows
   baseline `battery_707ea9c.json` is established when every metric of all 40 entries is equal
   (paths/hashes/timing excluded). Differences, if any, are listed as environment differences
   and are never attributed to 1.1.0. The Windows raw rows are not available here, so the
   driver's `--reference` (which re-reads raw rows) uses the Linux control.
2. **1.1.0** with `--reference <Linux control>`. Acceptance = the driver's registered
   directional rule: per variant ≤ +1 false-STOP episode on each empty / outside / unmatched row,
   ≤ 2 lost matching STOP rows per positive object, ≤ 2 lost STOP frames on a positive recording;
   identical source, label and protocol identities. `--judge-reference` is not passed here: the
   historical ±1 judge figures describe v1.0.0, so for 1.1.0 they are computed afterwards as
   information, not as the acceptance status.
3. Report in this directory: full JSONs, per-variant/per-object table, source/input identities,
   explicit PASS/FAIL with reasons, compact P2 table. A FAIL goes to P1/P3; no detector change.

Prediction stated before running (from H5: 0 changed STOP/warning flags on 18,329 gate frames;
1.1.0 changes only the monitored / clear range cap): STOP decisions identical to the control on
the nominal rows. This is a prediction, not a criterion.

## C. X1 — range attribution

`scripts/range_attrib.py`, observation-only, wrapping the judge `range_test.py` (same object
placement, ray cast and scoring). Hooks only wrap functions and record arguments/return values;
they never alter returns. Proof required per run: the decisions/distances written with hooks on
are identical, row by row, to a hooks-off `range_test.py` run of the same case and checkout.
Ego-motion: judge `icp_odometry.py` on the decoded caches in this runtime (the Windows/P3 ICP
artifacts are not available here); the ICP JSON hashes are recorded.

Cases on both 707ea9c and 1.1.0 (judge matrix arguments): A_cube03, A_lowbox_rail, A_cube05,
C_cube05, D_cube05, S_person_100, S_person_150, S_cube05_100, B_person; the 5 cm cable E6 (from
the judge's extra-runs script); Set O frames 300–340 (small_center) and 760–790 (thin_hanging)
via `probe.py`-equivalent replay. Aliases: A = roundT_squareT_pressureGate_squareT, B =
roundT_doubleT, C = roundT_pressureGate_roundT, D = squareT_platform_squareT_switch.

Every visible non-STOP frame gets exactly one cause from a fixed precedence list (first failing
blob check / zone reason / tracker hold); `unknown` is a failure of the harness, not a result.
Control numbers from the BACKLOG card (A_cube05 first STOP 135.06 m, held 83.37 m, 66 STOP;
S_person_100 82 STOP) are checked on 707ea9c; a disagreement is kept and its scorer /
denominator / ICP origin investigated, never tuned away. Output: cause → frames per distance bin
in `docs/evidence/range_attribution_2026-10-16/`.

## D. J1 preparation

Scripts copied unchanged to [`../rejudge_2026-10-16/scripts`](../rejudge_2026-10-16/scripts)
(`diff -r` identical to the 13.10 folder, which is never written). Dry run on 707ea9c with
`judge_runner.py` on the six organizer bags and the judge `summarize_empty.py`: must reproduce
doubleT_obstacle **193 STOP, first at frame 8** and the five empty bags **4 episodes / 13 frames**.

Disclosure: because raw bags are deleted after decoding, `judge_runner.py` was started on each
bag for 707ea9c and, as **pre-release** 1.1.0 material, for the 492e407 checkout, in the same
intake queue, a few minutes before this protocol was committed. No output of those runs was
read before the commit. Pre-release 1.1.0 runner outputs are not a J1 result or a score; the
release J1 (8 CSVs, 31 range summaries, perturbations, Docker, `scores.json`, `delta.md`) waits
for H6/E1. Current 66/100 remains v1.0.0. Set O and the ride are not part of the dry run.

## Delivery

Commit this protocol and the intake tool first; then immutable summaries, hash indexes,
commands and reports. Raw outputs too large for Git stay in the container and are indexed by
SHA-256; this container is ephemeral, so the index — not the raw bytes — is the durable record.

## Amendment 1 — BLAS kernel (before any 1.1.0 measurement)

The first Linux control (707ea9c, default environment) equalled the Windows baseline on **every
nominal row** but differed on **11 / 40** perturbed entries (pitch / roll / dedup / two dropout
seeds), with byte-identical inputs on three of the four recordings. Its judge reproduction failed
one row (doubleT_obstacle dedup 191 vs 189). Cause: numpy's bundled OpenBLAS 0.3.23 identifies this
VM's Xeon as **"Prescott"** and uses generic SSE3 kernels; float matrix products then differ in the
last bits, which some perturbed frames turn into different decisions. With `OPENBLAS_CORETYPE` =
`Haswell` or `SkylakeX`, the battery worker reproduces **all 11 differing entries and the nominal
checks exactly** (every metric equal to the Windows baseline,
[blas_calibration/](blas_calibration/)). Kernel selection was calibrated on the v1.0.0 control
only; no 1.1.0 output existed or was read.

From here **all** detector replays in this evaluation (X3 control, X3 1.1.0, X1 both versions) set
`OPENBLAS_CORETYPE=Haswell` (the kernel numpy's build names as its base target). The full Linux
control is re-run under it; comparability with Windows is decided on that re-run. The first
(Prescott) control is kept as evidence of the environment sensitivity, not used as a reference.
The aborted Prescott X1 run (stopped after 5 cases, before any table) is discarded.
Consequence for readers: X3 perturbation rows are sensitive to BLAS kernel selection at the level
of a few STOP frames / one episode on these recordings, independent of the detector version.
