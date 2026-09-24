#!/usr/bin/env bash
# Screen-record the jury chain with RViz (how docs/video/docker_chain_rviz.mp4 was made, 23.09):
# the node container with rviz:=true, /resense/decision echoed from a second container, the bag
# played as a normal user (uid 1000) from a third - every command shown in the console window is
# the command that runs. Works headless on a virtual display (Xvfb, software OpenGL), or on a
# real one with DISPLAY set and NO_XVFB=1.
#
#   scripts/record_rviz_chain.sh <bag dir> [rate]      # e.g. <bags>/doubleT_obstacle 0.5
#   OUT=out/rviz_chain  IMAGE=resense                   # output folder (chain_raw.mp4, node.log), image
#
# Needs: docker, the resense image, Xvfb (unless NO_XVFB=1), xterm, xdotool, ffmpeg.
# On 4 vCPU with software rendering the 360-degree bag was played at 0.5x (RViz renders the cloud
# at 6-10 fps on the same cores); captions were burnt in afterwards with ffmpeg drawtext.
set -uo pipefail
BAG="${1:?usage: scripts/record_rviz_chain.sh <bag dir> [rate]}"; RATE="${2:-0.5}"
BAG_DIR="$(cd "$(dirname "$BAG")" && pwd)"; BAG_NAME="$(basename "$BAG")"
OUT="${OUT:-out/rviz_chain}"; IMAGE="${IMAGE:-resense}"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
if [ "${NO_XVFB:-0}" != "1" ]; then
  export DISPLAY=:99
  Xvfb :99 -screen 0 1920x1080x24 -ac -nolisten tcp >/dev/null 2>&1 &
  XVFB=$!; sleep 2
fi
docker rm -f resense resense_echo >/dev/null 2>&1
rm -f "$OUT/done"

cat > "$OUT/console.sh" <<CONSOLE
say() { printf '\n\033[1;32m\$\033[0m \033[1;37m%s\033[0m\n' "\$1"; sleep 1.2; }
say "docker run -d --name resense --net=host --ipc=host -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix $IMAGE ros2 launch resense_ros detector.launch.py rviz:=true"
docker run -d --name resense --net=host --ipc=host -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix $IMAGE ros2 launch resense_ros detector.launch.py rviz:=true | cut -c1-12
for _ in \$(seq 1 60); do docker logs resense 2>&1 | grep -q "detector listening" && break; sleep 0.5; done
for _ in \$(seq 1 40); do xdotool search --name " - RViz" >/dev/null 2>&1 && break; sleep 0.5; done
sleep 1
xdotool search --name " - RViz" | head -1 | xargs -I{} xdotool windowmove {} 0 0 windowsize {} 1920 776
docker logs resense 2>&1 | grep -o "ReSense detector listening.*" | cut -c1-118
say "docker run --rm --net=host --ipc=host $IMAGE ros2 topic echo /resense/decision --field data    # right"
xterm -geometry 117x18+964+782 -fa 'DejaVu Sans Mono' -fs 10 -bg '#0d0f14' -fg '#ffd166' -title decision \
  -e docker run --rm --name resense_echo --net=host --ipc=host $IMAGE ros2 topic echo /resense/decision --field data &
sleep 5
say "docker run --rm --net=host --ipc=host --user 1000:1000 -e HOME=/tmp -v <bags>:/data:ro $IMAGE ros2 bag play /data/$BAG_NAME --delay 3 --rate $RATE"
docker run --rm --net=host --ipc=host --user 1000:1000 -e HOME=/tmp -v "$BAG_DIR":/data:ro $IMAGE \
  ros2 bag play /data/$BAG_NAME --delay 3 --rate $RATE --disable-keyboard-controls 2>&1 | cut -c1-118
sleep 4
say "docker logs resense 2>&1 | grep -m2 -o 'input 1:.*'"
docker logs resense 2>&1 | grep -m2 -o "input 1:.*" | cut -c1-118
sleep 5
touch "$OUT/done"
sleep 30
CONSOLE

xterm -geometry 117x18+0+782 -fa 'DejaVu Sans Mono' -fs 10 -bg '#0d0f14' -fg '#d8dee9' -title console \
  -e bash "$OUT/console.sh" &
XT=$!
sleep 1
ffmpeg -loglevel error -y -f x11grab -framerate 10 -video_size 1920x1080 -i "$DISPLAY" \
  -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p "$OUT/chain_raw.mp4" &
FF=$!
for _ in $(seq 1 600); do [ -f "$OUT/done" ] && break; sleep 0.5; done
kill -INT $FF; wait $FF
docker logs resense > "$OUT/node.log" 2>&1
docker rm -f resense resense_echo >/dev/null 2>&1
kill $XT 2>/dev/null
[ -n "${XVFB:-}" ] && kill $XVFB 2>/dev/null
echo "recorded: $OUT/chain_raw.mp4 ($OUT/node.log)"
