# P4 evaluation of the sealed 1.1.0 detector — 16.10 (Linux cloud runtime)

Continues [P4_HANDOFF](../integration_2026-10-16/P4_HANDOFF.md) from checkpoint `492e407`.
Registered [PROTOCOL](PROTOCOL.md) (`058a451`, before measurement) with **amendment 1** (`d656158`,
OpenBLAS kernel, fixed on the v1.0.0 control before any 1.1.0 output existed).

| stage | result |
|---|---|
| A — checkpoint, seal, data | seal **PASS** in a clean LF Linux checkout, before and after native build; 36 files, `db3f588d…d751`. Archives match committed hashes. Node caches: **6 of 7 recordings byte-identical** to the Windows H0 inputs, Set O **1,509 / 1,510** frames (see below) |
| B — X3 on 1.1.0 | **PASS**: 260 / 260 directional rows; **all 40 cases identical** to the 707ea9c control in every metric |
| C — X1 attribution | [range_attribution_2026-10-16](../range_attribution_2026-10-16/README.md) |
| D — J1 preparation | dry run on 707ea9c **PASS** (193 STOP from frame 8; 4 episodes / 13 frames): [rejudge_2026-10-16](../rejudge_2026-10-16/README.md). Release J1 waits for H6/E1 |
| E — G3 | not touched |

## Identity and runtime

| | control | candidate |
|---|---|---|
| detector | exact `707ea9cd…` (v1.0.0) | `492e407b…` (1.1.0; detector tree equal to measured `5211565`) |
| config SHA-256 | `cb32e239…` | `39367802…` |
| native `.so` (both identical bytes) | `b3323fdd…` | `b3323fdd…` |
| X3 wall time, `-j 2` | 1,183.9 s | 1,186.1 s |

Runtime: claude.ai cloud container, Intel Xeon @ 2.1 GHz (AVX-512), 4 vCPU, 15 GB; CPython 3.10.12,
numpy 1.26.4 (bundled OpenBLAS 0.3.23), scipy 1.13.1, scikit-learn 1.5.2, g++ 13.3 with the
committed flags; one BLAS thread per worker, **`OPENBLAS_CORETYPE=Haswell`**. Both runs fit the
30-minute target. This is neither the specified 4-vCPU team VM nor the H5 Docker image; timing is
informational. Harness commit for both batteries: `dd1814e`. Commands are in the logs next to the
JSONs; external raw outputs are indexed in [raw_sha256.json](raw_sha256.json) and archived durably in [raw/](raw/README.md).

## A. Inputs

[linux_intake.json](linux_intake.json) (`scripts/p4_linux_intake.py`): `meta.json` is byte-identical
for all seven recordings. Each frame's arrays, re-serialized as the Windows tool wrote them
(Python ≥ 3.11 `zipfile`, zip `create_system=0`), reproduce the committed Windows NPZ hash for
**every frame of the six organizer bags (2,488)** and **1,509 of 1,510 Set O frames**. Set O
`f_00332.npz` alone differs: same size and point count, different bytes. Three Linux decodes from
two independent extractions of the hash-verified archive are identical to each other, and frames
331 and 333 match Windows. So the committed Windows cache holds a different frame 332; which values
differ cannot be determined without that file. **Open for P1/P3:** hash the arrays of
`decoded/cloud_with_fake_obj/f_00332.npz` on the Windows machine. The difference has no visible
effect: every X3 Set O metric of the control equals Windows.

## B. X3 — runtime comparability, then 1.1.0

**Environment finding (amendment 1).** In the container's default environment, the first Linux control
equalled Windows on every **nominal** row but differed on **11 / 40** perturbed entries. Examples:
doubleT_obstacle dedup 191 vs 189 STOP, squareT roll +2° 26 vs 37 STOP frames, squareT pitch −2°
8 vs 7 episodes. That failed one judge reproduction row. numpy's OpenBLAS identifies this VM CPU as
"Prescott" and falls back to SSE3 kernels. With `Haswell` or `SkylakeX` kernels the worker reproduces
all 11 entries exactly ([blas_calibration/](blas_calibration/)). **X3 perturbation rows of an
unchanged detector move by a few STOP frames / one episode with the BLAS kernel alone**, so cross-machine
X3 comparisons must pin it. This is not a detector property.

**Comparability.** Under `Haswell` the Linux control equals the committed Windows v1.0.0 battery on
**all 40 entries and every metric** ([runtime_comparison_haswell.json](runtime_comparison_haswell.json)).
Driver identical (`9c599e3f…`); judge scripts and labels identical up to CRLF; judge reproduction
PASS (every historical figure exact).

**1.1.0 against that control** ([battery_1.1.0_linux_haswell.json](battery_1.1.0_linux_haswell.json),
`--reference` = the control, source/label/protocol identities checked, the reference's raw rows
re-validated): status **PASS**, **0 of 260** acceptance rows failing. The metrics of all 40 cases are
identical. Beyond the metrics, decision, nearest distance and every reported detection
(distance, centre) are identical in all **29,765** processed rows. This matches H5's gate-path finding
(0 changed STOP / warning flags). The historical judge figures ([judge_rows_1.1.0.json](judge_rows_1.1.0.json),
information only) are therefore also reproduced exactly by 1.1.0.

[x3_tables.md](x3_tables.md) has the full per-variant and per-object tables, and
[battery_table_1.1.0.json](battery_table_1.1.0.json) the compact numbers. P2 table (development-data
robustness, not held-out):

| input | platform false episodes | obstacle STOP | Set O inside hits |
|---|---:|---:|---:|
| nominal | 3 | 193/201 | 424/801 |
| pitch +2° | 4 | 192/201 | 414/801 |
| pitch −2° | 7 | 193/201 | 425/801 |
| roll +2° | 7 | 192/201 | 420/801 |
| 5 Hz | 9 | 95/101 | 200/401 |
| dropout 30 %, seed 7 | 14 | 154/201 | 403/801 |
| dedup | 3 | 189/201 | 406/801 |

1.1.0 = v1.0.0 in every cell. RoundT-squareT is zero in all ten variants. Dropout seeds 1/2/3 and
all per-object rows are in the JSON.

## Handoff to P1 / P3

* Seal digest measured: `db3f588df59184ad703436996f72bd94a91eca91dfcfe4a02655fcdd4397d751`.
* X3 **PASS** with no changed frame. No detector change was made or proposed.
* Pin `OPENBLAS_CORETYPE` (or use the same machine) whenever X3 or range numbers are compared
  across runtimes. The same applies to the release J1.
* Open: Set O frame 332 of the Windows decoded cache (above).
