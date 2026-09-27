# Supported cold playback — current branch, 27 September 2026

[CI run 36313880352, rerun attempt 2](https://github.com/pmixay/ReSense/actions/runs/36313880352)
passed all six jobs at `5a27c66c35457d36405600492106064dccb8fcdb`. The first attempt
reached no original-bag playback because Google Drive returned a quota page; it remains a dated
acquisition failure, not a detector result. On the rerun, CI downloaded the organizer archive,
verified SHA-256 `e23166801794cdeb2dcd77a3cc8b40a906b1d9cefab6f26739e368234e9168be`,
checked both bags' metadata and database hashes, and cached that archive under its hash. The
exact source and file hashes are in [provenance.txt](provenance.txt).

The Docker job built the image, completed the ROS transport and second-container viewer checks,
removed and reloaded the image for offline checks, then ran
`IMAGE=resense:ci DATASET_ZIP=... scripts/p1_cold_bag_test.sh`. That script evicted the page cache
before each original bag, played at rate 1.0 through `scripts/dry_run.sh` with its supported
default ten-message rosbag2 read-ahead, and required the freshness contract. The
[Actions artifact](https://github.com/pmixay/ReSense/actions/runs/36313880352/artifacts/10931626816)
has SHA-256 `c4dafbb5f71e74e17b927c327a5d316ef31e9bd75f4e0ea42d829eba7fe36e32`.
Its status streams and node logs are preserved here as deterministic gzip files.

| Original cold bag | Result |
|---|---|
| `doubleT_obstacle` | **PASS:** 199 status messages; 190 detector alarm frames; first STOP at +0.8 s and obstacle distance 55.5–56.5 m; decode + detect p95 76 ms. The first STOP was fail-safe with `freshness.valid=false` (`source_stale`). The first **current** STOP was at +13.6 s, 56.15 m, when catch-up ended. All 63 source messages after catch-up were processed; four apparent frame gaps are absent from the bag itself. [Status](doubleT_obstacle_status.jsonl.gz), [node log](doubleT_obstacle_node.log.gz). |
| `roundT_doubleT` | **PASS:** 252 status messages; zero alarm frames; decode + detect p95 48 ms; catch-up ended at +0.7 s; all 201 source messages after the five-second settle point were processed. [Status](roundT_doubleT_status.jsonl.gz), [node log](roundT_doubleT_node.log.gz). |

The checker output is in the CI log and both script-level passes in [result.txt](result.txt).
This verifies the supported ten-message procedure on this commit. It does not establish support
for Humble's 1,000-message cold whole-bag burst. The +13.6 s catch-up is close to the checker's
15 s cap, and the early fail-safe STOP is not evidence of a current detector result. No detector
configuration or independent quality score changed in this P1/P2 pass.
