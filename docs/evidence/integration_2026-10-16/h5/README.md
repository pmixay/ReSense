# H5 — final committed 1.1.0 gate and detector seal

**Final full gate PASS, exit 0, on actual Linux Git HEAD
`52115654417a660669b8dddfce447692c1d782cc`.**

This executes the registered `PLAN.md` acceptance order: independent selected-scope H4
accepted at `70072f1300d922d7542a6b45688084e7a426d7c7`, then all four version declarations
committed at 1.1.0 in `5211565`, then this full committed gate. The selected numerical core
is unchanged from reviewed `c9aea87cb5322092070158cd8987115ee44833c9`.

The passing gate evidence is committed before creating the new seal from a separate clean LF
Linux checkout containing this exact evidence. The new manifest path is
`docs/evidence/detector_freeze_2026-10-16_1.1.0.json`; seal-session provenance is added after
actual creation/verification. The parent owns the default-manifest pointer and release docs.

## Gate acceptance and all-frame comparison

| Check | Result |
|---|---|
| Final measured commit / version | `52115654417a660669b8dddfce447692c1d782cc` / **1.1.0** |
| Full gate vs 29 September shell-off baseline | **PASS, exit 0** |
| Full metrics vs retained same-Linux sealed 707ea9c control | **PASS** |
| Non-latency rows vs either control | **208 / 208 identical** |
| Gated rows | **146 passed**, no regressions or missing rows |
| Overrides / waivers | `config.set=[]`, `gate.allow=[]` |
| Total comparison rows | **224**, including 16 informational latency rows |
| Normal recording/object/ride results | All six recordings + Set O + eight ride pieces: **15,269 frames** |
| Set F | All 30 sequences, **3,060 frames** |
| Complete raw + serialized frame comparison | **18,329 / 18,329 frames** |
| Final vs independently reviewed selection's captures | **Zero changed frames/entries**, outside registered timing telemetry |
| Observer coverage / comparison contract checks | **PASS / 6 passed** |
| Version declarations | Core init, pyproject, ROS setup and package XML all **1.1.0** |

Complete metric rows are in `analysis/metrics_vs_same_runtime.{json,txt}` and
`analysis/metrics_vs_shell_off_2026_09_29.{json,txt}`. Timing is informational only on shared
Docker CPU; the gate reports 836.5 s wall time. No timing gain is attributed to the detector.

### Exact differences vs sealed 707ea9c

Only the previously accepted axis range cap and additive metadata remain. STOP/warning flags,
nearest distance, reported detections/warnings and every preexisting raw candidate descriptor,
track-geometry field, mount/ego result and raw corridor-membership identity match sealed.

| Field group | Changed frames | Changed leaf/schema entries |
|---|---:|---:|
| Obstacle / warning flags | 0 | 0 |
| Nearest / clear | 1,834 | 3,668 |
| Reported detections / warnings | 0 | 0 |
| Candidate metadata | 12,781 | 51,412 |
| Track metadata | 18,329 | 20,751 |
| Health range/metadata | 2,422 | 12,774 |
| Ego/accumulation, mount, other result fields | 0 | 0 |

Counts include both raw/serialized representations and additive schema entries; frame groups
overlap. The new raw `wall_drift` field exists even when its no-cap value is `1e9`, which explains
the generic report's all-frame changed count. All **25,706** candidates have `cut=false` and
`spared=false`; the previous historical H1 candidate promotion remains absent.

Finite drift is annotated in **2,422 frames**. Monitored range is reduced in **2,131** and clear
distance in **1,834**, never increased. All three output range fields satisfy the existing
one-decimal `min(control_range, wall_drift)` equation in every frame: **54,987 exact checks,
zero mismatches**. Detailed per-field counts/examples and all dataset denominators are in
`analysis/explained_frames.json`. Set F's only changed scoring-row field is `mon` in **90 rows**;
placement, injected return counts, hit/false-detection scoring, candidate matching and visibility
are identical.

Among **2,432,861 common captured raw numeric values**, only the **5,799 expected range values**
differ. No other raw numeric or categorical result difference remains. This is a claim about
captured results, not every unrecorded intermediate or arithmetic operation. Raw corridor
membership dtype/shape/SHA-256 matches on all 18,329 frames, including decision-negative frames.

The only excluded telemetry is the registered `timing_ms`, specific health latency p95/basis/
sample-age fields, exact latency-budget messages and proven latency-only WARN severity with
decision_level=ok and no scene message. Both configs set `latency_affects_decision=false`.
The complete excluded audit and every raw/serialized change remain external and hash-indexed.

## Independent-review continuity and version-only proof

`analysis/H5_RESULT.json` authenticates the actual selected/review/final Git objects:

- All **36 frozen paths** and their inventories match, except the intended version strings in
  `resense/__init__.py` and `pyproject.toml`.
- Each of the four release declarations is an exact single `1.0.0 -> 1.1.0` replacement; all
  other bytes of those files match reviewed selection.
- Numerical source, native source/build flags and configs are byte-identical to the accepted
  selected scope. `analysis/reviewed_selected_to_final_versions.patch` preserves all four edits.
