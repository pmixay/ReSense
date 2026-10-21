#!/bin/bash
# stream the ride archive and cache only the first N split files, then stop (a stated sample of the ride)
N=${1:-3}
cd /home/user/ReSense; . /home/user/venv/bin/activate
export CACHE=/home/user/data/cache SPOOL=/home/user/data/.ride_spool N
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/N8IUpAyd7jyvow" --data-urlencode "path=/new_data.zst" https://cloud-api.yandex.net/v1/disk/public/resources/download | python3 -c 'import json, sys; print(json.load(sys.stdin)["href"])')
curl -fsSL "$HREF" | python3 /home/user/rv/s/zstdcat.py | tar -x --wildcards '*.db3' --to-command='
  f="$SPOOL/$(basename "$TAR_FILENAME")"; name=$(basename "$f" .db3)
  n=$(ls "$CACHE"/new_data/*_stamps.json 2>/dev/null | wc -l)
  if [ "$n" -ge "$N" ]; then exit 3; fi
  cat > "$f" && python scripts/cache_frames.py "$f" "$CACHE/new_data" --every 1 --int16 --stamps
  rc=$?; rm -f "$f"; echo cached $name rc=$rc >&2; exit $rc'
echo RIDEDONE
