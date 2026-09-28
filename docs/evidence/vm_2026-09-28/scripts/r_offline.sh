#!/bin/bash
# docs/VM_GUIDE.md §5, steps 1-7 in one run inside tmux, nothing allowed out (no step 3b: the agent
# drives this VM over incoming SSH, which the block leaves open). Every rule is temporary.
. ~/r_env.sh
cd "$REPO" || exit 2
O=$EV/offline_$DAY${OFFLINE_SUB:+/$OFFLINE_SUB}; mkdir -p "$O"
# WARM=1: each recording is read once right before it is played, so the player reads it from the page cache
warm() { [ "${WARM:-0}" = "1" ] || return 0; for b in "$@"; do cat "$BAGS/$b"/*.db3 > /dev/null; done; echo "warmed: $* ($(free -g | awk '/Mem:/ {print $6}') GiB page cache)"; }
exec > >(tee -a "$O/steps.txt") 2>&1
step() { echo; echo "== $(date -u +%T) $*"; }

step "1. the restore script"
EXT_IF=$(ip route show default | awk '{ for (i = 1; i < NF; i++) if ($i == "dev") { print $(i + 1); exit } }')
echo "outbound interface: ${EXT_IF:?no default route: stop here}"
sudo tee /run/resense-restore.sh > /dev/null <<EOF
for t in iptables ip6tables; do
  while \$t -D OUTPUT -j RESENSE_OFFLINE 2>/dev/null; do :; done
  \$t -F RESENSE_OFFLINE 2>/dev/null; \$t -X RESENSE_OFFLINE 2>/dev/null
done
while iptables -D DOCKER-USER -o $EXT_IF -j REJECT 2>/dev/null; do :; done
echo "restored \$(date -Is)" >> /run/resense-restore.log
EOF

step "2. arm the restore timer (30 min)"
sudo systemd-run --on-active=30min --unit=resense-restore /bin/sh /run/resense-restore.sh
systemctl list-timers --all resense-restore.timer | grep -q resense-restore || { echo "timer not listed: stop"; exit 1; }
systemctl list-timers --all resense-restore.timer | head -n 2 | cut -c1-120

step "3. build the block"
for t in iptables ip6tables; do
  sudo $t -N RESENSE_OFFLINE
  sudo $t -A RESENSE_OFFLINE -o lo -j ACCEPT
  sudo $t -A RESENSE_OFFLINE -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
done
sudo iptables -A RESENSE_OFFLINE -d 224.0.0.0/4 -j ACCEPT
sudo iptables -A RESENSE_OFFLINE -d 169.254.169.254 -j ACCEPT
sudo iptables -A RESENSE_OFFLINE -p udp --dport 67:68 -j ACCEPT
sudo ip6tables -A RESENSE_OFFLINE -d fe80::/10 -j ACCEPT
sudo ip6tables -A RESENSE_OFFLINE -d ff00::/8 -j ACCEPT
echo "step 3b: not used (nothing allowed out)"

step "3c. switch it on"
for t in iptables ip6tables; do
  sudo $t -A RESENSE_OFFLINE -j REJECT
  sudo $t -I OUTPUT 1 -j RESENSE_OFFLINE
done
sudo iptables -I DOCKER-USER 1 -o "$EXT_IF" -j REJECT
date -u +"block on at %T" | tee "$O/window.txt"

step "4. check the block"
python3 scripts/check_no_network.py > "$O/check_no_network.txt" 2>&1
echo "check_no_network exit $?" | tee -a "$O/check_no_network.txt"
tail -n 3 "$O/check_no_network.txt"
curl -4 -sS -m 5 -o /dev/null https://github.com; echo "IPv4: curl exit $?"
curl -6 -sS -m 5 -o /dev/null https://ipv6.google.com; echo "IPv6: curl exit $?"
docker run --rm resense:latest python3 scripts/check_no_network.py > "$O/check_no_network_bridge_container.txt" 2>&1
echo "the same from a container on Docker's default bridge network: exit $?" | tee -a "$O/check_no_network_bridge_container.txt"
echo "waiting 60 s for the new-SSH-login test from outside"; sleep 60

step "5. the runs, offline"
docker image rm -f $(docker images -q resense | sort -u) 2>&1 | tail -n 3
docker images resense
ARCHIVE=$(ls -t dist/resense-image-*.tar.gz | head -n 1); echo "archive: $ARCHIVE"
warm doubleT_obstacle
IMAGE_TAR="$ARCHIVE" OFFLINE=1 OUT=out/off_obstacle ./scripts/dry_run.sh "$BAGS/doubleT_obstacle" 2>&1 | tee "$O/dry_obstacle.txt"
echo "exit ${PIPESTATUS[0]}" | tee -a "$O/dry_obstacle.txt"
warm roundT_doubleT
SKIP_BUILD=1 OFFLINE=1 OUT=out/off_clear ./scripts/dry_run.sh "$BAGS/roundT_doubleT" --expect-clear --max-alarm-frames 2 \
  2>&1 | tee "$O/dry_clear.txt"
echo "exit ${PIPESTATUS[0]}" | tee -a "$O/dry_clear.txt"
for r in off_obstacle off_clear; do
  cp "out/$r/node.log" "$O/${r}_node_log.txt"; gzip -c "out/$r/status.jsonl" > "$O/${r}_status.jsonl.gz"; done
echo "README «Кратко для жюри» steps 0, 2-5 from the host console (stock ROS 2 Humble, this user), offline"
warm roundT_doubleT doubleT_obstacle
D=$O ~/r_runs.sh jury
echo "README one-command variant: scripts/play_bag.sh <bag> --archive <archive>, offline"
docker image rm -f resense:latest > /dev/null 2>&1
warm doubleT_obstacle
scripts/play_bag.sh "$BAGS/doubleT_obstacle" --archive "$ARCHIVE" > "$O/play_bag_obstacle.txt" 2>&1
echo "play_bag exit $?" | tee -a "$O/play_bag_obstacle.txt"
sudo sysctl -w net.core.rmem_max=212992
grep -E "STOP|GO|CAUTION|FAULT" "$O/play_bag_obstacle.txt" | head -n 8

step "6. what tried to go out"
sudo iptables -L RESENSE_OFFLINE -v -n > "$O/rules_ipv4.txt"
sudo ip6tables -L RESENSE_OFFLINE -v -n > "$O/rules_ipv6.txt"
sudo iptables -L DOCKER-USER -v -n > "$O/rules_docker_user.txt"
cat "$O/rules_ipv4.txt" "$O/rules_ipv6.txt" "$O/rules_docker_user.txt"

step "7. restore"
sudo /bin/sh /run/resense-restore.sh; sudo systemctl stop resense-restore.timer
date -u +"block off at %T" | tee -a "$O/window.txt"
sudo iptables -L OUTPUT -n | grep -c RESENSE_OFFLINE; sudo iptables -L DOCKER-USER -n | grep -c REJECT
curl -sS -m 15 -o /dev/null -w 'github.com: %{http_code}\n' https://github.com
echo OFFLINE_DONE