- Canonical/ROS configs still match; H1 master routes resolve 0.0, H2 and axis settings remain.
- Every raw and serialized selected/final frame is independently aligned and compared:
  **18,329 frames, including 3,060 Set F frames, zero non-latency changes**.

Selected-difference H4 acceptance and the inherited High 8.1 limitation remain as documented in
`../h4_selected/README.md`. No G3 held-out case or new tuning/probe variant is run by this H5 gate.

## Source, data and runtime identity

| Item | Identity |
|---|---|
| Final source digest | `db3f588df59184ad703436996f72bd94a91eca91dfcfe4a02655fcdd4397d751` |
| Canonical/ROS config SHA-256 | `3936780252f00cf0dc34c9205b5633738368a0d5c3bdc4f07200d21d3de6143c` |
| Effective config SHA-256 | `ba23b06f460934b63478bcae5160376249a912570926d0fc6b5521e5b1073562` |
| Native binary, identical to control | `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534` |
| Cache inventory, identical to control | `87ad4712a99a3aeef62230388baec9ffd2e86c24c5a2036d6899fdd295761d9c` |
| Immutable tools image | `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19` |

The measured checkout has **36 clean-LF frozen files**, each matching its measured Git blob;
`uncommitted_detector_changes=[]`, clean before/after. Native kernels are built there with the
unmodified build script. The generated ignored Linux `.so` is excluded from seal scope; no
Windows `.pyd` exists. Source/native/config/import/hardware provenance is retained.

Python 3.10.12, NumPy 1.26.4, SciPy 1.13.1, scikit-learn 1.5.2, Open3D 0.19.0; g++ 11.4.0.
Controls are `--jobs 2 --chunks 8`, actual receive stamps, default config, native enabled,
OMP/OpenBLAS/MKL/NumExpr threads 1, `PYTHONHASHSEED=0`, explicit checkout `PYTHONPATH` and
`RESENSE_REPO`. Docker limits are two CPU equivalents, 4.5 GiB memory and 2 GiB swap.
Complete sampled usage and final exit/OOM state are retained.

Input bytes/format are unchanged: **15,499 files / 9,659,917,289 bytes**, original cache mounted
read-only. Active gate/recording/Set F/cache/object-scoring scripts, label JSON and intake are
identical to the retained control, checked against measured Git blobs. The sealed control was
not repeated; its original before/after seal PASS logs are retained.

## Evidence and reproduction

External root:

```text
C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs
```

Final run: `candidate-52115654417a-20261016T110150Z-d9084fe4`.
Control: `baseline-707ea9cda051-20261016T060147Z-68fb3429`.
Reviewed selection's captures: `candidate-c9aea87cb532-20261016T101302Z-8a9ae4d1`.

`candidate/` and `baseline/` contain full gate JSON/metric rows, inventories, version/config/native/
hardware/input provenance and coverage checks. `frame_diff/` and `analysis/` retain complete compact
counts/examples and version-only/selected-frame proof. `EXTERNAL_ARTIFACTS.json` indexes every full
external frame/change/timing file. Raw JSONL remains outside Git.

`PACKAGE_MAP.json` and `PACKAGE_TRANSFORMS.json` identify exact copies, lossless JSONL-to-array
representation and compact text formatting. Original external bytes are unchanged; compiler
banners in the compact copy omit their final empty line. `HASHES.json` indexes compact bytes.

Re-run the full gate from the external root with the retained control/cache:

```powershell
$runs = "C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs"
python "$runs\helpers\gate_control.py" --commit 52115654417a660669b8dddfce447692c1d782cc
```

Exact clone/native/gate argv are in `candidate/commands.json`; analysis commands and exits are in
`analysis/analysis_commands.json`. The gate uses the fixed 29 September shell-off baseline, no
overrides or waivers. Helpers are archived here for restoration to an external evaluation root.

### Seal creation protocol

After committing this passing evidence, use `helpers/launch_seal.py --source-commit <EVIDENCE_COMMIT>`.
It creates a fresh unique Linux Git checkout, authenticates all frozen bytes against measured
`5211565`, confirms the gate JSON is committed and byte-identical to the measured output, builds
native, checks config sync and invokes exactly:

```text
python3 scripts/detector_freeze.py create
  --manifest docs/evidence/detector_freeze_2026-10-16_1.1.0.json
  --baseline docs/evidence/results/regression_baseline_2026-09-29_shell_off.json
  --evidence docs/evidence/integration_2026-10-16/h5/candidate/gate.json
```

It explicitly verifies the new manifest, retaining before/after source inventories and commands.
The manifest is copied byte-exactly to the host; its source commit is that evidence-containing
checkout, while its measured commit remains `5211565`. A subsequent clean committed checkout
verifies before/after rebuilding native, proving that ignored generated `.so` leaves the seal valid.

The parent can verify a later default-pointer/docs commit in the same pinned Linux environment:

```text
python helpers/launch_seal.py --source-commit <FULL_PARENT_COMMIT> --verify-only --use-default
```

That mode requires the parent's actual `DEFAULT_MANIFEST` to point to the new explicit path and
verifies it both before and after native generation. It creates no new manifest or detector change.
