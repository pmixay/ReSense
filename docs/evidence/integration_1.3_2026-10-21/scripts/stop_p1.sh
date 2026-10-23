#!/bin/bash
for d in /proc/[0-9]*; do a=$(tr '\0' ' ' < $d/cmdline 2>/dev/null)
  case "$a" in "/bin/bash /home/user/tools/phase1_rest.sh"*) echo "kill ${d#/proc/}"; kill ${d#/proc/};; esac; done
