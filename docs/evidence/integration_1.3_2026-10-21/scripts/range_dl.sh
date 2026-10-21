#!/bin/bash
# range_dl.sh <url> <out> <total_bytes> [chunk_MB]: ranged download with resume (Drive serves 206 ranges
# when a whole-file request is refused for quota)
set -u
URL=$1; OUT=$2; TOTAL=$3; CH=$(( ${4:-64} * 1048576 ))
touch "$OUT"
while :; do
  have=$(stat -c %s "$OUT"); [ "$have" -ge "$TOTAL" ] && break
  end=$(( have + CH - 1 )); [ $end -ge $TOTAL ] && end=$(( TOTAL - 1 ))
  for t in $(seq 1 100000); do
    if curl -fsSL -m 600 -r ${have}-${end} -o "$OUT.part" "$URL"; then
      n=$(stat -c %s "$OUT.part"); want=$(( end - have + 1 ))
      if [ "$n" -eq "$want" ] && ! head -c 15 "$OUT.part" | grep -q "<!DOCTYPE"; then cat "$OUT.part" >> "$OUT"; break; fi
      echo "bad chunk at $have: $n bytes"
    fi
    sleep 180
  done
  [ "$(stat -c %s "$OUT")" -eq "$have" ] && { echo "FAILED at $have"; exit 1; }
  echo "$(date -u +%T) $(stat -c %s "$OUT")"
done
rm -f "$OUT.part"; echo DONE
