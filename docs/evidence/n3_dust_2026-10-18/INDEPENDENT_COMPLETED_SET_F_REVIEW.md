# Independent completed Set F review

The completed evidence verifies: **30 frozen placements × four levels, 120 compressed captures and 12,240 evaluated rows**. The [independent receipt](independent_completed_set_f_review.json) and [read-only checker](review_completed_set_f.py) reproduce every per-sequence summary, first matched range, lost/new hit list, aggregate and unmatched-detection episode count. No detector or renderer was rerun. This validates the evidence, not N3 acceptance.

| Level | Target-matched rows | Lost clean matched rows | Unmatched-target frames / episodes | GO | Degraded |
|---|---:|---:|---:|---:|---:|
| Clean | 1,064 | 0 | 23 / 11 | 1,501 | 0 |
| Low | 1,027 | 61 | 18 / 13 | 1,533 | 0 |
| Medium | 752 | 392 | 1,480 / 275 | 385 | 0 |
| High | 14 | 1,050 | 183 / 58 | 2,311 | 0 |

Each level contains 3,060 rows. Low and medium add 24 and 80 new matched rows respectively; those gains do not erase the separately reported losses. High loses every clean hit in 21 previously detected sequences. The low `46_box0.5` sequence loses all three clean matches. The low synthetic `68_person` first match moves from 144.10 m to 117.98 m. This synthetic result is separate from the real crossing-person criterion, whose low-density range remains 55.51 m in the regular battery. It cannot replace that measurement or justify a claim that all person cases passed.

The fields named `false_stop_frames`, `false_stop_episodes` and `false_detections` retain the registered **unmatched synthetic-target scoring**. They do not establish surveyed negative truth for every object in the real background. A frame may contain both a target match and an unmatched detection. Moreover, the legacy hit definition requires at least one clean-rendered object return; STOP rows with zero clean object returns number 24, 26, 302 and 28 across the four levels. These details prevent treating target-hit and unmatched-frame totals as a complete, disjoint classification of all STOP frames. The known-empty regular-recording episode criterion remains a different evaluation.

Independent matching bounds account for the 0.01 m serialized distance/lateral precision. Every recorded hit and unmatched count satisfies the bounds, with **zero ambiguous boundary rows** in this completed battery. This checks the approximate legacy association, not physical object identity.

All 30 archived placement banks match their frozen hashes. I reconstructed the six source approaches from original speed metadata and timestamps, including the 110-frame maximum and 8 m cutoff, and rehashed all 612 unique compressed source frames. Each raw row retains the original bank distance, stamp, clean rendering hash and clean return count at every density. Frozen clean coordinate references, density/attenuation specifications and seeds are consistent. Clean-supported rows remain 2,502 per level; rows retaining object returns fall to 2,496, 2,455 and 2,032 under low, medium and high dust. Clean physical truth is not removed when its observed returns disappear.

A separate [comparison with the native baseline gate](set_f_clean_gate_comparison.json) verifies all 3,060 clean rows individually, rather than relying on the matching aggregate of 1,064 hits. Effective configuration, speed/stamp identities, source-frame names, target specifications and vehicle placement, return counts, hits, unmatched counts, monitored range, visibility and first matched ranges agree exactly. The gate omits complete detections, timestamps and a candidate list, and stores unmatched geometry at a different precision. Therefore this is shared-field equality with source provenance, not proof of complete output equality or byte-identical injected point clouds. [The comparison helper](compare_set_f_clean_gate.py) performs no detection or rendering.

The pinned detector is `9b92df5` and the corrected harness is `b9ad5f4`, using the recorded native binary. The independent clean placement detector runs before the evaluated density sequences. The evaluated detector receives frames after obstacle-truth metadata removal; return labels and source-index truth are used only for scoring after processing. Bank/hash review does not independently rerender every injected point.

The results demonstrate severe synthetic stress failures, including high-density GO without degradation; they activate no suppression or health-observer candidate. They are not a fresh stress test of selected core `cecab1b`, measured physical-dust validation, surveyed background truth, held-out generalization or a throughput benchmark. The accepted core seal and the completed regular review remain unchanged.
