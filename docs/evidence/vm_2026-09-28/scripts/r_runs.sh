#!/bin/bash
# The 28.09 VM runs on main (docs/VM_GUIDE.md §3-§4.6), one subcommand per run:
#   r_runs.sh facts|build|dry|cold|warm|fastinput|ct_stock|jury|host_fastdds|host_cyclonedds|shm_fast|shm_cyclone|ct_shm|bench|gate|export
# The original bags are read from $BAGS on the VM's disk; evidence goes to $EV/<run>_$DAY.
. ~/r_env.sh
cd "$REPO" || exit 2
B=$BAGS
D=${D:-$EV/dry_run_$DAY}
mkdir -p "$D"

drop_caches() { sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'; }
ros() { set +u; source /opt/ros/humble/setup.bash
        unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML RMW_IMPLEMENTATION; }
# keep <run>: the node log and the gzipped status capture of out/<run> next to its output
keep() { local r=$1 to=${2:-$D}
  [ -f "out/$r/node.log" ] && cp "out/$r/node.log" "$to/${r}_node_log.txt"
  [ -f "out/$r/status.jsonl" ] && gzip -c "out/$r/status.jsonl" > "$to/${r}_status.jsonl.gz"; true; }
# dry <run> <bag> [check args...]: scripts/dry_run.sh reusing the image, output to $D/<run>.txt
dry() { local r=$1 bag=$2; shift 2
  SKIP_BUILD=1 OUT=out/$r ./scripts/dry_run.sh "$bag" "$@" 2>&1 | tee "$D/$r.txt"
  echo "exit ${PIPESTATUS[0]}" | tee -a "$D/$r.txt"; keep "$r"; }

# host_console <name> <node docker args...>: README «Кратко для жюри» steps 2-5 on the host.
# The node on the image's default command (console 1, stopped with SIGINT); the stock host player and
# listeners as this user (consoles 2-4), both recordings, --read-ahead-queue-size 10; the player's RMW
# from $PLAYER_RMW (unset: Humble's default rmw_fastrtps_cpp). Same harness as dry_run_2026-09-25_3/g_fix.sh.
host_console() {
  local name=$1; shift
  local O=out/$name N=resense_node; mkdir -p "$O"; rm -f "$O"/*
  docker rm -f $N >/dev/null 2>&1
  ( docker run --rm --name $N --net=host --ipc=host "$@" resense:latest > "$D/${name}_node_log.txt" 2>&1 ) &
  for _ in $(seq 1 60); do grep -q "ReSense detector listening" "$D/${name}_node_log.txt" 2>/dev/null && break; sleep 1; done
  ( ros; [ -n "${PLAYER_RMW:-}" ] && export RMW_IMPLEMENTATION=$PLAYER_RMW
    ls -l /dev/shm > "$D/${name}_ls.txt"
    ros2 topic echo /resense/decision --field data > "$O/decision.txt" 2>/dev/null & DEC=$!
    ros2 topic echo /resense/nearest_distance --field data > "$O/nearest_distance.txt" 2>/dev/null & DIST=$!
    ros2 topic echo /resense/status --field data > "$O/status.jsonl" 2>/dev/null & ECHO=$!
    sleep 4
    ( # console 4: while doubleT_obstacle plays, the RMW the player loaded and the node's queues it writes into
      for _ in $(seq 1 120); do P=$(pgrep -n -f "bag play .*doubleT_obstacle") && break; sleep 0.5; done
      sleep 8
      { echo "player pid $P ($(ps -o user= -p "$P" 2>/dev/null)), RMW loaded: $(grep -ohE 'librmw_[a-z]+_cpp\.so|libfastrtps\.so\.[0-9.]+|libddsc\.so\.[0-9.]+' /proc/$P/maps 2>/dev/null | sort -u | tr '\n' ' ')"
        grep -o '/dev/shm/fastrtps_port[0-9]*$' "/proc/$P/maps" 2>/dev/null | sort -u | xargs -r stat -c '%U %a %n'; } > "$D/${name}_console4.txt" ) &
    C4=$!
    { ros2 bag play "$B/roundT_doubleT" --delay 3 --read-ahead-queue-size 10 --disable-keyboard-controls && sleep 5 &&
      ros2 bag play "$B/doubleT_obstacle" --delay 3 --read-ahead-queue-size 10 --disable-keyboard-controls; } > "$O/player_log.txt" 2>&1
    echo "player exit $?" >> "$O/player_log.txt"
    sleep 3; kill $DEC $DIST $ECHO 2>/dev/null; wait $C4 2>/dev/null )
  docker kill -s INT $N >/dev/null 2>&1                 # Ctrl+C in console 1: Fast DDS removes its files
  for _ in $(seq 1 20); do docker ps -q -f name=$N | grep -q . || break; sleep 1; done
  docker rm -f $N >/dev/null 2>&1; wait
  ls -l /dev/shm > "$D/${name}_ls_after.txt"
  { echo "node docker args: ${*:-(none)}, image default command; player: uid $(id -u), RMW ${PLAYER_RMW:-unset (Humble default)}, no Fast DDS profile;" \
         "net.core.rmem_max $(sysctl -n net.core.rmem_max), rmem_default $(sysctl -n net.core.rmem_default)"
    echo "decisions seen: $(grep -v -- '^---$' "$O/decision.txt" | sort | uniq -c | tr '\n' ' ')"
    grep -E "resense.dds|resense.shm|WARN|ERROR" "$D/${name}_node_log.txt" | cut -c1-220 | head -8
    echo "console 4: $(tr '\n' ' ' < "$D/${name}_console4.txt" 2>/dev/null)"
    python3 scripts/check_dry_run.py "$O/status.jsonl" --require-freshness --expect-obstacle --obstacle-in 2 --expect-inputs 2 \
      --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
    echo "exit $?"; } 2>&1 | tee "$D/${name}.txt"
  gzip -c "$O/status.jsonl" > "$D/${name}_status.jsonl.gz"
  for f in decision nearest_distance player_log; do cp "$O/$f.txt" "$D/${name}_$f.txt"; done
}

case "$1" in
facts)   # §3: the machine facts
  mkdir -p "$EV/vm_$DAY"
  { lscpu; free -h; df -h "$DATA" /var/lib/docker; uname -srvmo; docker version; vmstat 1 5; git -C "$REPO" rev-parse HEAD
    sysctl net.core.rmem_max net.core.rmem_default; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
    dpkg -l | grep -E 'ros-humble-(ros-base|rmw-fastrtps-cpp|rmw-cyclonedds-cpp|rosbag2) ' | awk '{print $2, $3}'
    python3 --version; python -m pip show rosbags | grep Version
    echo "== sequential read of the 360-degree recording from disk, direct I/O (2 GiB)"
    dd if="$(ls "$B"/doubleT_obstacle/*.db3 | head -n 1)" of=/dev/null bs=4M count=512 iflag=direct 2>&1 | tail -n 1; } > "$EV/vm_$DAY/machine.txt" 2>&1 ;;
build)   # §4.1's first build, run ahead of the timed runs: the command dry_run.sh runs without SKIP_BUILD
  { echo "== building resense:latest from scratch (docker build --no-cache, as scripts/dry_run.sh) at $(git rev-parse --short HEAD) =="
    start=$(date +%s); docker build --no-cache -t resense:latest -f docker/Dockerfile .; rc=$?
    echo "build exit $rc, $(( $(date +%s) - start )) s"
    docker run --rm -w / resense:latest python3 -c "import resense, resense._native as n; print('image', resense.__version__, n.status())"
    docker image inspect -f '{{.Id}} {{.Size}}' resense:latest; } 2>&1 | tee "$D/build_no_cache.txt" ;;
dry)     # §4.1 as written, on the image of `build`
  dry dry_obstacle "$B/doubleT_obstacle"
  dry dry_clear "$B/roundT_doubleT" --expect-clear --max-alarm-frames 2
  python scripts/replay_node_frames.py out/dry_clear/status.jsonl --bag "$B/roundT_doubleT" 2>&1 | tee "$D/dry_clear_replay.txt"
  echo "exit ${PIPESTATUS[0]}" | tee -a "$D/dry_clear_replay.txt" ;;
cold)    # §4.1 cold-cache procedure (as scripts/p1_cold_bag_test.sh), page cache dropped before each; $2 = run suffix
  drop_caches
  dry "cold_obstacle$2" "$B/doubleT_obstacle" --expect-obstacle --distance 50:62 --min-frames 20 --max-p95-latency 100 --max-dropped 0
  drop_caches
  dry "cold_clear$2" "$B/roundT_doubleT" --expect-clear --max-alarm-frames 2 --max-p95-latency 100 --max-dropped 0 ;;
warm)    # the same with the recordings in the page cache (read once first); $2 = run suffix
  cat "$B"/doubleT_obstacle/*.db3 "$B"/roundT_doubleT/*.db3 > /dev/null
  dry "warm_obstacle$2" "$B/doubleT_obstacle" --expect-obstacle --distance 50:62 --min-frames 20 --max-p95-latency 100 --max-dropped 0
  dry "warm_clear$2" "$B/roundT_doubleT" --expect-clear --max-alarm-frames 2 --max-p95-latency 100 --max-dropped 0 ;;
fastinput)  # PR #20: the node's fast input path against rclpy's, every frame of both original recordings, in the image
  mkdir -p out/fastinput
  docker run --rm -v "$B":/data:ro -v "$REPO/out/fastinput":/out resense:latest \
    python3 /opt/resense/scripts/check_fast_input.py /data/doubleT_obstacle /data/roundT_doubleT --json /out/fast_input.json \
    2>&1 | tee "$D/fast_input.txt"
  echo "exit ${PIPESTATUS[0]}" | tee -a "$D/fast_input.txt"
  sudo cp out/fastinput/fast_input.json "$D/fast_input.json"; sudo chown "$(id -u):$(id -g)" "$D/fast_input.json" ;;
ct_stock)   # §4.2 in Docker: a uid-1000 stock Fast DDS player, both recordings into one node
  PLAYER_DDS=stock OUT=out/ct_stock ./scripts/console_test.sh "$B/roundT_doubleT" "$B/doubleT_obstacle" -- \
    --expect-obstacle --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000 \
    2>&1 | tee "$D/ct_stock.txt"; echo "exit ${PIPESTATUS[0]}" | tee -a "$D/ct_stock.txt"
  for f in out/ct_stock/*; do case "$f" in *.jsonl) gzip -c "$f" > "$D/ct_stock_$(basename "$f").gz";; *.log) cp "$f" "$D/ct_stock_$(basename "${f%.log}")_log.txt";; *) cp "$f" "$D/ct_stock_$(basename "$f")";; esac; done ;;
jury)    # README «Кратко для жюри» steps 0, 2-5 as written: rmem_max raised, the node on the image's default command
  sudo sysctl -w net.core.rmem_max=33554432
  host_console host_jury
  sudo sysctl -w net.core.rmem_max=212992 ;;
host_fastdds)  # §4.2 host console, stock Fast DDS player at Ubuntu's default rmem_max
  sudo sysctl -w net.core.rmem_max=212992
  host_console host_fastdds ;;
host_cyclonedds)  # §4.0 / §4.2: a CycloneDDS player at 32 MiB
  sudo sysctl -w net.core.rmem_max=33554432
  PLAYER_RMW=rmw_cyclonedds_cpp host_console host_cyclonedds
  sudo sysctl -w net.core.rmem_max=212992 ;;
shm_fast)   # §4.6: the node with RESENSE_DDS=shm, rmem_max at Ubuntu's default, stock Fast DDS player
  sudo sysctl -w net.core.rmem_max=212992
  host_console host_shm -e RESENSE_DDS=shm ;;
shm_cyclone) # §4.6: the same node, a CycloneDDS player (no shared memory) at 32 MiB
  sudo sysctl -w net.core.rmem_max=33554432
  PLAYER_RMW=rmw_cyclonedds_cpp host_console host_shm_cyclonedds -e RESENSE_DDS=shm
  sudo sysctl -w net.core.rmem_max=212992 ;;
ct_shm)     # §4.6: the same in Docker
  sudo sysctl -w net.core.rmem_max=212992
  NODE_DDS=shm PLAYER_DDS=stock OUT=out/ct_shm ./scripts/console_test.sh "$B/roundT_doubleT" "$B/doubleT_obstacle" -- \
    --expect-obstacle --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000 \
    2>&1 | tee "$D/ct_shm.txt"; echo "exit ${PIPESTATUS[0]}" | tee -a "$D/ct_shm.txt"
  for f in out/ct_shm/*; do case "$f" in *.jsonl) gzip -c "$f" > "$D/ct_shm_$(basename "$f").gz";; *.log) cp "$f" "$D/ct_shm_$(basename "${f%.log}")_log.txt";; *) cp "$f" "$D/ct_shm_$(basename "$f")";; esac; done ;;
bench)   # §4.3
  RESENSE_DATA="$BAGS" RESENSE_CACHE="$CACHE" ./scripts/bench_8core.sh; echo "exit $?" ;;
gate)    # §4.4: the newest baseline with the ride, --jobs = physical cores
  BASELINE=$(python3 -c "import glob, json; print(max((json.load(open(p))['created'], p) for p in glob.glob('docs/evidence/results/regression_baseline_*.json') if json.load(open(p)).get('ride', {}).get('available'))[1])")
  echo "baseline: $BASELINE"
  mkdir -p "$EV/gate_$DAY"
  /usr/bin/time -v python scripts/regression_gate.py --cache "$CACHE" --jobs 4 --baseline "$BASELINE" \
    --out "$EV/gate_$DAY/gate_$(git rev-parse --short HEAD).json" 2>&1 | tee "$EV/gate_$DAY/gate_table.txt"
  echo "exit ${PIPESTATUS[0]}" | tee -a "$EV/gate_$DAY/gate_table.txt" ;;
export)  # §4.5
  mkdir -p "$EV/export_$DAY"
  ./scripts/export_image.sh 2>&1 | tee "$EV/export_$DAY/export.txt"; echo "exit ${PIPESTATUS[0]}" | tee -a "$EV/export_$DAY/export.txt"
  ARCHIVE=$(ls -t dist/resense-image-*.tar.gz | head -n 1)
  ./scripts/load_image.sh "$ARCHIVE" 2>&1 | tee "$EV/export_$DAY/load.txt"; echo "exit ${PIPESTATUS[0]}" | tee -a "$EV/export_$DAY/load.txt"
  { ls -l "$ARCHIVE"; cat "$ARCHIVE.sha256"; git rev-parse HEAD; docker image inspect -f '{{.Size}}' resense:latest; } \
    > "$EV/export_$DAY/archive.txt" ;;
*) echo "unknown run $1" >&2; exit 2 ;;
esac
