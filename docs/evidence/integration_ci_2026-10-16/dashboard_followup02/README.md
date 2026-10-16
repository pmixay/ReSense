# Upload acknowledgement/log boundary follow-up 02

Baseline `e6cf5f2`, authoritative Actions run `38928306547`, webapp job
`117065713401`: backend/frontend/wheels passed, browser suite 46 passed / 1 failed.
The uploaded recording had already passed exact byte equality. The only failed assertion
was the strict no-resend log partition: before `{0,1}`, after `{3,4,5}`, missing chunk 2.

## Preregistered repro and fix

The recovery phase permits chunk 2 but waits only for >=8 MiB, already satisfied by the
16 MiB initial prefix. It can reload before chunk 2's acknowledgement. Additionally,
reading `stored` and then independently taking `stat().st_size` leaves a gap in log
coverage if a successful PUT is logged between those two operations.

Reproduce deterministically using the original browser case and a diagnostic backend
launcher that delays only the **real successful chunk-2 access-log record**. Actual
request handling, response, stored chunk, and final file bytes stay real. Release that
record immediately after the first `accepted_chunks` snapshot, wait for its actual
arrival, then return that snapshot to the test. The old reader/cursor pair must miss
chunk 2 and fail its original strict final union assertion, despite byte equality.

Before a relevant patch, run that old-case red repro. Then require the chunk-2 HTTP 200
response and completed body, exactly 24 MiB on the receiving server, and the entire
acknowledged prefix in the access log before reload. Record the log set and its byte
cursor from the same read, compare the server/log prefix across reload, and retain
the original strict no-resend disjointness/coverage assertion. Exercise the same
diagnostic interleaving on the fixed case, repeat focused cases, then run all 47
browser cases once without diagnostic injection. Clean held routes in fixture finally.

No production change is planned: the authoritative CI already proved the final file
bytes are correct. Preserve pause/offline recovery/multitab/beforeunload assertions.

## Repro observations

`red.txt` reproduces the **exact** final missing-2 union failure on the original test,
after its byte-equality assertion passed. The diagnostic reports snapshot `[0,1]`,
actual log after release `[0,1,2]`, actual server bytes `25165824`. For this logging-only
repro the reload wrapper first allows the real server to commit 24 MiB, isolating the
log-reader race from the independent early-reload race. The fixed case passes the same
interleaving (`green.txt`); production upload code is unchanged.

A deliberate failure immediately after staging exposed pending route-handler cancellation
noise with the first cleanup ordering (`teardown.txt`). Abort must run **before** removing
interception. If pause/reload already cancelled a request, `route.fallback()` resolves its
local pending handler after abort fails; then interception is removed. The same deliberate
failure now has only its intended RuntimeError and no CancelledError (`teardown-fixed.txt`).
The first repetition batch was interrupted during focused run 2, before any full suite,
to apply this cleanup correction; its completed boundary/normal cases passed and its
partial output is retained in `pre-cleanup-checks.txt`. Final verification uses the corrected
source and overwrites those provisional JUnit outputs with complete results.

## Retained reproduction resources

- Source archive: `C:/Users/alikh/AppData/Local/Temp/opencode/upload-followup02-e6cf5f2.tar`,
  produced with `git -c core.autocrlf=false archive e6cf5f2213f47945d753a0694deb7ebf21be87f7`.
- Existing container/image: `rs-web-ci-pw164-20261016` /
  `resense:web-ci-tools-pw164-20261016` (3 GiB cap, 4 CPUs, Playwright 1.64.0 / Chromium
  156.0.8078.4). Separate fresh source directory `/upload-followup02-e6cf5f2`.
- Native kernels rebuilt in that directory with `bash scripts/build_native.sh`;
  Python imports and enabled native status verified by `run.sh`. Python 3.10.12,
  Open3D 0.19.0 and NumPy 1.26.4 are recorded explicitly; not claimed identical to CI's
  numerical dependency versions.
- Frontend installed/built from this exact source with `npm ci && npm run build`.
  Logs: `/tmp/upload-followup02-{install,build}.txt`; production source is unchanged.
- Sole source overlay `webapp/e2e/test_upload_resume.py`, identical host/container Git
  blob `1a9000e2b5425e403d663be3c8df576b2aa39132`.
- Diagnostic helpers: `/tmp/upload-followup02-probe/`; full runner copy:
  `/tmp/upload-followup02-run.sh`. Raw results: `/tmp/upload-followup02-results/`;
  aggregate stdout/exit `/tmp/upload-followup02-checks.{txt,exit}`. Red/green/teardown
  captures remain under `/tmp/upload-followup02-*.txt` and corresponding JUnit XML.

Reproduce from the retained environment:

```powershell
docker exec -w /upload-followup02-e6cf5f2 -e PYTHONPATH=/upload-followup02-e6cf5f2:/upload-followup02-e6cf5f2/webapp/backend:/upload-followup02-e6cf5f2/ros2_ws/src/resense_ros:/tmp/upload-followup02-probe -e WEBAPP_DIST=/upload-followup02-e6cf5f2/webapp/frontend/dist rs-web-ci-pw164-20261016 bash /tmp/upload-followup02-run.sh
```

`run.sh` executes one additional injected-boundary case, two normal focused repetitions,
then the full browser suite with **no diagnostic plugin**, validates all positive JUnit
results have zero skips/errors/failures, and checks the positive logs for pending-task /
CancelledError noise. The deliberate teardown failure is a separate negative probe and
must fail only with `deliberate held-route teardown probe`.

## Final results

| Check | Result |
| --- | --- |
| Exact original-case boundary injection | **RED**, same missing-2 final union as CI; byte equality already passed |
| Fixed case under that same injection | **GREEN** (`green.txt`), repeated on final cleanup source (`results/boundary.xml`) |
| Normal focused case on final source | **2 consecutive passes**, 24.48 s / 22.79 s |
| Full browser suite, once, no diagnostic plugin | **47 passed**, zero skips/errors/failures, 641.77 s |
| Forced assertion failure with held routes | Only the intended failure; **no CancelledError** after cleanup fix |
| Positive-log pending-task / CancelledError check | **PASS** |
| Ruff 0.15.8 on owned Python code | **PASS** |
| Production frontend build from pinned source | **PASS** |

Final runner exit: **0** (`exit.txt`). Complete positive JUnit and logs are in `results/`;
aggregate proof is `checks.txt`. Negative diagnostic logs retain their original whitespace
and are separate from the positive JUnit verifier. Application-source whitespace check passed.

The successful test still exercises real pause, real CDP offline/recovery, second-tab
ownership restrictions, the actual beforeunload dialog, rejection of a different file,
missing-chunk resume, exact final recording bytes, cleared persisted session and processing
of the uploaded recording. The final assertion remains:

```python
assert not (after & stored) and after | stored == set(range(n_chunks))
```

The prefix is now explicitly `{0,1,2}`, backed by completed HTTP responses, the real server's
three received chunks / 24 MiB / missing range, and the access log. Its log cursor comes from
that same read before reload; post-reload state must still be 24 MiB and no new successful
PUT may appear before selecting the file again. No production code, distance/window checks,
file size, upload concurrency or assertion timeouts changed.
