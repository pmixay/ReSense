#!/usr/bin/env bash
# One jury-chain run with the image's default command: node container (README step 2), the judge's
# listener (listener.py) and a player as uid 1000 from the same image (README step 3), all --net=host.
#   DATA=/home/user/data ./run_chain.sh <bag name> <out dir> [warm|cold]
#   PLAYER_ARGS=""  -> the organizers' literal `ros2 bag play <bag>` (Humble defaults)
#   NO_CLOUD=1      -> the listener does not subscribe to the input clouds
set -u
BAG=$1; OUT=$(realpath -m "$2"); MODE=${3:-warm}
DATA=${DATA:-/home/user/data}; HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"; chmod 777 "$OUT"
docker rm -f jnode jlisten jplay >/dev/null 2>&1
if [ "$MODE" = cold ]; then sync; echo 3 > /proc/sys/vm/drop_caches; fi
docker run -d --name jnode --net=host --ipc=host resense > /dev/null
docker run -d --name jlisten --net=host --ipc=host -e NO_CLOUD="${NO_CLOUD:-}" -v "$HERE":/judge -v "$OUT":/out \
    resense python3 /judge/listener.py /out/listen.jsonl > /dev/null
sleep 4
T0=$(date +%s.%N)
docker run --name jplay --user 1000:1000 --net=host -v "$DATA/for_hackathon":/data:ro -e HOME=/tmp resense \
    ros2 bag play "/data/$BAG" ${PLAYER_ARGS---delay 3 --read-ahead-queue-size 10} > "$OUT/player.log" 2>&1
T1=$(date +%s.%N)
sleep 4
docker logs jnode > "$OUT/node.log" 2>&1
docker rm -f jnode jlisten jplay > /dev/null 2>&1
echo "{\"bag\": \"$BAG\", \"mode\": \"$MODE\", \"t_play_start\": $T0, \"t_play_end\": $T1}" > "$OUT/run.json"
