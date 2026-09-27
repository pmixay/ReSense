#!/bin/sh
# ReSense offline rehearsal: restore outbound network. Idempotent. Written by scripts/vm/run_plan.sh.
# By hand, if ever needed:  sudo sh /var/lib/resense-offline/restore.sh     (a reboot also clears the block: it is never saved)
for T in iptables ip6tables; do
  command -v "$T" >/dev/null 2>&1 || continue
  while "$T" -w -D OUTPUT -j RESENSE_OFFLINE 2>/dev/null; do :; done
  while "$T" -w -D DOCKER-USER -j RESENSE_OFFLINE_FWD 2>/dev/null; do :; done
  for C in RESENSE_OFFLINE RESENSE_OFFLINE_FWD; do "$T" -w -F "$C" 2>/dev/null; "$T" -w -X "$C" 2>/dev/null; done
done
mkdir -p /var/lib/resense-offline && echo "$(date -Is) restored (${1:-by hand})" >> /var/lib/resense-offline/history.txt
[ "${1:-}" = timer ] || systemctl stop resense-offline-restore.timer 2>/dev/null
exit 0
