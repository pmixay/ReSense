# B4 integration with main and P4 — 18 October 2026

Work continues on **`det/b4-orientation`**. Main `9917851` (including PR #37)
was merged into B4 tip `6cc27be`. Two conflicts combine B4's channel-axis
constraint and observation cadence with main's orientation-readiness guard.
The committed measured source is **`0779db74beddc07fcb8cb89cda6e2837e31e4d62`**,
version **1.2.0**. Defaults remain unchanged, including startup replay 0.

At the user's later request, all P4 work through `8a0af65` was merged in
`eb03c98`, pushed, and remote branch `ccr-027997e8-kqywat` deleted after verifying
that its history was preserved on the target remote. P4's merge changes no
frozen detector bytes. [Merge/deletion and archive checks](p4_import.json).

## Evidence and seal

[Acceptance and frame totals](acceptance.json) is the machine-readable result.
It is produced by [finalize.py](finalize.py), which checks committed source
bytes, re-derives gate/X3 results from raw rows, compares every serialized
non-timing output, and reopens every archived member to verify its hash.
The integrating agent performed these checks; this is not a new independent
P4 review of the merged source.

| Check | Evidence |
|---|---|
| Matched-native full reference/candidate gates | [Reference](gate-reference.json), [candidate](gate.json), [complete frame comparison](gate_frame_review.json) |
| Fresh paired X3, 40 cases per source | [Reference](x3-reference.json), [candidate](x3.json), [raw-frame review](x3_frame_review.json) |
| Fresh B4, 24 mounts × two full recordings × two sources | [Comparison](b4_summary.json), [execution](b4_execution.json) |
| Real short-window B1 reproducer | [Directed checks](directed.json): identity and recovered rotation 4 first STOP at frame 8, no lost matched person frame |
| Affected tests | [JUnit](affected_tests.xml): 676 passed, six seal subtests passed; no skipped cases |
| Clean measurement build | [Before/after fingerprints](initial_clean_build.json), [native build](native_build.log) |

Both full gates passed all 18,329 rows per source. All 208 non-latency
metrics are identical; all 805 ordinary STOP frames in 51 intervals are retained.
Set F rows are exact. Paired X3 passed 40 cases / 29,765 rows per source, retaining
all 6,284 STOP frames in 204 episodes; every non-timing output is identical.

B4 passed all 202 checks across 35,808 rows. The candidate has zero empty-recording
STOPs across all 24 mounts (13,080 frames), with correct mapping by frame 1 and
no GO before confirmation. All 16 newly recovered sideways positive cases have
193 STOP frames, starting at frame 8, and preserve all matched person/object
frames from the correctly oriented control. The seven existing nonidentity
upright cases retain their baseline 191 STOP frames, starting at frame 10.

The [replacement candidate seal](../detector_freeze_2026-10-18_b4_merged.json)
is created **after committing this evidence**, using the existing freeze tool.
Its measured source is `0779db7`; subsequent evidence, P4 import and seal commits
do not change that frozen source. The default manifest is switched when the replacement is created.
[Final fresh-checkout verification before/after native build](../b4_merge_clean_2026-10-18/verification.json)
is recorded separately after seal creation, avoiding a circular evidence hash.

The source inventory has **38 files**, fingerprint
`68dee667f19e862913575c72fada3820199ec29cf497697cd7194b9e897f16d3`.
Both measurement checkouts compile native SHA-256
`67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394`.
The working checkout was also rebuilt to that hash; its previous generated
library is preserved outside Git ([record](working_native_alignment.json)).
The old seal correctly rejected the three changed detector files before and
after the initial native build; these failures are retained, not overwritten.

## Source identities, runtime and durable records

The fresh reference is `e9d8fc6`, whose 38 frozen files are identical to merged
main `9917851`. The only changed frozen files are `calibration.py`, `detector.py`
and `health.py`. The native-build amendment and measurement criteria were
committed in `008a7ec` before the recording runs ([protocol](PROTOCOL.md)).

Runs are serial on the available shared **one-CPU** host, Python 3.12.3,
NumPy 1.26.4, Haswell BLAS, one numerical thread and one worker. Timing is
informational; no speed improvement or 2/4/8-core result is inferred.
`*_execution.json` records commands, exact source/native identity, exit codes
and log hashes. The verified dataset intake receipts match the previously
committed receipts ([check](input_receipt_check.json)).

Raw outputs are retained in `gate-reference.tar.gz`, `gate.tar.gz`,
`x3-reference_raw.tar.gz`, `x3_raw.tar.gz` and `b4.tar.gz`. Each has a corresponding
`*_manifest.json` with every member's size and SHA-256. No raw frame is discarded.
For relocated X3 archives, `review_x3.py` accepts `--reference-raw-root` and
`--candidate-raw-root`; the gate comparator accepts explicit work/cache/source
directories. Original absolute run paths remain provenance, not portable defaults.
Set F's legacy records store hit/false-positive scoring rows rather than full
detections: aggregate reconstruction is checked; independent reassignment of
every Set F hit is not claimed.

## P4 reviews and remaining limits

The imported [P4 review of `0bbc6ed`](../p4_review_1.2.0_2026-10-18/README.md)
found no blocker. Its [B4 review of `6cc27be`](../p4_audit_b4_6cc27be_2026-10-18/README.md)
closed B1, passed B4/X3, and requested a fresh committed-source gate pair.
These reports retain their exact original source identities. The new measurements
supply the gate pair for the **merged** source; final P4 acceptance of that source
remains pending. The seal is candidate integrity, not release authorization.

* B4 validates transformed upright-Pandar inputs with usable channel evidence.
  Scan axis is not gravity. Physical horizontal scanners, translated/deskewed
  clouds and ring-free Falcon do not gain a new orientation guarantee.
* The late-ring control still produces empty STOPs at frames 4–8 if frame 0
  lacks usable channels. P4's S1–S4 availability, stale-message and sparse-channel
  findings remain documented. No blanket L16 closure is claimed.
* Existing upright nonidentity mappings retain their two-frame startup delay.
  Newly recovered sideways cases use the correctly oriented control; old
  wrong-coordinate alarms are not credited as real obstacle detections.
* B4 label matching uses the judge tolerances and may associate one detection
  with two labels; matched-frame retention is not proof of separate detections.
* Curves, dust robustness and N6's 60 m target remain open. Experimental dust
  suppression and rail extension stay off; startup replay remains opt-in.
* No new Docker/DDS or whole-Falcon run is claimed for this merged B4 source.
  Historical missing Windows Set O frame 332 remains a provenance limitation;
  X3 uses the verified Linux reference. No G3 run, release, tag or new J1 score.

P4's measured `explicit_mount.py` is unchanged. One exact hash-checked archival
lint exclusion preserves it, including its disclosed distance-field limitation;
[Git-blob provenance](p4_helper_provenance.json) and the policy tests record this
integration change. Maintained code remains subject to pinned Ruff 0.15.8.
