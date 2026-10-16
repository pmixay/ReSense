# Preparation handoff

Prepared against integration `b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1`.
All source refs matched before/after the capture. No deletion, merge, push,
pruning, staging or commit was performed. The owned deliverables are confined to
this new `retirement/` folder. They are left uncommitted for the parent so the
current CI/PR head and source refs remain unchanged.

## Current blocker

PR33 is **OPEN**. Latest observed checks: `checks` and GitBook successful;
`pytest` and `offline-build` **FAILURE**; `webapp` and `docker` still in progress.
Run: <https://github.com/pmixay/ReSense/actions/runs/38897519801>.
The recorded inventory contains its own point-in-time CI response. Parent owns
CI repair/merge and final-main bundle restoration; this preparation does not
execute P4 work or investigate/change application code.

## Ref scope (conditional, not deleted)

`L` = local branch; `O` = live origin branch. All full identities and tracking
refs are in `inventory.json`. All entries below must pass the README gates.

| Name | Locations | Expected tip | Preservation |
|---|---|---|---|
| experiment/cross-ring-sparse-evidence | L | `2acda69e9ed9b47d6b79b674c269ee40a97faf4f` | bundle |
| h2/cut-bar | L, O | `7380f650829fd1c64a9b894afcf2868b6ffc2434` | frozen seed |
| integration/web-ci-20261016 | L, O | `f29e212abe933dcfa76ee9b0ea4afb9cd95bf810` | recognized merged web tip + raw ZIP |
| p1/decision-policy-2026-10-15 | L | `d3aa88414a9927a81a273b8883156198afa9a141` | bundle |
| p1/offline-rebuild-2026-10-15 | L | `0cccb7e2bea60716e2cd1d352589b8341055b705` | bundle |
| p1/start-2026-10-15 | L, O | `01e1f669d8b558755cf0c8ebd680c7641d59becf` | frozen seed |
| p1/startup-2026-10-15 | L | `a14ddd1faf53b4477b28c1494995b925ce278746` | bundle |
| p3/range-screen | L, O | `527a76c4139add1862b7eaaf954129a73d65964f` | frozen seed |
| r3/column | L, O | `ccb68c106f562a1768636685f4513c09336dbec6` | frozen seed |
| final/silent-misses | O | `d0d17bb5dcc2b5b23f9ddd96744a8fd0424e0b5d` | frozen seed |
| p2/docs-and-pitch-20261015 | O | `90a472e31f225efc7689ce74db6c36c6e4d7fc5c` | frozen seed |
| r3/axis | O | `972edd2b7a9986e277a30a69d4adce6255462103` | frozen seed |
| r3/axis-B-trial | O | `d77a861aefc1b9b889eb28851feb365326684b34` | bundle; rejected candidate retained |
| integration/2026-10-15-16 | L, O | `b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1` | final main required; retire last, currently blocked |

These are **20 conditional ref locations: 10 local + 10 origin**. KEEP-ACTIVE:
local/origin `p4/eval-start-2026-10-15` at
`ab295b144c67d9ea5a63ef9fa75fd7d72346073a`, local
`p4/heldout-spec-2026-10-15` at `9f6a54e4e0c6203bf24973815aa780d844a5a267`,
all P4 worktrees and any new/advanced/unknown refs. Main remains at
`3fdc87957f5d09ff32573eabe6637924b91ea376` in this snapshot.

## All registered worktrees

