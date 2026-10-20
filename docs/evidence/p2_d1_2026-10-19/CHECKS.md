# Execution checks and residual acceptance

Commands run from the repository root unless a frontend working directory is shown.

| Check | Result | Scope |
|---|---|---|
| `python3 .../check.py --out .../checks.json` | PASS | exact Git/working-tree source hashes, altered-byte positive control, detailed gate/X3 recount, five archived payload hashes, score sum, video duration by two methods, P4 direct values and changed Markdown targets |
| `python3 scripts/detector_freeze.py verify` | PASS, 38 files | integrity only; no recording replay |
| `bash scripts/sync_params.sh --check` | PASS | detector/ROS configuration copies agree |
| `python3 scripts/release_meta.py version` | 1.2.0 | current checkout package, not release authorization |
| P4 export `build_export.py --check` | PASS, 343 cases / 3,396 entries / 146 derived, zero mismatches | existing registered export; D1 separately checks all 3,250 direct entries |
| `ffprobe` overview + `nb_frames/avg_frame_rate` | 180.000 s by both methods | current historical media; original 2:50 records remain dated |
| Ruff 0.15.8 on `check.py` and navigation browser tests | PASS | Python syntax/lint |
| Frontend production TypeScript/Vite build | PASS | new control styling and strict final-stop journey |
| Frontend `npm test` | PASS, 354 tests | includes all 72 ordered tab pairs and mid-journey reduced-motion release |
| Browser navigation/control tests | Recorded with the UI gallery | real native picker keyboard selection, 101-position ordered travel, four desktop sizes, target-nav identity, final alignment, history/focus/recovery |
| Impeccable mechanical detector | no findings | scoped UI scan; actual rendered screenshots inspected separately |
| `git diff --check` | PASS | source/document whitespace |
| Unauthenticated GitHub releases endpoint | HTTP 404 | not a successful public release/asset-access verification |

The first package's available documentation/evidence work is implemented and
checked against each registered requirement. **External completion is not claimed:**
P1 shared-doc approval, allowed defence version/O1, final release/image, merged-source
P4 acceptance, release J1/G3, selected-image full viewer acceptance, physical
rehearsals/devices and final PDF/media remain with their owners. S5 is not run by
this D1 package. Later P2 packages are not marked complete.
