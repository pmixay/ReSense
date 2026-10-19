# Independent checkpoint review — 28 September 2026

## Result: 66/100

This is GPT-6 Astra’s independent review judgment against official specification §8. The weights below are internal weights requested for this review; organizers publish no numerical weights. The score is not a measured performance percentage.

## Scope and blind procedure

Reviewed measured candidate `ef1d8f50299d9ccbbf65fc4ad5519764615853f6` and image source `6104122bccce0ef4800533016774690ede5218f0`. The source proof establishes equality of all 31 frozen files. Image: `sha256:ca5ce7502cca717f581ea7de09306b0e00e3bbe78fc138dfc9ae79632fdeebb6`.

I did not read README.md, SCORECARD.md, CURRENT_REVIEW files, IMPROVEMENT_CYCLE files, or old checkpoint score JSONs. Assessment used the official rubric, direct source inspection, experiment artifacts, captures and presentation. New parallel P3 work did not affect the rating. Root subsequently reported development integration at `84763cf`; this document preserves the completed rating and adds no new review or testing.

## Criterion scores

| Criterion | Score / weight | Reason |
|---|---:|---|
| §8.1 Detection performance | 17/25 | Raw rail continuity improves 123 to 126/126 after frame 75; person remains 61/61. Negative outputs remain unchanged, including existing false alarms. Real positive coverage is narrow. |
| §8.2 Detection range | 6/15 | Real positive evidence is around 56 m. Synthetic results support longer ranges for larger objects, but small and edge objects remain weak. Reliable real detection at 100–300 m is unproven. |
| §8.3 Speed | 7/10 | Efficient CPU detector and successful historical ROS runs. Latest quiet full-speed candidate run fails freshness and the 100 ms target; matched baseline also fails. No candidate speed gain established. |
| §8.4 Generalization | 6/15 | Environment geometry, perturbation tests and reserved evaluation provide useful evidence. Reserved synthetic sustained detection is 14/32 float32 and 13/32 compact, with no candidate gain. No unseen real positive route. |
| §8.5 Technical development | 9/10 | Clear architecture, bounded continuation, 841 image tests passed, strict regression gate, provenance and 33 identical history captures. Monitoring overclaims remain unresolved. |
| §8.6 Ease of launch | 8/10 | Built image, installed/native imports and offline two-topic smoke pass. Full-speed local real-bag acceptance fails; candidate CI and organizer stand remain unverified at review time. |
| §8.7 Team approach | 9/10 | Extensive controlled experiments, rejected alternatives, explicit limitations and preserved failures. |
| §8.8 Pitch | 4/5 | Substantive presentation and demonstration assets explain the algorithm and limitations. Candidate metrics need refreshing; timed human delivery is unverified. |
| **Total** | **66/100** | |

## Integration decision

**Support development-branch integration with the proposed defaults.** The bounded continuity improvement passes the full quality gate without waivers, adds no measured negative alarms, preserves all 33 history captures and causes no reserved-synthetic regression. Keeping it default-off is not required solely by a runtime failure also observed in the matched baseline.

**Deployment acceptance remains provisional.** The quiet candidate run produced 198/201 frame statuses, decode-plus-detect mean 103 ms / p95 125 ms, detector mean 36 ms / p95 53 ms, and no fresh valid result. Matched baseline also failed: 166/201 statuses, decode-plus-detect mean 119 ms / p95 137 ms, detector mean 42 ms / p95 58 ms, and no fresh valid result. This single unrandomized pair on a four-physical-core i7-8565U does not establish a speed gain. Candidate CI and organizer-stand validation were pending at review time.

Integration measurement note: the 36/53 ms and 42/58 ms figures above are the
instrumented pipeline stages. They exclude health computation performed later
in `Detector.process`; decode-plus-detect remains the runtime acceptance metric.
The subsequent clear-bag candidate run passes all 252 frames with zero alarms or
drops and decode-plus-detect p95 93 ms; current-result end-to-end p95 is 105 ms.
These clarifications do not change the completed independent rating.

The earlier heavily loaded failed run remains evidence. The passing two-topic synthetic smoke used half-speed replay and proves integration and freshness behavior under that condition, not full-speed real-bag acceptance.

## Limits and next work

Raw positive continuity improves 123→126/126 after frame 75, with person 61/61 unchanged. Compact-cache gate counts are separate: rail 129/185 overall and 126/126 after frame 75. Existing negative alarms remain unchanged. Reserved synthetic results have no gain, only 14/32 sustained positives for float32 and 13/32 for compact, with zero negative STOP frames out of 64 per encoding. These are not evidence of unseen real-world transfer.

Existing 16 set O GO-overclaim diagnostics remain; those envelope labels inherit a historical detector fit. Development-v2 synthetic reports also show 208 GO-overclaim frames per encoding. No unseen real positive route or organizer-stand test supports stronger generalization claims. Public presentation role cards are intentional; absent public personal names were not counted as broken templating.

1. Resolve full-speed ROS freshness on representative hardware using matched runs.
2. Measure unseen real positive approaches, particularly small objects beyond 100 m.
3. Validate physical envelope labels independently and address overstated clear distance.
4. Reduce station/switch false alarms while preserving continuity.


## Evidence

Paths beginning with `docs/` are relative to the repository root. External workspace evidence paths identify the reviewed artifacts.

- **official rubric:** `docs/organizers/technical_specification_case05.txt, section 8`
- **candidate source proof:** `/home/likikikpa/ReSense-cycle-data/proposed_image_source.json`
- **raw continuity:** `/home/likikikpa/ReSense-continuity/docs/evidence/cycle_2026-09-28/continuity/raw/summary.json`
- **candidate gate:** `docs/evidence/cycle_2026-09-28/regression/candidate/gate.json`
- **monitoring:** `docs/evidence/cycle_2026-09-28/regression/candidate/monitoring_acceptance.json`
- **history:** `/home/likikikpa/ReSense-continuity/docs/evidence/cycle_2026-09-28/continuity/history`
- **development v2:** `/home/likikikpa/ReSense-cycle-data/synthetic/comparison-development-v2.json`
- **reserved v2:** `/home/likikikpa/ReSense-cycle-data/synthetic/candidate-reserved-v2.json`
- **image tests:** `/home/likikikpa/ReSense-cycle-data/image_candidate_test_output/junit.xml`
- **image smoke:** `/home/likikikpa/ReSense-cycle-data/image_candidate_smoke.log`
- **candidate quiet runtime:** `/home/likikikpa/ReSense-cycle-data/candidate_raw_node/quiet_positive/status.jsonl`
- **candidate quiet checker:** `/home/likikikpa/ReSense-cycle-data/candidate_raw_node_quiet_positive.log`
- **baseline quiet runtime:** `/home/likikikpa/ReSense-cycle-data/baseline_raw_node/quiet_positive/status.jsonl`
- **historical cold runtime:** `docs/evidence/p1_p2_cold_bags_2026-09-28`
- **historical node input:** `docs/evidence/node_input_2026-09-28/cold_local`
- **full data:** `docs/evidence/results/p4_full_data_2026-09-28/final_regression_gate.json`
- **presentation:** `docs/presentation/ReSense_LCT2026.pdf`
- **architecture:** `docs/ARCHITECTURE.md`
- **experiments:** `docs/EXPERIMENTS.md`

The candidate earns credit for a specific continuity fix, not demonstrated gains in range, generalization or false-alarm reduction.
