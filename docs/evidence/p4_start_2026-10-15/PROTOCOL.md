# P4 H0 / X3 protocol (registered before measurement)

## Identity and runtime

Harness branch: `p4/eval-start-2026-10-15`, from `origin/main` `3fdc879`.
Measure **exact `707ea9cda051369326fb9407c42488c1033dad76`**, detached at
`C:/Users/alikh/AppData/Local/Temp/opencode/rs-p4-baseline-707ea9c`.
This is the v1.0.0 detector, not `final/silent-misses` or a 1.1.0 candidate.
The 1.1.0 standing baseline is future H5/X3 work after its seal exists.

The user's Windows computer is the authorized team runtime for this run.
This is a local offline replay, not a Linux VM / Docker node timing result.
Use the shared read-only `resense-p3-venv/Scripts/python.exe`, MSVC x64
`resense-build-native.cmd` (`/O2 /fp:strict`), and explicit `PYTHONPATH`
and `RESENSE_REPO` to the detached checkout. Include scratch
`C:/Users/alikh/AppData/Local/Temp/opencode` for the existing `resource.py`
RSS-only adapter. Set OMP / OpenBLAS / MKL / NUMEXPR threads to 1.
At most two replay workers total; run the full gate and X3 serially.

## H0

Data root `C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-data`:
`for_hackathon` = six raw bags, `cache` = compact16 gate inputs,
`decoded` = node float32 sensor-frame inputs, `odometry` = P3 ICP/axes.
Raw Set O is `D:/Datasets/ReSense/cloud_with_fake_obj`; raw ride is
`D:/Datasets/ReSense/new_data`. Reuse P3's published archive/intake evidence
as attributed intake, but independently inventory counts/stamps and measure here.

Expected counts: doubleT_obstacle 201, doubleT_platform 345,
roundT_doubleT (C) 252, roundT_pressureGate_roundT (B) 268,
roundT_squareT_pressureGate_squareT (A) 545,
squareT_platform_squareT_switch (S) 877, Set O 1510, ride 11271
(221 splits × 51). Check every gate stamp against original DB3 receive time;
check node cache metadata against raw header time/topic/frame id and all NPZ
arrays for float32 xyz/intensity, uint16 ring and consistent dimensions.
Build missing node caches with the existing judge `cache_decoded.py` tool.

Run the detached checkout's complete `scripts/regression_gate.py --jobs 2`
with the shared cache, eight ride chunks, the default config, no overrides,
and `docs/evidence/results/regression_baseline_2026-09-29_shell_off.json`.
Require exit 0 without `--allow` and equality of **every nonlatency metric
row**, including informational rows, not merely absence of gated regressions.
Retain the original per-frame work, JSON, log and strict comparison.
Verify the seal's committed source blobs separately from Windows checkout
bytes / generated native binary; report the actual freeze command result.

## X3 standing development battery

Run `scripts/robustness_battery.py --repo <detached baseline> --cache <decoded>
--out <fresh summary.json> -j 2 --judge-reference --resource-adapter <scratch>`.
The driver uses the committed judge scripts without editing them. Each job
gets a new NodeReplica and the default config. Dedup precedes dropout, then
vehicle-frame rotation followed by float32 sensor remapping, exactly as probe.
5 Hz selects original indices 0,2,..., retaining original timestamps and label
indices. Episodes count transitions in processed order (5 Hz STOPs are not
artificially split because their original indices differ by two).

Four full recordings: squareT_platform_squareT_switch, doubleT_obstacle,
roundT_squareT_pressureGate_squareT, cloud_with_fake_obj. Ten variants each:
nominal, pitch +2°, pitch -2°, roll +2°, 5 Hz, dropout 30% with seeds 1,2,3,
historical judge dropout seed 7, dedup. The judge hardcodes RNG seed 7: the
worker replaces only that RNG construction for the named s1/s2/s3 jobs.
No future G3 cases are generated or run here.

Raw output lives at `<summary stem>.raw/<bag>/<variant>/probe.jsonl`, with
job, process log and completion/identity sidecar. Existing summary or raw
directories are rejected, even after a failed run. The summary records source
payload/metadata/label hashes, judge script and driver hashes, protocol,
harness and evaluated commits, import/native identity and runtime.
Incomplete/invalid raw rows, wrong indices/stamps/decisions, failed workers
and incomplete references must result in ERROR, never PASS. A reference is
revalidated against its raw reports and their hashes before comparison.

### Metrics and acceptance

Empty backgrounds: false-STOP frames and episodes. Labelled recordings:
total STOP frames plus per-object plausible/nonzero visible denominators,
matching STOP rows and first STOP range/frame; outside-object false STOPs
and unmatched STOPs are reported separately. Matching follows judge
`score_objects.py`: distance tolerance max(2 m, 3% distance) + half length,
lateral tolerance 1 m + half width using the labelled bbox centre.
First distances are descriptive because a tilt changes geometry relative to
unrotated labels; this does not make false outside detections positive hits.

Candidate acceptance against a specified, complete reference: **no more than
one additional false-STOP episode** per empty/outside/unmatched row, **no more
than two lost matching STOP rows per positive object**, and no more than two
lost total STOP frames on a positive recording. Denominators and source /
label / protocol identities must match exactly. Improvements are allowed;
each comparison records signed delta, absolute delta and directional
`worse_by`. An absolute difference > tolerance may therefore still PASS
when it is an improvement. Absolute reproduction against historical judge
figures is a separate ±1 check, not this directional rule.

Historical reproduction rows: squareT episodes nominal/+pitch/-pitch/+roll/
5Hz/drop30(seed7) = 3/4/7/7/9/14; dedup 3. Obstacle STOP frames nominal/
+pitch/5Hz/drop30(seed7) = 193/192/95/154; dedup 189. RoundT-squareT is
zero under every variant. Record actual discrepancies without implementation
or detector tuning. No reference means status MEASURED, not candidate PASS.
The runtime target is ≤30 minutes on 4 vCPU at jobs 2; report the actual
shared-Windows duration without treating it as the specified VM benchmark.

## Checks and delivery

Driver tests cover corrupt/truncated reports, wrong metadata, inconsistent
decisions, 5 Hz episodes, labelled matching, directional versus absolute
tolerances, deterministic/aligned judge transforms, and incomplete references.
Run relevant standing gate/cache/native tests and seal verification. Commit
this harness/protocol before measurement; then commit immutable summaries,
hash indexes, commands and a report with results and unresolved acceptance.
