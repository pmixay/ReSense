# VM Guide

> **Purpose:** how a person or an agent on the team's temporary cloud VM prepares it, fetches the
> organizers' data and runs the checks that need a real machine (8-core bench, dry run with the
> original bags, stock-player console test, regression gate with the ride, image archive, offline
> rehearsal), and how the results come back as evidence in a PR. Instructions only: every step is
> a plain command of the repository's own tools, parameterised by shell variables you set.
> **Audience:** team (a person or an agent on the VM) · **Owner:** P1 · **Language:** EN
> **Last verified:** 2026-09-25 against `46bb266`: the ride loop of §2.3 run in the dev sandbox on
> the first split files of `new_data.zst` (cache files byte-identical to the dev VM's ride cache of
> 25.09), both download endpoints of §2 answering; the other commands follow the scripts' headers
> and the README, not yet run on a VM · **Status:** current

## 0. What the VM is for, and when

The organizers' stand (i7-9700E, 8 cores, Ubuntu 22.04, ROS 2 Humble, Docker) has **no
internet**, and the team gets **no access** to it before the upload
([`organizers/answers.md`](organizers/answers.md) §6–§7). The VM stands in for it:

| run | tool | board item ([`CAPTAIN.md`](CAPTAIN.md)) | here |
|---|---|---|---|
| data: six recordings, `cloud_with_fake_obj`, the ride's frame cache | `scripts/unpack_dataset.py`, `scripts/cache_frames.py` | action 3 | §2 |
| clean-machine dry run with the **original** bags | `scripts/dry_run.sh` | C7, action 15 | §4.1 |
| the organizers' console: stock-DDS player, host console | `PLAYER_DDS=stock scripts/console_test.sh`, `ros2 bag play` | C4 | §4.2 |
| 8-core bench, native and numpy kernels | `scripts/bench_8core.sh` | C8, action 7 | §4.3 |
| regression gate with the ride | `scripts/regression_gate.py` | §6 (the gate), action 11 | §4.4 |
| image archive and its check | `scripts/export_image.sh`, `scripts/load_image.sh` | C25, action 15 | §4.5 |
| offline rehearsal from the archive | `IMAGE_TAR=… OFFLINE=1 scripts/dry_run.sh` with outbound traffic blocked | C25, action 15 | §5 |

**When** (the captain, 25.09): deployment and the presentation come later. The dry run, the
bench, the archive and the offline rehearsal run when the team deploys; the data and the gate
whenever a detector or config change needs the ride. **Releases are deferred** (no tags): the
archive comes from `scripts/export_image.sh`, not from a release, and no step here pushes a tag.

