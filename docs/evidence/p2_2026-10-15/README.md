# P2 — D1 pass 1 and PT1 slide cuts, 15.10.2026

Base: `main` `3fdc879`; working branch `p2/docs-and-pitch-20261015`.
Plan: [`BACKLOG`](../../BACKLOG.md) §5, cards D1/PT1; current state:
[`web/P2_STATUS.md`](../../../web/P2_STATUS.md).

## D1: facts checked and corrected

| claim / contradiction | verification and correction |
|---|---|
| release absent / tag planned on `70bc265` | `git ls-remote origin refs/tags/v1.0.0` → `5d6e9b5a5f7118821ada9b59f5f6a4fcf5620b98`; authenticated `gh api repos/pmixay/ReSense/releases/tags/v1.0.0` → published 29.09 17:58:58 UTC, archive 477 449 541 bytes + `.sha256` + `SHA256SUMS` |
| archive verification | independently verified by the judge 13.10; this pass checked metadata, **not** a new archive download or logged-out access |
| scores 61 / 65 / 69 / 67.5 presented as current | SCORECARD headline and CAPTAIN §2 now use **13.10, 66/100** (15+9+7+8+7+8+8+4); older scores have a dated history table; no new score awarded |
| 29.09 judgement cited as a completed re-run | that directory contains scripts only; completed independent judgement is [`13.10`](../judgement_2026-10-13/README.md) |
| gate command against competitor-rules baseline | CAPTAIN/EVALUATION now use `regression_baseline_2026-09-29_shell_off.json`; VM_GUIDE current selection already uses it; earlier baseline retained only as history |
| dual-return copies cannot change decisions | SENSOR corrected: voxel clustering is not the whole pipeline; raw-point path/health fits change (13.10: 193→189 STOP frames; platform CAUTION 51→11 %) |
| 30–56 / 35–56 / 43–56 / 48–56 m treated as one range | O rail/centre cubes: **42.7/55.8 m cache**, **48.0/55.8 m node-path**; edge cube 35 m; hanging **5 cm** object 30.1 m; sources and pipeline named |
| person transplanted into other tunnels | explicitly **older detector, 28.09**; constant-distance insertion in moving windows conflicts with current ego veto; not a current range claim |
| 2.1/km without the event definition | cache gate: 27 track events / 30 STOP episodes; node-path 13.10: 32 episodes (~2.5/km); all in-sample |
| 81–82 ms as universal current performance | historical 28.09 team-VM measurement; current 13.10 on 4 vCPU: offline decode+detect p95 106–119 ms, Docker node p95 111 ms, distinct from result age/freshness |
| pitch / deck / video owned wholly by P2 | CAPTAIN §8 and docs index now give P1 content/approval and pitch ownership; P2 visual cuts/chart/cards/fallback as in BACKLOG |
| prototype PR #31 still open / not in main | merged `317eabf`; remains outside v1.0.0 image/release; remote detector branches match BACKLOG H1–H6 |

The dated decision-log rows in CAPTAIN were retained. D1's grep deliberately also finds its own
quoted defect examples and acceptance expression in BACKLOG; those are the plan, not current
claims. The remaining no-release count in SCORECARD is explicitly dated 28.09.
DATASET's duplicated dual-return claim is P4-owned, outside D1's P1-doc lane; its owner must make
the equivalent correction (and EXPERIMENTS' older summaries need their pipeline labels). These
are recorded handoff items, not silently rewritten as new measurements.

## PT1 task 2: slide preparation

Rebuilt `docs/presentation/ReSense_LCT2026.pptx` and `.pdf`, 16 slides, using the original
organizer template. The four names and five photos were recovered from the **existing public
PPTX** to temporary build inputs; no private JSON/photos were added to the repository.
Required template slides 7–11 retain layout/structure. Detail is in speaker notes; historical
numbers retain their dates/pipeline. Current 13.10 context is explicitly labelled, and the
range-by-geometry chart remains dependent on J1 of the next released seal.

The builder's `--audit` counts whitespace-delimited words in text, grouped shapes, tables,
chart categories, data labels (including units) and configured axis tick labels. Notes and raster
illustrations are excluded. The build fails above **80 per slide / 1,100 total**.

PDF exported with LibreOffice 7.4.7.2 and the repository's Montserrat fonts; review covers all
16 pages, especially team cards, history, results and both charts. P1's final pitch approval
is still pending after O1/J1; the speech is marked as the historical 29.09 draft.

## Checks

Commands (use a Python environment with the presentation extras; web checks also need Open3D,
Playwright/Chromium):

```bash
python scripts/build_deck.py --audit docs/presentation/ReSense_LCT2026.pptx
python scripts/build_deck.py --check-gate docs/evidence/results/regression_baseline_2026-09-29_shell_off.json
python scripts/detector_freeze.py verify
python -m pytest -q web/demo tests/test_overview_video.py
git diff --check
```

Results:

* Word audit: **963 total**, **max 80** (chart labels, units and axis ticks included).
  Slides 1–16: `15, 75, 67, 79, 75, 47, 57, 49, 57, 53, 64, 80, 77, 56, 54, 58`.
  Original slide-shape text alone was 1,912 words, max 239; the new count is stricter because it
  also counts chart labels/ticks. The original BACKLOG's count (1,917) used a slightly different extraction.
* Gate block: **GATE matches** the shell-off baseline.
* Seal: **PASS**, 36 files, source `075a20df9fcdba6605a92e6505ae4dfdb3bf410ec09d17a8b3c79ce714db9292`.
  This is an integrity check; no detector-data replay was needed for slide/doc edits.
* P2 checks and video checks: **88 passed**, 39.85 s, Open3D + Chromium available,
  `RESENSE_REQUIRE_WEB=1` (skips would fail the run), Python 3.10 in a disposable test container.
  After the final caption/word-counter adjustments, the presentation artifact check also passed (1 test).
* PDF text extraction: **998 words**, **max 80**, 16 pages. All 16 final pages visually inspected;
  team-picture SHA-1s and the four names match the pre-edit PPTX. P1 sign-off remains separate.
* `ruff==0.15.8 check scripts/build_deck.py` (the CI-pinned version): **passed**.
* Relative-link check over every edited Markdown file and this evidence page: **0 broken links**.
* `git diff --check`: clean.

## Next dependencies (checked, not marked complete)

* **C1:** no `decision_policy.py` or `caution_reason` producer in current main. Wait for P1's
  additive status contract and example payloads before changing RViz/web consumers.
* **PT1:** J1 for first-STOP by geometry/object on the released seal, O1 for allowed version/format,
  G3 for the held-out line; then P2 renders the chart and video cards and P1 updates the speech.
* **PT2:** no v1.1.0 tag/image yet; the replacement fallback must identify that released image.
  The second-device check and timed rehearsals need the team's devices; no rehearsal is fabricated.
* **S5 / D1 pass 2:** final image and S1/S2/J1 first, scheduled 21.10. No benchmark of the older
  local image is presented as the final-node measurement. This workstation's `lscpu -e` lists
  cores 0–3 twice (8 logical CPUs): **4 physical cores / 8 threads**, not S5's ≥8 physical cores.
* **D2:** scheduled after 23.10, following the plan's order.
