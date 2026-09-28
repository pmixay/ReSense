#!/bin/bash
# The 28.09 runs in order (VM_GUIDE §3-§4.5), each logged to ~/logs/r_<step>.log; one summary line per step
for s in facts dry fastinput "cold _1" "warm _1" "cold _2" "warm _2" ct_stock jury host_fastdds host_cyclonedds \
         shm_fast shm_cyclone ct_shm bench gate export; do
  n=${s// /}
  echo "$(date -u +%T) == $n"
  ~/r_runs.sh $s > ~/logs/r_$n.log 2>&1
  echo "$(date -u +%T) $n: $(grep -hE '^(PASS|FAIL)|^exit|build exit|RMW loaded|replay|equal' ~/logs/r_$n.log | cut -c1-160 | tr '\n' ' ')"
done
sysctl net.core.rmem_max
echo CHAIN_DONE
