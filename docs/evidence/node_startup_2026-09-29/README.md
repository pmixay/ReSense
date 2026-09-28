# Node start-up, 29.09: root causes, the change, A/B through the jury chain

> **Purpose:** why the node's first results after `ros2 bag play` were late, what was changed in
> the node (not the sealed detector) and the measured effect, with the raw captures.
> **Audience:** team, jury · **Owner:** P1 · **Language:** EN · **Status:** dated record, 2026-09-29

## Root causes (measured on the captures of the 28.09 judgement)

1. **The player's start-up burst.** Even with `--read-ahead-queue-size 10`, `ros2 bag play` sends
   the first ~0.7 s of a 360° recording nearly back to back (frames 1–7 within 0.29 s of each
   other); with Humble's default read-ahead it sends the whole overdue recording.
2. **Every frame of the first backlog was processed.** The node took every input-period frame of a
   recording's first backlog (so a cold-disk burst would not reset the scene). At ~70–90 ms of work
   per 360° frame against a 100 ms period it gained only ~20–30 ms per frame: the results of the
   first ~2 s were 0.4–0.7 s old (e2e p95 over all frames 0.4–1.1 s at 360°), then current.
3. **A cold first frame.** The first frame cost 49 ms decode + 72 ms detect (imports, first
   allocations) instead of ~25 + 40 ms.
4. **The decode itself.** `pointcloud2_to_arrays` read x / y / z of the 921 600-slot, 26-byte-point
   360° cloud through three unaligned strided views and boolean-indexed each field: 20–23 ms median.

## The change (node only; `scripts/detector_freeze.py verify` PASS)

* `resense_ros/fastcloud.decode`: one 12-byte-per-point copy of x / y / z, the same float32 range
  arithmetic, one index gather: **byte for byte the arrays of `pointcloud2_to_arrays`** on all 453
  frames of both original recordings; 360° 20.3 → 16.6 ms median (p95 29.2 → 23.7), 120°
  7.4 → 4.8 ms (4-vCPU sandbox). Other layouts use the reference decode.
* **Start-up catch-up at 5 Hz** (`catchup_startup_step`, 0.2 s): a recording's first backlog is
  chained 0.2 s of recording apart — every other 10 Hz frame, the rate the detector is validated
  on (EXPERIMENTS log §1g) — short backlogs included; a frame waiting alone is processed at once;
  0 restores the every-frame chain. The 20 s start-up lag allowance and the scene-reset guard are
  unchanged.
* **Warm-up** (`warmup`, true): before logging "listening" the node runs the decode and a
  throwaway detector on three synthetic 360°-sized frames: 0.61–0.76 s at node start; the first
  real frame then costs ~31 + 42 ms. The node's own detector is untouched.
* Ctrl+C: `rclpy.try_shutdown()` (VM run of 28.09, finding 4). Checked with SIGINT to the node's
  container: the old image logs `RCLError: rcl_shutdown already called` and launch's "process has
  died … exit code 1"; the new image exits with neither.
* `scripts/check_dry_run.py` also prints the end-to-end latency over all results (start-up
  included) and the playback pace, with an optional `--min-playback-rate` (VM finding 2).

## A/B through the jury chain

`resense:base464` (the image of `main` 464f5bc) against the image with the change, run alternately
on one idle 4-vCPU sandbox: node with the image's default command, player as uid 1000 from the
same image (`--delay 3 --read-ahead-queue-size 10`, or none of it for "default player"), the
judge's listener (it also subscribes to the clouds, which adds load: absolute latencies here are
higher than without it). e2e = the listener receives a cloud → receives the status of that cloud.
Round 1 had the change without chaining short backlogs; round 2 is the final code.
[`summary_round2.json`](summary_round2.json), [`summary_round1.json`](summary_round1.json), raw
captures in [`raw/`](raw), scripts in [`scripts/`](scripts).

| condition (round 2) | runs | e2e median, first 3 s | e2e p95, all results | first STOP after the first cloud |
|---|---:|---|---|---|
| 360° `doubleT_obstacle`, bag in page cache | 3 + 3 | 312–325 → **38–105 ms** | 410–447 → **212–344 ms** | 0.90–0.99 → 0.79–0.98 s |
| 360°, page cache dropped | 2 + 2 | 829–1029 → **120–300 ms** | 864–1084 → **333–599 ms** | 1.16–1.35 → 0.81–1.16 s |
| 120° `roundT_doubleT` (clear), warm / cold | 2 + 2 | 37–42 → 29–32 ms (p95 295–340 → 66–123 ms) | 52–60 → 48 ms | no STOP in either |
| 360°, default player (read-ahead 1000) | 1 + 1 | 7.0 → 4.3 s (all stale) | — | 7.5 → 2.3 s; 57 → 145 of 201 frames processed |

Unchanged: the decisions after the start-up (STOP 55.5–56.6 m from frame 8, the GO at frame 111
and the CAUTION frames of the sealed detector), the steady-state cost (decode + detect p95 79–86 ms
here) and the current-result e2e p95 (~95–105 ms here with the extra listener; 81–82 ms on the team
VM without it). With Humble's default read-ahead the results are still stale for the whole 20 s
recording (the player itself sends the overdue recording): keep `--read-ahead-queue-size 10`.
