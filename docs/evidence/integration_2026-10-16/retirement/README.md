# P1 retirement preparation only — 16 October 2026

**No deletion, ref mutation, push or merge was performed by this preparation.**
`prepare.py` has no cleanup operation. `inventory.json` is a point-in-time report,
not execution authorization. Its external copy and ZIP manifests are retained at
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-retirement-20261016/premerge-01/`.

## Scope and pinned identities

- Reviewed integration/PR33 head: `b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1`.
- Recognized web advance, already merged into integration:
  `f29e212abe933dcfa76ee9b0ea4afb9cd95bf810` (original archive tip was `36324e2`).
- Frozen restore seed: `e39a011e0f07a9809ba1000f800c39e91d28d15c`.
- Branch bundle: 47,312,366 bytes; SHA-256
  `26b2a311fedc1a0e07b85058badad6953df69fb4de4091c4e60e43c7a662b314`.
- Web ZIP: 149,177 bytes; SHA-256
  `abc9690d4e04fc345d88d2c84708445b882ec65e74c81ad2ba8c8e7523a3587a`;
  all 19 raw files / 1,939,465 raw bytes verified.

The original 20 entries already include the **local** web branch. Current scope is
those 20 plus origin web and local/origin integration: **23 ref locations**, before
the P4 hold. Three original locations are **KEEP-ACTIVE**: local/origin
`p4/eval-start-2026-10-15` and local `p4/heldout-spec-2026-10-15`. Any new P4 branch
also stays active. Both old P4 worktrees and `rs-p4-baseline-707ea9c` remain active.

The remaining **20 potential ref locations (10 local, 10 origin)** are conditional
candidates only. Main and origin main/HEAD stay. Unrecognized/advanced heads stay,
even if they happen to be ancestors of main. The unrelated missing/prunable
`resense-cross-ring-base` registration is excluded; never run global pruning.
All raw data/cache directories outside candidate worktrees are outside scope.

## Non-Git preservation

The helper first checks both existing archives, including their committed bytes.
It parses Git worktree/status/path metadata with NUL delimiters, inventories every
existing registered worktree including ignored entries, and queries live origin
heads without fetching or updating tracking refs. It physically enumerates each
candidate tree and backs up **every file absent from its Git index**, including
compiled modules, caches, ignored raw results, and unknown/untracked files. Empty
directories are recorded as well. ZIP member hashes/CRC and the original source
bytes/size/mtime are rechecked. Each external manifest includes every member's
path, SHA-256, size, mode and nanosecond mtime. Source files are never rewritten.

P4/main/unknown-head trees receive status inventory only and remain in place.
Symlinks, junctions/reparse points, nested repositories, submodules, and special
files block backup rather than traversing external targets. An incomplete backup
is retained for inspection but cannot satisfy retirement. Unknown ignored files,
tracked changes, and untracked owner work remain **KEEP/blocked even if backed up**.
Only recognized caches and the hash-matching 19 web files are classified as
reviewed ignored payload. New preparation files in integration are owner work;
the parent must commit/review them before that tree can become removable.

ZIPs are external, not committed evidence. Keep their manifests and this report
together. Restore members into a **new external directory**, verify hashes against
the manifest, and restore recorded mtimes/modes as needed. The archives store
ordinary file contents; they do not claim to preserve Windows ACLs or ADS.

## Minimal parent sequence AFTER green, history-preserving merge

Run from a retained checkout of final main, outside every tree being retired.
Use the helper from this folder after the parent has incorporated these files.
Every command below is a future instruction; none was executed as cleanup here.

1. Confirm PR33 is merged normally and all checks passed for its exact final head.
   Fetch main **without pruning**; inspect any changed PR head rather than silently
   accepting it. The explicit SHA parameter is an owner-reviewed identity.

   ```powershell
   git fetch --no-tags origin main
   if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
   python -B docs/evidence/integration_2026-10-16/retirement/prepare.py postmerge-check --pr-head REVIEWED_FULL_PR_HEAD
   if ($LASTEXITCODE -ne 0) { throw 'Main/CI/archive gate failed' }
   ```

   This read-only gate compares live origin main with local origin/main, requires
   merged PR33/all-green checks, and proves PR head, merge commit, frozen seed and
   web tip are ancestors of main. It checks exact bundle/support/web bytes in main.
   A squash/rebase losing the frozen ancestry fails.

2. Reproduce the branch restore **from final main**, using the existing immutable
   helper and a new bare scratch path. Retain its successful output externally;
   verify all 20 original refs and `fsck_exit: 0`. Do not reseal old evidence.

   ```powershell
   if (-not (Test-Path -LiteralPath 'C:/Users/alikh/AppData/Local/Temp/opencode')) { throw 'Missing parent' }
   python -B docs/evidence/integration_2026-10-16/branch_archive/archive.py restore --source FINAL_MAIN_CHECKOUT --scratch C:/Users/alikh/AppData/Local/Temp/opencode/rs-final-main-retirement-restore-NEW.git
   if ($LASTEXITCODE -ne 0) { throw 'Final-main restore failed' }
   ```

3. Refresh the full inventory/backup into a **new** external snapshot. The helper
   intentionally pins integration to the reviewed premerge head; if parent-owned
   commits advance it, it will KEEP that branch/tree. Review those commits and
   preserve/re-inventory explicitly before retiring integration last. Never relax
   the pin for unrelated or unrecognized advancement. Any new branch stays KEEP.

   ```powershell
   if (-not (Test-Path -LiteralPath 'C:/Users/alikh/AppData/Local/Temp/opencode')) { throw 'Missing parent' }
   python -B docs/evidence/integration_2026-10-16/retirement/prepare.py prepare --label postmerge-NEW
   if ($LASTEXITCODE -ne 0) { throw 'Fresh inventory failed' }
   ```

4. For each reviewed candidate, stop writers and recheck branch SHA, tracked and
   untracked cleanliness, and the complete ignored/non-Git backup immediately
   before ordinary worktree removal. Example (substitute the fresh report path):

   ```powershell
   python -B docs/evidence/integration_2026-10-16/retirement/prepare.py verify-backup --inventory C:/Users/alikh/AppData/Local/Temp/opencode/resense-retirement-20261016/postmerge-NEW/inventory.json --worktree C:/Users/alikh/AppData/Local/Temp/opencode/rs-h1
   if ($LASTEXITCODE -ne 0) { throw 'KEEP: backup/head/status drift' }
   git worktree remove C:/Users/alikh/AppData/Local/Temp/opencode/rs-h1
   if ($LASTEXITCODE -ne 0) { throw 'KEEP: ordinary removal refused; review, do not force' }
   ```

   Git may remove ignored files during ordinary removal: the verified external
   copy is mandatory even for caches. No `git clean`, forced removal, pruning,
   reset, or deletion of out-of-tree data is part of this plan. Backup checks are
   snapshots, not locks: if writers cannot be stopped, KEEP the worktree.

5. Delete local branches individually only after their exact SHA is rechecked
   and all associated worktrees are resolved. Prefer `git branch -d NAME` after
   proving ancestry to final main. **Only** original bundle-advertised local tips
   `experiment/cross-ring-sparse-evidence`, `p1/decision-policy-2026-10-15`,
   `p1/offline-rebuild-2026-10-15`, and `p1/startup-2026-10-15` may require
   `git branch -D NAME`; permit that only with the exact archived SHA, successful
   final-main independent restore proof and resolved worktree preservation.
   The bundled P4 heldout tip stays KEEP-ACTIVE. If an ordinary deletion fails for
   any other reason, stop rather than generalizing the `-D` exception.

6. Remote deletion is individual and conditional on an immediate live SHA check.
   Use `git ls-remote --heads origin refs/heads/NAME`, require exactly the expected
   SHA in `inventory.json`, then `git push origin --delete refs/heads/NAME`, then
   confirm absence with `ls-remote`. Example for a known seed-covered head:

   ```powershell
   $live = git ls-remote --heads origin refs/heads/r3/column
   if ($LASTEXITCODE -ne 0 -or @($live).Count -ne 1 -or $live -ne "ccb68c106f562a1768636685f4513c09336dbec6`trefs/heads/r3/column") { throw 'KEEP: remote SHA drift' }
   git push origin --delete refs/heads/r3/column
   if ($LASTEXITCODE -ne 0) { throw 'Remote deletion failed; stop' }
   git ls-remote --heads origin refs/heads/r3/column
   ```

   **No force push / force-with-lease.** Neither `gh` ref deletion nor a separate
   `ls-remote` plus push offers an atomic lease against the inventory SHA. Git's
   push protects the ref advertised during that push, but a change between the
   preceding check and push advertisement can still be deleted. Therefore only
   use this sequence when owners/writers are quiescent; otherwise leave remote
   deletion blocked. Do not claim atomic compare-and-delete safety. The remote
   rejected `r3/axis-B-trial` additionally requires its restored bundled tip.

7. Integration local/origin deletion is last, after the final head is explicitly
   reviewed and proven on main and all preparation/parent work is committed or
   retained. Record results outside the retiring tree. Inspect remaining refs and
   worktrees without pruning, preserving all P4/main/excluded registrations.

## Verification of this preparation

```powershell
python -B -m ruff check --no-cache docs/evidence/integration_2026-10-16/retirement/prepare.py
python -B docs/evidence/integration_2026-10-16/retirement/prepare.py prepare --label premerge-01 --record
```

The snapshot includes actual PR/CI state and full ref SHAs, full per-worktree
status, external ZIP hashes, manifest hashes and source-preservation results.
Adding the inventory/summary files after capture makes integration's backup
stale by construction; integration is KEEP/blocked until freshly re-inventoried.
