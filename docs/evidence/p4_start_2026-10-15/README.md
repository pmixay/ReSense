# P4 H0 and X3: 15–16 October start

## Identity and H0 result

**H0 local reproduction: PASS.** The complete gate on exact
`707ea9cda051369326fb9407c42488c1033dad76` exits **0**, without `--allow`,
and all **208/208 non-latency rows match** the 29.09 baseline, including
informational rows. It replays **15,269 frames**, the ride in eight chunks,
and all 30 Set F straight sequences. Gate elapsed time: **778.05 s**.

| identity | value |
|---|---|
| evaluated detector / version | exact detached `707ea9cda051369326fb9407c42488c1033dad76` / **1.0.0** |
| evaluation checkout | `C:/Users/alikh/AppData/Local/Temp/opencode/rs-p4-baseline-707ea9c` |
| comparison baseline | `docs/evidence/results/regression_baseline_2026-09-29_shell_off.json`, recorded code `7464d80ec06f484ce1691b0ca7a87ce1ed82c5a0` |
| sealed source identity | `075a20df9fcdba6605a92e6505ae4dfdb3bf410ec09d17a8b3c79ce714db9292`; all **36 committed blobs match** |
| effective gate config | `873374a221e37da48fbe9d31806f7a26349399ed09f9b58d9768c1ae50a2916e` |
| local native binary | MSVC x64 `/O2 /std:c++17 /fp:strict`, SHA-256 `85a3dc5f9774a0962874a398028875a80deb66722a9b87f1a969408968cfe475` |
| harness | branch `p4/eval-start-2026-10-15`, based on `origin/main` `3fdc879`; protocol `fc9db80`, per-row label scoring `ea50f92`, final pre-X3 harness `6157dcd` |

The user explicitly selected this **Windows computer as the team runtime**.
The measurements use native Windows Python, with one BLAS/OpenMP thread per
worker and at most two replay workers. They are local offline detector
replays, not a Linux team-VM, live ROS node, Docker playback or stand latency
measurement. Docker Desktop was available (Engine 29.2.0 / WSL2); its
availability did not change the evaluation runtime. Details: [provenance](provenance.json).

The Windows checkout's `detector_freeze.py verify` actually exits **1**:
CRLF source/config/evidence bytes differ from the LF seal and the generated
`.pyd` is an added file. This is retained verbatim in [freeze_verify.log](freeze_verify.log),
not relabelled PASS. Independently hashing the **Git blobs** proves all 36
sealed committed sources equal the manifest. The runtime gate and strict
metric equality are separate evidence. No seal or default-manifest change
was made. A Linux/release checkout verification is still a separate check.

## Shared data paths

Use this shared root (`DATA` below):

```text
C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/
  for_hackathon/   six original organizer raw bags
  cache/          compact16 gate caches (NPY / lossless NPY.zst)
  decoded/        node-decoded float32 sensor-frame NPZ caches
  odometry/       P3's ICP / baseline-axis artifacts, available to other lanes
```

| recording | gate frames / raw receive stamps checked | decoded frames / raw headers and arrays checked |
|---|---:|---:|
| doubleT_obstacle | 201 | 201 |
| doubleT_platform | 345 | 345 |
| roundT_doubleT (C) | 252 | 252 |
| roundT_pressureGate_roundT (B) | 268 | 268 |
| roundT_squareT_pressureGate_squareT (A) | 545 | 545 |
| squareT_platform_squareT_switch (S) | 877 | 877 |
| cloud_with_fake_obj (Set O) | 1,510 | 1,510 |
| new_data (ride) | 11,271 | not needed by X3 |
| total | **15,269** | **3,998** |

Each recording is a subdirectory under `cache/` or `decoded/`. The missing
`decoded/cloud_with_fake_obj` was built here with exact baseline judge
`cache_decoded.py`, **1,510 frames**, without modifying the tool. Every node
NPZ was checked for float32 xyz/intensity, uint16 rings, finite coordinates
and consistent dimensions. Every metadata row agrees with raw header time,
receive time, frame id and topic; first and last raw payloads of each bag
were freshly decoded and match the NPZ arrays exactly. Every compact gate
array was read and checked, and every receive stamp matches original DB3.
Ride validation reports all 221 splits × 51 frames, with real gaps preserved.
`ride_validation.arrays_read=0` refers only to the second structural validator;
the preceding full inventory did read/check all 11,271 ride arrays.

