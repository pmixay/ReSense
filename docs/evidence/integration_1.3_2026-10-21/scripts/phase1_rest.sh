#!/bin/bash
# after the six caches: gate (4 trees) + ICP, then range jobs, then X3 (no commits during X3)
until grep -qE "SIX_DONE|FAIL|MISMATCH" /data/acc/six.log 2>/dev/null; do sleep 30; done
grep -q SIX_DONE /data/acc/six.log || { echo "SIX failed"; exit 1; }
echo "$(date -u +%T) gate+icp start"; /home/user/tools/gate4.sh > /data/acc/gate4_run.log 2>&1 & /home/user/tools/icp.sh > /data/acc/icp_run.log 2>&1; wait
echo "$(date -u +%T) range start"; /home/user/tools/range.sh > /data/acc/range_run.log 2>&1
echo "$(date -u +%T) x3 start"; /home/user/tools/x3.sh > /data/acc/x3_run.log 2>&1
echo "$(date -u +%T) PHASE1_REST_DONE"
