# H1 miss audit — intended compact public subset

**Prepared for publication; no Git operation or upload was performed.** The measured
source is `f56ad5e62d9d051811c804734c7731b6951eae90`. Publication preparation
only projects and verifies the retained successful captures; it does not replay
the detector or alter the production measurements.

The exact intended file allowlist, byte sizes and SHA-256 values are in
`publication-manifest.json`; the two publication metadata filenames are listed
there separately. `SHA256SUMS-publication` covers all intended files except
itself, including the manifest. Files absent from that allowlist are **VM-only**
even if still present in this audit directory. Do not include the whole directory
by wildcard.

## What the compact evidence actually contains

`publication-evidence.json.gz` is **5,411,599 bytes**, SHA-256
`92d9882e36cdb56bf9836c1d1fede5ce8ec32511ef2ea3e122672971933bc954`.
It is strict JSON after decompression, with lossless tagged binary arrays:

* All **177 visible rows**: full-precision input placement (`X/Y/Zb`), original
  rounded evaluator information, metadata and injected-input fingerprints;
  raw full-precision detection/warning outputs, non-cloud frame/model/health
  fields, original hit labels and matching detection IDs.
* Complete baseline/ICP/frame-metadata placement inputs needed to independently
  recalculate the 177 positions. Raw/processed target returns, ring/intensity,
  target point indices and target corridor membership are included.
* All **63 misses**: all **3285 captured branch events**, including executed line
  sequences/returns/checkpoints and their captured states, local candidate
  blobs/support, tracker states, thin/low-height evidence, core masks/retained
  indices/bars and the verified attribution records. These events are copied
  exactly from the successful traced capture; no branch labels are invented.
* All **340 full-snapshot canonical IEEE hashes**, full-scene processed-array
  byte hashes/dtype/shape and successful source-capture SHA-256 values.

Whole-scene raw or processed point clouds are **not included**. Candidate-local
support may include background points in a target cluster; these are needed to
explain the executed merge/infrastructure decisions. They are not whole clouds.
The largest included local point array has 9810 points. Array tags record
`dtype.str`, shape and base64 C-order bytes; tuple tags and nonfinite float IEEE
bits preserve state without numerical rounding.

The published result remains **114 hits / 63 misses / 177 visible rows**.
Primary counts: 43 column hold, 9 axis limit, 7 zone vote delay, 2 merged wall
segment, 1 height-reference limit, 1 tracker confirmation. All miss intervals are
listed in `README.md`; all individual rows and proofs are in `report.json`.

**Scope:** injection follows a cached detector baseline. It does not establish
independent in-gauge truth, a certified axis, real-world stopping range or braking
sufficiency. Wrong-selected-rail-pair/no-rails limits are covered by the main
agent's separate [h1_rail_limits evidence](../h1_rail_limits_2026-10-20/README.md).

## Portable checks versus VM checks

Run in the directory containing only the allowlisted files:

```bash
sha256sum -c SHA256SUMS-publication
python3 verify_publication.py
```

The verifier uses **Python standard library only**. It independently reconstructs
177 positions, recalculates raw-output hit matching, verifies the 63 actual miss
paths and 61 reached core calls, checks masks by scalar polygon intersections,
bar/hold/confirmation states, historical miss-set equality and package hashes.
Positive controls exercise a lost hit/payload, a deleted actual branch, a changed
core-mask bit, a changed checksum byte and a planted private connection string.

`publication-checks.json` records these data checks and the separately executed
VM projection check. Portable checking does not recreate the omitted 340 whole
clouds or independently repeat full-scene plain/traced equality. That equality
remains a production receipt (`ieee-exact-check.json`) tied to the retained
VM captures and their recorded hashes.

On the evaluation VM, with NumPy and the retained captures:

```bash
PYTHONDONTWRITEBYTECODE=1 /tmp/opencode/resense-b4-venv/bin/python \
  verify_publication.py --vm
```

This reads existing files only: it verifies 340 full-snapshot hashes, exact
projection of all 177 target supports/outputs and all 63 event/state/candidate
sets, and resolves the original production checksums through the storage map.
It performs neither a detector replay nor a Git operation.

## Historical production receipts are immutable

`SHA256SUMS`, `artifact-manifest.json`, `archive-manifest.json` and
`checksum-verification.json` are published **as historical production records**.
Their bytes are unchanged. Their original names describe the production layout,
including VM-only files; they do not assert that full captures are published.
The original `SHA256SUMS` hash is
`d8534f8b052dfe51eaf8b5a2f0aceda305533ae196fb77d265cd50d35b4fb5c4`.

`storage-map.json` records exact old/new paths, sizes and hashes. Original
README/protocol bytes were preserved before editing their public-facing routing
and connection information. `historical-receipt-verification.json` records all
**33/33** original checksum entries verified against their resolved production
bytes. The old checksum file is not rewritten to describe this new subset.

Use `SHA256SUMS-publication` to verify the portable files. Historical path
resolution requires VM-only files and is explicitly part of `--vm`.

## VM-only locations

Preserved, not deleted, in `/tmp/opencode/h1-miss-audit/vm-only/`:

| File | Bytes |
|---|---:|
| `raw-captures.tar.gz` | 1,009,663,897 |
| `miss-snapshots.pkl.gz` | 68,835,044 |
| `report-initial.json` | 31,918,404 |
| `inspection.json` | 13,554,124 |
| `README.production.md` | original document bytes; see storage map |
| `PROTOCOL.production.md` | original pre-replay protocol bytes; see storage map |

Original successful/failed `.pkl.gz` captures remain in
`/tmp/opencode/h1-miss-audit/`; decoded cache, baseline and ICP remain in place.
`source-tools-input-metadata.tar.gz` remains in the audit directory on the VM,
is recorded by its original archive/member hashes, and is excluded from the
public allowlist. Existing diagnostic tools/logs not on the allowlist remain
VM-only too. The raw/source material needed for VM-side reproduction is retained.

## Preparation tools

`build_publication.py` preserves/moves owned files and projects existing captures;
`verify_publication.py` checks portable data and optional VM provenance;
`finalize_publication.py` writes the publication-specific receipts/allowlist.
Original `audit.py` / `verify_audit.py` are included as historical replay/audit
tools, not invoked during publication preparation. Publication checks scan the
allowlisted text and decompressed evidence for private SSH connection strings.
