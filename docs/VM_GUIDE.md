# VM Guide

> **Purpose:** how a person or an agent on the team's temporary cloud VM prepares it, fetches the
> organizers' data and runs the checks that need a real machine (dry run with the original bags,
> host consoles, bench, regression gate with the ride, image archive, offline rehearsal), and how
> the results come back as evidence in a PR. Instructions only: plain commands of the repository's
> own tools, parameterised by shell variables you set.
> **Audience:** team (a person or an agent on the VM) · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-29: the procedure against the full VM run of 28.09
> ([`evidence/vm_2026-09-28/summary.md`](evidence/vm_2026-09-28/summary.md)), the node's start-up,
> warm-up and shutdown against the launch file and the node, the image's default command against
> `docker/Dockerfile`; 29.09 evening: §4.4's baseline selection against `main` `7532a6b` (it picks
> `regression_baseline_2026-09-29_competitor_rules.json`) · **Status:** current

## 0. What the VM is for

The organizers' stand (i7-9700E, 8 cores, Ubuntu 22.04, ROS 2 Humble, Docker) has **no
internet**, and the team gets **no access** to it before the upload
([`organizers/answers.md`](organizers/answers.md) §6–§7). A cloud VM stands in for it: §1–§3
prepare it, §4.0 lists every run with its evidence and what PASS looks like. **What is tested** is
the commit the captain names. A failing criterion is a **finding to report** with its numbers, not
something to fix on the VM: no code, config or test changes there, and no step here creates or
pushes a tag. The latest complete run: [`evidence/vm_2026-09-28/summary.md`](evidence/vm_2026-09-28/summary.md).

## 1. Prerequisites

