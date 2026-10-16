# Web worktree raw-evidence preservation — 16 October 2026

This folder resolves the **19 ignored raw files** identified for
`rs-integration-web-20261016` in `../../branch_archive/manifest.json` (the actual
repository path is `docs/evidence/integration_2026-10-16/branch_archive/manifest.json`).
The original measured web result commit is `36324e2ca71a3106079f0cf5708ae0e2349e95b2`.

## Preservation contract

- `web-raw.zip` contains all 19 original `.log` / `.jsonl` files **verbatim**, at their
  original repository-relative paths. Binary ZIP attributes prevent line-ending conversion.
- `manifest.json` records each original absolute/relative path, exact byte count, SHA-256
  and mtime, alongside the frozen branch-archive web entry and its full manifest identity.
  Its live path set and metadata must exactly match that original 19-file inventory.
- All raw streams are stored independently; normalized tracked `.txt` outputs are not
  used as replacement payloads. Existing tracked web evidence is checked by Git blob ID
  against the integration tip recorded in the manifest.
- `verification.json` records the actual external-copy and independent disk-restore proof,
  source-file postchecks, complete non-cache inventory review and supporting-file hashes.
  Its manifest hash is separate to avoid a recursive checksum definition.

The external keeper is:

```text
C:/Users/alikh/AppData/Local/Temp/opencode/resense-integration-web-raw-20261016
```

It contains byte-identical ZIP/manifest/helper/proof copies and `roundtrip-restored/`
with the independently restored 19 files. Synthetic recovery-contract test artifacts are
also retained outside the worktree. Source raw files remain in their original locations.

## Verify after the parent merges this folder

From the repository root of the integration/final-main clone (Python 3.10+ standard library):

```powershell
python -B docs/evidence/integration_2026-10-16/web_ci/retirement/preserve_raw.py check --git-ref HEAD
```

On the original machine, also verify the independent keeper:

```powershell
python -B docs/evidence/integration_2026-10-16/web_ci/retirement/preserve_raw.py check --git-ref HEAD --external C:/Users/alikh/AppData/Local/Temp/opencode/resense-integration-web-raw-20261016
```

`check` reads the committed payload and manifest, without consulting the retired worktree
or Docker. `--git-ref HEAD` additionally compares the ZIP, manifest, proof, helper, tests,
README and attributes to exact Git blob bytes. The external helper can also run `check`
without `--git-ref` after the source worktree no longer exists.

## Restore without the old worktree

Choose a **new, nonexistent destination** with an existing parent. For example:

```powershell
python -B docs/evidence/integration_2026-10-16/web_ci/retirement/preserve_raw.py restore --destination C:/Users/alikh/AppData/Local/Temp/opencode/resense-web-raw-recovery-new
```

All ZIP members, byte counts and hashes are validated before creating the destination.
The helper then writes the original relative paths below it, verifies every restored byte
stream and restores recorded mtimes. Existing destinations are refused, so the command
cannot overwrite the source worktree. `capture` is preparation-only and must not be rerun
against existing output files; it contains no source deletion or ref mutation operation.

The branch archive retains its frozen original ref (`36324e2…`). This preservation commit
advances the web branch. The parent must merge the new tip normally, verify the folder on
final main and refresh the retirement ancestry/inventory checks before later retirement.
The existing source archives, patch and Docker resources described in `../README.md` are
already outside the worktree and remain separately retained.

## Recovery-contract checks

Six standard-library tests cover verbatim binary/CRLF roundtrip, truncated ZIP rejection,
missing manifest entries, per-file checksum mismatch, existing-destination preservation
and unsafe paths. Set `WEB_RETIRE_TEST_PARENT` to an existing approved scratch directory;
all generated synthetic test artifacts remain there:

```powershell
$env:WEB_RETIRE_TEST_PARENT = 'C:/Users/alikh/AppData/Local/Temp/opencode'
python -B -m unittest discover -s docs/evidence/integration_2026-10-16/web_ci/retirement -p test_preserve_raw.py -v
```
