#!/bin/bash
# X3: fresh control battery, then the candidate against it (no commits to these trees during the run)
. /data/work/env.sh
(setrepo /opt/base; cd /opt/base; python scripts/robustness_battery.py --repo /opt/base --cache /data/decoded --out /data/acc/x3/control.json -j 2 > /data/acc/x3/control.log 2>&1; echo "control exit $?")
(setrepo /opt/cand1; cd /opt/cand1; python scripts/robustness_battery.py --repo /opt/cand1 --cache /data/decoded --out /data/acc/x3/cand.json -j 2 --reference /data/acc/x3/control.json > /data/acc/x3/cand.log 2>&1; echo "cand exit $?")
echo X3_DONE
