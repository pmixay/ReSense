# Pre-registration validation record

Registration date: 2026-10-15. Base: `3fdc879`.
Branch: `p4/heldout-spec-2026-10-15`.

Only `validate.py` was executed. It uses the Python standard library, imports
no ReSense / judge / native / Open3D modules and writes no files.

Command, run in two fresh processes with `PYTHONHASHSEED=1` and `8675309`:

```powershell
& "C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe" -B "docs/evidence/heldout_2026-10-15/validate.py" --check-inputs --self-test
```

Both processes returned **PASS**, with identical canonical hashes:

| Check | Result |
|---|---|
| Fixed seed / complete deterministic case table | 84 unique cases |
| Fixed disjoint ride windows; whole-recording exclusion check | 4 windows, PASS |
| Shapes / classes | 9 configurations, 8 classes |
| Perturbations / scheduled future replays | 11 / 924 |
| Deliberately invalid specifications rejected | 8 of 8 |
| Timestamp input files fingerprinted | 56 |
| Compact point filenames present (payload not read) | 2,856 |
| Original DB3 split filenames present (payload not read) | 56 |
| Input definition hashes / A,B,C,D,S interval extraction | PASS |
| Duplicate-key / finite-JSON parsing and structural validation | PASS |

* Canonical spec SHA-256:
  `36d2c867d856330059416a8bfe3a13c9b119d4b4fcc019ec27fe3e667fca6093`
* Canonical case-table SHA-256:
  `0e799d2845884ff2abeb213659ee01abdf7d2945db8bb8ee61e240e2f6838232`
* Canonical input-metadata SHA-256:
  `a7a952237aaef4fad1047a4327623bff95f29061b688fcb25deb3f95e730bf80`

Canonical means UTF-8 JSON with sorted keys, compact separators, ASCII escaping
and nonfinite values forbidden; these are not whitespace-dependent file hashes.

This is **schema / input-metadata / determinism validation**, not detector,
range, visibility, ICP, held-out scoring or final-seal verification. No results
were produced. Remaining geometry/runner and input-gap limitations, and the
incidental legacy-snippet exposure, are disclosed in `README.md`.
