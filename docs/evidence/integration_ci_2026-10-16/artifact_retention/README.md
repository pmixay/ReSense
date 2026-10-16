# Actions artifact retention — 2026-10-16

## Result and remaining blocker

**14 historical image artifacts were downloaded, independently verified, retained
locally, and then deleted from GitHub Actions by exact artifact ID.** Their original
ZIPs total **7,301,353,966 bytes (7.30 GB / 6.80 GiB)**. Each deletion was followed
by a GET returning HTTP 404. The final audit re-read and verified all 14 local ZIPs.

The operation stopped at the approved **5 GiB free-space reserve**. At the final
audit, C: had 5,797,285,888 free bytes: insufficient to retain the next 521,555,426-byte
ZIP while maintaining that reserve. Artifact `10913468780`
(`resense-image-1.0.0-8a10449`) was not downloaded or deleted.

The initial two-page inventory contained 146 artifacts: 85 eligible September
images totaling 44,603,273,527 bytes, 60 small log artifacts, and the protected
October main image. The final inventory contains **132 artifacts**, including
**72 images totaling 37,831,800,986 bytes**. Of those, 71 September images
(37,301,919,561 bytes) remain eligible for archival. Completing them requires
approximately **36.9 GB additional local free capacity** beyond the final free
space, with the reserve maintained.

**Actions quota unblocking is not established.** Substantial image storage remains,
and GitHub storage accounting may take 6–12 hours to recalculate after deletion.

## Retained results

Original ZIPs and full API snapshots are retained at:

```text
C:\Users\alikh\AppData\Local\Temp\opencode\resense-actions-artifact-archive-20261016
```

This external directory is the archive, not disposable scratch space. Each ZIP is
named `<artifact-id>--<artifact-name>.zip`. All members, including image tarballs
and embedded checksum sidecars, remain in their original ZIP bytes. No image
binary is stored in Git.

The committed evidence contains:

- `manifest.json`: exact artifact IDs, names, API sizes/digests, workflow run IDs
  and commit SHAs; local ZIP/tar SHA256 values; verification, deletion, and 404 times.
- `local-final-verification.json`: successful post-deletion local re-verification.
- `inventory-before.json` / `inventory-after.json`: compact complete inventories,
  pagination counts, and hashes of the full external API snapshots.
- `release-before.json` / `release-after.json`: identical release `v1.0.0` and its
  three published asset IDs, names, sizes, and digests.
- `summary.json`: final totals, disk blocker, and preservation checks.
- `preflight.json`: most recent capacity report; each execution printed its own
  preflight before attempting downloads or deletions. The first preflight had
  13,104,918,528 free bytes and 7,736,209,408 bytes above the reserve.
- `retain_artifacts.py`: executable helper source, restricted to the approved
  external directory.
- `SHA256SUMS`: hashes of the nine generated evidence/source files.

All 60 original log artifacts remain remotely present. The main image
`11990270962` (`resense-image-1.0.0-3fdc879`) remains remotely present. Release
`v1.0.0` (ID `399396306`) and assets `598868511`, `598868494`, and `598868487`
have unchanged metadata. The immutable selection only admits version 1.0.0
images created September 24–29; new/current 1.1 artifacts cannot enter it.

## Verification and resumption

Before deletion, every archive passed:

1. Exact ZIP byte-count equality with GitHub API metadata.
2. ZIP SHA256 equality with the API `sha256:` digest (mandatory).
3. CRC verification of every ZIP member by streaming each member to EOF.
4. Streaming SHA256 verification of every embedded `.tar.gz` against its
   corresponding `.tar.gz.sha256`, including filename validation.
5. A fresh exact-ID metadata check against the original snapshot.

The manifest was flushed to disk before DELETE and after its successful response;
a subsequent exact-ID GET confirmed 404. Missing hashes, failed checks, changed
metadata, download failures, or insufficient capacity stop processing without
deleting that artifact. The helper uses authenticated `gh api` binary stdout;
tokens and signed redirect URLs are not logged. No extraction is required.

After additional capacity is available in the approved location, resume with:

```powershell
python "C:\Users\alikh\AppData\Local\Temp\opencode\resense-actions-artifact-archive-20261016\retain_artifacts.py" execute --limit 85
```

Already completed IDs are skipped. Existing undeleted ZIPs are reverified before
deletion. Failed `.zip.partial` files are preserved and block automatic overwrite;
investigate them before retrying. `audit` performs a read-only remote inventory,
release comparison, and full local verification; `export` additionally refreshes
the small evidence files in this directory. Neither mode deletes remote artifacts.

## Subsequent completion on D: — 2026-10-16 15:56 UTC

After the user designated available space on D:, all remaining 71 eligible ZIPs
were retained there and their verified Actions copies deleted. The combined total
is **85 archives / 44,603,273,527 bytes**, with no eligible September images left
remotely. The original C: archive and proof files above remain unchanged; the disk
blocker described above is historical. See [the appended D: continuation evidence](d_continuation/README.md)
for the final multi-root audit, current inventories, and preservation checks.
