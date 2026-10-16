# Final exact-source Linux suite: current node and volume driver

**Full suite PASS: 1,601 passed, 0 failed, 0 errors, 0 skipped, 10 data-local deselections.**
This supersedes the source coverage of `attempt-01` (1,562 cases on `0caf5c2`), not its saved
measurements. **Static lint is not fully green:** seven pre-existing E701 findings remain,
documented below. YAML parsing and the owned Python/helper checks pass.

**Parent follow-up, 16.10:** the seven E701 lines were expanded without changing the test AST.
The final CI-scope Ruff command passes; production code still matches this tested source.
See [FINALIZATION.json](../FINALIZATION.json). Historical receipts below retain their actual
lint-failure status; this follow-up does not rewrite that run.

## Immutable source and construction

| Identity | Exact value |
|---|---|
| Final checked source/revision label | `7d3d5a05c258fc26a16c711e092822ff60d59d56` |
| Git tree | `ed471243f3224331fdcf4cd677f0ff0b1d7de008` |
| Source archive SHA-256 | `12f44f14ad1a6a4e176522171395158354c2851063bdde1051abc40309a55303` |
| Final image | `resense:p1-combined-tools-7d3d5a05c258` |
| Final image ID | `sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19` |
| Dependency/base image | `resense:p1-combined-tools-0caf5c227b68` |
| Required and verified base ID | `sha256:14bb79c2e0755bf846a5df66a82da3671839c3b26335e4ff09dae20851c1607a` |
| Source-manifest SHA-256 | `783fdc6ec6fd9050af44d8df631aa6f02a14170e5e8acf55927e8fc0344914e7` |

The frozen source contains the **`5e002e5` decode-failure skip-credit fix**, latest volume/warm-cache
driver and tests from `72a601b`/`62d055f`, and the owned packaging/check-helper follow-ups:

* `dda698c`: exact `bags_volume.py` ignore exception and COPY input, fixture inventory/context
  check, and optional incremental-source verification;
* `e5640d9`: retain lint results separately from the requested full-suite execution;
* `7d3d5a0`: account for the Dockerfile's declared shell normalization in provenance hashes.

**This was an incremental offline tools-image rebuild, not a fresh `docker/Dockerfile` build.**
The helper extracted a new immutable Git archive of the checked commit, used that commit's
`docker/Dockerfile.offline`, and appended the exact current runtime fixture COPY instructions
plus complete fresh `tests/` and `scripts/` copies. The generated Dockerfile text is preserved as
[`final-04/Dockerfile.incremental`](final-04/Dockerfile.incremental).

The base tag's immutable ID was checked before and after the run. Root/ROS dependency metadata,
core detector source, native source, configurations and version inputs were unchanged from the
base. Open3D and the other already-verified tools dependencies were reused, without downloading
or reinstalling them. The build used **`--network none --pull=false --no-cache`**:

1. Uninstall the inherited detector wheel outside the source directory; remove source/native
   build caches and the complete old ROS workspace.
2. Copy the frozen detector/native/config/build metadata and rebuild with
   `PIP_NO_INDEX=1 pip3 install --no-deps --no-build-isolation .`.
3. Clean-build the current ROS overlay from the Humble underlay; require installed native
   imports and resolved launch/share config.
4. Delete inherited tests/scripts/backend/docs/labels, then copy their exact current inputs.
   The newly required pure `docker_tools/bags_volume.py` is included; no recorded bags,
   measured matrix outputs, frontend or other backend application modules are copied.
5. Apply the same existing line-final-CR removal to shell scripts as the production Dockerfile.

Before pytest, **all 306 expected image-source files were hash-verified** against the frozen
archive, with raw and resulting hashes recorded for **23 declared shell normalizations**.
The full test/script inventories were also checked for missing or inherited extra files. Current
node/driver/Python test bytes are exact, without normalization; the ROS node's resolved import
must point to the freshly rebuilt source overlay. See
[`source_manifest.json`](final-04/source_manifest.json) and
[`runtime_identity.json`](final-04/runtime_identity.json).
The evidence-local `.gitattributes` preserves the manifest's exact original bytes, including
Windows JSON line endings, so its recorded byte SHA-256 remains verifiable after commit.
The generated Dockerfile's recorded SHA-256 uses its LF-canonical text.

