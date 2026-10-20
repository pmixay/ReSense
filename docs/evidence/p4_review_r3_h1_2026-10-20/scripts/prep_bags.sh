#!/bin/bash
# Unpack each of the six recordings from the verified dataset.zip, cache it for the gate (int16 + stamps,
# every frame) and, for the four X3 bags, node-decode it (judge cache_decoded.py); then delete the bag.
# The next bag is unpacked while the previous one is cached.
set -u
W=/home/user/wt_ship; D=/home/user/data
export PATH=/home/user/venv/rs/bin:$PATH OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=1 RESENSE_REPO=$W
export PYTHONPATH=$W:$W/ros2_ws/src/resense_ros
X3=" squareT_platform_squareT_switch doubleT_obstacle roundT_squareT_pressureGate_squareT "
BAGS="doubleT_obstacle squareT_platform_squareT_switch roundT_squareT_pressureGate_squareT doubleT_platform roundT_doubleT roundT_pressureGate_roundT"
process() {
  b=$1
  ( cd $W && python scripts/cache_frames.py $D/for_hackathon/$b $D/cache/$b --every 1 --int16 --stamps ) > $D/logs/cache_$b.log 2>&1 &
  p1=$!
  if [[ "$X3" == *" $b "* ]]; then
    ( cd $W && python docs/evidence/judgement_2026-10-13/scripts/cache_decoded.py $D/for_hackathon/$b $D/decoded/$b ) > $D/logs/decoded_$b.log 2>&1
    echo "decoded $b exit $?"
  fi
  wait $p1; echo "cache $b exit $?"
  cmp $D/for_hackathon/$b/metadata.yaml $W/docs/evidence/bag_metadata/${b}_metadata.yaml && echo "$b metadata original"
  rm -rf "$D/for_hackathon/$b"; echo "done $b $(date -u +%T)"
}
prev=""
for b in $BAGS; do
  ( cd $W && python scripts/unpack_dataset.py $D/dataset.zip --out $D --only $b ) > $D/logs/unpack_$b.log 2>&1
  echo "unpacked $b exit $? $(date -u +%T)"
  [ -n "$prev" ] && wait $pp
  process $b > $D/logs/process_$b.log 2>&1 &
  pp=$!; prev=$b
done
wait
echo PREP_DONE $(date -u +%T)
