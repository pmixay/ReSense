#!/bin/bash
# VM_GUIDE §3-§4 runs for the §4.0 confirmation re-run: g_runs.sh facts|stage|dry|console|host|bench|export
# Playback reads the two original bags from a RAM tmpfs copy ($B; the VM disk reads ~64 MB/s,
# the 360° bag plays at ~220 MB/s); the caches stay in $CACHE.
. ~/g_env.sh
cd "$REPO"
B=/mnt/ramdata/for_hackathon
D="$EV/dry_run_$DAY"
mkdir -p "$D"
case "$1" in
facts)  # §3
  mkdir -p "$EV/vm_$DAY"
  { lscpu; free -h; df -h "$DATA" /var/lib/docker; uname -a; docker version; vmstat 1 5; git -C "$REPO" rev-parse HEAD; \
    sysctl net.core.rmem_max net.core.rmem_default; } > "$EV/vm_$DAY/machine.txt" 2>&1
  git status --short --untracked-files=no; git rev-parse --short HEAD ;;
stage)  # the two original bags into RAM, checked against the committed metadata
  mountpoint -q /mnt/ramdata || { sudo mkdir -p /mnt/ramdata && sudo mount -t tmpfs -o size=7G,mode=0755 tmpfs /mnt/ramdata && sudo chown "$(id -u):$(id -g)" /mnt/ramdata; }
  mkdir -p "$B"
  for b in doubleT_obstacle roundT_doubleT; do
    [ -d "$B/$b" ] || cp -r "$BAGS/$b" "$B/"
    cmp "$B/$b/metadata.yaml" "docs/evidence/bag_metadata/${b}_metadata.yaml" && echo "$b original"
    cmp "$B/$b/${b}_0.db3" "$BAGS/$b/${b}_0.db3" && echo "$b copy identical"
  done
  chmod -R a+rX "$B" ;;
dry)    # §4.1 (the first build on this VM, --no-cache), then the replay of §4.0
  OUT=out/dry_obstacle ./scripts/dry_run.sh "$B/doubleT_obstacle" 2>&1 | tee "$D/dry_obstacle.txt"
  echo "exit ${PIPESTATUS[0]}" | tee -a "$D/dry_obstacle.txt"
  SKIP_BUILD=1 OUT=out/dry_clear ./scripts/dry_run.sh "$B/roundT_doubleT" --expect-clear --max-alarm-frames 2 \
    2>&1 | tee "$D/dry_clear.txt"
  echo "exit ${PIPESTATUS[0]}" | tee -a "$D/dry_clear.txt"
  python scripts/replay_node_frames.py out/dry_clear/status.jsonl --bag "$B/roundT_doubleT" 2>&1 | tee "$D/replay_dry_clear.txt"
  echo "exit ${PIPESTATUS[0]}" | tee -a "$D/replay_dry_clear.txt" ;;
console) # §4.2, the stock player in Docker
  PLAYER_DDS=stock OUT=out/ct_stock ./scripts/console_test.sh "$B/roundT_doubleT" "$B/doubleT_obstacle" -- \
    --expect-obstacle --obstacle-in 2 --expect-inputs 2 --min-frames 20 --max-p95-latency 1000 --max-dropped 100000 \
    2>&1 | tee "$D/ct_stock.txt"
  echo "exit ${PIPESTATUS[0]}" | tee -a "$D/ct_stock.txt" ;;
host)   # §4.2 host console as the jury does it; $2 = fastdds | cyclonedds
  RMW=$2; T=${TAG:+_$TAG}; O=out/host_$RMW$T; N=resense_node; mkdir -p "$O"; rm -f "$O"/*
  docker rm -f $N >/dev/null 2>&1
  docker run -d --name $N --net=host --ipc=host ${NODE_ARGS:-} resense:latest >/dev/null   # console 1: the node, no arguments (NODE_ARGS: diagnostics only)
  for _ in $(seq 1 60); do docker logs $N 2>&1 | grep -q "ReSense detector listening" && break; sleep 1; done
  set +u; source /opt/ros/humble/setup.bash
  unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE RMW_FASTRTPS_USE_QOS_FROM_XML RMW_IMPLEMENTATION
  [ "$RMW" = cyclonedds ] && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  ros2 topic echo /resense/decision --field data > "$O/decision.txt" 2>/dev/null & DEC=$!    # console 3
  ros2 topic echo /resense/status --field data > "$O/status.jsonl" 2>/dev/null & ECHO=$!     # console 2
  sleep 4
  { ros2 bag play "$B/roundT_doubleT" --delay 3 --disable-keyboard-controls && sleep 5 &&
    ros2 bag play "$B/doubleT_obstacle" --delay 3 --disable-keyboard-controls; } > "$O/player_log.txt" 2>&1
  sleep 3; kill "$ECHO" "$DEC"; wait "$ECHO" "$DEC" 2>/dev/null
  docker logs $N > "$O/node.log" 2>&1; docker rm -f $N >/dev/null
  { [ -n "${NODE_ARGS:-}" ] && echo "DIAGNOSTIC: node started with extra docker arguments: $NODE_ARGS"
    echo "host console: $(id -un) uid $(id -u), RMW ${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp (default)}, no Fast DDS profile;" \
         "net.core.rmem_max $(sysctl -n net.core.rmem_max), rmem_default $(sysctl -n net.core.rmem_default)"
    echo "decisions seen: $(grep -v -- '^---$' "$O/decision.txt" | sort | uniq -c | tr '\n' ' ')"
    grep -E "WARN|rmem" "$O/node.log" | cut -c1-240 | head -5
    python3 scripts/check_dry_run.py "$O/status.jsonl" --expect-obstacle --obstacle-in 2 --expect-inputs 2 \
      --min-frames 20 --max-p95-latency 1000 --max-dropped 100000
    echo "exit $?"; } 2>&1 | tee "${HOST_OUT:-$D}/host_console_$RMW$T.txt" ;;
bench)  # §4.3
  RESENSE_DATA="$B" RESENSE_CACHE="$CACHE" ./scripts/bench_8core.sh; echo "exit $?" ;;
export) # §4.5
  ./scripts/export_image.sh; echo "export exit $?"
  ARCHIVE=$(ls -t dist/resense-image-*.tar.gz | head -n 1)
  ./scripts/load_image.sh "$ARCHIVE"; echo "load exit $?"
  mkdir -p "$EV/export_$DAY"
  { ls -l "$ARCHIVE"; cat "$ARCHIVE.sha256"; git rev-parse HEAD; docker image inspect -f '{{.Size}}' resense:latest; } \
    > "$EV/export_$DAY/archive.txt"
  cat "$EV/export_$DAY/archive.txt" ;;
esac
