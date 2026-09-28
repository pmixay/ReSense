# Paired processing-history stress check

Status: **passed, 33/33 histories**. [Comparison](comparison.json) checks each history using the
[registered criteria](acceptance.json). A removed STOP elsewhere cannot cancel a new STOP frame.

Across 12,468 processed frames per variant, every paired compressed capture is byte-identical.
There are zero new or removed false STOP frames, zero new events, and zero changed detection
payloads. Both variants retain 204 false STOP frames and 55 distinct track events across
15 histories. This check shows no regression on these known clear development recordings;
it does not establish performance on unseen recordings. Replay timings were concurrent and
are not latency evidence.

## Results

Each cell is **STOP frames / track events**, identical for baseline and candidate. All 30 cache
histories use seed 0. Full frame identities, timestamps, and detections are in the compressed
captures linked by [baseline.json](baseline.json) and [candidate.json](candidate.json).

| Recording | Every | Drop 20% | Drop 40% | Catchup | Offset | Dither ±5 mm |
|---|---:|---:|---:|---:|---:|---:|
| roundT_doubleT | 0 / 0 | 2 / 1 | 2 / 1 | 0 / 0 | 0 / 0 | 0 / 0 |
| doubleT_platform | 2 / 3 | 5 / 2 | 13 / 5 | 7 / 2 | 1 / 1 | 10 / 4 |
| roundT_pressureGate_roundT | 0 / 0 | 0 / 0 | 0 / 0 | 5 / 1 | 0 / 0 | 0 / 0 |
| roundT_squareT_pressureGate_squareT | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| squareT_platform_squareT_switch | 38 / 8 | 25 / 7 | 6 / 3 | 24 / 4 | 26 / 6 | 38 / 7 |

The three mandatory histories replayed from the original `roundT_doubleT` bag also match:

| Raw history | Processed frames | STOP frames / events |
|---|---:|---:|
| failed_clear | 233 | 0 / 0 |
| old_stock | 243 | 0 / 0 |
| old_pass | 234 | 0 / 0 |

## Identity and method

The runner now requires the original `roundT_doubleT` bag and all three captured node histories.
It checks that every requested raw frame is replayed in order and rejects missing cache frames
or timestamps. Each history saves a compressed per-frame capture containing source frame index,
frame ID, timestamp, and every STOP detection. Each report pins the effective config, source files,
imported detector path, runner, recordings, captured histories, and cache inventory by SHA-256.

The comparator checks input alignment and rejects each history that gains any false STOP frame
or unmatched STOP event. Events are distinct reported track IDs, matched one-to-one across runs
when they overlap at a nearby position in an identical input frame. Every changed detection
payload is retained exactly, including changes that meet that correspondence rule.
It also requires the expected production file maps and effective config hashes from the
registered criteria, so comparing one detector variant to itself cannot validate this pair.

The baseline uses the original detector in `ReSense-score`; the candidate uses the proposed
0.3-second low-object continuation defaults in `ReSense-continuity` at `ef1d8f5`. Only scripts,
tests, and evidence are changed by this history check. The frozen production files are untouched.

The baseline report records commit `6f910cf8e77bacfc861fc23dd051ae3298a84700`; its production
file map equals the original detector at `846cbfb`. The candidate records
`ef1d8f50299d9ccbbf65fc4ad5519764615853f6`. Both maps were unchanged throughout replay and
match the expected maps in `acceptance.json`.

| Identity | Baseline | Candidate |
|---|---|---|
| Production SHA-256 | `4e6eb1e72c49980a345134373e4e05e053b61aa4e4fb5e54854a3cb9f83ca252` | `9cc928915ab175de95675ed7ea880d7424410dbb7ed7426ca52cc076f51c5774` |
| Effective config SHA-256 | `de5c7fd6dfa74c1e656af6e233efd625e3e552736534e32efa625e5e8ff57f47` | `6a6e5d859a0c1a86adce91edf1e8a46cd35b4bee21c5876406f1071cf2eaa46f` |

The detector-only subsets also match the previously frozen synthetic pair. Production hashes
above use the wider `detector_freeze.py` scope, including configurations and build files.
The same replay runner was used for both variants:
`384403ede6e6359505e1d4c27a582933af718969aaea5202c0194dd4a9532bc2`.

## Reproduce

Inside the replay container, use the same new runner for both checkouts, each at its recorded
source commit. Run the comparison from the candidate checkout. `--source-root` selects imports
explicitly and the runner checks the loaded detector path at entry and in each worker.

```bash
python /workspace/ReSense-continuity/scripts/history_stress.py \
  --source-root /workspace/ReSense-score \
  --cache /cycle/cache --bag /data/for_hackathon/roundT_doubleT --jobs 1 \
  --out /workspace/ReSense-continuity/out/history/baseline.json

python /workspace/ReSense-continuity/scripts/history_stress.py \
  --source-root /workspace/ReSense-continuity \
  --cache /cycle/cache --bag /data/for_hackathon/roundT_doubleT --jobs 1 \
  --out /workspace/ReSense-continuity/out/history/candidate.json

python scripts/compare_history_stress.py \
  --baseline out/history/baseline.json --candidate out/history/candidate.json \
  --expect-identities docs/evidence/cycle_2026-09-28/continuity/history/acceptance.json \
  --out out/history/comparison.json
```

The 21 focused tests exercise missing raw histories and replay frames, missing timestamped cache
frames, source-root errors, capture hash checks, input sequence changes, event ID changes, split
events, equal totals hiding new false STOPs, and incorrect or inconsistent frozen identities.
They passed, as did Ruff for the runner, comparator, and tests. The independent tooling review
found no remaining blocker after the expected source/config identity check was added.
