#!/bin/bash
# stop running range downloaders (args start with the interpreter and the script path)
for d in /proc/[0-9]*; do
  a=$(tr '\0' ' ' < $d/cmdline 2>/dev/null)
  case "$a" in "/bin/bash /home/user/tools/range_dl.sh "*) echo "kill ${d#/proc/}"; kill ${d#/proc/};; esac
done
