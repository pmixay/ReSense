# Acceptance test (dry run)

`scripts/dry_run.sh` is the end-to-end check of the jury path on a real bag: it builds (or loads)
the image, starts the node, waits until it advertises `/resense/status`, plays the bag with the
supported settings, captures the status stream and asserts the result with
`scripts/check_dry_run.py`. Exit code 0 = pass, 1 = a criterion failed, 3 = no Docker or the node
did not start.

## The two standard runs

```bash
./scripts/dry_run.sh <bags>/doubleT_obstacle                  # builds --no-cache; the person must be reported 50–62 m ahead
SKIP_BUILD=1 ./scripts/dry_run.sh <bags>/roundT_doubleT --expect-clear --max-alarm-frames 2
```

With no extra arguments the `doubleT_obstacle` criteria apply: the obstacle at 50–62 m, p95 of
decode + detect ≤ 100 ms, and no frame of the recording left unprocessed after the start-up
catch-up. Arguments after the bag are passed to the checker, so the thresholds live in one place
(`python3 scripts/check_dry_run.py --help`). The checker also prints the end-to-end latency of the
current results (from the player's publication through DDS, the node's queue, decode and detection
to the result) and the node's CPU use and peak memory; `--max-p95-e2e <ms>` makes the end-to-end
p95 a criterion.

The raw capture stays in `out/dry_run/` (`status.jsonl`, `node.log`); `status.jsonl` replays in the
[web dashboard](../visualisation/web-dashboard.md).

## Options (environment)

| variable | meaning |
|---|---|
| `SKIP_BUILD=1` | reuse `$IMAGE` (default `resense:latest`) instead of rebuilding |
| `IMAGE_TAR=<archive>` | load the image from an archive instead of building |
| `OFFLINE=1` | node, player and recorder with `--network none`; needs `IMAGE_TAR` or `SKIP_BUILD=1` |
| `RATE=1.0` | playback rate |
| `BAG_READ_AHEAD_QUEUE_SIZE=10` | the player's read-ahead; change only for a separately tested setup |
| `OUT=out/dry_run` | where the capture goes |
| `DOCKER_ARGS=""` | extra `docker run` arguments, e.g. `-e RESENSE_NATIVE=0` for the numpy path |

## Why "after the start-up"

`ros2 bag play` preloads the bag with its clock already running and then sends the overdue first
seconds back to back. The node works through that burst one frame per `catchup_step` (0.3 s) of
recording and skips the frames in between on purpose (`node.catchup_skipped` in the status). Drops
are therefore counted from the later of 5 s and the end of that catch-up (at most 15 s), and with
`--bag` (which `dry_run.sh` passes) against the recording's own messages, so frames the recording
itself lacks are not counted as drops.

## The organizers' console

A player run by a normal user with the stock ROS 2 Humble middleware, as on a jury console:

```bash
PLAYER_DDS=stock ./scripts/console_test.sh <bags>/roundT_doubleT <bags>/doubleT_obstacle -- \
  --expect-obstacle --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
```

## On an 8-core stand-in

`scripts/bench_8core.sh <bags>/doubleT_obstacle <bags>/roundT_doubleT` bundles the build, the dry
runs on the native and numpy paths, the console tests, `docker stats` and offline timing into
`docs/evidence/bench_<date>/`.

## What CI runs instead

The dataset is not in CI. On every push CI plays 40-frame synthetic bags in the organizers' exact
message layout (a clear run, then a person at 60 m; both topic / frame pairs) through the image,
with a uid-1000 player from another container and with a stock Fast DDS player, and plays them
through the runtime image loaded from its archive on an internal network with no way out. Pushes
to `main` also replay the two original bags, restored from a checksum-verified Actions cache, from
a cold disk. See
[Setup, tests and CI](../development/setup-and-ci.md).
