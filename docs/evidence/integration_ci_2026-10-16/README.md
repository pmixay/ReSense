# Integration full-CI routing — 16 October 2026

The `integration/2026-10-15-16` push now selects the Docker job's `FULL` path,
matches the original-bag Bash branch guard, and qualifies for the successfully
validated offline archive download. Existing full-CI branches remain selected.

The workflow remains push-triggered. These checks attach to the pushed integration
commit used by the PR; this is not a new `pull_request` merge-ref trigger.

## Expected complete CI coverage

- `checks`: pinned Ruff, parameter-copy synchronization, detector seal/evidence.
- `pytest`: full host suite with Open3D and skip prohibition, dashboard browser
  tests, synthetic dashboard replay, and independent JUnit skip counts.
- `webapp`: backend/policy wheel import outside the checkout, backend tests,
  frontend tests/type check/build, production-build browser tests, skip counts.
- `docker`: tools image, installed-package full unit suite, ROS launch resolution,
  no-network synthetic smoke, uid-1000 console/player, one-command playback,
  stock Fast DDS, shared-memory interoperability, remote Foxglove viewer and
  pause/recovery, original-bag cold positive/clear runs, byte-for-byte input parity,
  warm-cache full-rate positive/clear runs, retained cold/warm evidence.
- `offline-build`: runtime archive export/load, identical-layer offline rebuild,
  loaded runtime/native checks, internal-network playback, and the commit-named
  archive plus checksum artifact after success.

No cold/warm command body, checksum pin, frame/drop/rate/latency/alarm threshold,
regression timeout, or existing branch selection was relaxed. The fetch step no
longer uses `continue-on-error`; unavailable or unverifiable bags fail the job.
The missing-regression handler runs after that failure and emits an error plus
nonzero exit, preventing a green result that silently omitted original-bag tests.

## Focused preflight

[`preflight-v2/result.json`](preflight-v2/result.json): **PASS**, against owned
workflow/script edits over `70072f1300d922d7542a6b45688084e7a426d7c7`.

- Executed the production Bash branch guard for all **9** selected branches and
  **4** negative refs; each agreed with the workflow `FULL` expression.
- Syntax-checked the cold/warm script and all **36** workflow shell blocks in
  Linux Bash.
- Checked cache-hit and successful-download routing to the regression, and the
  failed-download route to the error handler.
- Executed the real missing-data handler: exit **1**, `::error::` annotation, and
  a retained `NOT RUN` summary.
- Verified that the cold/warm body is byte-for-byte unchanged after its guard,
  and that integration archive upload requires a successful push.
- Focused Ruff of the evidence helpers passed.

Reproduce with a fresh output directory:

```powershell
python docs/evidence/integration_ci_2026-10-16/verify.py --out docs/evidence/integration_ci_2026-10-16/preflight-new
```

The retained tools image supplies Linux Python, PyYAML and Bash only. Its old
installed detector is not evidence for the parent's current 1.1.0 shipping source.
No full detector suite, viewer, bag replay, or new release build was duplicated.
The initial `preflight/` transcript records an evidence-harness mount-path error
before checks began; locating the host root only in host mode fixed it for v2.

## H4 Docker fixture blocker — repaired and verified

The newly added `tests/test_h4_spare_rearm.py:23` unconditionally reads:

```text
docs/evidence/integration_2026-10-16/h4_safety/results/rearm_witness.json
```

The original inspection found this 101,534-byte committed JSON fixture excluded
by `.dockerignore` and missing its production Dockerfile `COPY`. The original
Linux Docker context probe failed with exit **1** on precisely that `COPY`; see
[`fixture-probe/result.json`](fixture-probe/result.json) and its build transcript.

The repair adds its exact ignore exception, production fixture-block `COPY`, and
`tests/test_docker_fixtures.py` inventory entry. The surrounding H4 output directory
is still excluded. A fresh offline source reinstall on retained tools dependencies
verified the actual production fixture block and installed import from `/`:

- Image: `resense:h4-fixture-fixed-1cfe8de-20261016`, ID
  `sha256:5b56394178f5c809febfd40017011d726eefe66008bc484ca0b968aba3f46b4c`.
- Source frozen at `1cfe8de4cebf457a099705b12cdc2c1712e2dda1`, with only the named
  packaging overlays. The parent's four in-progress version edits were excluded.
- All **25** production fixtures match the filtered context and installed paths;
  all **46** core/native/config/ROS source inputs match the frozen hashes.
- The H4 JSON is 105,484 bytes in this Git archive's CRLF form; its recorded hash
  matches both context and `/opt/resense/docs/evidence/.../rearm_witness.json`.
- Installed package: `/usr/local/lib/python3.10/dist-packages/resense/__init__.py`;
  native enabled, Open3D `0.19.0`, build/test networking disabled.

| Focused Linux group | Passed | Skipped |
| --- | ---: | ---: |
| Existing robustness battery | 18 | 0 |
| Docker fixtures, metrics/labels, policy, startup harness | 216 | 0 |
| Native, fastcloud, core synthetic | 105 | 0 |
| Changed H4 re-arm, shipping, opted-in free-top, late candidates, structure cut | 75 | 0 |
| **Total** | **414** | **0** |

Full-suite collection/imports also passed: **1,617 selected / 1,627 collected**, with
**10** recorded-data tests deselected by the existing absent-cache policy. The
changed shipping tests actually execute their external fixtures: canonical and
ROS YAML are present, byte-identical, and keep H1 disabled; H4's measured witness
constructs the real cluster and passes the tracker re-arm regressions. The new
shipping tests require no additional external fixtures. Focused Ruff passed.

Results and transcripts:
[`h4-fixture-fixed/result.json`](h4-fixture-fixed/result.json) and
[`h4-fixture-fixed/shipping-result.json`](h4-fixture-fixed/shipping-result.json).

Reproduce with a fresh image/output:

```powershell
python docs/evidence/offline_rebuild_2026-10-15/context_check.py --source-ref 1cfe8de --image resense:h4-fixtures-recheck --out docs/evidence/integration_ci_2026-10-16/h4-recheck
python docs/evidence/integration_ci_2026-10-16/shipping_fixture_check.py --image resense:h4-fixtures-recheck --out docs/evidence/integration_ci_2026-10-16/h4-recheck
```

This is frozen installed-source fixture evidence and focused tests, not a full
suite execution or validation of the pending 1.1.0 release/version seal.

The final pushed/sealed-source CI remains authoritative. Other execution risks
are bag-cache availability/Drive quota on a cache miss, the existing strict cold
and warm runtime thresholds, and viewer/ROS behavior on the Actions runner.
