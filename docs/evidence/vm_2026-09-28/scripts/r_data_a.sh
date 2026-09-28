#!/bin/bash
# VM_GUIDE §2.1 + §2.2: the six recordings (all kept: disk allows) and set O
. ~/r_env.sh; cd "$REPO"; set -x
mkdir -p "$CACHE"
if [ ! -d "$BAGS/doubleT_platform" ] || [ ! -d "$BAGS/squareT_platform_squareT_switch" ]; then
  [ -s "$DATA/dataset.zip" ] || curl -fL -sS --retry 5 --retry-delay 5 --connect-timeout 30 -o "$DATA/dataset.zip" \
    "https://drive.usercontent.google.com/download?id=1WTlR2wDSuEHTOARGK_gZeXDTZ9RZpswu&export=download&confirm=t"
  head -c 2 "$DATA/dataset.zip"; echo
  ls -l "$DATA/dataset.zip"
  python scripts/unpack_dataset.py "$DATA/dataset.zip" --out "$DATA" \
    --only doubleT_platform,roundT_pressureGate_roundT,roundT_squareT_pressureGate_squareT,squareT_platform_squareT_switch || exit 1
fi
chmod -R a+rX "$BAGS"
for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT \
         roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do
  [ -f "$CACHE/$b/_stamps.json" ] || ls "$CACHE/$b"/*stamps.json >/dev/null 2>&1 || \
    python scripts/cache_frames.py "$BAGS/$b" "$CACHE/$b" --every 1 --int16 --stamps
done
if [ ! -d "$CACHE/cloud_with_fake_obj" ]; then
  [ -d "$DATA/cloud_with_fake_obj" ] || python scripts/unpack_dataset.py https://disk.yandex.ru/d/KpkG_yKoGk-vHQ --out "$DATA"
  python scripts/cache_frames.py "$DATA/cloud_with_fake_obj" "$CACHE/cloud_with_fake_obj" --every 1 --int16 --stamps
fi
for b in doubleT_obstacle doubleT_platform roundT_doubleT roundT_pressureGate_roundT roundT_squareT_pressureGate_squareT squareT_platform_squareT_switch; do cmp "$BAGS/$b/metadata.yaml" "docs/evidence/bag_metadata/${b}_metadata.yaml" && echo "$b original"; done
echo DATA_A_DONE
