# Current review evidence — 28 September 2026

Reviewed source: `20e82297bbf859e7d63bee35044d6c8314f746c5` on
`gpt-score-push-20260928`. [Assessment](../../CURRENT_REVIEW_2026-09-28.md): **69/100**.
[Machine-readable scores](score.json) retain the prior internal weights and assign zero delta.

## Fresh checks

| Record | Scope and result |
|---|---|
| `fresh_raw_default.jsonl.gz`, `fresh_replay_comparison.json` | Current native detector on all 201 original obstacle-bag frames. Person 61/61; rail object from frame 75: 123/126. Public detection fields equal the previous raw default; tiny track-fit numerical differences are recorded. |
| `pytest.txt`, `junit.xml` | Full local test run: 764 passed, six subtests passed; one failure because an older partial ride cache lacks `new_data_55_0013`. |
| `pytest_ride.txt`, `junit_ride.xml`, `ride_sources.sha256` | Rebuilt the needed cache from original ride splits 55 and 56; the remaining test passes. These are complementary runs, not a claim that the initial run was all green. |
| `fixture_smoke.json.gz` | 302 controlled synthetic frames; gap behavior, clear/transient scenes and six repeated far-object scans. No new-scene or timing claim. |
| `ci_receipt.json` | GitHub API receipt for four successful jobs on the exact reviewed source, run 36453635491. Extended cold-bag and remote-viewer checks are skipped by this branch's allowlist. |
| `recomputed_judge_outputs.json`, `recompute.txt` | Recount of already committed raw/ROS outputs, not a fresh replay of all bags. |
| `recent_evidence_audit.json` | Independent hash, label-match and gate-accounting verification of the new fixture and rejected continuity experiment. 146 enforced rows, 208 unchanged rows including informational values. |

`SHA256SUMS` covers the retained files. The `.py.txt` scripts preserve the review commands without
adding production/test-suite code. They require the reviewed repository contents; the two Docker
scripts use `/work` as the source mount and write under `out/current_score_2026-09-28/`.

## Environment

Host: Intel i7-8565U, four physical cores/eight threads. An isolated review container was based on
the PC's existing `resense:p2-demo` image, with **current source installed at `/work`**, rather than
using that image's older installed detector. Python 3.10.12, NumPy 1.26.4, SciPy 1.13.1,
scikit-learn 1.5.2, Open3D 0.20.0, pytest 9.1.1, Ruff 0.15.8; native kernels enabled.

The original input dataset was mounted read-only at `/data`. The obstacle DB3 SHA-256 matches
`scripts/cold_bags.sha256`. Timing and load-dependent health were excluded from the raw output
comparison because other checks overlapped. This was a functional replay, not a speed benchmark.
No fresh ROS deployment, full ride gate or stand rehearsal is claimed.

## Commands

From `/work` in that environment, with the repository dependencies installed:

```bash
python3 scripts/detector_freeze.py verify
bash scripts/sync_params.sh --check
ruff check .
RESENSE_REQUIRE_SYNTHETIC=1 python3 -m pytest -q -rs --junitxml=out/current_score_2026-09-28/junit.xml

python3 -m resense.cli run --bag /data/for_hackathon/doubleT_obstacle \
  --config configs/default.yaml --out out/current_score_2026-09-28/fresh_raw_default.jsonl --quiet
python3 docs/evidence/current_review_2026-09-28/check_fresh_replay.py.txt
python3 docs/evidence/judge_outputs_2026-09-28/recompute.py \
  --json out/current_score_2026-09-28/recomputed_judge_outputs.json
python3 docs/evidence/current_review_2026-09-28/recompute_recent_evidence.py.txt \
  out/current_score_2026-09-28/recent_evidence_audit.json
python3 docs/evidence/current_review_2026-09-28/fixture_smoke.py.txt
```

Repair of the local cache and the focused rerun:

```bash
python3 scripts/cache_frames.py /data/full_ride/new_data/new_data_55.db3 \
  out/current_score_2026-09-28/ride_cache --every 1 --int16 --stamps --zstd
python3 scripts/cache_frames.py /data/full_ride/new_data/new_data_56.db3 \
  out/current_score_2026-09-28/ride_cache --every 1 --int16 --stamps --zstd
RESENSE_REQUIRE_SYNTHETIC=1 RESENSE_RIDE_CACHE=/work/out/current_score_2026-09-28/ride_cache \
  python3 -m pytest -q -rs \
  tests/test_rail_start.py::test_finding_rail_heads_ahead_of_a_standing_fresh_start_do_not_stop \
  --junitxml=out/current_score_2026-09-28/junit_ride.xml
```
