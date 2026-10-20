# Role 2 — 20 October 2026 execution plan

Execution receipt: [README.md](README.md). Today's scoped code checks are complete.
After the user's publishing request and corrected domain, publication completed
at [resense.amdm.life](https://resense.amdm.life/): [receipt](PUBLISH.md). Non-code
deliverables below are the stopping point requested by the user.

## Scope and stopping point

Requested by the user: finish today's Role 2 code work, double-check it against
the plan, then notify the user and stop when the remaining work is documentation,
video, presentation assets, recordings or human demo/rehearsal work.

Authority: `docs/BACKLOG.md`, “Current plan / P2 · frontend / visuals”, and
`docs/CAPTAIN.md` §4 on fetched main `2a5836922ad90faf50ba3f4a88740b1c6c129d65`.
Starting UI checkout: `b36c21c8a955924a19517edbd8b7ca08ecb21b47`.
P0 deadline: **20 October, 23:59 MSK**. P1 presentation deadline: **23 October**.
“P2” in the backlog's priority column means after the pitch, not Role 2 ownership.

## Ordered execution and acceptance

1. **Integrate the pinned main into `ui-improvement`.** Resolve the seven
   documentation conflicts using main's current release/ownership/archive facts
   while retaining applicable UI-branch playback instructions. Preserve the
   desktop-only UI (minimum 1280 px). The incoming track model adds `curv_step`
   and `curv_knot` support to the dashboard and React client. Acceptance: main is
   an ancestor of the completed branch, no unresolved conflicts, and detector,
   configuration and ROS runtime sources equal the pinned main byte for byte.
2. **Check code compatibility and fix integration defects in Role 2's lane.**
   Run frontend unit tests and type-checked production build, backend tests,
   static dashboard tests and the webapp browser suite. Check piecewise-axis
   consumers for consistent geometry and retain the existing desktop behavior.
   Run repository lint/integrity/parameter checks where available. Record inherited
   release/seal blockers separately from the UI integration results.
3. **Double-check and publish the code handoff.** Inspect the final diff against
   both parents, record exact commands/results and remaining work, commit completed
   work, run `scripts/deploy_webapp.sh`, then verify the public `/api/health` and
   `/deployment.json` against the checkout. If required deployment configuration
   is unavailable, report that blocker explicitly; do not claim publication.

Only fixes required by these acceptance checks extend the code work. New findings
must be recorded before a repair, with its scope and verification.

### Integration finding 1 — point-cloud shader parity

The incoming CPU track geometry consumes `curv_step` / `curv_knot`, but
`player/shaders.ts` still colors bed/rail points against a quadratic axis and
`player/scene.ts` does not supply the added coefficients to either point material.
Repair: add a shared step/knot uniform to the main and close-up point materials
and use the piecewise term in the vertex shader. Verify actual GPU color output
before/at/after the knot, both signs of the step and the legacy zero-step case,
then run the planned frontend/build/browser checks. Detector switches stay as
defined by the pinned main (K1/K2 off).

### Integration finding 2 — new track-field input validation

Both web input boundaries accept nonnumeric `curv_step` / `curv_knot` even though
the incoming renderers now consume those fields. Extend the existing optional
numeric-field checks to reject malformed values and retain legacy records with
absent/null fields. Verify frontend boundary cases and dashboard import/live
rejection alongside an accepted numeric piecewise track.

### Verification environment — browser startup budget

After resolving temporary test-disk exhaustion, five-second default browser
assertions time out on cold Player and lazy-detail loading with no console errors.
Use a local pytest runner with a 30-second default expectation budget on this
software-rendered host. The resumed check identified only one CPU core; a real
Player transition completed at 35 seconds without console errors. For this host,
raise the local default expectation/action budget to 60 seconds and run browser
modules separately to bound resource retention. Keep all explicit animation,
navigation and performance limits intact. Report this environment adjustment.

### Integration finding 3 — expired navigation callback

The browser suite reproduces a stuck `travelling` state with no frozen stages or
animations: under slow snapshot preparation, the 12-second watchdog releases the
overlay, then a queued preparation poll restarts travel after its snapshots were
disposed. Scope: guard the covered-to-travelling state transition against an
expired phase and ignore cancelled snapshot warm-up callbacks. Acceptance: a
deterministic timer regression reproduces the failure before the fix and passes
after it; the production-build browser suite, including navigation, passes.

### Integration reconciliation — retained D1 inserts

Two UI-branch D1 inserts still name 1.1.0 as the next J1 target, contradicting the
incoming current backlog; an archived Role 2 link retained its pre-move relative
path. Correct these integration leftovers to final-seal 1.2.0 and the relocated
evidence path as part of step 1, before the non-code handoff.

### Verification finding — stale-row scenario setup

The analysis browser test deletes a run on the server while the previous
successful rename's list refresh is still in flight. That refresh legitimately
removes the deleted row before the test can exercise its intended stale-row 404.
Wait for the rename-triggered list response before deleting the other run and
hold subsequent list refreshes (including system-count invalidation) until both
stale-row 404s have been exercised. Release the list for the successful deletion;
retain the real backend 404 assertions and final server/list consistency checks.

### Verification finding — native resize versus virtual clock

The resize regression exhausts its virtual-clock loop before Chromium delivers
the native resize/finished promise. The endpoint is correctly aligned and the
test passes the release point when the clock is driven again. Synchronize on the
resized frozen endpoint's actual width, then advance the existing painted-frame
check. Preserve the requirement to reach `opening` before advancing its 330 ms
timer, and preserve the clean-strip/history/overflow assertions.

### Verification finding — uploads and navigation snapshots

The data-page test's throttled 24 MB transfer can finish before a slow round-trip
navigation; throughput is not a barrier for an assertion about an active upload.
Hold chunks after the first two until cancellation (the upload-resume test
already uses this approach), then verify staging cleanup. Scope post-navigation
text assertions to the real `main` landmark so frozen, aria-hidden snapshots do
not create duplicate matches. Keep real transfer progress and backend checks.

### Integration finding 4 — paused simulation reconnect race

The system browser suite observed `end of recording` after toggling loop while
paused at 10×. A focused rerun passes, but source review confirms the race: the
server starts streaming before the browser's delayed `onopen` sends pause/seek.
Add a backward-compatible `paused` socket query parameter, pass it when reopening
a paused simulation, and establish paused state before opening the socket. Verify
a server connection held longer than the entire recording still seeks/plays
correctly, frontend reconnect/zero-position behavior, and the live browser flow.

## Non-code handoff — stop before executing these

- **P0 today:** the three root photos (`1591221.jpeg`, `IMG_8349.jpeg`,
  `IMG_8350.jpeg`) need a usage/licensing decision, then relocation into deck
  assets or deletion. Main records this assignment; no tracked source references
  were found beyond the backlog. Preserve them pending the asset decision.
- **P1:** cut the Falcon person demo bag around 280–330 seconds; verify actual
  `ros2 bag play` and update `web/DEMO_HANDOFF.md`.
- **P1:** second-device readability check; fallback clip recorded on the final
  1.2.0 image; rehearsals on 20 and 22 October, fallback switch within 30 seconds.
- **P1:** straight/curve/double-track range chart, Falcon slide, final document
  and GitBook numbers after the final reseal and P4 J1 results.
- **P1 review:** captain review and merge of this UI branch into main, or a
  decision to exclude it from the pitch.
- **After 23 October:** deferred personal-path tests/orphan-script cleanup (D2).

The detector reseal, release image, CI account repair and final J1 evaluation are
owned by P1/P3/P4. This UI integration does not establish release acceptance.
