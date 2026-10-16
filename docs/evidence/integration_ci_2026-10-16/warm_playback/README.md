# P1 warm-playback investigation — 16 October 2026

**Verdict: runtime/full CI remains BLOCKED.** The harness now verifies its warm-cache
precondition and records resource/residency evidence. The original Actions loss of
nine post-settle frames has not been demonstrated fixed or attributed to a node bug.

## Authoritative failed run

- Actions run **38897519801**, Docker job **116961605744**, source
  `b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1`.
- `original-ci/docker-job.txt` is the complete retained job transcript;
  `failed-steps.txt`, `run.json` and `capture.json` preserve failure and provenance.
  Raw capture paths have byte-preserving Git attributes; trailing whitespace in
  the three original ROS/GitHub log files is retained rather than cleaned up.
- Tools-image units: **1,640 passed, 10 recorded-data tests deselected**. Native,
  synthetic smoke, console/player interoperability and remote viewer checks passed.
- Cold positive: **201 statuses**, decode+detect p95 **73 ms**, no post-settle bag
  messages lost. Cold clear: **252 statuses**, p95 **49 ms**, no losses or alarms.
- Input parity: **201 + 252 = 453** original frames byte-identical.
- Warm positive: **192/201 statuses**, **9** post-settle bag messages not processed,
  **9** catch-up skips; decode+detect p95 **81 ms**, current E2E p95 **107 ms**, pace
  **1.05x**. Its strict frame/drop checks correctly failed. Warm clear did not run.
- Player queue-starvation warnings appear in both cold positive and warm positive.
  The latter cannot be diagnosed from the total pace or p95 alone: bursts/stalls
  and the missing frames require the raw timeline.
- Raw capture upload failed because Actions artifact storage quota was exhausted.
  The transcript's **3.3 GB free is filesystem space, not available RAM**. It contains
  no mincore/cgroup/host-memory proof for the warm phase. No causal claim about the
  CI cache or whether each missing frame would have produced STOP can be made.

## Confirmed harness gap and repair

The old warm setup only ran `cat "$warm_db" > /dev/null` before starting the
playback container. Successful reads neither prove that all pages remain cached
nor establish residency after node/recorder startup. The gap is observed directly
in the local diagnostic below, rather than inferred from the word "warm".

`scripts/check_warm_cache.py` reads each database **once**, verifies byte counts and
unchanged file identity, then uses Linux `mincore` to inspect **all** database files
after **all** reads. This catches eviction of an earlier split while reading a later
one. It checks ownership/CAP_FOWNER before trusting mincore's bits; unsupported or
unavailable residency information fails rather than claiming warmth.

With `WARM_CACHE=1`, `scripts/dry_run.sh` invokes that check after node and recorder
startup, immediately before the unchanged rosbag play command (including its
existing 3-second discovery delay). A nonresident page fails the precondition with
a retained error receipt; there is no retry, cache pinning, eviction, CPU-affinity
change or altered resource limit. This is a boundary observation, not a guarantee
against later eviction. The post-play observation runs after the existing drain
delay and does not assert that playback succeeded.

Both receipts record meminfo, CPU affinity, cgroup CPU limits/throttling, memory
limits/events, I/O counters and memory/I/O/CPU pressure where exposed. Player output
is also retained in `player.log`. Warm output directories with prior receipts are
refused before existing captures can be overwritten.

`p1_cold_bag_test.sh` enables the guard for its two warm phases. The cold-cache
procedure, production node/defaults and all acceptance bounds remain unchanged:
positive **201** frames, clear **252**, **zero** post-settle drops, p95 **100 ms**,
minimum pace **0.9x**, rate **1.0**, read-ahead queue **10**, clear alarms **0**, and
positive distance **50:62 m**. The checker, database pins and original bag bytes
are unchanged.

## Exactly one local baseline and one guarded attempt

