# D1 full-cloud context: rejected

The fixed candidate failed two acceptance conditions. It stays on the isolated experiment
branch; it is not part of the frozen detector and was not retuned after these results.

| Measure | Frozen baseline | D1 |
|---|---:|---:|
| Set O outside false STOP frames | 6 | 9 |
| Ride STOP episodes | 38 | 40 |
| Ride false alarm events | 45 | 45 |
| Five empty recordings: events / episodes | 13 / 16 | 13 / 16 |
| Small edge object: STOP frames | 2 | 7 |
| Small edge object: sustained STOP distance | 5.2 m | 14.5 m |
| Novel placements: target-matched frames | 544 | 591 |
| Novel placements: cases with a target match | 45 / 72 | 45 / 72 |

## What the measurements show

Full context helps some compact small objects, but compactness does not establish correct
envelope membership. The nearby object labelled outside gains false STOPs at frames 519–521,
starting at 27.2 m. Its baseline floating advisory becomes a regular gauge candidate. Some
returns already lie inside the current fitted strict polygon; that fitted membership is not
independent proof of the physical envelope. The baseline production traces and both output
records are retained in [the three examples](new_false_stop_examples.json).

All 72 fixed novel cases were retained. Eight existing-hit cases gained 47 matched frames,
with no lost matched frames and unchanged control STOP frames (12). Small-center matches
rose 230→271 and small-on-rail matches 211→217. Top-box matches stayed 58 and hanging-object
matches stayed 45. No previously missed whole case became detected. These synthetic
combinations use seen backgrounds and source shapes; they do not establish real hold-out recall.

The full unchanged scorer produced 199 comparison rows: 146 gated, with 138 unchanged,
six improved and two worse. None is missing and no waiver was used. The protocol's phrase
“183 gated values” did not match the actual tool/baseline count; every returned row is preserved.

## Receipts and evidence

- [Preregistered method](../quality_cycle_2026-09-26_D1_protocol.json), committed `eea6a6b`.
- Candidate implementation `c0aa51c`; evaluation receipt `a3cbb4e`.
- [Pinned 72-case plan](../quality_cycle_2026-09-26_D1_novel_plan.json): only the code receipt
  and explicit parent-plan receipt changed; cases, config and inputs stayed identical.
- [Decision and detailed comparison](summary.json), [all comparison rows](comparison_rows.json).
- [Full gate](gate.json), [gate log](gate.txt), [Set F frame results](setF_straight.json.gz).
- [All novel frame results](novel_result.json.gz), [novel run log](novel.txt).
- [15 focused unit tests](unit_tests.txt). Independent review found no blocking mismatch
  with the registered component construction and conservative boundary rejection.
- All 15 real/cache replay streams are compressed in `gate_frames/`.
- [Artifact hashes](manifest.json).

Original ordinary candidate objects are preserved by the implementation. Final tracking
outputs are not guaranteed unchanged: a newly promoted candidate can alter greedy associations.
The full replay, including its two failures, governs the decision.

Raw replay and ROS timing were not run after decisive rejection, as directed by the captain.
No runtime pass is claimed. Offline timing fields were collected under
concurrent load. The exact failed variant is retained for review; none of its detector changes
should be cherry-picked into the accepted implementation.
