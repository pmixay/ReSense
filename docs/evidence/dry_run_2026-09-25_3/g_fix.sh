#!/bin/bash
# Runs for the fixes of be39362: README jury step 0 and the opt-in shared-memory mode (VM_GUIDE §4.6).
#   g_fix.sh update|dry|jury0|shm_fast|shm_cyclone|ct_shm
. ~/g_env.sh
cd "$REPO"
B=/mnt/ramdata/for_hackathon
if [ ! -f ~/g_day.txt ]; then          # evidence folder date, fixed once: the next free <date>[_n]
  base=$(date +%F); d=$base; n=2
  while [ -e "$EV/dry_run_$d" ] || [ -e "$EV/bench_$d" ]; do d=${base}_$n; n=$((n + 1)); done
  echo "$d" > ~/g_day.txt
fi
DAY=$(cat ~/g_day.txt); D="$EV/dry_run_$DAY"; mkdir -p "$D"
ros() { set +u; source /opt/ros/humble/setup.bash
        unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML RMW_IMPLEMENTATION; }
# host_console <name> <node docker args...>: the node (console 1, foreground-style with tee, stopped with SIGINT),
# stock host player / listeners as this user (consoles 2-4), both recordings; RMW from $PLAYER_RMW
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
    ( # console 4: while doubleT_obstacle plays, the node's queues the player writes into
      for _ in $(seq 1 120); do P=$(pgrep -n -f "bag play .*doubleT_obstacle") && break; sleep 0.5; done
      sleep 8
      { echo "player pid $P ($(ps -o user= -p "$P" 2>/dev/null)), RMW loaded: $(grep -ohE 'librmw_[a-z]+_cpp\.so|libfastrtps\.so\.[0-9.]+|libddsc\.so\.[0-9.]+' /proc/$P/maps 2>/dev/null | sort -u | tr '\n' ' ')"
        grep -o '/dev/shm/fastrtps_port[0-9]*$' "/proc/$P/maps" 2>/dev/null | sort -u | xargs -r stat -c '%U %a %n'; } > "$D/${name}_console4.txt" ) &
    C4=$!
    { ros2 bag play "$B/roundT_doubleT" --delay 3 --disable-keyboard-controls && sleep 5 &&
      ros2 bag play "$B/doubleT_obstacle" --delay 3 --disable-keyboard-controls; } > "$O/player_log.txt" 2>&1
    sleep 3; kill $DEC $DIST $ECHO 2>/dev/null; wait $C4 2>/dev/null )
  docker kill -s INT $N >/dev/null 2>&1                 # Ctrl+C in console 1: Fast DDS removes its files
  for _ in $(seq 1 20); do docker ps -q -f name=$N | grep -q . || break; sleep 1; done
  docker rm -f $N >/dev/null 2>&1; wait
  ls -l /dev/shm > "$D/${name}_ls_after.txt"
  { echo "node docker args: ${*:-(none)}; player: $(id -un) uid $(id -u), RMW ${PLAYER_RMW:-rmw_fastrtps_cpp (default)}, no Fast DDS profile;" \
         "net.core.rmem_max $(sysctl -n net.core.rmem_max), rmem_default $(sysctl -n net.core.rmem_default)"
    echo "decisions seen: $(grep -v -- '^---$' "$O/decision.txt" | sort | uniq -c | tr '\n' ' ')"
    grep -E "resense.dds|resense.shm|WARN" "$D/${name}_node_log.txt" | cut -c1-220 | head -8
    echo "console 4: $(cat "$D/${name}_console4.txt" 2>/dev/null | tr '\n' ' ')"
    python3 scripts/check_dry_run.py "$O/status.jsonl" --expect-obstacle --obstacle-in 2 --expect-inputs 2 \
      --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
    echo "exit $?"; } 2>&1 | tee "$D/${name}.txt"
  gzip -c "$O/status.jsonl" > "$D/${name}_status.jsonl.gz"
  cp "$O/decision.txt" "$D/${name}_decision.txt"; cp "$O/nearest_distance.txt" "$D/${name}_nearest_distance.txt"; cp "$O/player_log.txt" "$D/${name}_player_log.txt"
}
case "$1" in
prep)
  git rev-parse --short HEAD; git status --short --untracked-files=no
  mountpoint -q /mnt/ramdata || { sudo mkdir -p /mnt/ramdata && sudo mount -t tmpfs -o size=7G,mode=0755 tmpfs /mnt/ramdata && sudo chown "$(id -u):$(id -g)" /mnt/ramdata; }
  mkdir -p "$B"; for b in doubleT_obstacle roundT_doubleT; do [ -d "$B/$b" ] || cp -r "$BAGS/$b" "$B/"; cmp "$B/$b/${b}_0.db3" "$BAGS/$b/${b}_0.db3" && echo "$b staged"; done; chmod -R a+rX "$B"
  mkdir -p "$EV/vm_$DAY"; { lscpu; free -h; df -h / /var/lib/docker; uname -a; docker version; vmstat 1 5; git rev-parse HEAD; sysctl net.core.rmem_max net.core.rmem_default; } > "$EV/vm_$DAY/machine.txt" 2>&1
  echo "evidence day: $DAY" ;;
