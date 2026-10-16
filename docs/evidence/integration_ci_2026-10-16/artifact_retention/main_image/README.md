# Final October 15 Actions image archival

The user extended the approved archive-and-clean operation to the previously
retained October main image. This is a new decision; prior evidence remains an
unchanged historical record. Selection is restricted to this exact artifact:

| Field | Value |
| --- | --- |
| Artifact ID | `11990270962` |
| Name | `resense-image-1.0.0-3fdc879` |
| Workflow run | `38765546278` |
| Original ZIP bytes | `529881425` |
| ZIP SHA256 (matches API) | `d047bd5693deda64b7680991908d61dc9a53ff83e08b61b186aeb5e95e10d367` |
| Embedded tar.gz bytes | `529880968` |
| Embedded tar.gz SHA256 | `80d429268e9393eb27ed1cf032933e98e60b9754afa9959c081ce3a18b7e995a` |
| Verified before deletion | `2026-10-16T16:51:22.678256+00:00` |
| DELETE succeeded | `2026-10-16T16:51:24.896294+00:00` |
| GET confirmed HTTP 404 | `2026-10-16T16:51:25.781633+00:00` |

The original ZIP is retained at:

```text
D:\ReSense-actions-archive-20261016\main_image\11990270962--resense-image-1.0.0-3fdc879.zip
```

Exact ZIP size, API SHA256, every ZIP member's CRC, and the tarball's embedded
`.sha256` sidecar passed verification. The manifest was flushed before DELETE;
the archive was fully reverified afterward. No extraction or Git binary storage
was used. D: retained 86,731,923,456 free bytes at final export, above the 5 GiB
reserve. No failures occurred.

## Final state

- This step: **1 image / 529,881,425 bytes archived and deleted**.
- Cumulative: **86 images / 45,133,154,952 bytes retained locally and removed from Actions**.
- Remote Actions: **60 log artifacts / 7,059,109 bytes**, **zero image artifacts**.
- All 60 pre-existing logs remain present; release v1.0.0 and its three assets
  have unchanged IDs, sizes, and digests.
- The C: archive and preceding D: manifests, summaries, inventories, and final
  verification proof remain unchanged, checked against `prior-proof-hashes.json`.
- No new/current 1.1 or P4 artifact is eligible for this exact-ID operation.

**Quota availability is not confirmed.** GitHub accounting may still require
6–12 hours to recalculate. This proof does not establish green CI.

## Evidence

`manifest.json` records the API metadata, local path, checksums and deletion
receipt. `local-final-verification.json` records the post-deletion verification.
`inventory-before.json` and `inventory-after.json` are complete raw paginated API
snapshots. Release snapshots and `summary.json` record preservation and totals.
`SHA256SUMS` covers the 11 generated proof/source files; `verify_evidence.py`
checks their hashes, inventory reconciliation and manifest consistency.

`archive_main_image.py` reuses the byte-identical original helper with a separate
archive root and an in-memory exact-ID eligibility predicate. It records this
operation in a new manifest and never updates prior manifests. Completed IDs
are skipped on resumption. The script only runs from the approved D: subdirectory.
