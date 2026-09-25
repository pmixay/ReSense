# ReSense VM results, 2026-09-25

Packed by `scripts/vm/run_plan.sh collect` on 2026-09-25T10:39:02+00:00. Machine and commit:

```text
os:        Ubuntu 22.04.5 LTS (id ubuntu 22.04, codename jammy), arch amd64, kernel 5.15.0-191-generic
cpu:       Intel Xeon Processor (Icelake); 8 vCPU, 4 physical cores, 2 thread(s) per core
ram:       15.6 GiB
disk:      / -> /dev/vda1 /: 38.8 GiB free of 96.3 GiB
disk:      /data -> /dev/vda1 /: 38.8 GiB free of 96.3 GiB
disk:      /home/mdm -> /dev/vda1 /: 38.8 GiB free of 96.3 GiB
disk:      /var/lib/docker -> /dev/vda1 /: 38.8 GiB free of 96.3 GiB
commit:    72908737f2f8d1caf2b513f730abd930c8dac20d (claude/nifty-pascal-lzgl78)
worktree:  clean
```

| run | result | copy to the repository | then update |
|---|---|---|---|
| setup | READY. Next (new login first if you just joined the docker group): | `docs/evidence/vm_2026-09-25/` | — |
| fetch | DATA READY (log /home/mdm/resense_results/2026-09-25/fetch/fetch_log.txt) | `docs/evidence/vm_2026-09-25/` | — |
| dryrun | dryrun: FAIL  (2026-09-25T09:35:24+00:00, 546 s, commit 7290873, 8 vCPU) | `docs/evidence/dry_run_2026-09-25/` | SUBMISSION "Dry run"; CAPTAIN C7 (C4 when host_fastdds passed), action 15 |
| bench | bench: FAIL  (2026-09-25T10:38:30+00:00, 430 s, commit 7290873, 8 vCPU) | `docs/evidence/bench_2026-09-25/` | EXPERIMENTS §3 (append the 8-core table); CAPTAIN C8, action 7 |
| gate | gate: PASS  (2026-09-25T09:53:01+00:00, 536 s, commit 7290873, 8 vCPU) | `docs/evidence/gate_2026-09-25/` (JSON, no work dirs) | CAPTAIN action 11 (go / no-go is the human's) |
| export | export: PASS  (2026-09-25T09:53:09+00:00, 550 s, commit 7290873, 8 vCPU) | `docs/evidence/export_2026-09-25/` (archive.txt, .sha256; never the archive) | CAPTAIN actions 14b / 16 and §5 (size, sha256); SUBMISSION "Upload" |
| offline | offline: FAIL  (2026-09-25T09:58:04+00:00, 243 s, commit 7290873, 8 vCPU) | `docs/evidence/offline_2026-09-25/` | CAPTAIN C25 (and action 15 on 28.09); SUBMISSION "Dry run" |
| all | not run | — | — |

## dryrun

```text
dryrun: FAIL  (2026-09-25T09:35:24+00:00, 546 s, commit 7290873, 8 vCPU)
  original_bags                        PASS    exit 0         0 s  
  dry_obstacle                         FAIL    exit 1       217 s  
  dry_clear                            FAIL    exit 1        39 s  
  console_image                        PASS    exit 0        69 s  
  console_stock_dds                    PASS    exit 0        70 s  
  host_fastdds                         PASS    exit 0        75 s  
  host_cyclonedds                      FAIL    exit 1        73 s  
  ride_replay                          SKIPPED exit -         0 s  the 20-minute bag is not kept on this disk (fetch_data.sh --ride keep needs ~90 GB)
  results: /home/mdm/resense_results/2026-09-25/dryrun

## console_image
status messages      : 379 (49 lines skipped)
alarm frames         : 136
obstacle distance    : 55.5 .. 114.9 m
latency decode+detect: mean 46 / p95 67 / max 83 ms
detector stage total : mean 25 / p95 36 ms
dropped input frames : 67 (53 after the first 5 s)
fps (last report)    : 10.05
start of the input   : 37 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +23.8 s
recordings seen      : 2 ['/lidar_points', '/sensing/lidar/hesai128/pointcloud']
PASS: all dry-run criteria met
## console_stock_dds
status messages      : 361 (49 lines skipped)
alarm frames         : 119
obstacle distance    : 55.6 .. 114.9 m
latency decode+detect: mean 46 / p95 64 / max 90 ms
detector stage total : mean 25 / p95 36 ms
dropped input frames : 91 (75 after the first 5 s)
fps (last report)    : 8.14
start of the input   : 35 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +23.9 s
recordings seen      : 2 ['/lidar_points', '/sensing/lidar/hesai128/pointcloud']
PASS: all dry-run criteria met
PASS: a stock Fast DDS player and listener (shared memory on) reached the UDP-only node
## dry_clear
status messages      : 231 (18 lines skipped)
alarm frames         : 3
obstacle distance    : 111.0 .. 114.9 m
latency decode+detect: mean 38 / p95 49 / max 72 ms
detector stage total : mean 24 / p95 34 ms
dropped input frames : 15 (0 after the first 5 s)
fps (last report)    : 10.0
start of the input   : 36 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +23.6 s
FAIL: 3 false alarms on a bag expected to be clear (allowed 2)
## dry_obstacle
status messages      : 142 (25 lines skipped)
alarm frames         : 132
obstacle distance    : 55.7 .. 56.5 m
latency decode+detect: mean 58 / p95 69 / max 98 ms
detector stage total : mean 26 / p95 37 ms
dropped input frames : 54 (20 after the first 5 s)
fps (last report)    : 10.08
start of the input   : 18 frames in the first 5 s after the first one, largest gap 1.0 s, first STOP at +1.6 s
FAIL: 20 dropped input frames after the first 5 s > 0
## host_cyclonedds
decisions seen:  159 CAUTION 89 FAULT 31 GO 3 STOP 
status messages      : 193 (89 lines skipped)
alarm frames         : 3
obstacle distance    : 111.0 .. 114.9 m
latency decode+detect: mean 39 / p95 49 / max 82 ms
detector stage total : mean 24 / p95 35 ms
dropped input frames : 19 (5 after the first 5 s)
fps (last report)    : 0.0
start of the input   : 36 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +20.0 s
recordings seen      : 2 ['/lidar_points', '/sensing/lidar/hesai128/pointcloud']
FAIL: recording 2: 0 alarm frames, expected >= 3
## host_fastdds
decisions seen:  172 CAUTION 52 FAULT 68 GO 137 STOP 
status messages      : 377 (52 lines skipped)
alarm frames         : 137
obstacle distance    : 55.7 .. 114.9 m
latency decode+detect: mean 46 / p95 67 / max 84 ms
detector stage total : mean 25 / p95 36 ms
dropped input frames : 75 (59 after the first 5 s)
fps (last report)    : 9.18
start of the input   : 35 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +23.9 s
recordings seen      : 2 ['/lidar_points', '/sensing/lidar/hesai128/pointcloud']
PASS: all dry-run criteria met
```

## bench

```text
bench: FAIL  (2026-09-25T10:38:30+00:00, 430 s, commit 7290873, 8 vCPU)
  bench_8core                          FAIL    exit 1       428 s  
  note: 8 vCPU = 4 physical cores x 2 threads (the i7-9700E: 8 cores, no hyper-threading)
  note: cpu steal before the runs: 0.0 % (shared vCPUs make timing noisy above ~5 %)
  results: /home/mdm/resense_results/2026-09-25/bench

## bench_8core
status messages      : 146 (23 lines skipped)
alarm frames         : 139
obstacle distance    : 55.6 .. 56.6 m
latency decode+detect: mean 58 / p95 70 / max 171 ms
detector stage total : mean 27 / p95 38 ms
dropped input frames : 53 (20 after the first 5 s)
fps (last report)    : 10.0
start of the input   : 18 frames in the first 5 s after the first one, largest gap 0.7 s, first STOP at +1.0 s
FAIL: 20 dropped input frames after the first 5 s > 0
status messages      : 233 (13 lines skipped)
alarm frames         : 4
obstacle distance    : 53.0 .. 114.9 m
latency decode+detect: mean 38 / p95 48 / max 57 ms
detector stage total : mean 24 / p95 34 ms
dropped input frames : 14 (0 after the first 5 s)
fps (last report)    : 10.03
start of the input   : 37 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +15.4 s
FAIL: 4 false alarms on a bag expected to be clear (allowed 2)
status messages      : 116 (21 lines skipped)
alarm frames         : 108
obstacle distance    : 55.6 .. 56.6 m
latency decode+detect: mean 104 / p95 118 / max 154 ms
detector stage total : mean 65 / p95 78 ms
dropped input frames : 76 (45 after the first 5 s)
fps (last report)    : 8.44
start of the input   : 21 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +0.5 s
FAIL: p95 latency 118 ms > 100 ms
FAIL: 45 dropped input frames after the first 5 s > 0
status messages      : 231 (15 lines skipped)
alarm frames         : 3
obstacle distance    : 111.0 .. 114.9 m
latency decode+detect: mean 65 / p95 77 / max 81 ms
detector stage total : mean 48 / p95 59 ms
dropped input frames : 17 (0 after the first 5 s)
fps (last report)    : 9.85
start of the input   : 34 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +23.7 s
FAIL: 3 false alarms on a bag expected to be clear (allowed 2)
status messages      : 378 (49 lines skipped)
alarm frames         : 139
obstacle distance    : 53.0 .. 114.9 m
```

## gate

```text
gate: PASS  (2026-09-25T09:53:01+00:00, 536 s, commit 7290873, 8 vCPU)
  gate_native                          PASS    exit 0       536 s  
  note: ride cached (221 split files): the gate covers all 13 759 real frames
  note: regression_gate.py exit codes: 0 identical or better, 1 a gated metric worse, 2 missing data / failed set F
  results: /home/mdm/resense_results/2026-09-25/gate

## gate_native
doubleT_obstacle                          201    188      2      3     84   11
doubleT_platform                          345      4      4      1    180   34
roundT_doubleT                            252      2      1      1    173  233
roundT_pressureGate_roundT                268      0      0      0    104    -
roundT_squareT_pressureGate_squareT       545      0      0      0    146    -
squareT_platform_squareT_switch           877    101     15     25    394  312
note: ride (set E): this run only; not compared
note: set F straight: this run only; not compared
GATE PASS: no gated metric worse (0 gated better, 0 worse but allowed, 14 information rows changed)
```

## export

```text
export: PASS  (2026-09-25T09:53:09+00:00, 550 s, commit 7290873, 8 vCPU)
  export_image                         PASS    exit 0       532 s  
  load_check                           PASS    exit 0        18 s  
  note: no --ref: exported from the checkout at 7290873 as 0.6.3-7290873 (the upload uses --ref v1.0-rc1 / v1.0-final)
  results: /home/mdm/resense_results/2026-09-25/export

## export_image
   archive: 475489127 bytes (0.44 GiB)
   image:   2075079161 bytes uncompressed (1.93 GiB)
   sha256:  98be33db23417a88fcb001d0bc7515f151d9e9e41957e163953f63794510ed84
   tags:    resense:0.6.3-7290873 resense:latest ros:humble-ros-base-jammy
   commit:  72908737f2f8d1caf2b513f730abd930c8dac20d
## load_check
PASS: resense:latest loaded from resense-image-0.6.3-7290873.tar.gz and runs without network. Next:
```

## offline

```text
offline: FAIL  (2026-09-25T09:58:04+00:00, 243 s, commit 7290873, 8 vCPU)
  apply_block                          PASS    exit 0         0 s  outbound blocked until 10:24:01 at the latest
  verify_blocked                       PASS    exit 0       100 s  
  remove_images                        PASS    exit 0         1 s  
  load_image                           PASS    exit 0        29 s  
  dry_obstacle                         FAIL    exit 1        34 s  
  dry_clear                            FAIL    exit 1        38 s  
  jury_console                         PASS    exit 0        40 s  
  note: image archive: /home/mdm/resense_dist/resense-image-0.6.3-7290873.tar.gz
  note: outbound attempts blocked and logged (rate-limited; they include the deliberate ones of check_no_network.py): 54, by uid:  7 UID=1000 47 UID=101 
  results: /home/mdm/resense_results/2026-09-25/offline

## dry_clear
status messages      : 234 (18 lines skipped)
alarm frames         : 3
obstacle distance    : 111.0 .. 114.9 m
latency decode+detect: mean 38 / p95 48 / max 50 ms
detector stage total : mean 24 / p95 34 ms
dropped input frames : 14 (0 after the first 5 s)
fps (last report)    : 10.0
start of the input   : 37 frames in the first 5 s after the first one, largest gap 0.3 s, first STOP at +23.8 s
FAIL: 3 false alarms on a bag expected to be clear (allowed 2)
## dry_obstacle
status messages      : 147 (24 lines skipped)
alarm frames         : 137
obstacle distance    : 55.6 .. 56.5 m
latency decode+detect: mean 58 / p95 78 / max 114 ms
detector stage total : mean 27 / p95 42 ms
dropped input frames : 53 (22 after the first 5 s)
fps (last report)    : 10.0
start of the input   : 20 frames in the first 5 s after the first one, largest gap 0.7 s, first STOP at +1.2 s
FAIL: 22 dropped input frames after the first 5 s > 0
## jury_console
decisions seen:  2 CAUTION 35 FAULT 10 GO 134 STOP 
status messages      : 146 (35 lines skipped)
alarm frames         : 134
obstacle distance    : 55.7 .. 56.5 m
latency decode+detect: mean 60 / p95 71 / max 103 ms
detector stage total : mean 27 / p95 38 ms
dropped input frames : 57 (24 after the first 5 s)
fps (last report)    : 10.0
start of the input   : 17 frames in the first 5 s after the first one, largest gap 0.7 s, first STOP at +2.3 s
PASS: all dry-run criteria met
## load_image
PASS: resense:latest loaded from resense-image-0.6.3-7290873.tar.gz and runs without network. Next:
```

## Before committing

* No personal data: names, e-mails, tokens, keys, IP addresses of team members. Files that look
  suspicious (automatic scan):
  * none found
* The VM hostname `compute-vm-8-16-100-ssd-1790323951159` is recorded (uname, docker info): fine unless it is a person's name.
* `.gitignore` hides `*.log` and `*.jsonl`: `collect --to-repo` renames and gzips them.
