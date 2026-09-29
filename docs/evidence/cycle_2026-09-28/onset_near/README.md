# Near-preserving fresh STOP onset candidate

Status: **rejected for promotion**. The full default gate failed two Set F first-detection metrics. No score improvement is claimed; history replays were not started.

Production source is `8983ea24c61d4be36cc502784313605551e61417`, based on health candidate `ef71c9dc4f88147327dcb41ea79358dfc690ba77`. Protocol commit `1cef43d` preceded production edits. See [validation.json](validation.json) for the source inventory, config/native hashes, retained test failures and proposed gate command.

The onset check preserves established near escalation only with zero misses, a current eligible near cluster and latest source `ordinary` or `off_gauge`. Prior thin continuation can still contribute to near history; this preserves the earlier policy and does not certify that every near hit was ordinary. Current continuation does not use the exception. The only effective default change is `tracking.fresh_stop_evidence: false -> true`; low continuation remains 0.3 seconds. The original P3 experiment config is unchanged.

## Focused results and retained limitations

Focused boundary, near geometry, approach, opinion, calibration, long-gap, low-continuation and config checks passed across the recorded runs after updating explicit old-policy expectations. Initial failure logs remain attached; no production thresholds were tuned to them.

- Optional thin mode 2 now starts a STOP one frame later in the tested sequence, after the second ordinary match following thin history.
- With both thin continuation and near escalation disabled, the raycast signature-only case loses five additional STOP frames after a gap (15–19, beyond the earlier misses at 13–14). This compatibility limitation is asserted explicitly.
- Thin mode 1 under either onset policy and the actual proposed defaults retain every STOP after frame 3 in that raycast sequence. This is not universal recall parity.
- The proposed default suppresses stale-gauge STOP onset on a current advisory. Tests preserve the historical comparison and directly assert the new behavior and unchanged majority vote.

The authorized original-header positive replay is archived under `raw_positive/`. Its timings are diagnostic under shared load. The full gate must compare the final proposed default source against `/cycle/health_histogram/default/gate.json`, with no overrides or waivers; paired histories and monitoring acceptance remain required.

## Failed full gate

The exact merged source at `0ca664cec25f8521bee3e9e65d134bc7e0b2baba` completed the full native gate in 635.7 seconds with no overrides or waivers. Source, config, native binary and baseline hashes were unchanged. All captures, metadata and the failed result are retained in [default/](default/).

| Metric | Health baseline | Candidate |
|---|---:|---:|
| Person median first detection | 151.0 m | 150.5 m |
| Trolley median first detection | 151.4 m | 135.4 m |
| Ride false events | 32 | 27 |
| Ride STOP episodes | 31 | 26 |
| Ride STOP frames | 130 | 117 |

Four of 30 Set F sequences lose nine hit frames, with no gained hits. The affected person sequence starts at 151.01 m instead of 166.28 m; one trolley sequence starts at 116.10 m instead of 148.06 m. The saved per-sequence comparison is [setF_failure_analysis.json](default/setF_failure_analysis.json). Real negative gate captures have no new false STOP frames or unmatched events, and monitoring costs pass, but these benefits do not compensate for the positive recall failures.

The separately registered [observer diagnosis](observer/README.md) reproduces all four affected Set F sequences under both sources (800 frames) and two ride prefixes (589 frames), with exact semantic parity and unchanged source identities. Four direct Set F losses reject current `beyond_height_ref` advisory evidence; four reject the first ordinary gauge hit after two advisory hits; one is the ensuing lost missed-frame hold. The representative ride false events instead combine low-object and corridor evidence. Full traces and protocols are retained; production remains unchanged.

## Original positive replay

All four variants processed the same 201 original header-stamped frames. Against the health configuration, the proposed default preserves person coverage 61/61, rail coverage 128/185 overall and 126/126 from frame 75, and six unmatched detections. There are no changed non-timing top-level fields or monitoring ranges and no new onset gain on this recording. Non-latency health messages and decision levels agree. The health level differs only at frame 200 because measured latency p95 crosses the unchanged 100 ms warning threshold (100.1 versus 99.8 ms); this shared-load timing difference is not a speed claim.

## Evidence import

This rejected candidate's evidence was imported from commit
`199a6e897753326fa1879bd5e8d398af5d79a8e7`. Its measured source/configuration remains identified
in the original records. Only this evidence directory was imported.
[import_manifest.json](import_manifest.json) maps original files to their archived paths and
hashes; frozen observer scripts use `.py.txt` and logs use `.txt`.
