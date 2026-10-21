#!/usr/bin/env bash
# One trial: one node, the recorder, `ros2 bag play` of BAG at RATE. Own DDS domain; containers removed at the end.
# trial.sh LABEL RATE BAG PROFILE POLICY IMAGE OUTDIR [--no-input-sub]
set -uo pipefail
LABEL=$1 RATE=$2 BAG=$3 PROFILE=$4 POLICY=$5 IMAGE=$6 OUT=$7 ; NOSUB=${8:-}
D=$OUT/$LABEL; mkdir -p "$D"; chmod 777 "$D"; rm -f "$D"/*
export_dom="-e ROS_DOMAIN_ID=${DOM:-87}"
NODE=rsd_node_$LABEL REC=rsd_rec_$LABEL PL=rsd_player_$LABEL
HERE=$(cd "$(dirname "$0")" && pwd)
cleanup() { docker rm -f $NODE $REC $PL >/dev/null 2>&1; kill ${SAMP:-0} 2>/dev/null; }
trap cleanup EXIT
docker run -d --name $NODE --net=host --ipc=host $export_dom "$IMAGE" ros2 launch resense_ros detector.launch.py \
  freshness_mode:=replay clear_range_policy:=$POLICY >/dev/null
for i in $(seq 1 120); do docker logs $NODE 2>&1 | grep -q 'ReSense detector listening on' && break; sleep 0.5; done
docker logs $NODE 2>&1 | grep -q 'ReSense detector listening on' || { echo "node did not start"; docker logs $NODE | tail; exit 3; }
SUBTOPIC=${IN_TOPIC:-/iv_points}
docker run -d --name $REC --net=host --ipc=host --user 1000:1000 -e HOME=/tmp $export_dom -v "$D":/rec -v "$HERE":/h:ro "$IMAGE" \
  python3 -u /h/recorder.py /rec/events.jsonl $( [ "$NOSUB" = "--no-input-sub" ] && echo /nonexistent_topic || echo $SUBTOPIC ) >/dev/null
for i in $(seq 1 60); do [ -f "$D/ready" ] && break; sleep 0.5; done
[ -f "$D/ready" ] || { echo "recorder not ready"; docker logs $REC | tail; exit 3; }
sleep 3   # let discovery settle
docker exec $export_dom $NODE /entrypoint.sh python3 /opt/resense/scripts/reset_replay.py --profile "$PROFILE" | tee "$D/reset.txt"
( while true; do echo "$(date +%s.%N) $(docker stats --no-stream --format '{{.MemUsage}} {{.CPUPerc}}' $NODE 2>/dev/null)"; done ) > "$D/docker_stats.txt" &
SAMP=$!
T0=$(date +%s.%N); echo "player_cmd_start $T0" > "$D/times.txt"
docker run --rm --name $PL --net=host --ipc=host --user 1000:1000 -e HOME=/tmp $export_dom -v "$BAG":/data/bag:ro "$IMAGE" \
  ros2 bag play /data/bag --rate "$RATE" --delay 3 --read-ahead-queue-size 10 --disable-keyboard-controls > "$D/player.log" 2>&1
echo "player_exit $? $(date +%s.%N)" >> "$D/times.txt"
sleep 8   # let the node finish what it holds
echo "end $(date +%s.%N)" >> "$D/times.txt"
kill $SAMP 2>/dev/null
docker logs $NODE > "$D/node.log" 2>&1
docker logs $REC > "$D/recorder.log" 2>&1
docker rm -f $NODE $REC $PL >/dev/null 2>&1
wc -l "$D/events.jsonl"
