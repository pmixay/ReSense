# Dashboard fast replay CI repair

Baseline: `b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1`, Actions run
`38897519801`, pytest job `116961605720`.

## Registered before the patch

CI passed 1649 core tests (8 existing external-data deselections), but dashboard tests
had 1 failure / 73 passes. The 14-frame synthetic replay had five alarm frames,
first distance 53.917877 m; at speed 10 the checker observed only 37.9 m, outside
its unchanged [40, 72] m acceptance window. The independent 60-frame smoke passed.

The UI advances every 10 ms at speed 10. The checker sleeps 20 ms between Python
polls and obtains frame index and banner text in separate browser round trips.
Both omissions and mismatched frame/text pairs are possible; seeking for the
screenshot must not substitute for observing the actual playback.

Deterministic preregistered repro: play a small JSONL at speed 10 through the real
file input and Play button, but keep Python inside the click wrapper until playback
finishes. Require every displayed frame/title pair to be captured, including a
single in-window alarm and subsequent 37.9 m alarm. Also suppress only the actual
rendered alarm titles in a negative control: input alarm flags alone must not pass.
Run these against the existing checker before replacing polling with in-browser
DOM transition observation. Keep the distance window, replay speed and timeout.

Verification: focused red/green repro, original synthetic tiny-run test repeatedly,
full `web/demo` suite with required browser coverage, original 60-frame smoke;
inspect the completed webapp CI job independently. Source, native library and Python
imports must come from the pinned Linux source checkout.

## Result

The original checker failed the deterministic positive control with **no alarm observed**;
the suppressed-title negative control correctly failed the playback acceptance (`red.txt`).
After the patch both controls pass (`green.txt`). The checker registers a `MutationObserver`
on `#banner-title` before Play, captures index/title together at the mutation checkpoint
after each replay timer task, and retrieves the sequence after playback completes. It
disconnects before the nearest-obstacle screenshot seek. The report uses actual DOM text,
not JSONL obstacle flags or a reconstructed alarm sequence. Replay timing, accepted distance
bounds and failure criteria are unchanged. No dashboard UI or detector changes were needed.

| Validation | Result |
| --- | --- |
| Original 14-frame synthetic test + both deterministic controls | 3 passes per run, **three consecutive runs** |
| Complete `web/demo` suite, `RESENSE_REQUIRE_WEB=1` | **76 passed**, zero skips/failures/errors |
| Original default 60-frame CLI smoke, screenshot | **PASS**, 144,774-byte PNG |
| Ruff 0.15.8, owned Python files | **PASS** |

`checks.txt` records all commands' output; `full.xml` preserves the full-suite JUnit and
`exit.txt` records runner exit **0**. The focused `-k` probes deliberately deselect unrelated
tests; the full suite deselects none. Text log trailing whitespace is normalized for Git.

### Exact reproduction

Retained container: `rs-web-ci-pw164-20261016` (3 GiB / 4 CPUs), tools image
`resense:web-ci-tools-pw164-20261016`, Playwright **1.64.0**, Chromium **156.0.8078.4**.
Python **3.10.12**, Open3D **0.19.0**, NumPy **1.26.4**; these latter versions differ from
the hosted runner and are explicitly recorded rather than claimed identical.

Source: `git -c core.autocrlf=false archive b0c9c17` extracted into a fresh Linux directory
`/dashboard-ci-b0c9c17` in that container. Host archive retained at
`C:/Users/alikh/AppData/Local/Temp/opencode/dashboard-ci-b0c9c17.tar`.
Only the two patched web/demo files were overlaid; their Git blob IDs match host/container:

- `check_dashboard.py`: `b2f8e7a79848c65e283103cbadf6f54b94d25b2b`
- `test_web.py`: `719738a3b412ece2974f1abdb4330fecd807b201`

The native library was rebuilt there with `bash scripts/build_native.sh`; both Python imports
and the enabled native kernel resolve to this pinned directory (`checks.txt` identity).
Raw outputs, JUnit files, synthetic JSONL and screenshot remain at
`/tmp/dashboard-ci-b0c9c17-results`; initial red/green logs and XML remain at
`/tmp/dashboard-{red,green}.{txt,xml}`. The runnable copy of `run.sh` is `/tmp/dashboard-run.sh`:

```powershell
docker exec -w /dashboard-ci-b0c9c17 -e PYTHONPATH=/dashboard-ci-b0c9c17 -e RESENSE_REQUIRE_WEB=1 rs-web-ci-pw164-20261016 bash /tmp/dashboard-run.sh
```
