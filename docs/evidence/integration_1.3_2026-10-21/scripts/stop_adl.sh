#!/bin/bash
for d in /proc/[0-9]*; do a=$(tr '\0' ' ' < $d/cmdline 2>/dev/null)
  case "$a" in "python3 /home/user/tools/adaptive_dl.py "*) echo "kill ${d#/proc/}"; kill ${d#/proc/};; esac; done