The declared order was baseline then guarded, one attempt each; both red results
are retained under `local-once/`. No pass-selected rerun was performed.

- Existing volume `rs-s1-original-bags-20261016-72a601b` was inspected before use
  and mounted **read-only**, with `volume-nocopy`; no bag or image was duplicated.
- Both database SHA-256 values match `scripts/cold_bags.sha256`; full hash/size
  receipts are present for each attempt.
- Core/native/ROS source was frozen at the failed CI commit and reinstalled in
  each disposable container on retained tools dependencies. Installed Python
  source equality was asserted, `resense` reports **1.1.0**, and native is enabled.
- The diagnostic host exposes **12 CPUs**, **7,192,399,872 bytes** guest memory,
  unrestricted CPU affinity, and `cpu.max = max 100000`. It is not the Actions host.
  No CPU quota, affinity, node parameter or global cache-drop operation was applied.
- Baseline adds a read-only residency observation at the player boundary to the
  previous cat-before-startup sequence; that instrumentation and local resources
  mean it is diagnostic evidence, not an exact recreation of Actions timing.

| Measurement | Baseline | Guarded |
| --- | --- | --- |
| Bag size | 4,821,250,048 bytes | same |
| Database pages | 1,177,063 | same |
| Missing pages at playback boundary / after read | **192,725 (~752.83 MiB)** | **44,123 (~172.36 MiB)** |
| Full-file read completed | cat completed | **4,821,250,048 bytes**, once |
| Playback attempted | yes | **no: precondition failed** |
| Status frames | **191/201** | none; player never started |
| Decode+detect p95 | **155 ms** | not measured |
| Playback pace | **0.40x** | not measured |
| Strict acceptance | **FAIL** | **NOT RUN / BLOCKED** |

Baseline had ten startup catch-up skips and no post-settle bag-message loss, so it
does **not** reproduce the Actions nine-post-settle-loss timeline. It does reproduce
queue starvation under a falsely assumed warm cache. The guarded read still left
44,123 pages nonresident despite completing; the guard correctly prevented a
second unsupported warm-playback claim. During that read the cgroup records
memory pressure, no OOM events and **zero CPU-throttling periods**. These are local
observations, not proof of the Actions cause or of a particular process evicting
pages. No production-node bug is established by this investigation.

The diagnostic invokes the unchanged acceptance checker even after the guarded
precondition failure; its exit 2/no-status result is retained and is not a playback
failure or a successful runtime test. `runs.json` retains both nonzero attempts.

## Focused red/green validation

`preflight-final/result.json` and `linux-contracts.txt` record:

- **12 contract tests passed, zero skipped** in Linux Docker, including real
  mincore on a small generated file and byte preservation.
- A completed-read/nonresident-pages witness that the previous cat-only check
  accepted is rejected by the new guard; a complete resident fixture passes.
- Partial/growing reads, changed identity, absent metadata/database, unavailable
  mincore, eviction across split files and receipt overwrite all fail appropriately.
- Real Bash guard wiring: invalid fixture exits **1 before player invocation**;
  verified fixture invokes the stub player once with the original rate/clock/delay/
  queue arguments and retains both receipts.
- Both full warm acceptance command lines are compared to the failed CI source;
  they differ only by the new `WARM_CACHE=1` precondition variable.
- Linux Bash syntax and focused **Ruff 0.15.8** checks pass.

`preflight/` retains the initial contracts. The final harness moves the post-play
observer after the existing 3-second drain (avoiding competition with last-frame
processing) and rejects an already-used warm output directory. Neither change
replays the red originals; `local-once/*/executed-inner.sh` records their exact code.

The new harness distinguishes a valid warm trial from incomplete cache setup.
It does not make the CI runtime failure green. A future authoritative run still
needs the original **201/252, zero-drop** checks to pass after verified warm setup.
If setup passes and the same loss remains, that is an unresolved runtime issue
requiring separate diagnosis/acceptance, not a reason to weaken these thresholds.
