# CI checkpoint and original-bag capture audit

Both exact runs completed successfully:

- Experimental `25a218a0a8b4e10089dfcf73b8d557d4a963290e`: https://github.com/pmixay/ReSense/actions/runs/36471997066
- PR `f577a7cac83fef70c0fd2f0a9f071598563108ea`: https://github.com/pmixay/ReSense/actions/runs/36471632628

All four jobs passed: source/config/lint checks, pytest/browser checks, offline
archive/runtime build, and Docker runtime/original-bag checks. Only the small
cold-bag artifacts were downloaded. Each ZIP SHA256 exactly matches GitHub's
artifact digest. Extracted metadata, run/job state, original provenance, captures
and input parity reports are retained; the ZIPs are not duplicated in this archive.
No large image archive was downloaded. `manifest.json` maps every retained file
to its source hash and records the verified GitHub ZIP digests. Status captures
are lossless `.jsonl.gz`; decompressed bytes match the audit's original hashes.

## CI pass, freshness availability and recall are separate

Every capture contains the full original header-stamp sequence: 201/201 positive,
252/252 clear, with no missing, unmatched or duplicate headers. There are zero
freshness-contract violations. Fast input decode matches all 201+252 original
frames in both runs.

| Run / recording | Strict current frames | p95 decode+detect | p95 end-to-end among valid frames |
|---|---:|---:|---:|
| Experimental / positive | 165/201 | 47.75 ms | 60.78 ms |
| Experimental / clear | 241/252 | 33.61 ms | 38.36 ms |
| PR / positive | 145/201 | 80.09 ms | 94.91 ms |
| PR / clear | 244/252 | 50.69 ms | 57.67 ms |

Cold-start availability remains limited. The experimental positive capture's
frames 0–35 are invalid (29 source_stale, 7 catchup); clear frames 0–10 are invalid
(6 queue_stale, 5 catchup). The PR positive capture has invalid frames 0–55
(42 source_stale, 14 catchup); clear frames 0–7 (1 epoch_unconfirmed, 7 catchup).
These states correctly restrict GO. Passing the contract does not make them
fresh results. The two CI timing samples are not a controlled speed comparison.

All four captures have complete source-frame coverage. The positive node's final
`dropped_frames=4` counter must not be mistaken for missing bag messages: exact
header matching confirms all 201 stored messages were processed; the recording
itself lacks four nominal-rate frames. Clear captures end with counter zero.

## Target recall and first sustained fresh STOP

Raw current detector matching, without requiring freshness, is identical in both
runs: person 61/61; rail 128/185 overall and 126/126 from frame 75 onward. Fresh
matching additionally requires a frame snapshot, valid/current freshness, no
catchup, registered source/residence/queue age bounds, the per-frame freshness
contract, an actual detector STOP, and no held STOP. This schema has no literal
`result_state`; its state is `snapshot_kind` plus the `freshness` fields.

- Experimental person: **33/61 fresh matches**, frames 36–68. First fresh STOP and
  first run of at least five consecutive fresh STOPs start at frame 36. Frames
  8–35 are missed under the fresh-result metric.
- PR person: **13/61 fresh matches**, frames 56–68. First/sustained fresh STOP starts
  at frame 56. Frames 8–55 are missed under the fresh-result metric.
- Rail in both runs: **128/185 fresh matches**, frames 73–200; first/sustained fresh
  STOP at 73, **126/126** after frame 75. Visible missed intervals are 1–11 and
  27–72. Earlier rail coverage remains only 2/59 visible frames before frame 75.

`capture_audit.json` preserves exact frame IDs, header identities, target timelines,
invalid-reason counts, raw/fresh results, artifact hashes and checker identity.
`audit_captures.py` reads SQLite CDR header prefixes and captures only; it does not
run the detector, modify the repository, or tune any configuration. This audit
adds a startup availability measurement; it does not replace the raw 61/61 person
recall with a claim of full fresh recall.

The auditor is archived byte-for-byte as executed, with its original workspace
and `/cycle` paths. To reproduce it, restore the captures to its original task
directory (decompressing the `.jsonl.gz` files); its hashes in `capture_audit.json`
and the manifest identify the exact observer. The audit's `artifact_files` paths
describe the original downloaded files, including verified ZIP hashes; use the
manifest for their retained archive locations. No detector replay is required.
