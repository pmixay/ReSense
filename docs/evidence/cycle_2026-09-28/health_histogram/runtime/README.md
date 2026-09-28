# Quiet installed-image runtime comparison

One registered, fixed-order, warm-disk local pair per recording. Only
`resense/health.py` differs between installed implementations; config, native
binary, dependencies and ROS node code match. This is not cold-start or
target-hardware acceptance.

| Capture | Original frames processed | Strict current results | Decode+detect p95 | Current-result E2E p95 |
|---|---:|---:|---:|---:|
| Baseline positive | 201/201 | 0/201 | 105.15 ms | unavailable |
| Candidate positive | 201/201 | 170/201 | 76.32 ms | 167.85 ms |
| Baseline clear | 252/252 | 245/252 | 77.33 ms | 86.76 ms |
| Candidate clear | 252/252 | 250/252 | 60.51 ms | 73.78 ms |

**The baseline positive run failed** the 100 ms p95 requirement and produced no
fresh result. It is retained in full. The candidate passed the registered checks,
but fresh availability remains incomplete. Candidate fresh person recall is
49/61 and fresh rail recall 117/185, including 115/126 from frame 75. First fresh
person STOP is frame 16, with five consecutive fresh STOPs first starting at 18;
rail first/sustained fresh STOP starts at 73. Eleven later rail frames remain
catch-up results. See [the detailed audit](audit/README.md) for missed intervals,
complete distributions and the exact freshness predicate.

Raw matching stays person 61/61 and rail 128/185 (126/126 after frame 75). The
selected raw detector outputs match exactly on all 453 paired frames. Both clear
runs have zero STOPs. These results support a local processing improvement, not
full fresh recall or an independent score increase.

Header matching confirms zero unprocessed stored messages. The positive bag's
two original timestamp gaps represent four absent nominal-rate slots; the node
counter of four is not four lost bag messages. All original captures, checker
outputs, build identities, protocol, execution record, observers and audits are
preserved.

## Archive integrity

`manifest.json` maps every original file to its stored path, original and stored
SHA256, sizes and encoding. The four `status.jsonl.gz` files decompress to exactly
the captured bytes; original `node.log` files are retained as `node.txt`. Image
identities and build logs are included; image layers are not duplicated.

Observer reports retain original `/cycle` paths and hashes. Use the manifest to
locate the corresponding compressed or renamed files. The frozen auditor and
summary generator are in `audit/`; their provenance binds the original captures,
labels, checker, image identities and registered execution. No failed run was
discarded or replaced.

The observer snapshots are `audit/audit_fresh_capture.py.txt` and
`audit/summarize.py.txt`, retaining their exact original bytes and hashes. Restore
their original `.py` names outside the archive to execute them. The original audit
README/report refer to those original filenames; the manifest maps them to these
stored evidence snapshots. Repository lint does not execute or rewrite them.