**The VM.** Ubuntu **22.04** (Humble's packages exist for 22.04 only; elsewhere everything but the
host consoles runs), 16 GB RAM or more, disk as in §2. A vCPU is usually one hyper-thread
(`lscpu`: `Core(s) per socket` × `Socket(s)`); the stand has 8 physical cores, and the native path
met every timing criterion on 4 ([`evidence/bench_2026-09-28/`](evidence/bench_2026-09-28/summary.txt)).
**Disk speed:** the 360° recording is 4.5 GB for 20 s, ~225 MB/s at rate 1.0; on a slower disk
(the team VM's network disk read 79 MB/s) the player falls behind real time and stalls, so the
timed runs read the bags from the page cache or a RAM tmpfs (§3). Turn on the provider's **serial
console** (the way in if SSH breaks, §5) and work inside `tmux`.

**Variables**, set in each new shell (or in a file you `source`):

```bash
REPO_URL='<clone URL of the repository>'; BRANCH='<branch or commit named by the captain>'
REPO=$HOME/ReSense                  # the clone
DATA=/data                          # bags and caches; mount a data disk here if there is one
BAGS=$DATA/for_hackathon            # the six recordings (the scripts' default)
CACHE=$DATA/cache                   # frame caches, read by eval_real.py / regression_gate.py
EV=$REPO/docs/evidence; DAY=$(date +%F)   # evidence folders <run>_<date>
```

**Packages and Docker.** `sudo apt-get update && sudo apt-get install -y git curl zstd tmux
build-essential python3-venv python3-pip`; `sudo mkdir -p "$DATA" && sudo chown "$(id -u):$(id -g)"
"$DATA"`. Docker Engine as [Docker's instructions for Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
describe, with the [post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/)
(the `docker` group); done when `docker run --rm hello-world` works as your user.

**ROS 2 Humble on the host**, only for the host consoles (§4.2, §4.6): the
[Debian packages](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html), **naming
the RMWs**: `sudo apt-get install -y ros-humble-ros-base ros-humble-rmw-fastrtps-cpp
ros-humble-rmw-cyclonedds-cpp` (with only the CycloneDDS one, a player with `RMW_IMPLEMENTATION`
unset runs CycloneDDS, not Humble's default Fast DDS). What a player loads: `ros2 topic echo /x
std_msgs/msg/String & sleep 4; grep -oE 'librmw_[a-z]+_cpp\.so' /proc/$!/maps | sort -u`.

**The clone and the Python environment** (GitHub credentials stay on the VM, never in a commit):

```bash
git clone "$REPO_URL" "$REPO" && cd "$REPO" && git checkout "$BRANCH"
python3 -m venv .venv && . .venv/bin/activate    # activate it in every new shell
pip install -U pip && pip install -e ".[dev]"    # the package, rosbags / zstandard for the data, the C++ kernels
pip install "rosbags==0.11.5"                   # §2.3 reads single .db3 split files: needs rosbags >= 0.11.0
scripts/build_native.sh                          # rebuild the kernels and print their status (after every checkout)
python -m pytest -q                              # optional: needs no data
git rev-parse HEAD                               # the commit every result is recorded against
```

**An agent** (for example a Claude Code session) is started by a person in `$REPO` with this guide
as its task and the variables set; §5 cuts its own connection unless its API host is allowed.

## 2. Data

About **50 GB free** holds everything but the ride's bag (peak while unpacking): `Датасет.zip`
3.7 GB (deleted after unpacking); the two dry-run bags `doubleT_obstacle` + `roundT_doubleT`
6.4 GB (keep), the other four 15.3 GB (unpack, cache, delete one at a time); the six caches 3.8 GB;
set O 1.75 GB download → 7.4 GB bag → 2.2 GB cache; the ride 17.1 GB download → 16.5 GB cache (its
90 GB bag only for a 20-minute replay); Docker about 10 GB on the disk of `/var/lib/docker`. Links,
formats and checksums: [`DATASET.md`](DATASET.md). All commands run in `$REPO` with the venv active.

### 2.1 The six recordings

```bash
curl -fL -o "$DATA/dataset.zip" \
  "https://drive.usercontent.google.com/download?id=1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu&export=download&confirm=t"
head -c 2 "$DATA/dataset.zip"; echo    # PK: a zip; anything else: Google sent a page (download it in a browser, scp it)
python scripts/unpack_dataset.py "$DATA/dataset.zip" --out "$DATA" --only doubleT_obstacle,roundT_doubleT
for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT \
         roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
  [ -d "$BAGS/$b" ] || python scripts/unpack_dataset.py "$DATA/dataset.zip" --out "$DATA" --only "$b"
  python scripts/cache_frames.py "$BAGS/$b" "$CACHE/$b" --every 1 --int16 --stamps
  case "$b" in doubleT_obstacle|roundT_doubleT) ;; *) rm -rf "${BAGS:?}/$b" ;; esac   # keep the dry-run pair only
done
chmod -R a+rX "$BAGS"; rm "$DATA/dataset.zip"   # the console tests play as uid 1000
```

Each `unpack_dataset.py` call streams the whole archive (a few minutes) and writes only the bags
asked for; with 22 GB to spare, unpack all six at once (no `--only`) and drop the `rm -rf` line.

### 2.2 `cloud_with_fake_obj` (set O)

```bash
python scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out "$DATA"   # streamed, -> $DATA/cloud_with_fake_obj
python scripts/cache_frames.py "$DATA/cloud_with_fake_obj" "$CACHE/cloud_with_fake_obj" --every 1 --int16 --stamps
rm -rf "${DATA:?}/cloud_with_fake_obj"   # optional: the gate reads only the cache
```

### 2.3 The 20-minute ride, split by split

`new_data.zst` is a zstd-compressed tar of one bag: 221 split files `new_data_<N>.db3` of 408 MB.
`curl` streams it, `zstd` unpacks it on the fly, and `tar --to-command` hands each split file to a
command that spools, caches and deletes it, so at most one is on disk. A split file whose
`_stamps.json` (written last) is in the cache is read past, so running the lines again resumes
after a break (20–40 min in all; `python -m pip show rosbags` must say 0.11.5).

```bash
cd "$REPO"; SPOOL=$DATA/.ride_spool; mkdir -p "$CACHE/new_data" "$SPOOL"
export CACHE SPOOL                      # tar's command runs in a child shell
HREF=$(curl -fsS --get \
  --data-urlencode "public_key=https://disk.yandex.ru/d/N8IUpAyd7jyvow" \
  --data-urlencode "path=/new_data.zst" \
  https://cloud-api.yandex.net/v1/disk/public/resources/download \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["href"])')   # Yandex Disk public API, no account
curl -fsSL "$HREF" | zstd -dc | tar -x --wildcards '*.db3' --to-command='
  f="$SPOOL/$(basename "$TAR_FILENAME")"; name=$(basename "$f" .db3)
  if [ -f "$CACHE/new_data/${name}_stamps.json" ]; then cat > /dev/null; exit 0; fi
  cat > "$f" && python scripts/cache_frames.py "$f" "$CACHE/new_data" --every 1 --int16 --stamps
  rc=$?; rm -f "$f"; exit $rc'
ls "$CACHE"/new_data/*_stamps.json | wc -l   # 221 when complete; fewer (tar exits 2): run the lines again
```

The whole bag instead (90 GB): `python scripts/unpack_dataset.py https://disk.yandex.ru/d/N8IUpAyd7jyvow
--member new_data.zst --out "$DATA"`, then `cache_frames.py` on each `"$DATA"/new_data/new_data_*.db3`.

### 2.4 Check

```bash
for d in "$CACHE"/*/; do printf '%-40s %6d frames\n' "$(basename "$d")" "$(find "$d" -name '*.npy' | wc -l)"; done
for b in doubleT_obstacle roundT_doubleT; do cmp "$BAGS/$b/metadata.yaml" "docs/evidence/bag_metadata/${b}_metadata.yaml" && echo "$b original"; done
```

Done when the counts are `doubleT_obstacle` 201, `doubleT_platform` 345, `roundT_doubleT` 252,
`roundT_pressureGate_roundT` 268, `roundT_squareT_pressureGate_squareT` 545,
`squareT_platform_squareT_switch` 877, `cloud_with_fake_obj` 1 510, `new_data` 11 271, and both
dry-run bags print `original`.

## 3. Before the runs

* `git status --short --untracked-files=no` is empty, `git rev-parse --short HEAD` is the named
  commit, `scripts/build_native.sh` was run on it; the VM is otherwise idle for the timed runs.
* The machine facts, once per day (`st` in `vmstat` is CPU steal; the `dd` line the disk's speed):

  ```bash
  mkdir -p "$EV/vm_$DAY"
  { lscpu; free -h; df -h "$DATA" /var/lib/docker; uname -a; docker version; vmstat 1 5; git -C "$REPO" rev-parse HEAD
    sysctl net.core.rmem_max net.core.rmem_default
    dd if="$(ls "$BAGS"/doubleT_obstacle/*.db3 | head -n 1)" of=/dev/null bs=4M count=512 iflag=direct 2>&1 | tail -n 1
  } > "$EV/vm_$DAY/machine.txt" 2>&1
  ```

* **Below ~250 MB/s**, read the bags into the page cache right before every timed run (§4.1–§4.3,
  §5): `cat "$BAGS"/doubleT_obstacle/*.db3 "$BAGS"/roundT_doubleT/*.db3 > /dev/null` (6.4 GB of
  free RAM; a build, the gate or an image load pushes them out again). Or copy them once to a RAM
  tmpfs: `sudo mkdir -p /mnt/ramdata && sudo mount -t tmpfs -o size=7g tmpfs /mnt/ramdata && cp -a
  "$BAGS"/doubleT_obstacle "$BAGS"/roundT_doubleT /mnt/ramdata/ && BAGS=/mnt/ramdata`.

The exit code of a command piped into `tee` is `${PIPESTATUS[0]}`, printed after each run.

## 4. The runs

On a fresh VM the dry run's `--no-cache` build (§4.1) is the first build, so that it is the clean
machine. Evidence goes to `docs/evidence/<run>_<date>/`; §6 turns it into a PR.

### 4.0 Checklist

| run (tool) | evidence | PASS |
|---|---|---|
| §4.1 dry run, both original bags (`scripts/dry_run.sh`) | `dry_run_<date>/dry_*.txt` | both exit 0; replay alarm list = the node's; each recording plays in about its own length |
| §4.1 cold start (the same, page cache dropped) | `dry_run_<date>/cold_*.txt` | both exit 0 (meaningful on a fast disk only) |
| §4.2 stock player in Docker (`PLAYER_DDS=stock scripts/console_test.sh`), host console (`ros2 bag play`) | `dry_run_<date>/ct_stock.txt`, `host_console*.txt` | exit 0 / check passes, `STOP` on the obstacle recording |
| §4.3 bench (`scripts/bench_8core.sh`) | `bench_<date>/summary.txt` | `dry_obstacle_native` PASS |
| §4.4 gate with the ride and set F (`scripts/regression_gate.py`) | `gate_<date>/` | exit 0, every gated metric identical or better |
| §4.5 archive (`scripts/export_image.sh`, `scripts/load_image.sh`) | `export_<date>/archive.txt` | both exit 0 |
| §4.6 shm mode, optional (`-e RESENSE_DDS=shm`) | `dry_run_<date>/host_console_shm*.txt` | check passes at `rmem_max` 212992 |
| §5 offline (`IMAGE_TAR=… OFFLINE=1 scripts/dry_run.sh`, outbound blocked) | `offline_<date>/` | block verified; both dry runs exit 0; host console `STOP` |

### 4.1 Dry run with the original bags

```bash
mkdir -p "$EV/dry_run_$DAY"
OUT=out/dry_obstacle ./scripts/dry_run.sh "$BAGS/doubleT_obstacle" 2>&1 | tee "$EV/dry_run_$DAY/dry_obstacle.txt"
echo "exit ${PIPESTATUS[0]}"
cat "$BAGS"/doubleT_obstacle/*.db3 "$BAGS"/roundT_doubleT/*.db3 > /dev/null   # §3
SKIP_BUILD=1 OUT=out/dry_clear ./scripts/dry_run.sh "$BAGS/roundT_doubleT" --expect-clear --max-alarm-frames 2 \
  2>&1 | tee "$EV/dry_run_$DAY/dry_clear.txt"
echo "exit ${PIPESTATUS[0]}"
python scripts/replay_node_frames.py out/dry_clear/status.jsonl --bag "$BAGS/roundT_doubleT" | tee "$EV/dry_run_$DAY/dry_clear_replay.txt"
```

The first command builds the image `--no-cache` (about 10 min on 4 cores), plays the bag through
the node with `--read-ahead-queue-size 10` (the supported setting; Humble's default of 1 000 sends
the overdue recording in a burst and the results go stale) and checks `/resense/status` with
`scripts/check_dry_run.py --require-freshness --bag`; on a slow disk repeat it with `SKIP_BUILD=1`
after the pre-read. **Done:** both exit 0: the obstacle at 50–62 m in ≥ 3 frames; decode + detect
p95 ≤ 100 ms; no message of the recording unprocessed after the settle point (the later of 5 s
and the end of the start-up catch-up, at most 15 s; the 4 frames missing from `doubleT_obstacle`
itself are not drops); a current result for each recording; on `roundT_doubleT` at most 2 alarm
frames; equal alarm lists from the replay line. The checker also prints the end-to-end latency of
the current results (`--max-p95-e2e <ms>` asserts it) and the node's CPU.

**The playback speed:** the checker passes a player that fell behind real time, since every
message is eventually processed. The wall time the node's results span:

```bash
python3 -c 'import json, sys
t = [s["freshness"]["evaluated_at_utc_s"] for s in map(json.loads, filter(lambda l: l.startswith("{"), open(sys.argv[1])))
     if (s.get("freshness") or {}).get("source_age_s") is not None]
print(len(t), "frame results in", round(max(t) - min(t), 1), "s of wall time")' out/dry_obstacle/status.jsonl
```

About the recording's length is right (`doubleT_obstacle` 20.4 s, `roundT_doubleT` 25.1 s); three
times that means the disk set the pace: pre-read the bags (§3) and run again.

**The node's start-up.** It logs `ReSense detector listening on …` after a warm-up (`warmup`, on by
default: the decode and a throwaway detector on three synthetic frames, ~0.7 s), so the first real
frame costs what the next ones do. A new recording's first backlog (the player's start-up burst)
is worked through every observed input-period frame by default
(`catchup_startup_step` = 0), within `catchup_startup_max_lag` 20 s. Explicit
`catchup_startup_step:=0.2` enables the 5 Hz thinning that was the default until PR #27 was merged
(29.09); its target coverage still needs separate acceptance. A frame waiting alone is processed at once; later stalls use
`catchup_step` 0.3 s and `catchup_max_lag` 5 s. Results made while it catches up are not
current (`node.catchup`): FAULT, CAUTION or a held STOP, never GO. A storage stall of a second or
more mid-recording makes the catch-up skip frames after the settle point and fails the check.

**Cold start** (a separate result; CI runs it on every push to `main`, `scripts/p1_cold_bag_test.sh`):
the two dry-run commands with `SKIP_BUILD=1`, `OUT=out/cold_*` and output into `cold_*.txt`, each
right after `sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'`; on a disk below ~250 MB/s it
measures the disk. A latency or drop failure is a result to record with the core count.

### 4.2 The organizers' console: stock-DDS player, host console

In Docker, a uid-1000 player with Humble's stock Fast DDS (shared memory + UDP, no XML profile) and
a stock listener, both recordings into one node (its header lists the assertions):

```bash
PLAYER_DDS=stock OUT=out/ct_stock ./scripts/console_test.sh "$BAGS/roundT_doubleT" "$BAGS/doubleT_obstacle" -- \
  --expect-obstacle --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000 \
  2>&1 | tee "$EV/dry_run_$DAY/ct_stock.txt"; echo "exit ${PIPESTATUS[0]}"
```

With ROS 2 on the host, the same by hand as the jury does it (README «Кратко для жюри»), as a
normal user with stock settings, the bags pre-read (§3). Console 1, the node on the image's default
command (`freshness_mode:=replay`):

```bash
docker run --rm --name resense_node --net=host --ipc=host resense:latest 2>&1 | tee "$EV/dry_run_$DAY/host_console_node_log.txt"
```

```bash
# console 2: the player, stock RMW, no Fast DDS profile; in a console 3 meanwhile:
#   source /opt/ros/humble/setup.bash && ros2 topic echo /resense/decision --field data   # GO | CAUTION | STOP | FAULT
source /opt/ros/humble/setup.bash
unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML RMW_IMPLEMENTATION
mkdir -p out/host_console
ros2 topic echo /resense/status --field data > out/host_console/status.jsonl & ECHO=$!
sleep 4
ros2 bag play "$BAGS/roundT_doubleT" --delay 3 --read-ahead-queue-size 10 --disable-keyboard-controls && sleep 5 &&
  ros2 bag play "$BAGS/doubleT_obstacle" --delay 3 --read-ahead-queue-size 10 --disable-keyboard-controls
sleep 3; kill "$ECHO"
python3 scripts/check_dry_run.py out/host_console/status.jsonl --require-freshness --expect-obstacle --obstacle-in 2 --expect-inputs 2 \
  --min-frames 20 --max-p95-latency 1000 --max-dropped 100000 | tee "$EV/dry_run_$DAY/host_console.txt"
```

**Done:** the check passes (453 of 453 frames) and console 3 shows `STOP` during the obstacle
recording. Stop the node with Ctrl+C in console 1: it exits cleanly (no traceback, no `process
has died`). A stock Fast DDS player delivers every 360° cloud at Ubuntu's `rmem_max` 212992.
Optional: consoles 2 and 3 with `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` (into
`host_console_cyclonedds.txt`); a CycloneDDS player needs `sudo sysctl -w net.core.rmem_max=33554432`
(README jury step 0; `…=212992` afterwards), and the node logs a WARN below 32 MiB.
`scripts/play_bag.sh <bag>` does README steps 0–5 in one command with Docker only.

### 4.3 Bench

```bash
cat "$BAGS"/doubleT_obstacle/*.db3 "$BAGS"/roundT_doubleT/*.db3 > /dev/null   # §3
RESENSE_DATA="$BAGS" RESENSE_CACHE="$CACHE" ./scripts/bench_8core.sh; echo "exit $?"
```

Builds the image (timed), runs `dry_run.sh` on both bags with the native and the numpy kernels,
`console_test.sh` with the image's and the stock player, samples `docker stats`, times the detector
on the host with peak RSS and summarises (10–25 min; its header has the details) into
`docs/evidence/bench_<date>/`, ready to commit. **Done:** `summary.txt` shows `dry_obstacle_native`
PASS (p95 ≤ 100 ms, no drop after the settle point); write down the physical core count. The numpy
fallback is not real time at 360° on 4 physical cores, so there the script exits 1 on
`dry_obstacle_numpy` (known; the image ships the native kernels).

### 4.4 Regression gate with the ride

```bash
BASELINE=$(python3 -c "import glob, json; print(max((json.load(open(p))['created'], p) for p in glob.glob('docs/evidence/results/regression_baseline_*.json') if json.load(open(p)).get('ride', {}).get('available'))[1])")
echo "$BASELINE"      # the newest baseline with the ride: regression_baseline_2026-09-29_competitor_rules.json for the sealed detector (1e2ed82)
mkdir -p "$EV/gate_$DAY"
python scripts/regression_gate.py --cache "$CACHE" --jobs 4 --baseline "$BASELINE" \
  --out "$EV/gate_$DAY/gate_$(git rev-parse --short HEAD).json" 2>&1 | tee "$EV/gate_$DAY/gate_table.txt"
echo "exit ${PIPESTATUS[0]}"
```

Every frame of the six recordings, set O, the ride (8 pieces) and set F straight against the
baseline; `--jobs` about the physical core count (about 7 min at 4); no Docker. **Done:** exit 0,
every gated metric identical or better (on the sealed detector identical but the informational
latency rows). Exit 1: a gated metric is worse (report the rows) or missing (the ride and set F
need `$CACHE/new_data`; a run without them passes only with `--allow 'ride.*' --allow
'set_F_straight.*'`, said in the report); 2: a cache is missing or incomplete (§2.4). A candidate
branch runs in its own `git worktree add ../candidate <branch>` after `scripts/build_native.sh`.
`out/regression_gate/` (per-frame results) stays out of git.

### 4.5 Image archive

```bash
./scripts/export_image.sh                               # clean --no-cache build of HEAD from git archive, gzip, .sha256
ARCHIVE=$(ls -t dist/resense-image-*.tar.gz | head -n 1)
./scripts/load_image.sh "$ARCHIVE"                      # sha256, docker load, the image checked with --network none
mkdir -p "$EV/export_$DAY"
{ ls -l "$ARCHIVE"; cat "$ARCHIVE.sha256"; git rev-parse HEAD; docker image inspect -f '{{.Size}}' resense:latest; } \
  > "$EV/export_$DAY/archive.txt"
```

15–20 min, needs the internet; `export_image.sh` refuses uncommitted changes to tracked files.
**Done:** both exit 0 (about 0.48 GB). Commit `archive.txt`, **never** the archive (`dist/` is
ignored by git). The public archive is published as the assets of the GitHub release `v1.0.0` by
`.github/workflows/release.yml` when the tag is pushed; until then it is the CI artifact of a
`main` run (job `offline-build`, GitHub login) or `scripts/export_image.sh` as here.

### 4.6 Shared-memory mode (opt-in `RESENSE_DDS=shm`)

Optional (CI's `docker` job tests it on every push). `-e RESENSE_DDS=shm` puts the node on shared
memory + UDP and opens its Fast DDS files in `/dev/shm` to other users (`docker/dds_transport.sh`),
so a stock Fast DDS player hands the clouds over `/dev/shm`; the default stays UDP-only. Run the
host console of §4.2 at `rmem_max` 212992 with `-e RESENSE_DDS=shm` in console 1 (its log shows
`DDS transport: shm`; a `[WARN] [resense.dds]` line means it fell back to UDP), results into
`host_console_shm.txt`. **Done:** the check passes, `STOP` in console 3, and while
`doubleT_obstacle` plays, `grep -o '/dev/shm/fastrtps_port[0-9]*$' /proc/$(pgrep -n -f "bag
play")/maps | sort -u | xargs -r stat -c '%U %a %n'` prints `root 666 …` lines. In Docker:
`NODE_DDS=shm PLAYER_DDS=stock` before §4.2's `console_test.sh` line, exit 0. Stop the node with
Ctrl+C, not `docker rm -f`, so that Fast DDS removes its files from `/dev/shm`.

## 5. Offline rehearsal

The stand has no internet: the jury loads the archive and runs it offline. CI proves this with
synthetic bags; here it is proven with the original bags and the network cut. Nothing is
scripted, and **every rule is temporary** (never saved, gone after a reboot). Before you block
anything: §4.5 is done (the archive in `dist/`, both bags on disk); the provider's serial console
works (try it once); you work in `tmux` with a second SSH session open. **An agent's own API
access is cut** unless its API host is allowed (step 3b); otherwise a person runs this section, or
the agent runs steps 3c–7 as one command in `tmux` and reads the output after the restore.

**1–2. Write the restore first** (into `/run`, cleared by a reboot) **and arm it** (a timer runs it
after the window whatever happens to your shell):

```bash
EXT_IF=$(ip route show default | awk '{ for (i = 1; i < NF; i++) if ($i == "dev") { print $(i + 1); exit } }')
echo "outbound interface: ${EXT_IF:?no default route: stop here}"
sudo tee /run/resense-restore.sh > /dev/null <<EOF
for t in iptables ip6tables; do
  while \$t -D OUTPUT -j RESENSE_OFFLINE 2>/dev/null; do :; done
  \$t -F RESENSE_OFFLINE 2>/dev/null; \$t -X RESENSE_OFFLINE 2>/dev/null
done
while iptables -D DOCKER-USER -o $EXT_IF -j REJECT 2>/dev/null; do :; done
echo "restored \$(date -Is)" >> /run/resense-restore.log
EOF
sudo systemd-run --on-active=30min --unit=resense-restore /bin/sh /run/resense-restore.sh
systemctl list-timers --all resense-restore.timer    # it must be listed; if not, stop here
```

**3. Build the block:** outbound only, in an own chain for IPv4 and IPv6; incoming SSH and its
replies still pass. Nothing is blocked until step 3c.

```bash
for t in iptables ip6tables; do
  sudo $t -N RESENSE_OFFLINE
  sudo $t -A RESENSE_OFFLINE -o lo -j ACCEPT                                        # node, player, DDS on this host
  sudo $t -A RESENSE_OFFLINE -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT   # open SSH sessions, replies to new logins
done
sudo iptables -A RESENSE_OFFLINE -d 224.0.0.0/4 -j ACCEPT                           # multicast (DDS discovery), not routed out
sudo iptables -A RESENSE_OFFLINE -d 169.254.169.254 -j ACCEPT                       # the cloud's metadata service (SSH keys on many clouds)
sudo iptables -A RESENSE_OFFLINE -p udp --dport 67:68 -j ACCEPT                     # DHCP lease renewal
sudo ip6tables -A RESENSE_OFFLINE -d fe80::/10 -j ACCEPT                            # link-local: neighbour discovery
sudo ip6tables -A RESENSE_OFFLINE -d ff00::/8 -j ACCEPT                             # multicast: neighbour discovery, DHCPv6
```

**3b. Only for an agent that must keep its connection:** DNS and HTTPS to its API host (Claude
Code: `api.anthropic.com`), IPv4 only; the rehearsal is then not fully offline: say so.

```bash
sudo iptables -A RESENSE_OFFLINE -p udp --dport 53 -j ACCEPT
sudo iptables -A RESENSE_OFFLINE -p tcp --dport 53 -j ACCEPT
for ip in $(getent ahostsv4 api.anthropic.com | awk '{ print $1 }' | sort -u); do
  sudo iptables -A RESENSE_OFFLINE -d "$ip" -p tcp --dport 443 -j ACCEPT
done
```

**3c–4. Switch it on** (everything else rejected at once, from this host and from containers on
Docker bridge networks) **and check it** on both address families:

```bash
for t in iptables ip6tables; do
  sudo $t -A RESENSE_OFFLINE -j REJECT
  sudo $t -I OUTPUT 1 -j RESENSE_OFFLINE
done
sudo iptables -I DOCKER-USER 1 -o "$EXT_IF" -j REJECT
mkdir -p "$EV/offline_$DAY"
python3 scripts/check_no_network.py | tee "$EV/offline_$DAY/check_no_network.txt"; echo "exit ${PIPESTATUS[0]}"   # 0: nothing reachable
curl -4 -sS -m 5 -o /dev/null https://github.com; echo "IPv4: curl exit $?"          # non-zero expected
curl -6 -sS -m 5 -o /dev/null https://ipv6.google.com; echo "IPv6: curl exit $?"     # non-zero expected
```

If anything is reachable: restore (step 7), find the leak, start again. Then open a **new** SSH
session from your computer: it must still log in; if not, restore now from the open one.

**5. The runs, offline**, each recording read into the page cache right before it plays (§3):

```bash
docker image rm -f $(docker images -q resense)          # start from the archive only
ARCHIVE=$(ls -t dist/resense-image-*.tar.gz | head -n 1)
cat "$BAGS"/doubleT_obstacle/*.db3 > /dev/null
IMAGE_TAR="$ARCHIVE" OFFLINE=1 OUT=out/off_obstacle ./scripts/dry_run.sh "$BAGS/doubleT_obstacle" \
  2>&1 | tee "$EV/offline_$DAY/dry_obstacle.txt"; echo "exit ${PIPESTATUS[0]}"
cat "$BAGS"/roundT_doubleT/*.db3 > /dev/null
SKIP_BUILD=1 OFFLINE=1 OUT=out/off_clear ./scripts/dry_run.sh "$BAGS/roundT_doubleT" --expect-clear --max-alarm-frames 2 \
  2>&1 | tee "$EV/offline_$DAY/dry_clear.txt"; echo "exit ${PIPESTATUS[0]}"
```

Then the host console of §4.2, still offline, into `offline_<date>/host_console.txt`; optionally
`scripts/play_bag.sh "$BAGS/doubleT_obstacle" --archive "$ARCHIVE"`. **Done:** both dry runs exit 0
with the §4.1 criteria and the host console passes with `STOP` on `doubleT_obstacle`.

**6–7. Record what tried to go out** (packet counters per rule; the `REJECT` line counts the
blocked attempts), **then restore by hand** and stop the timer:

```bash
sudo iptables -L RESENSE_OFFLINE -v -n > "$EV/offline_$DAY/rules_ipv4.txt"
sudo ip6tables -L RESENSE_OFFLINE -v -n > "$EV/offline_$DAY/rules_ipv6.txt"
sudo /bin/sh /run/resense-restore.sh; sudo systemctl stop resense-restore.timer
curl -sS -m 15 -o /dev/null -w '%{http_code}\n' https://github.com    # 200: online again
```

**Safety net, in order:** the timer restores at the end of the window; the serial console works
without the network; a reboot from the provider's console clears every rule. **Never** save the
rules (`iptables-save` into a file loaded at boot, `netfilter-persistent save`,
`iptables-persistent`) and never stop the timer while the block is on.

## 6. Results and the PR

One folder per run, `docs/evidence/<run>_<date>/`: `vm_` (with a `summary.md`: one row per run
and the findings), `dry_run_`, `bench_`, `gate_`, `export_`, `offline_`. `.gitignore` hides `*.log`
and `*.jsonl`, so rename and compress what you keep, then look at every file the `grep` lists:
**no personal data** in a commit (names, e-mails, tokens, SSH keys, IP addresses including the VM's
public one, home paths with a person's name):

```bash
for r in dry_obstacle dry_clear cold_obstacle cold_clear ct_stock host_console off_obstacle off_clear; do
  d=out/$r; case "$r" in off_*) to="$EV/offline_$DAY" ;; *) to="$EV/dry_run_$DAY" ;; esac
  [ -f "$d/node.log" ] && cp "$d/node.log" "$to/${r}_node_log.txt"
  [ -f "$d/status.jsonl" ] && gzip -c "$d/status.jsonl" > "$to/${r}_status.jsonl.gz"
done
find "$EV" -path "*_$DAY/*" -type f -size +20M     # must print nothing
grep -rIlE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}|ghp_|github_pat_|PRIVATE KEY|([0-9]{1,3}\.){3}[0-9]{1,3}' "$EV"/*_"$DAY"
```

Never commit bags, caches, `*.npy`, `*.db3`, the image archive or `out/`. Add one row per folder
to [`evidence/README.md`](evidence/README.md) §2; a number that disagrees with the current results
in `docs/EXPERIMENTS.md` goes into the PR description. **The PR** ([`CAPTAIN.md`](CAPTAIN.md) §6):
a new branch `vm-evidence-$DAY` against `main` with `docs/evidence/*_"$DAY"` and the index rows
only (never push to `main`, force-push or merge your own PR; `gh pr create --base main`); a FAIL is
evidence too: commit it as it is.

## 7. When something goes wrong

| symptom | what to do |
|---|---|
| `permission denied … docker.sock` | the `docker` group (§1): log out and in, or `newgrp docker` |
| the base image cannot be pulled | retry; a registry mirror as Docker's documentation describes |
| Google Drive answers with a page (§2.1) | download `Датасет.zip` in a browser, `scp` it to `$DATA/dataset.zip` |
| the ride stream broke off (§2.3) | run the same lines again: cached split files are skipped |
| disk full | §2: delete bags you do not need, or mount a bigger data disk at `$DATA` |
| a run exits 3 | no Docker daemon (`scripts/require_docker.sh`) |
| a dry run fails on frames skipped by the catch-up after an input stall | the disk stalled the player: pre-read the bags or use a tmpfs (§3), run again, keep both results |
| a 20 s recording's results span about a minute of wall time (§4.1) | the disk sets the pace: the same |
| a host console gets few or no 360° clouds | the player runs CycloneDDS (§1): `rmem_max` 32 MiB (§4.2), or install the Fast DDS RMW |
| the block is still on (§5) | `sudo /bin/sh /run/resense-restore.sh`; else the serial console; else a reboot |
| no ROS 2 on the host | everything but the host consoles runs; the organizers' console rests on the stock player in Docker |
| a step fails | keep its output, commit it, report it in the PR; do not change code on the VM |

## Experimental branch validation record

For the accepted P3 and health changes, use the measured commits and procedures recorded in
[`P3_SCORE_SYNC_2026-09-28.md`](P3_SCORE_SYNC_2026-09-28.md) and the
[health validation record](evidence/cycle_2026-09-28/health_histogram/README.md). Its runtime
captures precede the new node implementation. `catchup_startup_step:=0` is the default; the A/B at
0.2 s (the default before PR #27 was merged) does not prove full input-frame coverage.
