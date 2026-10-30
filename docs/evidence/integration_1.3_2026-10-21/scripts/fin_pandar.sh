#!/bin/bash
export TREES="fin:/home/user/wt/fin" LAST=fin
[ -s /data/acc/markers/fin_switch.jsonl ] || { /home/user/tools/markers.sh > /data/acc/markers_fin_run.log 2>&1; rm -f /data/markers.zst; }
grep -q "exit 0" /data/acc/ride/fin.log 2>/dev/null || { rm -rf /data/acc/ride/fin; /home/user/tools/ride_rows.sh > /data/acc/ride_fin_run.log 2>&1; }
grep -q "exit 0" /data/acc/setO_rows/fin.log 2>/dev/null || { rm -rf /data/acc/setO_rows/fin; /home/user/tools/setO_rows.sh > /data/acc/setO_fin_run.log 2>&1; }
echo FIN_PANDAR_DONE
