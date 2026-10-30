#!/bin/bash
# the ride intake, resumed until complete (each run reuses validated splits)
. /home/user/venv/bin/activate; cd /home/user/ReSense
for k in 1 2 3 4 5 6 7 8; do
  python scripts/cache_extended_ride.py --cache /data/cache/new_data --spool /data/.ride_spool --reserve-gib 3 >> /data/acc/ride_intake.log 2>&1
  rc=$?; echo "attempt $k exit $rc" >> /data/acc/ride_intake.log; [ $rc -eq 0 ] && break; sleep 30
done
echo INTAKE_END >> /data/acc/ride_intake.log
