#!/bin/sh
# ReSense offline rehearsal: block outbound traffic from this host (and from Docker bridge
# networks), keep loopback, established connections (the SSH sessions), replies of sshd (ports:
# 22 ), DDS discovery multicast, the cloud metadata service and DHCP.
set -e
C=RESENSE_OFFLINE
iptables -w -N $C 2>/dev/null || iptables -w -F $C
iptables -w -A $C -o lo -j ACCEPT
iptables -w -A $C -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
for p in 22 ; do iptables -w -A $C -p tcp --sport "$p" -j ACCEPT; done
iptables -w -A $C -d 224.0.0.0/4 -j ACCEPT
iptables -w -A $C -d 169.254.169.254/32 -j ACCEPT
iptables -w -A $C -p udp --dport 67:68 -j ACCEPT

iptables -w -A $C -m limit --limit 30/min -j LOG --log-prefix "RESENSE-OFFLINE " --log-uid   || iptables -w -A $C -m limit --limit 30/min -j LOG --log-prefix "RESENSE-OFFLINE " || true
iptables -w -A $C -p tcp -j REJECT --reject-with tcp-reset
iptables -w -A $C -j REJECT
iptables -w -C OUTPUT -j $C 2>/dev/null || iptables -w -I OUTPUT 1 -j $C
if iptables -w -n -L DOCKER-USER >/dev/null 2>&1 && [ -n "eth0" ]; then
  F=RESENSE_OFFLINE_FWD
  iptables -w -N $F 2>/dev/null || iptables -w -F $F
  iptables -w -A $F -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
  iptables -w -A $F -o eth0 -j REJECT
  iptables -w -C DOCKER-USER -j $F 2>/dev/null || iptables -w -I DOCKER-USER 1 -j $F
fi
# IPv6 in a subshell: if it cannot be applied, the IPv4 block stays and the check that follows
# (scripts/check_no_network.py) still fails the rehearsal when IPv6 reaches the internet
if command -v ip6tables >/dev/null 2>&1 && ip6tables -w -n -L OUTPUT >/dev/null 2>&1; then (
  set -e
  ip6tables -w -N $C 2>/dev/null || ip6tables -w -F $C
  ip6tables -w -A $C -o lo -j ACCEPT
  ip6tables -w -A $C -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  for p in 22 ; do ip6tables -w -A $C -p tcp --sport "$p" -j ACCEPT; done
  ip6tables -w -A $C -p ipv6-icmp -j ACCEPT
  ip6tables -w -A $C -d ff00::/8 -j ACCEPT
  ip6tables -w -A $C -d fe80::/10 -j ACCEPT
  ip6tables -w -A $C -p udp --dport 546:547 -j ACCEPT
  ip6tables -w -A $C -m limit --limit 30/min -j LOG --log-prefix "RESENSE-OFFLINE6 " || true
  ip6tables -w -A $C -j REJECT
  ip6tables -w -C OUTPUT -j $C 2>/dev/null || ip6tables -w -I OUTPUT 1 -j $C
) || echo "WARNING: the IPv6 block could not be applied"; fi
