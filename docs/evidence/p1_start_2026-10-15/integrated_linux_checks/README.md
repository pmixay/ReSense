# Combined Linux tools-image suite after independent-review fixes

**PASS on the first attempt: 1,562 passed, 0 failed, 0 errors, 0 skipped.**
The repository deselected exactly **10** cases marked `realdata` whose local recording/cache
directories were absent. No `-k`, `-m`, extra exclusion, or failure-specific deselection was used.

## Exact image and source identity

| Field | Measured value |
|---|---|
| Branch at start | `p1/start-2026-10-15`, clean tracked working tree |
| Source commit | `0caf5c227b68d7d73513c514f40eff1a0edc9d11` |
| Source Git tree | `c79de7a177dd393ad621cdcd7e5a4be69ed26fbe` |
| Build context | immutable `git archive --format=tar` of that commit, extracted under the approved temporary directory |
| Archive SHA-256 | `6565af16a62ca703a3cffa06a3d53c69d6b8063f7c9be2ccb6922a2401b8fd2c` |
| Image tag | `resense:p1-combined-tools-0caf5c227b68` |
| Immutable image ID | `sha256:14bb79c2e0755bf846a5df66a82da3671839c3b26335e4ff09dae20851c1607a` |
| Revision label | `org.opencontainers.image.revision=0caf5c227b68d7d73513c514f40eff1a0edc9d11` |
| Build option | `WITH_TOOLS=1` |
| Container platform | Linux x86-64, Python 3.10.12; Docker Engine 29.2.0 |

The image includes all three review-fix commits: `1f2dab7` (node), `9173a00` (fixtures and
reproduction), and `0caf5c2` (C1 packaging/imports). Image layers/configuration, exact commands,
runner hashes and elapsed times are retained in [`attempt-01/report.json`](attempt-01/report.json).

The volume-harness follow-up **`72a601b` landed while this immutable build/suite was running**.
It changes startup orchestration, tools and their tests, rather than the reviewed node/C1 code.
It is not part of this image or the 1,562-case result. The evidence commit likewise adds only
this report/check helper. No claim is made that the checked image contains later commits.

## Complete suite and runtime

The container ran the entire `/opt/resense/tests` directory with:

* `--network none`, working directory **`/`**;
* `RESENSE_REQUIRE_SYNTHETIC=1` and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`;
* the installed `resense` package imported and checked **before** adding `/opt/resense` for
  the tests' `scripts.*` source consumers;
* native kernels enabled; Open3D **0.19.0**, pytest **8.4.2**, numpy **1.26.4**, scipy **1.13.1**,
  scikit-learn **1.5.2**, rosbags **0.11.5**, zstandard **0.25.0**;
* one OpenMP/OpenBLAS/MKL thread, matching the image defaults.

The imported detector was
`/usr/local/lib/python3.10/dist-packages/resense/__init__.py`, outside the source working tree.
[`runtime_identity.json`](attempt-01/runtime_identity.json) records actual package versions,
the ROS node origin and image-side hashes of node, launch, policy, observer importer and driver.

| Result | Count |
|---|---:|
| Passed | **1,562** |
| Failed | **0** |
| Errors | **0** |
| Skipped | **0** |
| Deselected by the existing missing-`realdata` hook | **10** |

[`suite_receipt.json`](attempt-01/suite_receipt.json) lists every deselected node ID, its
`realdata` path and the missing-directory check. It also records empty failed/skipped lists.
[`junit.xml`](attempt-01/junit.xml) contains the complete case-level result;
[`suite.log`](attempt-01/suite.log) contains the original terminal summary.

## Elapsed times and resource handoff

| Stage | Seconds |
|---|---:|
| Tools-image build | **444.671** |
| Full-suite container, including imports/startup | **207.516** |
| Pytest call measured by the runner | **186.759** |
| Total helper invocation, including snapshot and cleanup | **665.125** |

These are local verification wall times, not detector or S1 throughput measurements. The build
used available Docker build cache and downloaded the tools dependencies; it is not a cold-build
benchmark. The test run itself had no network.

Both the guard and test containers used names starting `resense-p1-final-suite` and label
`resense.p1.checks=final`. The sleeping guard stayed up throughout build and tests so the separate
S1 timing agent could wait. Both are now removed; `--rm` had already removed the suite container
when the defensive cleanup ran (the retained cleanup log's “No such container” is expected).
The tools image is retained for reuse. No user image, unrelated container or build cache was
removed. **Testing stopped after this pass**, releasing Docker for the original-bag timing run.

## Original findings and fix provenance

There were **no failures or fixture repairs during this full-suite attempt**. Earlier findings
are preserved in their owning evidence rather than replaced by this unit-suite result:

| Original finding | Fix already included in this image | Owning evidence |
|---|---|---|
| Malformed raw flags/health could preserve freshness or release STOP; orphaned cross-input skip credits double-counted drops | `1f2dab7` validates raw results before freshness/latch projection and retains bounded active-epoch credits | [`S1.md`](../../node_startup_2026-10-15/S1.md), independent-review corrections |
| Backend wheel lacked its shared ROS-Python dependency; old overlays/historical checkouts could select the wrong observer policy | `0caf5c2` declares the dependency and resolves observer imports by source origin | [`PACKAGING_REVIEW.md`](../../caution_policy_2026-10-15/PACKAGING_REVIEW.md), including the original missing-git test-environment failure and its resolution |
| Docker image omitted pure backend/startup identity fixtures; E2 reproduction reused an existing mutation tag | `9173a00` adds exact context/COPY inputs, fresh/configurable tags and redirected output support | [`E2 follow-up`](../../offline_rebuild_2026-10-15/README.md), frozen packaging checks |

The older original-bag matrix remains a **FAIL**, as recorded in
[`node_startup_2026-10-15/docker/README.md`](../../node_startup_2026-10-15/docker/README.md).
This full unit pass does not supersede its measurements or establish the pending Linux-volume
S1 timing criteria. The separately verified 148-case backend/import suite was not repeated here;
the frontend was not part of this task.

## Reproduction

The host helper preserves each attempt and refuses an existing image tag. From this worktree,
use a fresh tag and attempt name if deliberately repeating the check later:

```powershell
& 'C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe' docs/evidence/p1_start_2026-10-15/integrated_linux_checks/run_checks.py --source-ref 0caf5c227b68d7d73513c514f40eff1a0edc9d11 --image resense:p1-combined-tools-0caf5c227b68-recheck --attempt attempt-02
```

The equivalent image build is:

```sh
docker build --build-arg WITH_TOOLS=1 --label org.opencontainers.image.revision=0caf5c227b68d7d73513c514f40eff1a0edc9d11 -f docker/Dockerfile -t resense:p1-combined-tools-0caf5c227b68 .
```

Use the immutable commit's context, as the helper does. `suite.py` adds receipt/JUnit recording
and the no-skip/data-only-deselection assertion around the full pytest invocation; it does not
change the tests, node, policy, Dockerfile or test-selection logic.
