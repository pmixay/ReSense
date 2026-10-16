# Verified branch archive — 16 October 2026

This is the preservation prerequisite for the user's authorized **later** retirement
of temporary branches after verified integration into main. Archive preparation
performed no deletion. All source refs and registered worktrees were retained.

## Frozen archive identity

| Item | Exact value |
|---|---|
| Frozen integration exclusion tip / restore seed | `e39a011e0f07a9809ba1000f800c39e91d28d15c` |
| Bundle | `retired-heads.bundle` (Git bundle v2, SHA-1 Git objects) |
| Bundle SHA-256 | `26b2a311fedc1a0e07b85058badad6953df69fb4de4091c4e60e43c7a662b314` |
| Bundle byte count | **47,312,366** (45.12 MiB; below 50 MB and GitHub's 100 MiB limit) |
| Retirement inventory | **20 refs: 11 local heads + 9 live origin heads; 15 unique tips** |
| Preservation split | **14 refs** are ancestors of the frozen seed; **6 refs** are advertised by the bundle |
| Existing main at inventory | `3fdc87957f5d09ff32573eabe6637924b91ea376` |

The seed is frozen even if H4 review/documentation commits advance integration.
It must remain an ancestor of final main through a normal history-preserving merge
(merge commits are fine). A squash or rebase that discards this ancestry does not
satisfy this archive's restoration contract.

Git's incremental bundle header records **nine boundary prerequisite commits**,
not necessarily the excluded integration tip itself. Their complete original SHAs
and subjects are in `manifest.json` under `bundle.header.prerequisites`. All nine
were independently checked as ancestors of the frozen seed. Fetching that one
explicit seed with its history therefore satisfies every actual prerequisite.
The older `df24c18...` commit appears as a history prerequisite; this does not put
its unrelated detached worktree in retirement scope.

The bundle was created with **all 20 retired ref names as arguments**, followed by
`--not e39a011e0f07a9809ba1000f800c39e91d28d15c`. `git bundle list-heads`, not the
creation argument list, determines which tips the bundle actually advertises.
The exact creation arguments, full inventory, live origin advertisement, all
associated worktree statuses and per-path metadata are frozen in `manifest.json`.
The current integration ref is excluded, so the bundle cannot include itself.

## Retirement list

`L` means the original local `refs/heads/<name>`; `O` means the original origin
`refs/heads/<name>`, represented in the bundle/manifest as
`refs/remotes/origin/<name>`. Both locations are separate retirement entries.
`seed` means already an ancestor of the frozen seed; `bundle` means advertised at
the exact original SHA. These are preservation designations, not approval to ship
rejected candidates.

| Original name | Location | Original full SHA | Preserved by |
|---|---|---|---|
| `experiment/cross-ring-sparse-evidence` | L only | `2acda69e9ed9b47d6b79b674c269ee40a97faf4f` | bundle |
| `h2/cut-bar` | L, O | `7380f650829fd1c64a9b894afcf2868b6ffc2434` | seed |
| `integration/web-ci-20261016` | L | `36324e2ca71a3106079f0cf5708ae0e2349e95b2` | seed |
| `p1/decision-policy-2026-10-15` | L | `d3aa88414a9927a81a273b8883156198afa9a141` | bundle |
| `p1/offline-rebuild-2026-10-15` | L | `0cccb7e2bea60716e2cd1d352589b8341055b705` | bundle |
| `p1/start-2026-10-15` | L, O | `01e1f669d8b558755cf0c8ebd680c7641d59becf` | seed |
| `p1/startup-2026-10-15` | L | `a14ddd1faf53b4477b28c1494995b925ce278746` | bundle |
| `p3/range-screen` | L, O | `527a76c4139add1862b7eaaf954129a73d65964f` | seed |
| `p4/eval-start-2026-10-15` | L, O | `ab295b144c67d9ea5a63ef9fa75fd7d72346073a` | seed |
| `p4/heldout-spec-2026-10-15` | L | `9f6a54e4e0c6203bf24973815aa780d844a5a267` | bundle |
| `r3/column` (H1) | L, O | `ccb68c106f562a1768636685f4513c09336dbec6` | seed |
| `final/silent-misses` | O | `d0d17bb5dcc2b5b23f9ddd96744a8fd0424e0b5d` | seed |
| `p2/docs-and-pitch-20261015` | O | `90a472e31f225efc7689ce74db6c36c6e4d7fc5c` | seed |
| `r3/axis` | O | `972edd2b7a9986e277a30a69d4adce6255462103` | seed |
| `r3/axis-B-trial` — REJECTED | O | `d77a861aefc1b9b889eb28851feb365326684b34` | bundle |

The experiment's origin branch was already deleted by the user; its stale **local**
head and unique history are preserved here. P1/P4 original intermediate commits
remain bundled even where their changes also exist under later cherry-pick IDs.

Excluded from this retirement list: local main, origin main/HEAD, current
`integration/2026-10-15-16`, and the older unrelated detached
`resense-cross-ring-base` registration (already missing/prunable at inventory).
No pruning was performed. Main/current integration require separate future cleanup.
The associated detached `rs-p4-baseline-707ea9c` was inspected and retained; it is
not a branch retirement entry or an automatic worktree-removal instruction.
Data/cache/raw directories outside worktrees are outside cleanup scope.

## Worktree preservation and pending owner review

`git status --porcelain=v1 -z --untracked-files=all --ignored=traditional` was run
on every existing associated worktree, plus main/current integration. Only names,
status, kind, byte size and modification time were recorded for status entries.
No private key, secret, untracked evidence or ignored file contents were read.

| Worktree basename | Ignored entries at inventory | Review result |
|---|---:|---|
| `ReSense` (main) | 203 | Known compiled/cache metadata; separate future cleanup |
| `rs-h1` | 39 | Known compiled/cache metadata |
| `rs-h2` | 51 | Known compiled/cache metadata |
| `rs-integration-20261016` | 6 | Known cache metadata plus concurrent untracked H4 owner work; retain |
| `rs-integration-web-20261016` | 19 | **Ignored raw evidence/log files; retain and owner-review** |
| `rs-p1-offline` | 30 | Known compiled/cache metadata |
| `rs-p1-policy` | 69 | Known compiled/cache metadata |
| `rs-p1-start` | 115 | Known compiled/cache metadata |
| `rs-p1-startup` | 32 | Known compiled/cache metadata |
| `rs-p4-baseline-707ea9c` (detached) | 41 | Known compiled/cache metadata; retained |
| `rs-p4-eval` | 14 | Known compiled/cache metadata |
| `rs-p4-heldout` | 0 | Clean |
| `rs-range-screen` | 33 | Known compiled/cache metadata |

There were no tracked modifications at inventory. Known metadata consists of
`.pytest_cache`, `.ruff_cache`, `__pycache__`, `.pyc`, and compiled native `.pyd`
files; these classifications do not authorize deletion. Every path and metadata
entry is recorded, including the ignored compiled modules.

**Future worktree-removal blocker:** the web worktree has 19 ignored files under
`docs/evidence/integration_2026-10-16/web_ci/`: baseline/controlled/browser/test
`.log` files, raw/baseline event `.jsonl` files, and five targeted/upload event
files under `results/`. Git bundles do not preserve uncommitted or ignored files.
Their contents have not been assumed to duplicate tracked `.txt` evidence. Keep
the worktree until its owner explicitly preserves or resolves these files.
The exact 19 paths and original metadata are in the manifest.

Concurrent H4 work under `h4_correctness/` and `h4_safety/` is also retained and
listed in the postcheck. It is outside this archive's ownership. The archive's
own source/test files can show metadata changes between initial inventory and
the final postcheck as verification helpers are completed. The postcheck reports
such drift explicitly; it also checks unchanged retirement SHAs, the origin
advertisement, main, registered worktree paths and frozen-seed ancestry.

## Restore from a final-main clone

Use a **full-history clone of final main containing this committed folder**.
For a shallow clone, first obtain the history through the frozen seed. Python
3.10+ and Git are sufficient; the helper uses only the standard library.

From that clone's root, first confirm the seed remains in main's ancestry:

```powershell
git merge-base --is-ancestor e39a011e0f07a9809ba1000f800c39e91d28d15c main
if ($LASTEXITCODE -ne 0) { throw 'Final main does not preserve the frozen seed' }
python -B docs/evidence/integration_2026-10-16/branch_archive/archive.py check
```

Then restore into a **new, nonexistent** scratch path whose parent already exists.
For example, substitute the absolute path of that final-main clone for `C:/restore/ReSense`:

```powershell
if (-not (Test-Path -LiteralPath "C:/Users/alikh/AppData/Local/Temp/opencode")) { throw 'Missing scratch parent' }
if (Test-Path -LiteralPath "C:/Users/alikh/AppData/Local/Temp/opencode/rs-archive-recovery-new.git") { throw 'Choose a new scratch path' }
python -B docs/evidence/integration_2026-10-16/branch_archive/archive.py restore --source C:/restore/ReSense --scratch C:/Users/alikh/AppData/Local/Temp/opencode/rs-archive-recovery-new.git
```

The helper validates byte count, SHA-256, the v2 header, exact advertised refs,
original namespaces, complete original inventory and every prerequisite ancestry
claim. It initializes a new bare repository, fetches **only** the frozen seed
from the read-only source, verifies the bundle there, unbundles it, checks every
retired SHA with `git cat-file` (commit and tree), recreates all 20 original
local/origin namespaces **in scratch only**, and runs `git fsck --full --no-reflogs`.
No object alternates are used. No persistent Git configuration is changed;
`safe.directory` is supplied only with per-command `git -c`.

The essential manual Git operations, if independently auditing the helper, are:

```text
git init --bare NEW_SCRATCH
git -C NEW_SCRATCH fetch --no-tags --no-write-fetch-head FINAL_MAIN_CLONE e39a011e0f07a9809ba1000f800c39e91d28d15c:refs/archive/frozen-prerequisite
git -C NEW_SCRATCH bundle verify ABSOLUTE_COMMITTED_BUNDLE_PATH
git -C NEW_SCRATCH bundle unbundle ABSOLUTE_COMMITTED_BUNDLE_PATH
git -C NEW_SCRATCH cat-file -e ORIGINAL_SHA^{commit}
git -C NEW_SCRATCH update-ref ORIGINAL_ARCHIVE_REF ORIGINAL_SHA
git -C NEW_SCRATCH fsck --full --no-reflogs
```

Repeat `cat-file` and scratch `update-ref` for every entry in
`manifest.json:retirement_refs`, including seed-covered tips. An unborn default
scratch HEAD is harmless; the original main branch is intentionally not recreated.

## Recorded proof and reproducible checks

- `manifest.json`: frozen original inventory, creation arguments, bundle identity,
  nine actual header prerequisites, preservation mode for each ref, and complete
  original worktree status metadata.
- `restore_proof.json`: actual new bare restore at
  `C:/Users/alikh/AppData/Local/Temp/opencode/rs-branch-archive-restore-20261016`,
  read-only prerequisite fetch from the common source `.git`, all 20 exact restored
  refs, commit/tree checks, no alternates, and **fsck exit 0**. Before unbundling,
  precisely the 14 seed-covered refs were available; the six bundled tips were
  absent. After import, every retired SHA was available.
- `preservation_postcheck.json`: later source preservation snapshot. All 20 retired
  refs and all origin heads remained unchanged; worktree registrations were
  retained and the frozen seed remained an integration ancestor. Status metadata
  drift is explicitly reported rather than silently overwritten.
- `file_manifest.json`: SHA-256 and byte count of the eight evidence/helper files
  above and below, excluding this checksum manifest itself to avoid recursion.
- `.gitattributes`: bundle bytes are binary with no CRLF conversion; text evidence
  uses LF. The bundle is committed directly, without LFS or external storage.
- `archive.py` and `test_archive.py`: reproducible checks and seven failure-mode
  contract tests covering corrupted/truncated payload identity, dropped or retargeted
  unique heads, dropped seed-covered heads, namespace drift, moving the seed, and
  accidental retirement of current integration.

```powershell
python -B -m unittest discover -s docs/evidence/integration_2026-10-16/branch_archive -p test_archive.py -v
python -m ruff check --no-cache docs/evidence/integration_2026-10-16/branch_archive/archive.py docs/evidence/integration_2026-10-16/branch_archive/test_archive.py
python -B docs/evidence/integration_2026-10-16/branch_archive/archive.py check
python -B docs/evidence/integration_2026-10-16/branch_archive/archive.py inventory
```

The original proof used Git 2.50.1.windows.1 and Python 3.11.9. All seven contract
tests and focused Ruff checks passed. `inventory` summarizes the recorded final
worktree snapshot; it does not read other owners' file contents. `postcheck` and
`seal` are preparation commands that regenerate owned evidence; keep the committed
evidence frozen when auditing it.

## Handoff before any later retirement

After the verified normal main merge, confirm this entire archive and binary
bundle are tracked on main, verify their identity, and reproduce the restore from
that main clone. Re-inventory every live head and worktree. A retiring head must
still equal its archived full SHA or be an ancestor of main; any other advancement
requires a new preservation review. Resolve the ignored web evidence and other
owner work before removing an associated worktree. Retain the excluded detached
registration and all out-of-worktree data/cache/raw directories. This archive
helper contains no source cleanup or remote mutation command.
