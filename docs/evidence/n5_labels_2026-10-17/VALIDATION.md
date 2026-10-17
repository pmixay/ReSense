# Annotation-tool validation — 17 October 2026

All seven owned Python files pass the repository's pinned **Ruff 0.15.8** `check` and
`format --check`: the annotation materializer, its two-test module, and the five archived
discovery/proposal/review scripts. Formatting and import fixes made during the combined
test run are the reason for the final source freeze below; canonical annotations did not change.
The final targeted rerun passed **2 tests** with unchanged source hashes:
[C2 follow-up receipt](../c2_acceptance_2026-10-17/final_annotation_followup.json).
The C2 validation report discloses the source drift during its otherwise successful full test run.

Final source SHA-256:

| File | SHA-256 |
|---|---|
| `scripts/annotate_synthetic_tracks.py` | `cb9b65681ffb7f6edfadcc79f066b27fb2063ba7419b487a36667ab276de7317` |
| `tests/test_team_annotation_builder.py` | `29447dca132bd12b3e130fc6ddb68b1037157656c4e9b21764047a78cf81f108` |

The two annotation tests cover retained radial-filter near-pass points, sensor-axis mapping,
echo duplicate counts, unknown gauge relations, non-exhaustive empty frames, and refusal to
emit an unsupported reviewed box. Geometric assignment tests belong to the independent
[scoring protocol](SCORING.md).

Canonical label SHA-256, independently validated before the six archived comparisons:

| Recording | SHA-256 |
|---|---|
| platform | `03578bd979d5a10d1067f4b83759d0863ccfa20e7e01c5c809d790d69e210ad7` |
| switch | `b6307eb801525ad5da4ac89cc3425ff337a02569effa0608b137e7e836fc49e6` |
| tunnels | `b1e7c5b081914f6bd480b83bafbc551be338dccb93f4615c1a44f5d95da3bc7b` |

The materializer source is frozen. The final boxes, uncertainty metadata and label hashes
are unchanged from the independently reviewed scoring inputs.
