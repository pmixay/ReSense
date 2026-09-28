#!/bin/bash
# VM_GUIDE §2.3: the ride, split by split (resumable)
. ~/r_env.sh; cd "$REPO"
SPOOL=$DATA/.ride_spool
mkdir -p "$CACHE/new_data" "$SPOOL"
export CACHE SPOOL
for attempt in 1 2 3; do
  HREF=$(curl -fsS --get \
    --data-urlencode "public_key=https://disk.yandex.ru/d/N8IUpAyd7jyvow" \
    --data-urlencode "path=/new_data.zst" \
    https://cloud-api.yandex.net/v1/disk/public/resources/download \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["href"])')
  curl -fsSL "$HREF" | zstd -dc | tar -x --wildcards '*.db3' --to-command='
    f="$SPOOL/$(basename "$TAR_FILENAME")"; name=$(basename "$f" .db3)
    if [ -f "$CACHE/new_data/${name}_stamps.json" ]; then cat > /dev/null; exit 0; fi
    cat > "$f" && python scripts/cache_frames.py "$f" "$CACHE/new_data" --every 1 --int16 --stamps
    rc=$?; rm -f "$f"; exit $rc'
  echo "attempt $attempt: pipe status ${PIPESTATUS[*]}"
  n=$(ls "$CACHE"/new_data/*_stamps.json 2>/dev/null | wc -l); echo "splits cached: $n"
  [ "$n" -ge 221 ] && break
done
echo DATA_B_DONE
