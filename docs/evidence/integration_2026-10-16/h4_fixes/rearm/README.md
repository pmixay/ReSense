# H4 free-top re-arm author fix: targeted verification passes

## Commits and test-first order

1. `e623aad1be281272d5adb61e03651f80cdf0008e`: regression tests, protocol,
   isolated commit-pinned Linux harness, **before production edits or measurement**.
2. `abd09df165d6f3e47b20ece1566224d498247f54`: test-only control corrections
   and first red evidence. Exact measured source is in `red-abd09df/identity.json`.
   **2 failed / 248 passed / 0 skipped**, only the default/opt-in frame-11 STOP
   assertions fail. The controls pass on unchanged production code.
3. `bb62b94d69425e00079be88e9adb835978f8282e`: production provenance fix and
   corrected red evidence. This is the exact green measured source.

The initial red run had seven additional control-expectation errors, corrected
before production edits; `RED.md` and `red-e623aad/` retain that history.

## Minimal provenance change

`tracking.py` now distinguishes measured infrastructure in `explained_hist` from
an imputed `column` on a `Cluster.spared` hit in a separate, equally bounded
`provisional_explained_hist`. Both require the existing clean run at a new STOP
onset. An **accepted strict-gauge free-top hit completing that run** discharges
only the provisional explanations. Accepted here means the existing spare-history
corroboration has already passed; the first spare remains a column for the zone
vote and `column_hist`.

This is deliberately stronger than excluding all spared hits from the explanation
gate: a single noisy spare followed by three ordinary clean hits still cannot
release an advisory. It requires the existing five-hit run. Repeated free-top
evidence completes the same run on frame 5, then its old imputed explanation
cannot reappear after the two-miss gap. The state does not depend on whether STOP
was ever reported. Future measured columns, overhead, retro and shell reasons
still enter ordinary explanation history and require a run at a new onset.

Misses reset `clean_run` and retain both histories. Real infrastructure history
is never discharged by free-top corroboration. It ages only on the existing
matched-hit window. There is no new parameter or change to hold/release defaults.

## Results

| Check | Unchanged tracker | Fixed tracker |
| --- | --- | --- |
| Selected suite | 248 pass, 2 expected fail, 0 skips | **250 pass, 0 skips** |
| Physical case 44 STOP frames | 5..9, 12..19 | **5..9, 11..19** |
| First missing frame 9 | held | held |
| Second missing frame 10 | released | released |
| Genuine column-to-vault STOP frames | none | none |

The physical inputs and initial clusters are identical. The only STOP-frame
difference in the paired physical controls is case-44 frame 11. It retains the
same 72 strict voxels / 18 rings, confidence 0.85, 9/10 gauge votes and track ID.
`compare.py` verifies these statements and emits `comparison.json`.

The 250 tests include 12 new regression/control cases plus existing explained,
free-top, tracking module, history robustness/stress, ego-veto, fresh evidence,
stop-keep, reseed, near-escalation, track-opinion and native parity tests.
The actual-column history control, associated ordinary-object clean-run control,
and measured overhead/retro/shell controls pass. The genuine-column-plus-single-
spare hold survives gaps. Fresh onset, ego veto and doubt remain operative.

## Linux snapshot identity

- Image: `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19`.
- Source: `bb62b94d69425e00079be88e9adb835978f8282e` cloned from the read-only
  common Git directory; clean tracked checkout asserted before native build.
- Imports: `/tmp/repo/resense/__init__.py`; Open3D **0.19.0**.
- Native built from that checkout: `/tmp/repo/resense/_resense_native.so`, SHA-256
  `b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534`.
- Clustering and config source hashes match the red snapshot exactly. Concurrent
  column-agent work was uncommitted when this snapshot was measured and therefore
  was not included. Each run retains its complete identity, launch command,
  native build output, pytest text/XML and physical frame state.

Reproduce from the integration checkout using a fresh output label:

```powershell
python docs/evidence/integration_2026-10-16/h4_fixes/rearm/launch.py bb62b94 rerun-rearm
python docs/evidence/integration_2026-10-16/h4_fixes/rearm/compare.py
```

## Integration interaction / review handoff

This tracker change consumes the existing `spared` provenance. The column agent's
changes may change which physical observations qualify as spared; genuinely
measured column observations retain their explanation/hold regardless. The parent
independent reviewer must rerun the full physical matrix on the combined committed
source, including tall recovered objects and genuine/dark column controls. This
author verification resolves the targeted re-arm witness; it is not the parent's
independent H4 matrix result. No further re-arm defect was observed in these checks.
