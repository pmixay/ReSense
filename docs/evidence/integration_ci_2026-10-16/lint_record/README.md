# P1 CI repair: immutable measured helpers and maintained-code lint

## Original failure, retained without changing the historical inputs

Push `492e407b76d9dee7852f9e1884200e27939f0fca`, Actions run **38895681129**:
the checks job failed Ruff; parameter synchronization and the detector seal passed,
and downstream jobs were skipped. The original failed-step transcript is retained
in `original-ci-failure.txt`. `original-diagnostics.json` reproduces the original
command using **Ruff 0.15.8**: **263 diagnostics in 38 files**.

| Rule | Count |
| --- | ---: |
| E702 | 114 |
| E701 | 87 |
| E402 | 27 |
| F401 | 14 |
| E731 | 9 |
| E401 | 7 |
| E741 | 2 |
| F541 | 1 |
| F821 | 1 |
| F841 | 1 |

These are dated, retained run-input/helper artifacts. Reformatting them or adding
`noqa` would change the author bytes recorded by the existing package indexes.
Neither those bytes nor the indexes have been rewritten. This repair concerns CI
classification and integrity, not the correctness or acceptance of any evaluation.

The F821 `scenes` finding in `h4_correctness/scene_runner.py` is retained, not
suppressed by changing its source: lines 19–22 load `independent_checks.py`, select
the `freeze`, `scene`, and `scenes` AST definitions and execute their compilation.
Ruff cannot statically see the resulting binding. The existing
`h4_correctness/run-004/completion.json` records exit 0 for that invocation. This
inspection does not replay it or infer that other historical diagnostics are safe.

## Exact policy

`scripts/check_archived_lint.py` is maintained, normally linted code. CI first runs
its integrity check. The lint step installs Ruff **0.15.8** in an isolated pipx
environment (`ruff-ci`), verifies the same policy again, checks the tool version,
then passes **39 absolute exact file paths** to Ruff's `--extend-exclude`.
There is no directory exclusion or per-rule/per-file lint-ignore blanket.

The 39 files comprise the 38 newly diagnosed snapshots plus the single previously
exempted `cycle_2026-09-28/complete_timing/default/run_gate.py`. Every other file,
including other Python inside these historical packages and all new P1 helpers,
receives ordinary full Ruff linting.

`snapshot_lock.json` contains an explicit file inventory and provenance pointers:

- **38 exclusions** resolve to their **existing package SHA-256 entries**, including
  the legacy gate runner's `artifact_manifest.json`. Each referenced package index
  is itself SHA-256/size/Git-blob locked.
- **One exclusion**, `h4_fixes/rearm/verify.py`, has no existing package SHA-256
  index. Its existing `green-bb62b94/launch.json` instead records a Git checkout of
  `bb62b94d69425e00079be88e9adb835978f8282e` and execution of this exact helper path.
  Lock construction resolved that commit's helper blob and verified it equals the
  pushed helper byte-for-byte. Its Git blob is
  `924726e14e77ac089cee477624ed5967ca6ccda9`; the launcher is also byte/blob locked.
  This is explicit pre-existing Git-pinned run-input provenance, not a newly
  invented claim of an old package SHA-256 entry.
- All Python in the enumerated frozen packages is inventoried, including Python
  that remains linted. **139 files total** (Python plus provenance indexes/launcher)
  have exact byte sizes, SHA-256 values and Git blob IDs. A new unlisted Python file
  anywhere in these inventories fails the integrity gate even if it is lint-clean.
- The lock JSON itself has a reviewed SHA-256 constant in the verifier, so removing
  an exclusion/inventory entry without a deliberate policy update fails. Exclusions
  must be inventoried exact paths; patterns, traversal and duplicates are rejected.
- Missing or modified historical inputs/indexes fail before Ruff receives any
  exemptions. Snapshot line endings are **not normalized**. A Windows checkout
  that converts a historical index to CRLF is rejected; validation therefore uses
  clean committed bytes, as Linux Actions does. Only the new policy JSON allows
  ordinary checkout EOL conversion for its own digest.

## Live-consumer boundary

The maintained-source audit covers `resense`, ROS sources, scripts, tests, web and
webapp, Docker scripts/build files and workflows: **304 files**. It rejects direct
frozen-module imports, exact helper path references/invocations, and explicit
archived-helper Python search-path additions. Current shipping/tests do not use
the exempted Python. The H4 test's JSON witness is data, not an imported helper;
its consumer and all shipping tests remain linted. Inspection also found no such
runtime helper dependencies in the shipping/test searches.

This static audit is not a general resolver for arbitrarily constructed dynamic
imports. Future code that builds imports dynamically still requires review; it
does not justify extending the exact exclusion list. A new reusable helper belongs
in maintained source and must pass Ruff, rather than editing measured artifacts.

## Validation (no evaluations, replays or reseal)

`validation-final/result.json` and transcripts record a clean source snapshot of
**492e407** plus only this owned CI repair overlay:

| Check | Actual result |
| --- | --- |
| Every locked historical file compared to original `git show 492e407:path` | **139 unchanged** |
| Integrity gate | **PASS**, 39 exact exemptions, 304 maintained-source files audited |
| Full pinned Ruff file discovery and lint | **438 files**, no diagnostics |
| Full pinned Ruff in Linux Docker | **PASS**, same clean source, read-only mount |
| Contract unit tests | **23 passed**, Windows and Linux, no skips |
| New broken maintained script | F401, nonzero exit |
| New lint-clean Python in frozen package | Integrity failure, nonzero exit |
| Modified frozen helper | Integrity failure, nonzero exit |
| Missing frozen helper | Integrity failure, nonzero exit |
| Broken maintained file sharing an exempted basename | F401, nonzero exit |

The 23 contract tests additionally cover corrupted/relocked provenance indexes,
Git-blob mismatch, missing/edited policy, duplicate and escaping paths, live imports,
shell invocations, search-path additions and valid JSON-witness consumers. They use
temporary synthetic files, never run a historical helper, and work without the
archival evidence in the Docker unit-test image.

`validation-final/lint-coverage.json` is Ruff's actual resolved file list.
`validation/` retains the earlier 20-contract-test run; `validation-final/` includes
the additional policy/from-import cases and Linux execution. The Windows tool was
installed in a separate scratch venv; Linux used `/tmp/lint-tools` in a disposable
container. No shared Python environment was changed.

Reproduce on a clean Linux checkout:

```bash
python3 scripts/check_archived_lint.py
pipx install --suffix=-ci ruff==0.15.8
python3 scripts/check_archived_lint.py --lint --ruff ruff-ci
python3 tests/test_archived_lint.py -v
```

No detector/config/version/seal file changed, and the original H3/H4/H5 directories
and legacy gate package have zero diff against 492e407. The downstream full CI jobs
remain the parent's authoritative next check; this record claims only P1 lint and
artifact-integrity repair.
