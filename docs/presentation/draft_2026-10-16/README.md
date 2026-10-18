# P2 draft deck — 16 October 2026

**Draft, not approved for defence.** Sealed prerelease 1.1.0 measurements from P4
commit `6d6aaca`; release J1, O1 and P1 approval remain pending. No new score.

* `ReSense_LCT2026_DRAFT.pptx` and its LibreOffice PDF: 18 slides; original team
  names/photos and organizer opening structure retained. Slides 17–18 are technical
  appendix material until P1 approves the timed talk.
* `range-x1`: all 11 candidate X1 cases, ≥3 recorded geometries, first STOP and
  held-from values, STOP-hit/visible counts. Missing held values are explicit;
  setO consists of selected attribution windows, not a range measurement.
* `x3-robustness`: all ten perturbations, platform/roundT-squareT false episodes
  and doubleT_obstacle STOP counts with denominators. All 40 cases and per-object
  metrics remain in `chart-input.json`; this slide is not a complete robustness score.
* `x1-causes`: all exported candidate attribution rows grouped by distance and
  cause family. Counts, not rates/recall; one first-in-code cause per row.
* `chart-input.json`: complete P4 register/export plus exact rows used in charts,
  shared input for later media. `sources/` contains byte-identical referenced JSONs
  and exports from P4, preserving provenance without merging P4 implementation.
* `manifest.json`: source identities, hashes and conservative slide-word budget
  including raster-chart labels (18 slides, ≤80 words each, ≤1,100 overall).

## Captions

All new numbers are **node-decoded, in-sample development data**, not held-out.
X3 1.1.0 equals its v1.0.0 Linux control; no improvement is claimed. Pin the BLAS
kernel for cross-runtime comparisons. These cloud measurements are not S5 timing.
The unchanged historical results slide explicitly identifies its cache/node paths.

Corrected organizer-object slide uses first STOP: edge box **28.2 m** (rounded
28), plank **89.0 m** (rounded 89), top-envelope box **111.4 m**. These replace
old 28.09 captions only in this draft, not historical measurement records.
Held-from is P4's judge metric, not guaranteed or continuous detection; stationary
S cases cannot establish moving-train range. See slide notes for aliases and scope.

## Rebuild

Requires Python with python-pptx and matplotlib, and fetched P4 commit `6d6aaca`.

```sh
python scripts/p2_draft_deck.py
libreoffice --headless --convert-to pdf --outdir docs/presentation/draft_2026-10-16 \
  docs/presentation/draft_2026-10-16/ReSense_LCT2026_DRAFT.pptx
```

The builder verifies every direct exported value and source hash. P4's separate
`build_export.py --check` verified all 2,461 numbers including 126 derived entries;
see the P2 intake receipt. Null held values omitted by the numeric export are
checked against the actual source JSON rather than replaced with zero.

PDF rendered and contact-sheet reviewed; new slides also inspected individually.
Template-background contrast/logo collisions found during review were corrected.
Final projection readability, speech timing, release reconciliation and owner
sign-off remain pending.
