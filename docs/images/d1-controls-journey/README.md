# Themed controls and strict final-stop navigation

> **Partly superseded (22.10):** its Player captures (`clear/caution/stop-1440.png`, `final-player-before-reveal-1440.png`) show the wall-mounted display, replaced by the driver's cab on 21.10; current captures: [`../player-cab/`](../player-cab/README.md). The controls and navigation captures remain current.

## Delivered behavior

- Shared native dropdowns use a themed `base-select` picker in supporting browsers:
  Raleway, rounded white surface, neutral hover and red selected checkmark.
  Native keyboard/typeahead/disabled behavior is retained; older browsers use the
  existing styled native fallback.
- Browser affordances inherit accent/caret/scrollbar colors; number fields avoid
  duplicate OS spin controls and file buttons use shared styling.
- Door closing/opening is 260/320ms. Travel is 280 + 130ms per interval (410–1320ms).
- Stage positions are explicit multiples of viewport width, in tab-bar order.
  Travel uses the actual last-stage offset. The destination must stay aligned
  for two painted frames before doors open; recovery finishes the journey rather
  than snapping from an intermediate tab to the live page.

## Verification and provenance

All **72 distinct ordered tab pairs** are covered by the journey contract test.
Browser tests sample 101 positions through Upload ↔ Player and Queue ↔ Compare,
requiring the observed sequence to be exactly current → each intermediate → final.
Other scenarios cover four desktop sizes, the system branch, history, reduced
motion, bitmap/font failure, resize and the hidden Player renderer. A themed
picker is opened and changed through its native keyboard interaction.

Screenshots are actual production-build Chromium renders at
`http://127.0.0.1:4182`, DPR 1, using the local API. `capture.json` records source
fingerprints, routes, viewport, observed order, final alignment and timing.
Native animations/browser time are held for repeatable inspection. Images are
UI demonstrations, not detector evaluation.

The D1 documentation/evidence package has separate requirement-by-requirement
acceptance in [`../../evidence/p2_d1_2026-10-19/`](../../evidence/p2_d1_2026-10-19/README.md).

## Acceptance review

| User request | Verified result |
|---|---|
| Execute D1 first and compare against the registered plan | Every P2-01 requirement is mapped in the separate D1 receipt; source/score/media/link checks are reproducible and P1/P4 dependencies stay explicit |
| Dropdowns and native browser affordances match the UI | Open picker screenshot, computed picker styles and real keyboard-selection browser check; form-control screenshot inspected |
| Shorter door transition | Close/open reduced from 350/450 to 260/320ms; travel reduced from 650–1700 to 410–1320ms |
| Current → all intermediate → target, either direction | All 72 tab pairs checked at contract level; 101-position browser samples validate the full visible sequence for both directions and multi-stop jumps |
| No intermediate pause followed by final snap | One near-linear cruise; final travel distance taken from the target's actual offset; recovery completes motion; target alignment is checked across two painted frames before opening |
| Existing desktop behavior and controls | Four desktop sizes, focus/history/reduced motion, resize/failure recovery and hidden renderer checks |

Production build and all **354 frontend tests** pass. Visual review: the themed
picker is legible, controls retain native-size labels, blurred stage silhouettes
remain visible behind the glass, and the final Player is aligned before reveal.
Current screenshots record no page errors.
The final complete navigation/control browser suite passes **19/19**, including
all four pinned desktop layouts. A late resize/layout delivery found during the
broader run is fixed: finished endpoints realign to the current viewport and repeat
the two-frame confirmation instead of remaining stuck or exposing a stale stage.
The gallery also includes fresh GO, CAUTION and STOP Player frames from the existing
synthetic demo runs; their exact routes and positions are recorded in `capture.json`.