Raw Set O: `D:/Datasets/ReSense/cloud_with_fake_obj`.
Raw ride: `D:/Datasets/ReSense/new_data`.
Odometry is shared P3 material, not recomputed or scored by H0/X3.

**Data provenance:** the local organizer dataset ZIP (3,940,746,006 bytes)
and Set O archive (1,746,145,824 bytes) were independently hashed here and
match the repository's published hashes. The ride archive's 17,078,961,996-byte
size / published SHA-256 verification and 221 payload-sample comparisons are
explicitly reused from P3 commit `527a76c`,
`docs/evidence/p3_start_2026-10-15/ride_intake.json` in `rs-range-screen`.
H0 independently rechecked every ride stamp and compact-array structure;
it did not repeat the archive hash or all raw ride payload decodes. Source
URLs, hashes and that attribution are in [provenance.json](provenance.json)
and [intake.json](intake.json).

### Gate summary (compact16 input, not the node-decoded X3 path)

* Five empty recordings: **39 STOP frames / 8 track events / 12 episodes**.
* Ride: **126 STOP frames / 27 events / 30 episodes** in 11,271 frames.
* `doubleT_obstacle`: **193 STOP frames**, first at **8**; labelled hits
  **190/246**, including **126/126** object-on-rail rows from frame 75.
* Set O: **411/801** inside-object STOP rows, **6** outside false-STOP rows;
  all 8 positive objects have STOP; background **0** frames / ids.
* Set F: all 30 sequences completed; every reported non-latency row equals
  the September baseline. [Strict comparison](gate_strict_comparison.json)
  retains every row and an empty `changed` list.

## X3 battery

**Complete: 40/40 cases, 29,765 processed frames, exit 0, 1,096.20 s
(18 min 16 s) at jobs 2.** This meets the 30-minute duration target on this
shared Windows runtime; it is not a measurement on the specified 4-vCPU VM.
The summary status is **MEASURED**. Every requested published judge figure
reproduces **exactly**, exceeding the required ±1 agreement; there is no
actual reproduction discrepancy to explain. RoundT-squareT remains zero in
all ten variants, including the newly added dropout seeds.

| variant | squareT false STOP episodes | obstacle STOP frames / processed | roundT-squareT false episodes | Set O matched inside / visible object-rows | Set O outside false frames / episodes | Set O unmatched frames / episodes |
|---|---:|---:|---:|---:|---:|---:|
| nominal | 3 | 193/201 | 0 | 424/801 | 9/1 | 6/6 |
| pitch +2° | 4 | 192/201 | 0 | 414/801 | 12/2 | 6/6 |
| pitch −2° | 7 | 193/201 | 0 | 425/801 | 7/1 | 6/6 |
| roll +2° | 7 | 192/201 | 0 | 420/801 | 9/1 | 7/7 |
| 5 Hz | 9 | 95/101 | 0 | 200/401 | 0/0 | 8/8 |
| dropout 30%, seed 1 | 12 | 178/201 | 0 | 403/801 | 6/1 | 10/8 |
| dropout 30%, seed 2 | 10 | 178/201 | 0 | 410/801 | 8/1 | 9/8 |
| dropout 30%, seed 3 | 13 | 178/201 | 0 | 407/801 | 7/1 | 6/6 |
| dropout 30%, judge seed 7 | 14 | 154/201 | 0 | 403/801 | 0/0 | 9/8 |
| dedup | 3 | 189/201 | 0 | 406/801 | 8/1 | 7/7 |

SquareT STOP frames, in that same order: **11, 20, 27, 37, 19, 56, 55,
51, 61, 20**. Thus nominal → dedup is 11 → 20 frames while episodes remain
3. Node-decoded Set O nominal is **452 STOP frames / 8 episodes** in 1,510
frames; the table separates matched positive rows from outside and wholly
unmatched false STOPs. All per-object rows and first-STOP ranges/indices are
in the JSON. [battery_table.json](battery_table.json) is the compact numeric
table; [SLIDE_TABLE.md](SLIDE_TABLE.md) is a short PT1 handoff.

