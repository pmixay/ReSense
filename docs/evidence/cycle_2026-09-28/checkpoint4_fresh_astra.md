# Checkpoint 4 — fresh independent score review

Reviewed 29 September 2026. **Fresh estimate: 65/100** for the detector implementation at commit `292397833edf9db649a24f16807b2cfb15812194`.

This is an independent, evidence-based estimate using the project's internal allocation of the eight §8 criteria. The organizers do not publish numeric weights for those criteria, so this is not an organizer score. Confidence is moderate because the real positive examples are limited. The historical 69/100 and earlier reviews remain distinct assessments; this review does not prove that any earlier score was fabricated or that the detector regressed.

## Scope

- Scored implementation: commit `292397833edf9db649a24f16807b2cfb15812194`.
- Detector source fingerprint: `506a1e05…`.
- The current `experiment/cross-ring-sparse-evidence` head retains that detector fingerprint. The subsequent branch commits add evidence, analysis, tests, and CI fixes; they do not change detector runtime source, configuration, or native code.
- The low-return-support candidate was evaluated separately after this score review. Its full gate failed the safety rule and the candidate is not integrated; it receives no score credit.

## Score by criterion

| Criterion | Score | Evidence and main limitation |
|---|---:|---|
| Functionality | **16/25** | Person detected on 61/61 labeled frames and all eight organizer objects detected at least once. Only 411/801 labeled object frames produced STOP. The empty ride has 32 false events; rail detection is late. |
| Range | **6/15** | Large targets are detected reliably at roughly 100–150 m. Small and edge targets need roughly 18–56 m. Reliable 200 m detection is unproven. |
| Speed | **8/10** | CPU and ROS timing measurements exist. The full timing gate showed output parity, not a speedup. Startup improvement measured with setting `0.2` cannot be credited to the shipped default `0.0`. |
| Generalization | **6/15** | Multiple tunnel backgrounds and synthetic tests are available, but there is no untouched real-positive holdout. A 0.5 m Set F box is detected in 1/6 sequences. |
| Technical quality | **9/10** | Modular design, source contracts, and reproducible tests. `clear_distance` still risks conveying more certainty than the evidence supports. |
| Launch | **8/10** | Docker, offline image, and bag replay are available; playback parameters affect results. |
| Team approach | **9/10** | Experiments are preregistered, and negative results and frame-level changes are retained. |
| Pitch | **3/5** | Slides, video, and ROS demonstration exist. Live delivery is unassessed and some presentation placeholders remain. |
| **Total** | **65/100** | Independent estimate; moderate confidence. |

## Later low-return-support gate

The candidate's preregistered full gate finished with one safety regression: STOP episodes on the empty ride increased from 31 to 32. STOP frames stayed at 130, and alarm events stayed at 32. All 207 other gated metrics matched; Set F matched baseline on all 3,060 frame rows. The candidate changed eight STOP transitions on the empty ride, replacing four baseline transitions with four different transitions. The gate therefore rejects it despite a synthetic pilot improvement; it is not part of the scored implementation.

The archived frame-by-frame comparison contains 585 semantic row changes. Two low-object reports moved from 49.74 m to 59.00 m and from 47.59 m to 59.37 m. The available evidence does not establish the exact raw-return mechanism behind these changes. Full identities, outputs, comparison, and artifact hashes are in [`the full-gate archive`](../low_return_support/full_gate/README.md).

## Limits

The score is a reviewer judgment based on the evidence inspected, not a measured physical quantity. The internal criterion maxima are project choices because §8 does not assign numeric weights. The 65/100 should be read as the current detector line's fresh assessment; evidence and CI commits after the scored commit do not themselves change detector performance. The rejected low-return candidate does not raise this score.
