#!/bin/bash
# after the six caches: gate (5 trees) + ICP, then range jobs (final tree, same placement both ways), then X3 (final
# tree against a fresh v1.2.0 battery; no commits during X3)
until grep -qE "SIX_DONE|FAIL|MISMATCH" /data/acc/six.log 2>/dev/null; do sleep 30; done
grep -q SIX_DONE /data/acc/six.log || { echo "SIX failed"; exit 1; }
until grep -q FIN_PANDAR_DONE /data/acc/fin_pandar.log 2>/dev/null; do sleep 30; done
echo "$(date -u +%T) gate+icp start"
TREES="ctl:/home/user/wt/base k2:/home/user/wt/k2 preg2:/home/user/wt/preg2 comb:/home/user/wt/comb fin:/home/user/wt/fin" /home/user/tools/gate4.sh > /data/acc/gate4_run.log 2>&1 &
/home/user/tools/icp.sh > /data/acc/icp_run.log 2>&1; wait
echo "$(date -u +%T) range start"; RANGE_CAND=/home/user/wt/fin RANGE_NAME=fin /home/user/tools/range.sh > /data/acc/range_run.log 2>&1
echo "$(date -u +%T) x3 start"; touch /data/acc/X3_RUNNING; X3_CAND=/home/user/wt/fin X3_NAME=fin /home/user/tools/x3.sh > /data/acc/x3_run.log 2>&1; rm -f /data/acc/X3_RUNNING
echo "$(date -u +%T) REST_DONE"
