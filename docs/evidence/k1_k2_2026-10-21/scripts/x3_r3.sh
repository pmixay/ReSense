#!/bin/bash
. /data/work/env.sh
(setrepo /opt/cand3; cd /opt/cand3; python scripts/robustness_battery.py --repo /opt/cand3 --cache /data/decoded --out /data/acc/x3/cand.json -j 2 --reference /data/acc/r1/x3/control.json > /data/acc/x3/cand.log 2>&1; echo "cand exit $?")
echo X3_DONE
