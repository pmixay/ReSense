#!/bin/bash
# VM_GUIDE 2.3: stream the ride split by split into the gate cache (resumable)
cd /home/user/ReSense; . /data/work/env.sh
CACHE=/data/cache; SPOOL=/data/.ride_spool; mkdir -p "$CACHE/new_data" "$SPOOL"; export CACHE SPOOL
HREF=$(curl -fsS --get --data-urlencode "public_key=https://disk.yandex.ru/d/N8IUpAyd7jyvow" --data-urlencode "path=/new_data.zst" \
  https://cloud-api.yandex.net/v1/disk/public/resources/download | python3 -c 'import json, sys; print(json.load(sys.stdin)["href"])')
curl -fsSL "$HREF" | zstd -dc | tar -x --wildcards '*.db3' --to-command='
  f="$SPOOL/$(basename "$TAR_FILENAME")"; name=$(basename "$f" .db3)
  if [ -f "$CACHE/new_data/${name}_stamps.json" ]; then cat > /dev/null; exit 0; fi
  cat > "$f" && python scripts/cache_frames.py "$f" "$CACHE/new_data" --every 1 --int16 --stamps
  rc=$?; rm -f "$f"; exit $rc'
echo "tar exit $?"; ls "$CACHE"/new_data/*_stamps.json | wc -l; echo RIDE_DONE
