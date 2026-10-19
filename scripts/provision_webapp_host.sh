#!/usr/bin/env bash
# One-time root setup of a dedicated nginx preview vhost, TLS and user-service persistence.
# Usage: sudo scripts/provision_webapp_host.sh --domain HOST --user USER [--port 8090] [--http-only] [--replace-site FILE]
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN=""
SERVICE_USER=""
PORT=8090
HTTP_ONLY=0
REPLACE_SITE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --user) SERVICE_USER="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --http-only) HTTP_ONLY=1; shift ;;
    --replace-site) REPLACE_SITE="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
[ "$(id -u)" = 0 ] || { echo 'Run this one-time provisioning command as root.' >&2; exit 2; }
[[ "$DOMAIN" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+$ ]] || { echo 'A domain is required.' >&2; exit 2; }
[[ "$PORT" =~ ^[0-9]+$ ]] || exit 2
id "$SERVICE_USER" >/dev/null
SITE=/etc/nginx/sites-available/resense-preview.conf
LINK=/etc/nginx/sites-enabled/resense-preview.conf
ACME=/var/www/resense-preview-acme
CERT="$DOMAIN"
if [ -n "$REPLACE_SITE" ]; then
  [[ "$REPLACE_SITE" =~ ^[a-zA-Z0-9._-]+$ ]] || exit 2
fi
if [ -f "$SITE" ] && ! grep -q '^# Managed by ReSense' "$SITE"; then
  echo "$SITE is not managed by this project." >&2; exit 2
fi
mkdir -p "$ACME/.well-known/acme-challenge" /var/backups/resense-nginx
printf 'resense-preview\n' > "$ACME/.well-known/acme-challenge/resense-host-check"
loginctl enable-linger "$SERVICE_USER"
TEMP="$(mktemp /tmp/opencode/resense-nginx.XXXXXX)"
trap 'rm -f "$TEMP"' EXIT
render() {
  python3 - "$DOMAIN" "$PORT" "$ACME" "$CERT" "$1" "$TEMP" <<'PY'
import sys
from pathlib import Path
domain, port, acme, cert, template, output = sys.argv[1:]
text = Path(template).read_text()
for key, value in {'DOMAIN': domain, 'PORT': port, 'ACME': acme, 'CERT': cert}.items():
    text = text.replace(f'@{key}@', value)
Path(output).write_text(text)
PY
}
activate() {
  local backup=""
  local replaced=""
  if [ -f "$SITE" ]; then
    backup="/var/backups/resense-nginx/$(date -u +%Y%m%dT%H%M%S)-$$.conf"
    cp -a "$SITE" "$backup"
  fi
  install -m 644 "$TEMP" "$SITE"
  if [ -n "$REPLACE_SITE" ] && [ -e "/etc/nginx/sites-enabled/$REPLACE_SITE" ]; then
    replaced="/var/backups/resense-nginx/$(date -u +%Y%m%dT%H%M%S)-$$-$REPLACE_SITE.enabled"
    cp -L "/etc/nginx/sites-enabled/$REPLACE_SITE" "$replaced.conf"
    mv "/etc/nginx/sites-enabled/$REPLACE_SITE" "$replaced"
  fi
  ln -sfn "$SITE" "$LINK"
  if ! nginx -t; then
    if [ -n "$backup" ]; then cp -a "$backup" "$SITE"; else rm -f "$SITE" "$LINK"; fi
    if [ -n "$replaced" ]; then mv "$replaced" "/etc/nginx/sites-enabled/$REPLACE_SITE"; fi
    exit 1
  fi
  systemctl reload nginx
}
if [ "$HTTP_ONLY" = 1 ] || [ ! -f "/etc/letsencrypt/live/$CERT/fullchain.pem" ]; then
  render "$REPO/deploy/nginx-preview-http.conf.in"
  activate
fi
if [ "$HTTP_ONLY" = 1 ]; then
  echo "HTTP preview ready: http://$DOMAIN/"
  exit 0
fi
certbot certonly --webroot -w "$ACME" -d "$DOMAIN" --cert-name "$CERT" \
  --non-interactive --agree-tos --register-unsafely-without-email --keep-until-expiring \
  --deploy-hook '/usr/bin/systemctl reload nginx'
render "$REPO/deploy/nginx-preview-https.conf.in"
activate
if systemctl list-unit-files certbot.timer --no-legend | grep -q certbot.timer; then
  systemctl enable --now certbot.timer
fi
echo "HTTPS preview ready: https://$DOMAIN/"