update)
  git fetch -q origin && git checkout -q "$BRANCH" && git pull -q --ff-only origin "$BRANCH"
  git rev-parse --short HEAD; git status --short --untracked-files=no
  scripts/build_native.sh | tail -1
  mountpoint -q /mnt/ramdata || { sudo mkdir -p /mnt/ramdata && sudo mount -t tmpfs -o size=7G,mode=0755 tmpfs /mnt/ramdata && sudo chown "$(id -u):$(id -g)" /mnt/ramdata; }
  mkdir -p "$B"; for b in doubleT_obstacle roundT_doubleT; do [ -d "$B/$b" ] || cp -r "$BAGS/$b" "$B/"; cmp "$B/$b/${b}_0.db3" "$BAGS/$b/${b}_0.db3" && echo "$b staged"; done; chmod -R a+rX "$B"
  ./scripts/build.sh > "$D/build.txt" 2>&1; echo "build exit $?" | tee -a "$D/build.txt"
  docker run --rm -w / resense:latest python3 -c "import resense, resense._native as n; print('image', resense.__version__, n.status())" | tee -a "$D/build.txt"
  mkdir -p "$EV/vm_$DAY"; { lscpu; free -h; uname -a; docker version; vmstat 1 5; git rev-parse HEAD; sysctl net.core.rmem_max net.core.rmem_default; } > "$EV/vm_$DAY/machine.txt" 2>&1
  echo "evidence day: $DAY" ;;
dry)    # §4.1 as written: the --no-cache build is this VM's first build; the node on its default (UDP)
  sudo sysctl -q -w net.core.rmem_max=212992
  OUT=out/dry_obstacle ./scripts/dry_run.sh "$B/doubleT_obstacle" 2>&1 | tee "$D/dry_obstacle.txt"; echo "exit ${PIPESTATUS[0]}" | tee -a "$D/dry_obstacle.txt"
  SKIP_BUILD=1 OUT=out/dry_clear ./scripts/dry_run.sh "$B/roundT_doubleT" --expect-clear --max-alarm-frames 2 2>&1 | tee "$D/dry_clear.txt"; echo "exit ${PIPESTATUS[0]}" | tee -a "$D/dry_clear.txt"
  for r in dry_obstacle dry_clear; do cp out/$r/node.log "$D/${r}_node_log.txt"; gzip -c out/$r/status.jsonl > "$D/${r}_status.jsonl.gz"; done ;;
jury0)  # README «Кратко для жюри» steps 0, 2-5 as written: rmem_max raised, the node on its default (UDP)
  sudo sysctl -w net.core.rmem_max=33554432
  host_console host_jury_step0
  sudo sysctl -w net.core.rmem_max=212992 ;;
fast_udp|fast_udp2)   # the host console with a genuine stock Fast DDS player (rmw_fastrtps_cpp installed), the node on its default (UDP), rmem_max at Ubuntu's default
  sudo sysctl -w net.core.rmem_max=212992
  host_console host_fastdds_udp${1#fast_udp} ;;
jury0_fast)  # README steps 0, 2-5 with the genuine Fast DDS player
  sudo sysctl -w net.core.rmem_max=33554432
  host_console host_jury_step0_fastdds
  sudo sysctl -w net.core.rmem_max=212992 ;;
shm_fast2)
  sudo sysctl -w net.core.rmem_max=212992
  host_console host_shm_fastdds2 -e RESENSE_DDS=shm ;;
shm_fastg)  # §4.6 with the genuine Fast DDS player
  sudo sysctl -w net.core.rmem_max=212992
  host_console host_shm_fastdds -e RESENSE_DDS=shm ;;
shm_fast)   # VM_GUIDE §4.6: the node with RESENSE_DDS=shm, rmem_max at Ubuntu's default, stock Fast DDS player
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
esac