## Full-suite results

The entire `/opt/resense/tests` directory ran from **CWD `/`**, with installed `resense` imported
from `/usr/local/lib/python3.10/dist-packages/resense` before adding the source root for
`scripts.*` consumers. Native kernels were enabled, Open3D was 0.19.0 and pytest was 8.4.2.
The container used `--network none`, `RESENSE_REQUIRE_SYNTHETIC=1` and
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. No `-k`, `-m`, or failure-specific selection was used.

| Coverage | Passed |
|---|---:|
| **Entire suite** | **1,601** |
| Node, including decode-credit regressions | 179 |
| Latest startup acceptance / volume / warm-cache driver | **116** |
| Docker fixture/verifier inventory | 19 |
| Native-kernel comparison suite | 28 |

All counts are from [`suite_receipt.json`](final-04/suite_receipt.json) and
[`junit.xml`](final-04/junit.xml). Every one of the ten deselections is the existing `realdata`
hook's missing-local-directory case; their node IDs and paths are retained in the receipt.
There are no failed, error or skipped cases.

| Wall time (local verification, not a benchmark) | Seconds |
|---|---:|
| Incremental offline build | **19.156** |
| Full suite container including preflight/imports | **179.094** |
| Pytest call measured by the helper | **172.103** |
| Total final invocation including snapshot, static checks and cleanup | **209.313** |

[`report.json`](final-04/report.json) retains the complete commands, labels, base/final image IDs,
layers, source tree/archive hashes, runner hashes, counts and durations.

## Preserved preflight failures and remaining lint concern

No pytest case failed and no case was deselected to get a pass. The earlier **preflight-only**
attempts are preserved:

* **`final-02`** stopped before build/pytest because focused Ruff over files changed since the
  old base found seven E701 single-line-if formatting findings in
  `tests/test_node.py:1043–1049`. `git blame` attributes every line to **`1eed357`**, before the
  current fixes. The helper was changed to record lint separately and continue the full suite.
* **`final-03`** built the offline image but stopped before pytest at the byte-provenance check.
  A read-only diagnostic found exactly 23 shell files changed by the already-declared
  `sed -i 's/\r$//'` transformation. All other source hashes matched. The original assertion,
  manifest and [`source-diff.json`](final-03/source-diff.json) remain retained. The verifier now
  records both raw and normalized hashes for precisely those build-transformed files.
* **`final-04`** verified that complete manifest and ran the full suite successfully.

Focused Ruff on the owned fixture/helper Python changes passes; the broader recorded changed-file
Ruff run still reports those **seven pre-existing E701 findings**. No node/policy/test-node source
was edited by this task. All **three workflow YAML files parse successfully**
([`yaml-parse.log`](final-04/yaml-parse.log)). The report's `static_checks_passed: false` and
`ruff_focused_exit: 1` are intentional and must not be presented as a fully green lint check.

The previous Windows-bind and Linux-volume **201/252-frame matrix FAIL reports are untouched**.
Those measurements describe their recorded earlier source/runtime, including `62d055f`, not the
new decode-credit node. This unit-suite result makes no new numeric S1 or original-bag claim.

All containers were uniquely named/labeled `resense-p1-final-suite*` /
`resense.p1.checks=final` and have been removed. Both the base and final images remain reusable;
the older tools image and historical reports were preserved. No Docker benchmark was run.
Testing stopped after the full-suite pass.

## Exact reproduction

Use a new attempt and image tag if intentionally reproducing later; existing attempts/tags are
refused. The checked source is pinned before any later parent documentation-only changes:

```powershell
& 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe' docs/evidence/p1_start_2026-10-15/integrated_linux_checks/run_checks.py --source-ref 7d3d5a05c258fc26a16c711e092822ff60d59d56 --attempt final-recheck --image resense:p1-combined-tools-7d3d5a05c258-recheck --incremental-base resense:p1-combined-tools-0caf5c227b68 --expected-base-id sha256:14bb79c2e0755bf846a5df66a82da3671839c3b26335e4ff09dae20851c1607a
```

The separate context-only checker now explicitly requires `bags_volume.py` in the filtered
context and compares its bytes with the installed fixture. Use a source ref containing that
file (for example the final checked commit), not the old `4e4d5a9` snapshot; historical proof
commands remain reproducible with their original helper commit.
