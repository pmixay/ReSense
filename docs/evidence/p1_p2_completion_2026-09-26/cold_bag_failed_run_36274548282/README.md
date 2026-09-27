# Initial cold-bag run — failed, preserved

GitHub Actions [run 36274548282](https://github.com/pmixay/ReSense/actions/runs/36274548282),
commit `446e0aded9f57e49abfff31516a728bd25e5e123`, downloaded and validated the organizer archive,
evicted the runner page cache, then ran the exact `dry_run.sh` path on `doubleT_obstacle`.

The recording contains 201 messages. The detector produced its first STOP at +1.4 s in the
55.6–56.5 m target window, but the node processed only 85 frames. It skipped 110 frames during
startup catch-up, counted 118 total dropped frames, and did not end catch-up until the recording's
last frame. The acceptance check correctly failed its `--max-dropped 0` requirement: 84 recording
messages remained unprocessed after +5 s. This rejected the then-current 20 s startup-lag-only
change; it did not waive the cold-start failure.

`provenance.txt` records the source archive, its SHA256, extracted metadata hash and bag hash.
`node.log` and compressed `status.jsonl` retain the complete replay diagnostics. The raw archive
and extracted database were deleted by the CI script and are not committed.
