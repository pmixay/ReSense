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

## Concrete pending Docker fixture blocker

The newly added `tests/test_h4_spare_rearm.py:23` unconditionally reads:

```text
docs/evidence/integration_2026-10-16/h4_safety/results/rearm_witness.json
```

At the inspected source, this 101,534-byte committed JSON fixture is excluded by
`.dockerignore` and has no production Dockerfile `COPY`. A focused actual Linux
Docker context probe failed with exit **1** on precisely that `COPY`; see
[`fixture-probe/result.json`](fixture-probe/result.json) and its build transcript.
The full tools-image suite therefore needs the fixture's exact ignore exception,
production fixture-block `COPY`, and inventory entry before it can pass. This
finding is separate from the passing CI-routing preflight.

The final pushed/sealed-source CI remains authoritative. Other execution risks
are bag-cache availability/Drive quota on a cache miss, the existing strict cold
and warm runtime thresholds, and viewer/ROS behavior on the Actions runner.
