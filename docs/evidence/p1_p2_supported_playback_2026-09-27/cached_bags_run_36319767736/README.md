# Verified-bag cache cold replay — 27 September 2026

[CI run 36319767736](https://github.com/pmixay/ReSense/actions/runs/36319767736)
passed all seven jobs at `2f237195a6bf80d9c3f57d4b12c9e9e6879d7d56`. On a cache miss,
the dataset job downloaded the organizer ZIP, verified its pinned SHA-256, extracted and verified
the two original bags, and saved the bag cache. The Docker job restored that cache, rechecked
both metadata and DB3 hashes without downloading, evicted the page cache before each playback,
and ran the two original bags at rate 1.0 with ten-message read-ahead. The exact bag hashes and
command provenance are in [provenance.txt](provenance.txt).

The [Actions artifact](https://github.com/pmixay/ReSense/actions/runs/36319767736/artifacts/10932626223)
has SHA-256 `706610b18187096ead1d8513d0378932594573894669c188f34a0dc082f3b6a3`.
Its status streams and node logs are preserved below as deterministic gzip files. Both script
checks passed in [result.txt](result.txt).

| Original cold bag | Result |
|---|---|
| `doubleT_obstacle` | **PASS:** 201 status messages, 187 detector alarm frames, obstacle distance 55.5–56.6 m, decode + detect p95 47 ms. First STOP at +1.1 s of source time was fail-safe while stale. First **current** STOP was at +2.6 s of source time, 55.83 m, as startup catch-up ended; all 151 source messages after the five-second settle point were processed. Four apparent frame gaps are absent from the bag itself. [Status](doubleT_obstacle_status.jsonl.gz), [node log](doubleT_obstacle_node.log.gz). |
| `roundT_doubleT` | **PASS:** 252 status messages, zero alarm frames, decode + detect p95 32 ms. Catch-up ended at +1.0 s; all 201 source messages after the five-second settle point were processed. [Status](roundT_doubleT_status.jsonl.gz), [node log](roundT_doubleT_node.log.gz). |

The cold-bag result on the preceding [archive-cache run](../README.md) settled at +13.6 s;
startup timing varies with the runner and storage state. Both runs satisfy the supported
ten-message procedure and freshness check. They do not validate Humble's 1,000-message default
or establish detector-quality improvement. The independent score and release hold are unchanged.