X3 uses the judge's spatial-window matching, which can match multiple labels;
the gate's labelled-hit metric uses one-to-one assignment. Together with the
float32 versus compact16 input difference, this means the two hit-count
columns must not be subtracted and labelled a detector improvement.

The committed [protocol](PROTOCOL.md) defines the four recordings and ten
variants, label matching, seed control, no-overwrite evidence paths and
directional acceptance. The driver wraps the unmodified judge `probe.py`.
Its module-local RNG proxy changes only the probe seed, not the detector's
NumPy module. Source and protocol hashes are recorded in the consolidated
summary, along with the evaluated version/commit/import and native identity.

For a moving label, inside/outside intent is evaluated **per row**. Positive
acceptance uses matched inside STOP rows per object; outside episodes and
unmatched episodes are separate. Source/label denominators must match.
The directional comparison allows at most **one additional false episode**
or **two lost positive STOP rows**; `absolute_delta` and `worse_by` are
separate. Historical judge reproduction instead uses an **absolute ±1** bar.
A complete unreferenced baseline is **MEASURED**, not candidate PASS.

Closed-evidence verification re-read all 40 raw reports, exercised the actual
reference-validation path and 260 self-comparison metric rows, checked all
188 indexed measurement-file hashes, and confirmed input identities match
H0 and the measured driver hash still matches the committed harness.
[evidence_validation.json](evidence_validation.json) records this integrity
check, not a second detector measurement or candidate acceptance.

## Reproduction and evidence

Prerequisites: build the native module in the selected detector checkout
with `C:/Users/alikh/AppData/Local/Temp/opencode/resense-build-native.cmd`
(no arguments, cwd = detector checkout). Use the shared read-only Python
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe`.
For judge tools on Windows, include scratch
`C:/Users/alikh/AppData/Local/Temp/opencode` in `PYTHONPATH` for its RSS-only
`resource.py` adapter. Pin `PYTHONPATH` and `RESENSE_REPO` to the selected
detector checkout. The driver itself pins its worker imports and threads.

```powershell
python scripts/robustness_battery.py `
  --repo C:/Users/alikh/AppData/Local/Temp/opencode/rs-p4-baseline-707ea9c `
  --cache C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data/decoded `
  --out <existing-parent>/fresh-baseline.json -j 2 --judge-reference `
  --resource-adapter C:/Users/alikh/AppData/Local/Temp/opencode
```

For a future candidate use a fresh output and `--reference <baseline.json>`;
the driver revalidates the reference's raw rows and hashes before comparing.
The 1.1.0 baseline is **future H5/X3 work after that seal exists**. This run
does not establish a 1.1.0 result. No future G3 cases were run.

Retained complete raw evidence root:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-p4-runs-2026-10-15/`.
The gate work is `gate_work/`; battery reports are
`battery_707ea9c.raw/<bag>/<variant>/probe.jsonl`, with job plans, logs and
completion/identity sidecars. [raw_sha256.json](raw_sha256.json) indexes
retained files by their original external path, size and exact SHA-256.
Copied text evidence is normalized by Git; the index identifies original
run bytes at those external paths.

* [commands.json](commands.json): exact argv, pinned environment, cwd, exit
  codes, elapsed times and log paths.
* [intake.json](intake.json): full inventory, node payload hashes, raw stamp
  checks, ride intake attribution and committed seal-blob comparison.
* [gate_707ea9c.json](gate_707ea9c.json) and
  [gate_strict_comparison.json](gate_strict_comparison.json): measured full
  gate and strict equality of all 208 non-latency metric rows.
* [battery_707ea9c.json](battery_707ea9c.json): consolidated X3 measurements,
  source/protocol/runtime identities and absolute judge reproduction rows.
* [CHECKS.md](CHECKS.md): **18 driver + 59 standing tests passed**, lint clean.
