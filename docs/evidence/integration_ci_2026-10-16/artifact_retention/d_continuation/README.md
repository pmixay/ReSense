# Completed historical Actions image archival on D:

Final audit: **2026-10-16 15:56:16 UTC**.

| Location | Original ZIPs retained | Exact ZIP bytes |
| --- | ---: | ---: |
| Original C: archive | 14 | 7,301,353,966 |
| User-designated D: archive | 71 | 37,301,919,561 |
| **Combined** | **85** | **44,603,273,527** |

All 85 historical September image artifacts have verified local copies and were
deleted from Actions by exact ID, with successful DELETE followed by HTTP 404.
The D: continuation deleted 71 IDs; it skipped the 14 previously completed IDs
and preserved their original manifest records without double-counting them.
No download, checksum, CRC, deletion, or final-audit failures occurred.

## Retained archives

```text
C:\Users\alikh\AppData\Local\Temp\opencode\resense-actions-artifact-archive-20261016
D:\ReSense-actions-archive-20261016
```

Both locations are retained archives. The original ZIPs include the tarballs and
their checksum sidecars; no extraction or image binaries in Git were needed.
The original C: proof files and 14 ZIPs were read only during this continuation.
`initialization.json` records the hashes of the original proof files, and the
final audit confirms those hashes remained unchanged.

D: initially had 124,564,492,288 free bytes at the first preflight. Final free
space was **87,262,085,120 bytes**, above the **5 GiB reserve** throughout.

## Remote final state

- **61 artifacts remain:** all 60 original `p1-cold-dry-run-*` log artifacts and
  image `11990270962`, `resense-image-1.0.0-3fdc879` (529,881,425 bytes).
- **Zero** eligible historical image IDs remain.
- Release `v1.0.0` and all three published assets have unchanged metadata/digests.
- No new artifacts appeared between the original and final snapshots. New/current
  1.1 artifacts could not enter the immutable September 1.0.0 selection.

**Quota availability and green CI are not established by this operation.** The
API confirms 44.60 GB of artifact deletions, but GitHub accounting may take
6–12 hours to recalculate. The deliberately retained main image still occupies
529,881,425 bytes, in addition to logs and any other separately accounted storage.

## Verification and provenance

Each D: ZIP passed exact API byte-count and SHA256 checks, every ZIP member's CRC,
and streaming tarball SHA256 against the embedded `.sha256` sidecar. Before
DELETE, the original helper independently repeated verification and checked the
exact-ID remote metadata. Each successful DELETE was followed by a GET returning
404. All 85 ZIPs across C: and D: were re-read and fully verified in the final
audit, including CRCs and embedded tarball checksums.

- `manifest.json`: combined 85-ID manifest, archive paths, API digests/run IDs,
  verified ZIP/tar digests, and individual deletion/404 timestamps.
- `local-final-verification.json`: fresh full verification results for all 85 ZIPs.
- `combined-summary.json`: reconciled totals, both roots, protected IDs, remaining
  artifacts, original-proof preservation, and capacity.
- `d-inventory-before.json` / `inventory-after.json`: complete compact inventories
  at D: start and final audit, with hashes of full raw snapshots retained on D:.
- `d-release-before.json` / `release-after.json`: unchanged published release assets.
- `initialization.json`: read-only C: proof provenance and initial D: capacity.
- `preflight.json`: latest D: capacity report; the selection count includes all 85
  original candidates, while the completed manifest excludes them from downloads.
- `continue_retention.py`: D:-restricted continuation wrapper; up to three
  simultaneous downloads with serial manifest updates and deletions.
- `retain_artifacts_base.py`: byte-identical original helper, loaded by the wrapper
  with its output root redirected to D:. Do not invoke its original CLI directly.
- `SHA256SUMS`: hashes of the 11 generated proof/source files.
- `verify_evidence.py`: read-only consistency and staged-byte hash verification.

The helper's raw snapshots and batch checkpoints remain on D:. The earlier C:
summary and inventories in the parent directory are intentionally historical.
To repeat the read-only remote and full local audit:

```powershell
python "D:\ReSense-actions-archive-20261016\continue_retention.py" audit
```

The `execute` mode skips all completed IDs. No release endpoint is mutated, no
new artifact is selected, and neither archive root is relocated or pruned.