**What is tested** is the branch or commit the captain names (`main` once PR #12 is merged). A
failing criterion is a **finding to report**, with the numbers, not something to fix on the VM:
no code, config or test changes are made there.

## 1. Prerequisites

**The VM.** Ubuntu **22.04** (ROS 2 Humble's packages exist for 22.04 only; on another release
everything but the host console of §4.2 still runs). For the bench, **8 physical cores**: on
most clouds a vCPU is one hyper-thread, so 16 vCPU = 8 cores (`lscpu`: `Core(s) per socket` ×
`Socket(s)`), on a type with the full core (not a burstable or shared-core one); 16 GB RAM or
more; disk as in §2. Turn on the provider's **serial console** (the way in if SSH breaks, §5) and
work inside `tmux`, so that long runs survive a dropped connection.

**Variables.** Every command below uses these; set them in each new shell (or in a file you
`source`):

```bash
REPO_URL='<clone URL of the repository>'          # set these two
BRANCH='<branch or commit named by the captain>'   # main once PR #12 is merged
REPO=$HOME/ReSense                  # the clone (any directory)
DATA=/data                          # bags and caches; mount a data disk here if there is one
BAGS=$DATA/for_hackathon            # the six recordings (the scripts' default)
CACHE=$DATA/cache                   # frame caches, read by eval_real.py / regression_gate.py
EV=$REPO/docs/evidence              # evidence folders <run>_<date>
DAY=$(date +%F)
```

**Packages.** `sudo apt-get update && sudo apt-get install -y git curl zstd tmux build-essential
python3-venv python3-pip`; `sudo mkdir -p "$DATA" && sudo chown "$(id -u):$(id -g)" "$DATA"`.

**Docker Engine**, as [Docker's instructions for Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
describe, then the [post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/)
(the `docker` group, so that the scripts run without `sudo`). Done when `docker run --rm
hello-world` works as your user.

**ROS 2 Humble on the host**, only for the host-console player of §4.2: the
[Debian-package installation](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)
(`ros-humble-ros-base` is enough; `ros-humble-rmw-cyclonedds-cpp` for the CycloneDDS variant).
Everything else needs no ROS on the host.

**The clone and the Python environment:**

```bash
git clone "$REPO_URL" "$REPO" && cd "$REPO" && git checkout "$BRANCH"
python3 -m venv .venv && . .venv/bin/activate    # activate it in every new shell
pip install -U pip && pip install -e ".[dev]"    # the package, rosbags / zstandard for the data, the C++ kernels
scripts/build_native.sh                          # rebuild the kernels in place and print their status (after every checkout)
python -m pytest -q                              # optional: needs no data
git rev-parse HEAD                               # the commit every result is recorded against
```

A private repository needs your GitHub credentials first (`gh auth login`, or a token); they stay
on the VM and never go into a commit.

**An agent** (for example a Claude Code session) is started by a person in `$REPO`, with this
guide as its task and the variables above set. It runs the steps as written and reports; §5 cuts
its own connection unless its API host is allowed there.

## 2. Data

Measured sizes (25.09); a cached frame takes about 1.45 MB (`--every 1 --int16 --stamps`):

| item | size | keep? |
|---|---|---|
| `Датасет.zip` (Google Drive) | 3.7 GB | delete after unpacking |
| bags `doubleT_obstacle` + `roundT_doubleT` | 6.4 GB | keep: dry run, console test, bench |
| the other four bags | 15.3 GB | unpack one at a time, cache, delete (keep if the disk allows) |
| caches of the six recordings | 3.8 GB (2 488 frames) | keep |
| `cloud_with_fake_obj`: download → bag → cache | 1.75 GB → 7.4 GB → 2.2 GB (1 510 frames) | keep the cache; the bag only to replay it |
| the ride `new_data`: download → bag → cache | 17.1 GB → 90 GB → 16.5 GB (11 271 frames, 221 split files) | keep the cache; the bag only for a 20-minute replay |
| Docker: base image, builds, the image archive (0.5 GB) | about 10 GB | on the disk of `/var/lib/docker` |

Everything but the ride's bag fits in **about 50 GB free** (peak while unpacking); keeping the
ride's bag too needs about 90 GB more. `df -h "$DATA" /var/lib/docker` before you start.

Links, formats and checksums: [`DATASET.md`](DATASET.md). All commands run in `$REPO` with the
venv active.

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
chmod -R a+rX "$BAGS"                  # the console tests play as uid 1000
rm "$DATA/dataset.zip"
```

`unpack_dataset.py` streams zip → zip → zstd → tar and writes only the bags asked for; each call
reads the whole archive (a few minutes). With 22 GB to spare, unpack all six in one pass (leave out
`--only`) and drop the `rm -rf` line.

### 2.2 `cloud_with_fake_obj` (set O)

```bash
python scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out "$DATA"   # streamed, -> $DATA/cloud_with_fake_obj
python scripts/cache_frames.py "$DATA/cloud_with_fake_obj" "$CACHE/cloud_with_fake_obj" --every 1 --int16 --stamps
rm -rf "${DATA:?}/cloud_with_fake_obj"   # optional: the gate reads only the cache
```

### 2.3 The 20-minute ride, split by split

`new_data.zst` is a zstd-compressed tar of one bag: 221 split files `new_data_<N>.db3` of 408 MB
(51 frames each) and `metadata.yaml`. The loop below never writes more than one split file:
`curl` streams the archive, `zstd` unpacks it on the fly, and `tar --to-command` hands each split
file to a short shell command instead of writing it. The command spools that one file, caches it
with `scripts/cache_frames.py --every 1 --int16 --stamps` and deletes it; meanwhile the next split
file waits in the pipe. A split file whose `_stamps.json` (written last by `cache_frames.py`) is
already in the cache is read past, so running the same lines again resumes after a break.

```bash
cd "$REPO"                              # the command below calls scripts/ relative to the clone
SPOOL=$DATA/.ride_spool
mkdir -p "$CACHE/new_data" "$SPOOL"
export CACHE SPOOL                      # tar's command runs in a child shell
# the download URL of new_data.zst: the Yandex Disk public API, no account needed
HREF=$(curl -fsS --get \
  --data-urlencode "public_key=https://disk.yandex.ru/d/N8IUpAyd7jyvow" \
  --data-urlencode "path=/new_data.zst" \
  https://cloud-api.yandex.net/v1/disk/public/resources/download \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["href"])')
# one split file at a time: spool, cache, delete; skip what is cached already
curl -fsSL "$HREF" | zstd -dc | tar -x --wildcards '*.db3' --to-command='
  f="$SPOOL/$(basename "$TAR_FILENAME")"; name=$(basename "$f" .db3)
  if [ -f "$CACHE/new_data/${name}_stamps.json" ]; then cat > /dev/null; exit 0; fi
  cat > "$f" && python scripts/cache_frames.py "$f" "$CACHE/new_data" --every 1 --int16 --stamps
  rc=$?; rm -f "$f"; exit $rc'
ls "$CACHE"/new_data/*_stamps.json | wc -l   # 221 when complete; fewer: run the lines again
```

About 4 s to stream and 3 s to cache each split file on the dev VM's link: 20–40 min in all,
16.5 GB of cache, 0.4 GB of spool. A split file that fails to cache leaves no `_stamps.json`; `tar`
then exits 2 at the end, and the next run caches only what is missing (it streams the archive
again). To keep the whole bag instead (90 GB, for a 20-minute `ros2 bag play "$DATA/new_data"`):
`python scripts/unpack_dataset.py https://disk.yandex.ru/d/N8IUpAyd7jyvow --member new_data.zst
--out "$DATA"`, then `cache_frames.py` on each `"$DATA"/new_data/new_data_*.db3`.

### 2.4 Check

```bash
for d in "$CACHE"/*/; do printf '%-40s %6d frames\n' "$(basename "$d")" "$(find "$d" -name '*.npy' | wc -l)"; done
```

Done when the counts are: `doubleT_obstacle` 201, `doubleT_platform` 345, `roundT_doubleT` 252,
`roundT_pressureGate_roundT` 268, `roundT_squareT_pressureGate_squareT` 545,
`squareT_platform_squareT_switch` 877, `cloud_with_fake_obj` 1 510, `new_data` 11 271; and the
two bags are the organizers' originals:

```bash
for b in doubleT_obstacle roundT_doubleT; do cmp "$BAGS/$b/metadata.yaml" "docs/evidence/bag_metadata/${b}_metadata.yaml" && echo "$b original"; done
```

## 3. Before the runs

* `git status --short --untracked-files=no` is empty and `git rev-parse --short HEAD` is the
  commit the captain named; `scripts/build_native.sh` was run on it.
* The VM is otherwise idle for the timed runs (§4.1, §4.3); `vmstat 1 5` (column `st`, CPU steal)
  goes into the machine facts.
* The machine facts, once per day:

  ```bash
  mkdir -p "$EV/vm_$DAY"
  { lscpu; free -h; df -h "$DATA" /var/lib/docker; uname -a; docker version; vmstat 1 5; git -C "$REPO" rev-parse HEAD; } \
    > "$EV/vm_$DAY/machine.txt" 2>&1
  ```

The exit code of a command piped into `tee` is `${PIPESTATUS[0]}`, printed after each run below.

## 4. The runs

In this order on a fresh VM: the dry run's `--no-cache` build (§4.1) should be the first build
there, so that it is the clean machine of C7. Each run says what "done" means and where its
evidence goes; §6 turns the evidence into a PR.

### 4.1 Dry run with the original bags

```bash
mkdir -p "$EV/dry_run_$DAY"
OUT=out/dry_obstacle ./scripts/dry_run.sh "$BAGS/doubleT_obstacle" 2>&1 | tee "$EV/dry_run_$DAY/dry_obstacle.txt"
echo "exit ${PIPESTATUS[0]}"
SKIP_BUILD=1 OUT=out/dry_clear ./scripts/dry_run.sh "$BAGS/roundT_doubleT" --expect-clear --max-alarm-frames 2 \
  2>&1 | tee "$EV/dry_run_$DAY/dry_clear.txt"
echo "exit ${PIPESTATUS[0]}"
```

The first builds the image with `--no-cache` (20–35 min with the build), plays the bag through
the node and checks `/resense/status` with `scripts/check_dry_run.py`. **Done:** both exit 0: the
person at 50–62 m in ≥ 3 frames, p95 of decode + detect ≤ 100 ms, no frame dropped after the first
5 s; on `roundT_doubleT` at most its 2 known alarm frames. A latency or drop failure is a result
to record with the core count. **Evidence:** `docs/evidence/dry_run_<date>/` (the two outputs,
plus the node logs and captures of `out/dry_*`, §6).

### 4.2 The organizers' console: stock-DDS player, host console

In Docker, a uid-1000 player with Humble's stock Fast DDS settings (shared memory + UDP, no XML
profile) and a stock listener, both recordings into one node:

```bash
PLAYER_DDS=stock OUT=out/ct_stock ./scripts/console_test.sh "$BAGS/roundT_doubleT" "$BAGS/doubleT_obstacle" -- \
  --expect-obstacle --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000 \
  2>&1 | tee "$EV/dry_run_$DAY/ct_stock.txt"
echo "exit ${PIPESTATUS[0]}"
```

**Done:** exit 0: both recordings seen, the obstacle in the second, the listener heard `STOP`, the
player used shared memory (the header of `scripts/console_test.sh` lists the assertions).

With ROS 2 Humble on the host, the same by hand, as the jury does it (README «Кратко для жюри»),
with a normal user's stock settings:

```bash
docker run --rm --name resense_node --net=host --ipc=host resense:latest     # console 1: the node, no arguments
```

```bash
# console 2: the player, a normal user, stock RMW, no Fast DDS profile
source /opt/ros/humble/setup.bash
unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML
mkdir -p out/host_console
ros2 topic echo /resense/status --field data > out/host_console/status.jsonl & ECHO=$!
sleep 4
ros2 bag play "$BAGS/roundT_doubleT" --delay 3 --disable-keyboard-controls && sleep 5 &&
  ros2 bag play "$BAGS/doubleT_obstacle" --delay 3 --disable-keyboard-controls
sleep 3; kill "$ECHO"
python3 scripts/check_dry_run.py out/host_console/status.jsonl --expect-obstacle --obstacle-in 2 --expect-inputs 2 \
  --min-frames 20 --max-p95-latency 1000 --max-dropped 100000 | tee "$EV/dry_run_$DAY/host_console.txt"
```

```bash
source /opt/ros/humble/setup.bash && ros2 topic echo /resense/decision --field data   # console 3: GO | CAUTION | STOP | FAULT
```

**Done:** the check passes and console 3 shows `STOP` during the obstacle recording. Optional:
the same with `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` in consoles 2 and 3 (the node stays
on Fast DDS; not tested so far, C4). **Evidence:** with the dry run's.

### 4.3 8-core bench

```bash
RESENSE_DATA="$BAGS" RESENSE_CACHE="$CACHE" ./scripts/bench_8core.sh; echo "exit $?"
```

Builds the image (timed), runs `dry_run.sh` on both bags with the node on the native kernels and
on numpy, `console_test.sh` with the image's and the stock player, samples `docker stats`, times
the detector on the host with peak RSS, and summarises (10–25 min; its header has the details).
Keep the VM otherwise idle. **Done:** exit 0 and `summary.txt`; C8 closes when
`dry_obstacle_native` passes (p95 ≤ 100 ms, no frame dropped after 5 s) on ≥ 8 physical cores.
**Evidence:** the script writes `docs/evidence/bench_<date>/` itself, ready to commit.

### 4.4 Regression gate with the ride

```bash
BASELINE=$(ls docs/evidence/results/regression_baseline_*_ride*.json | sort | tail -n 1)   # the newest baseline with the ride
mkdir -p "$EV/gate_$DAY"
python scripts/regression_gate.py --cache "$CACHE" --jobs 6 --baseline "$BASELINE" \
  --out "$EV/gate_$DAY/gate_$(git rev-parse --short HEAD).json" 2>&1 | tee "$EV/gate_$DAY/gate_table.txt"
echo "exit ${PIPESTATUS[0]}"
```

Every frame of the six recordings, set O, the ride (in 8 pieces) and set F straight, each against
the baseline. `--jobs` about the physical core count (the dev VM: 394 s at `--jobs 3` on 4 vCPU).
Needs no Docker. **Done:** exit 0, every gated metric identical or better; on the commit the
baseline was measured on, identical apart from latency. Exit 1: a gated metric is worse (the rows
are in the table: report them); 2: a recording's cache is missing or incomplete (§2.4). The ride
and set F are compared only when `$CACHE/new_data` exists: the JSON says "not available"
otherwise. A candidate branch runs in its own worktree: `git worktree add ../candidate <branch>`,
then `scripts/build_native.sh` and the same command there. **Evidence:** the JSON and the table in
`docs/evidence/gate_<date>/`; the per-frame results in `out/regression_gate/` stay out of git.

### 4.5 Image archive

```bash
./scripts/export_image.sh                               # clean --no-cache build of HEAD from git archive, gzip, .sha256
ARCHIVE=$(ls -t dist/resense-image-*.tar.gz | head -n 1)
./scripts/load_image.sh "$ARCHIVE"                      # sha256, docker load, the image checked with --network none
mkdir -p "$EV/export_$DAY"
{ ls -l "$ARCHIVE"; cat "$ARCHIVE.sha256"; git rev-parse HEAD; docker image inspect -f '{{.Size}}' resense:latest; } \
  > "$EV/export_$DAY/archive.txt"
```

15–20 min, needs the internet. `export_image.sh` refuses uncommitted changes to tracked files (the
image is built from `git archive HEAD`). **Done:** both scripts exit 0. **Evidence:**
`docs/evidence/export_<date>/archive.txt` (size, sha256, commit); **never** the archive itself
(`dist/` is ignored by git). No tag and no release: they are deferred by the captain (C13).

## 5. Offline rehearsal

The stand has no internet, so the jury loads the archive and runs it offline. CI proves this with
synthetic bags on every push; here it is proven with the original bags and the network cut, which
closes action 15 (with the later deployment). Instructions only: nothing here is scripted, and
**every rule is temporary** (never saved, gone after a reboot).

**Before you block anything:**

* §4.5 is done: the archive is in `dist/`, both bags are on disk.
* The provider's serial console works (try it once): it needs no network.
* You work in `tmux`, and a second SSH session is open.
* **An agent's own API access is cut** by the block unless its API host is allowed (step 3b), and
  it cannot reach its model until the restore. Without step 3b, a person runs this section, or the
  agent runs steps 3c–7 as one command in `tmux` and reads the output after the restore.

**1. Write the restore first** (into `/run`, which a reboot clears):

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
```

**2. Arm it before blocking:** a timer runs it after the window whatever happens to your shell.

```bash
sudo systemd-run --on-active=30min --unit=resense-restore /bin/sh /run/resense-restore.sh
systemctl list-timers --all resense-restore.timer    # it must be listed; if not, stop here
```

**3. Build the block:** outbound traffic only, in an own chain for IPv4 and IPv6. Incoming
traffic is not touched, so SSH still arrives, and its replies pass as established connections.
Nothing is blocked until step 3c hooks the chain in.

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

**3b. Only for an agent that must keep its connection**, before step 3c: DNS and HTTPS to its API
host (Claude Code: `api.anthropic.com`, unless it is set up for another provider), IPv4 only. The
rehearsal is then not fully offline: say so in the evidence.

```bash
sudo iptables -A RESENSE_OFFLINE -p udp --dport 53 -j ACCEPT
sudo iptables -A RESENSE_OFFLINE -p tcp --dport 53 -j ACCEPT
for ip in $(getent ahostsv4 api.anthropic.com | awk '{ print $1 }' | sort -u); do
  sudo iptables -A RESENSE_OFFLINE -d "$ip" -p tcp --dport 443 -j ACCEPT
done
```

**3c. Switch it on:** everything else is rejected at once (no hanging tools), from this host and
from containers on Docker bridge networks.

```bash
for t in iptables ip6tables; do
  sudo $t -A RESENSE_OFFLINE -j REJECT
  sudo $t -I OUTPUT 1 -j RESENSE_OFFLINE
done
sudo iptables -I DOCKER-USER 1 -o "$EXT_IF" -j REJECT
```

**4. Check the block, on both address families:**

```bash
mkdir -p "$EV/offline_$DAY"
python3 scripts/check_no_network.py | tee "$EV/offline_$DAY/check_no_network.txt"
echo "exit ${PIPESTATUS[0]}"                                                          # 0: nothing reachable
curl -4 -sS -m 5 -o /dev/null https://github.com; echo "IPv4: curl exit $?"          # non-zero expected
curl -6 -sS -m 5 -o /dev/null https://ipv6.google.com; echo "IPv6: curl exit $?"     # non-zero expected
```

If anything is reachable: restore (step 7), find the leak, start again. Then open a **new** SSH
session from your computer: it must still log in. If it does not, the open session still works:
restore now.

**5. The runs, offline:**

```bash
docker image rm -f $(docker images -q resense)          # start from the archive only
ARCHIVE=$(ls -t dist/resense-image-*.tar.gz | head -n 1)
IMAGE_TAR="$ARCHIVE" OFFLINE=1 OUT=out/off_obstacle ./scripts/dry_run.sh "$BAGS/doubleT_obstacle" \
  2>&1 | tee "$EV/offline_$DAY/dry_obstacle.txt"
echo "exit ${PIPESTATUS[0]}"
SKIP_BUILD=1 OFFLINE=1 OUT=out/off_clear ./scripts/dry_run.sh "$BAGS/roundT_doubleT" --expect-clear --max-alarm-frames 2 \
  2>&1 | tee "$EV/offline_$DAY/dry_clear.txt"
echo "exit ${PIPESTATUS[0]}"
```

Then README «Кратко для жюри» steps 2–5 by hand from a normal user's host console, still
offline (§4.2, host console). **Done:** both dry runs exit 0 with the §4.1 criteria, and the host
console shows `STOP` on `doubleT_obstacle`.

**6. Record what tried to go out**, before restoring (packet counters per rule; the `REJECT` line
counts the blocked attempts):

```bash
sudo iptables -L RESENSE_OFFLINE -v -n > "$EV/offline_$DAY/rules_ipv4.txt"
sudo ip6tables -L RESENSE_OFFLINE -v -n > "$EV/offline_$DAY/rules_ipv6.txt"
```

**7. Restore by hand** and stop the timer:

```bash
sudo /bin/sh /run/resense-restore.sh; sudo systemctl stop resense-restore.timer
curl -sS -m 15 -o /dev/null -w '%{http_code}\n' https://github.com    # 200: online again
```

**Safety net, in order:** the timer restores at the end of the window; the serial console works
without the network; a reboot from the provider's console clears every rule. **Never** save the
rules (`iptables-save` into a file loaded at boot, `netfilter-persistent save`, installing
`iptables-persistent`) and never stop the timer while the block is on.

## 6. Results and the PR

**Folders** (in the clone): `docs/evidence/<run>_<date>/`, one per run: `vm_`, `dry_run_`,
`bench_` (written by `bench_8core.sh`), `gate_`, `export_`, `offline_`. `.gitignore` hides `*.log`
and `*.jsonl`, so rename and compress what you keep:

```bash
for r in dry_obstacle dry_clear ct_stock off_obstacle off_clear; do
  d=out/$r; case "$r" in off_*) to="$EV/offline_$DAY" ;; *) to="$EV/dry_run_$DAY" ;; esac
  [ -f "$d/node.log" ] && cp "$d/node.log" "$to/${r}_node_log.txt"
  [ -f "$d/status.jsonl" ] && gzip -c "$d/status.jsonl" > "$to/${r}_status.jsonl.gz"
done
find "$EV" -path "*_$DAY/*" -type f -size +20M     # must print nothing
```

**No personal data** in a commit: names, e-mails, tokens, SSH keys, IP addresses (the VM's public
address included), home paths with a person's name. Look at what this finds before committing:

```bash
grep -rIlE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}|ghp_|github_pat_|PRIVATE KEY|([0-9]{1,3}\.){3}[0-9]{1,3}' "$EV"/*_"$DAY"
```

Never commit bags, caches, `*.npy`, `*.db3`, the image archive or `out/`.

**Doc rows to update** with the numbers exactly as the evidence has them (if a number disagrees
with EXPERIMENTS "Current results", say so in the PR instead of editing the current results):

| folder | edit | how |
|---|---|---|
| `bench_<date>/` | [`EXPERIMENTS.md`](EXPERIMENTS.md) §3; CAPTAIN C8, action 7 | one subsection "8-core bench on the team VM (<date>)": machine (CPU model, vCPU / physical cores, RAM), fps, latency mean / p95 / max, dropped frames, CPU %, memory, native vs numpy; C8 DONE only with ≥ 8 physical cores, else PARTIAL with the core count |
| `dry_run_<date>/` | EXPERIMENTS §3b; CAPTAIN C7, C4, action 15 | one paragraph: date, machine, original bags, each criterion's number, PASS / FAIL; C4 from the stock player and the host console |
| `offline_<date>/` | CAPTAIN C25, action 15 | the result, what was allowed (step 3b or nothing), the blocked attempts |
| `export_<date>/` | CAPTAIN C13 | size and sha256 (releases stay deferred) |
| `gate_<date>/` | the PR description | the table; a go / no-go on a change is the captain's |
| every folder | [`evidence/README.md`](evidence/README.md) §2 | one short subsection: how it ran, the result |

**The PR** (CAPTAIN §6): from a new branch, against `main`; never push to `main`, never
force-push, never merge your own PR (the captain merges after CI is green and a review from
another lane). The freeze times are those of CAPTAIN §6; the deployment runs come later by the
captain's decision, so their PR adds evidence and the rows above, nothing else (no changes to
`resense/`, `configs/`, `native/`, `labels/`, `docs/evidence/results/`, `web/` or the tests; a
finding for another lane goes into the PR description).

```bash
git switch -c "vm-evidence-$DAY"
git add docs/evidence/*_"$DAY" docs/EXPERIMENTS.md docs/CAPTAIN.md docs/evidence/README.md
git commit -m "VM runs of $DAY: <what ran, where, the headline result>"
git push -u origin "vm-evidence-$DAY"
gh pr create --base main --title "VM evidence $DAY" --body "<the runs, their results, anything that failed>"
```

(without `gh`: push, then open the PR on GitHub.) A FAIL is evidence too: commit it as it is.

## 7. When something goes wrong

| symptom | what to do |
|---|---|
| `permission denied … docker.sock` | the `docker` group (§1): log out and in, or `newgrp docker` |
| the base image cannot be pulled | retry; a registry mirror as Docker's documentation describes |
| Google Drive answers with a page (§2.1) | download `Датасет.zip` in a browser, `scp` it to `$DATA/dataset.zip` |
| the ride stream broke off (§2.3) | run the same lines again: cached split files are skipped |
| disk full | §2 table: delete bags you do not need, or mount a bigger data disk at `$DATA` |
| a run exits 3 | no Docker daemon (`scripts/require_docker.sh`) |
| the block is still on (§5) | `sudo /bin/sh /run/resense-restore.sh`; else the serial console; else a reboot |
| no ROS 2 on the host | everything but the host console of §4.2 runs; C4 then rests on the stock player in Docker |
| a step fails | keep its output, commit it, report it in the PR; do not change code on the VM |
