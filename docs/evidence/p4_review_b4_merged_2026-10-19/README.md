# P4 final review of the merged B4 source `0779db7`, 19.10

Candidate: `det/b4-orientation` measured source **`0779db74beddc07fcb8cb89cda6e2837e31e4d62`** (B4 `6cc27be` + main
`9917851`), checked at branch head **`da99de1`**, whose frozen detector files are byte-identical to `0779db7`. Seal
`detector_freeze_2026-10-18_b4_merged.json`: **PASS**, 38 files, source `68dee667…`. Version 1.2.0. Runtime of the
P4 protocol (`OPENBLAS_CORETYPE=Haswell`, one thread); native library from the unchanged `native/`. P4 changed no
detector code. This is the P4 review that `b4_merge_reseal_2026-10-18` lists as pending. It is not a release, a J1
score or a G3 run. Reviewer: the P4 AI agent and two fresh-context AI sub-reviewers, not a human approval.

## Conclusion

**ACCEPTED by P4 for sealing, with the should-fix items below. No blocking finding.**
B1 and B2 of the earlier blocking review are **closed for this source**:

* **B1:** the reproducer passes (rotation 4 first STOP at frame 8, no lost matched person frame).
* **B2:** a complete committed-source gate pair exists and was re-derived independently from its raw outputs;
  X3 was re-run by P4 on this source.

This acceptance covers the measured source `0779db7` / seal `68dee667…` only. A release still needs CI, a tag and an
image (E1); none exists yet.

## Evidence

| check | who | result |
|---|---|---|
| seal | P4 | `detector_freeze.py verify` PASS on `da99de1`; independently recomputed from git blobs at `0779db7` (gate re-derivation agent) |
| B1 reproducer | P4 run | rotation 4 and identity first STOP at frame 8, `lost_matched_stop_frames` empty ([b1_repro_merged.json](b1_repro_merged.json)); the same tool failed on the pre-fix source in the [6cc27be audit](../p4_audit_b4_6cc27be_2026-10-18/README.md) |
| B4, 24 mounts × 2 recordings | P4 run | empty recording **0 STOP** in all 24 cases; all correct by frame 1; 0 GO before confirmation; every frame of every case equal to the audited `6cc27be` run in decision, status and orientation; plain runs equal ([ana_m_*.json](.)) |
| X3 | P4 run | **PASS** 40 / 40, zero metric deltas; all **29,765** rows equal 1.1.0 except timing ([battery_merged.json](battery_merged.json)) |
| new recordings | P4 run | **28 PASS, 0 DIFF, 0 MISSING** ([new_recordings_compare.txt](new_recordings_compare.txt)): synthetic, Falcon 4,443 frames, switch, gauge on 10 recordings equal the 1.1.0 values |
| gate pair (P3's runs) | P4 agent, own comparators | every claim confirmed: 4 archives match their manifests member by member; commits `0779db7` / `e9d8fc6`, exit 0, same native and inputs, no overrides; 18,329 rows per side; the only non-timing difference is `mount.orientation_conflict = False` added on all 15,269 ordinary rows; Set F identical (71,352 leaves); 805 STOP frames / 51 intervals on both sides; 208 / 208 gated rows equal the baseline. Positive controls (planted changes) all detected |
| P3's X3 pair | P4 agent | identical non-timing rows, 260 / 260 checks; consistent with P4's own X3 run |
| merge resolution | P4 agent, code review | both features fully present; every confirming path sets `orientation_confirmed` and clears `orientation_conflict`; startup replay discards B4's injected observations instead of double-counting (16 synthetic runs equal upright); STOP precedence over health unchanged; 125 focused tests pass |
| lint change `ddf5b63` | P4 agent | adds exactly one exclusion (P4's own `explicit_mount.py`, which ruff rejects); no maintained code lost coverage; pinned ruff 0.15.8 and the policy tests pass |

Raw rows of P4's runs: [raw_merged.tar.xz](raw_merged.tar.xz) ([SHA256SUMS](SHA256SUMS)).

## Should fix (not blocking; all carried over from `6cc27be`, none introduced by the merge)

* **S1** `calibration.py:505–507`: `orientation_conflict` is set for any alternative vote when a scan axis was measured,
  even a vertical one agreeing with the configuration; such a frame becomes FAULT (the same input without rings is CAUTION).
* **S2** the flag is never cleared at `fallback` (`_finish`, ~`:703–708`): permanent FAULT on a mount that may be healthy.
  Fail-closed.
* **S3** "alternative orientation awaiting confirmation" is never replaced after the configured mapping passes.
* **S4** `scan_axis` returns None on 7–22 % of real frames (75 % channel rule); not re-measured on this source.
* **Note:** with startup replay off (default), a recovered sideways mount STOPs one frame later than an upright one in a
  synthetic run (main's existing opt-in trade-off). The lint pin is a review tripwire, not a cryptographic guard.

## Release and process notes

* **Two different sources carry version 1.2.0:** main (`b85a93…`) and this one (`68dee667…`). P1 should bump the version
  or record the decision before tagging.
* **main already contains the 1.2.0 candidate** (PR #37) whose own records say P4 acceptance was pending; P4 found no
  blocker in it on 18.10 ([review](../p4_review_1.2.0_2026-10-18/README.md)).
* **J1 target:** "sealed 1.1.0" is commit `3b7d7aa`, no longer main's head.
* CI on main fails on every recent run in ~2 s with no log (404); likely the known billing block, not verified.

## Not covered

P4 did not run the gate itself (no gate cache or ride here); its conclusion rests on the independent re-derivation of
P3's raw outputs, which cannot prove the runs happened as recorded. Not covered either: the real ROS node, Docker and
DDS; physical horizontal or ring-free (Falcon) mounts; S1 on real data; G3 (not touched).
