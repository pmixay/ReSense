#!/usr/bin/env bash
# Jury chain in Docker: node (image default command) -> ros2 bag play from a second container (uid 1000,
# as a normal console user) -> listener container recording /resense/status, /resense/decision, latency.
#   chain.sh <image> <bag_parent_dir> <bag_name> <label> [ros2 bag play options...]
# Writes out/docker/<label>.jsonl (listener), <label>.node.log, <label>.stats (docker stats every ~1 s),
# <label>.play.log and <label>.meta (wall times).
set -u
IMG=$1; PARENT=$2; NAME=$3; LABEL=$4; shift 4
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$HERE/../.." && pwd)/out/docker"
mkdir -p "$OUT"
docker rm -f rs_node rs_lis >/dev/null 2>&1
NODE_ARGS=${NODE_ARGS:-}
if [ -n "$NODE_ARGS" ]; then
  docker run -d --name rs_node --net=host --ipc=host "$IMG" ros2 launch resense_ros detector.launch.py $NODE_ARGS >/dev/null
else
  docker run -d --name rs_node --net=host --ipc=host "$IMG" >/dev/null
fi
t0=$(date +%s.%N)
for i in $(seq 1 120); do docker logs rs_node 2>&1 | grep -q "listening on" && break; sleep 1; done
t_ready=$(date +%s.%N)
docker run -d --name rs_lis --net=host -v "$HERE":/jl:ro -v "$OUT":/out "$IMG" \
  python3 /jl/listener.py --out /out/$LABEL.jsonl --seconds 900 >/dev/null
sleep 4
( while docker inspect rs_node >/dev/null 2>&1; do
    docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' rs_node 2>/dev/null | sed "s/^/$(date +%s.%N) /"
  done ) > "$OUT/$LABEL.stats" 2>/dev/null &
SP=$!
t_play=$(date +%s.%N)
docker run --rm --net=host --user 1000:1000 -e HOME=/tmp -v "$PARENT":/data:ro "$IMG" ros2 bag play /data/$NAME "$@" > "$OUT/$LABEL.play.log" 2>&1
t_end=$(date +%s.%N)
sleep 4
docker stop -t 5 rs_lis >/dev/null 2>&1
docker logs rs_node > "$OUT/$LABEL.node.log" 2>&1
docker stop -t 5 rs_node >/dev/null 2>&1
kill $SP 2>/dev/null
docker rm -f rs_node rs_lis >/dev/null 2>&1
echo "{\"t_start\": $t0, \"t_ready\": $t_ready, \"t_play\": $t_play, \"t_end\": $t_end, \"play_args\": \"$*\"}" > "$OUT/$LABEL.meta"
echo "$LABEL: node ready $(echo "$t_ready - $t0" | bc) s, play $(echo "$t_end - $t_play" | bc) s"
