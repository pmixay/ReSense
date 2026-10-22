#!/bin/bash
# log the far-range review branch head every 15 min; a change is appended to /data/acc/poll_far.log
cd /home/user/ReSense; last=""
while true; do
  h=$(git ls-remote origin claude/falcon-far-range-review-1.3 2>/dev/null | cut -c1-12)
  [ -n "$h" ] && [ "$h" != "$last" ] && { echo "$(date -u +%FT%T) review head $h" >> /data/acc/poll_far.log; last=$h; }
  sleep 900
done