| Worktree basename | Tracked changes | Untracked | Ignored | Decision |
|---|---:|---:|---:|---|
| ReSense (main) | 0 | 0 | 203 | KEEP |
| resense-cross-ring-base | — | — | — | KEEP excluded missing/prunable registration, untouched |
| rs-h1 | 0 | 0 | 39 | conditional candidate; backed up |
| rs-h2 | 0 | 0 | 51 | conditional candidate; backed up |
| rs-integration-20261016 | 0 | 2 | 14 | KEEP/blocked by own preparation; snapshot now stale |
| rs-integration-web-20261016 | 0 | 0 | 19 | conditional candidate; backed up |
| rs-p1-offline | 0 | 0 | 30 | conditional candidate; backed up |
| rs-p1-policy | 0 | 0 | 69 | conditional candidate; backed up |
| rs-p1-start | 0 | 0 | 115 | conditional candidate; backed up |
| rs-p1-startup | 0 | 0 | 32 | conditional candidate; backed up |
| rs-p4-baseline-707ea9c | 0 | 0 | 41 | KEEP-ACTIVE, detached `707ea9cda051369326fb9407c42488c1033dad76` |
| rs-p4-eval | 0 | 0 | 14 | KEEP-ACTIVE |
| rs-p4-heldout | 0 | 0 | 0 | KEEP-ACTIVE |
| rs-range-screen | 0 | 0 | 33 | conditional candidate; backed up |

The integration count is from before `inventory.json` and this summary were
created. The two untracked paths at capture were this folder's README and helper;
there was no unrelated tracked/untracked integration work at capture. The parent
must refresh before any future removal. Other candidate trees had no unknown
ignored files, untracked files or tracked changes.

## External preservation

Directory:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-retirement-20261016/premerge-01/`.
Nine ZIPs preserve **404 non-Git files / 12,643,912 raw bytes**, including the two
then-existing preparation files. Combined ZIP size: **5,140,000 bytes**. Every
archive has a sibling `<worktree>.manifest.json`; the report records each manifest
SHA-256 as well. Source bytes/size/mtime were unchanged through backup verification.

| ZIP basename | Files | SHA-256 |
|---|---:|---|
| rs-h1.zip | 39 | `d1d0fe8be97c48404f8234a2ab2fe08dffadb693ce39fa544d3476ad1d799c60` |
| rs-h2.zip | 51 | `a5d0a0ffdb4365f3f21480be5903c77648c529a2157baf2d91b6d519652b3a9d` |
| rs-integration-20261016.zip | 16 | `1a9cf54d69f39c8514c95504cdc98eb25bfe7259b30ef2f2e6624951a4229fb7` |
| rs-integration-web-20261016.zip | 19 | `b42d7a5e1960914e49c8611644b0856fbb4ccd120f20b124a522b9c13ed5bc45` |
| rs-p1-offline.zip | 30 | `42b447870493839ff473f8b9730d58cf30b1788101133b3bc184a29b9f8c0ba4` |
| rs-p1-policy.zip | 69 | `f31e96385f0a42c5928481cdfe611a10a71e1554e165bf80050c76c7910e3603` |
| rs-p1-start.zip | 115 | `fd0aa7706a0d3535d8e693102af5a85aac9f382bb80b59f456a224fb91e037ab` |
| rs-p1-startup.zip | 32 | `7be79a72a27f4af8f70d1fe7aa4083e9c8022e36989f8e8130281f4b63c199ea` |
| rs-range-screen.zip | 33 | `663511091990fa7fc7040999553fc23cdfdd8b78599c7cbae50f5332d225332f` |

## Checks and next commands

- Existing branch archive: hash/header/manifest/file seal/bundle checks PASS.
- Existing web preservation: 19 member hashes/support proof/committed bytes PASS.
- Preparation helper: focused Ruff PASS.
- Actual capture: all nine ZIPs' member hashes/CRC and unchanged sources PASS.
- Fresh `verify-backup` on H1 and web: PASS.
- `verify-backup` for active P4 eval and blocked integration: both correctly refused.
- `postmerge-check` before merge: correctly refused (`PR33 is not merged into main`).

Use the README's ordered command plan: green normal merge, main ancestry/archive
gate, independent final-main bundle restore, fresh snapshots, immediate backup and
SHA checks, ordinary worktree removal, individual branches, integration last.
Remote deletion is blocked while writers may race: non-force `push --delete` plus
an immediate read is not an atomic inventory-SHA lease. P4 stays active throughout.
