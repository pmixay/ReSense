# Checks

All commands use the existing read-only environment:
`C:/Users/alikh/AppData/Local/Temp/opencode/resense-p3-venv/Scripts/python.exe`.

| check | checkout | result |
|---|---|---|
| `python -m pytest -q tests/test_robustness_battery.py` | P4 harness `6157dcd` | **18 passed**, 0 skipped, 0.37 s |
| `python -m pytest -q tests/test_native.py tests/test_regression_gate.py tests/test_cache_io.py tests/test_cache_extended_ride.py` | detached exact `707ea9c` with its newly built native binary | **59 passed**, 0 skipped, 4.35 s |
| `ruff check scripts/robustness_battery.py scripts/p4_data_intake.py tests/test_robustness_battery.py` | P4 harness `6157dcd` | **All checks passed** |
| `git diff --name-only 3fdc879 HEAD -- resense native configs pyproject.toml setup.py ros2_ws/src/resense_ros/config scripts/detector_freeze.py docs/evidence/detector_freeze_2026-09-29_shell_off.json` | P4 branch | empty |

The driver tests exercise corrupt/truncated/extra/duplicate reports, wrong
stamps, missing detections, inconsistent decisions, invalid JSON/NaN,
5 Hz original indices and processed-frame episode counting, deterministic
seeded transforms on aligned intensity/ring arrays, sensor/vehicle mapping,
per-row crossing intent, directional tolerance, incomplete references/caches,
worker cap, and both public/internal no-overwrite paths. A worker that exits
zero but produces a truncated report results in **ERROR**, not PASS.

The standing tests cover native parity, the full gate's comparison and missing
row rules, compressed cache identity and the extended-ride intake checks.
They are in addition to the measured complete gate and 40-case X3 battery.
The gate and battery measurement commands, exit codes and retained logs are recorded in
`commands.json`; the Windows checkout freeze result is `freeze_verify.log`.

After measurement, all 40 complete raw reports (29,765 rows) were read through
the driver's reference-validation path. All 188 indexed measurement files
match their recorded byte counts/hashes; the four battery input identities
match H0, and the measured driver hash matches the committed file. All 260
self-comparison metric rows pass. See `evidence_validation.json`.
