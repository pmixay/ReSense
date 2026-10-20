#!/usr/bin/env bash
# Build away from the live site, publish assets, then atomically replace index.html.
# Frontend-only updates preserve the backend, its running jobs and WebSockets.
# Usage: scripts/deploy_webapp.sh [--install] [--restart]
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/resense"
if [ -f "$CONFIG/deploy.env" ]; then
  # This is the deploying user's local configuration, never a repository secret.
  source "$CONFIG/deploy.env"
fi
STATE="${RESENSE_DEPLOY_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/resense}"
PORT="${RESENSE_WEB_PORT:-8090}"
PUBLIC_URL="${RESENSE_PUBLIC_URL:-http://127.0.0.1:$PORT}"
INSTALL=0
RESTART=0
for arg in "$@"; do
  case "$arg" in
    --install) INSTALL=1 ;;
    --restart) RESTART=1 ;;
    -h|--help) sed -n '2,4p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done
mkdir -p "$STATE/releases" "$STATE/site" "$STATE/data" "$STATE/server-data" "$CONFIG" "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
exec 9>"$STATE/deploy.lock"
flock 9
if [ "$INSTALL" = 1 ]; then
  [ -x "$STATE/venv/bin/python" ] || python3 -m venv "$STATE/venv"
  PIP_ARGS=()
  [ ! -f "$STATE/runtime-constraints.txt" ] || PIP_ARGS=(-c "$STATE/runtime-constraints.txt")
  "$STATE/venv/bin/python" -m pip install "${PIP_ARGS[@]}" -e "$REPO" -e "$REPO/ros2_ws/src/resense_ros" -e "$REPO/webapp/backend"
  (cd "$REPO/webapp/frontend" && npm ci)
  RESTART=1
fi
PY="$STATE/venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "Runtime missing. Run scripts/deploy_webapp.sh --install first." >&2
  exit 2
fi
export PYTHONPATH="$REPO:$REPO/webapp/backend:$REPO/ros2_ws/src/resense_ros${PYTHONPATH:+:$PYTHONPATH}"
"$PY" -c 'import resense_web.app; from resense_ros.decision_policy import decision'
SHA="$(git -C "$REPO" rev-parse --short HEAD)"
RELEASE="$STATE/releases/$(date -u +%Y%m%dT%H%M%S)-$SHA-$$"
mkdir -p "$RELEASE"
echo "Building ReSense $SHA…"
if ! (cd "$REPO/webapp/frontend" && npm run build -- --outDir "$RELEASE/frontend") > "$RELEASE/build.log" 2>&1; then
  cat "$RELEASE/build.log" >&2
  exit 1
fi

# Render the user service and its runtime environment. Only actual configuration
# changes or backend-source changes require a restart.
CHANGED="$("$PY" - "$REPO" "$STATE" "$CONFIG" "$PORT" <<'PY'
import json, os, sys
from pathlib import Path
repo, state, config = map(Path, sys.argv[1:4])
port = sys.argv[4]
values = {
    'RESENSE_DEPLOY_HOME': str(state), 'RESENSE_WEB_DATA': str(state / 'data'),
    'RESENSE_WEB_STATIC': str(state / 'site'), 'RESENSE_DATA': str(state / 'server-data'),
    'RESENSE_WEB_HOST': '127.0.0.1', 'RESENSE_WEB_PORT': port, 'PYTHONUNBUFFERED': '1',
}
env = ''.join(f'{k}={json.dumps(v)}\n' for k, v in values.items())
unit = (repo / 'deploy/resense-web.service.in').read_text()
for key, value in {'REPO': str(repo), 'ENVFILE': str(config / 'runtime.env'), 'SERVE': str(repo / 'scripts/serve_webapp.sh')}.items():
    unit = unit.replace(f'@{key}@', json.dumps(value) if key == 'SERVE' else value)
unit_path = config.parent / 'systemd/user/resense-web.service'
changed = False
for path, content in [(config / 'runtime.env', env), (unit_path, unit)]:
    if not path.exists() or path.read_text() != content:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + '.new')
        temp.write_text(content)
        os.replace(temp, path)
        changed = True
print(int(changed))
PY
)"
FINGERPRINT="$("$PY" - "$REPO" <<'PY'
import hashlib, subprocess, sys
from pathlib import Path
repo = Path(sys.argv[1])
paths = ['resense', 'webapp/backend/resense_web', 'webapp/backend/pyproject.toml',
         'ros2_ws/src/resense_ros', 'configs', 'native', 'pyproject.toml', 'setup.py',
         'scripts/serve_webapp.sh']
names = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-z', '--', *paths]).decode().split('\0')
files = [repo / name for name in names if name]
files.extend(repo.glob('resense/_resense_native*.so'))
h = hashlib.sha256()
for path in sorted(set(files)):
    if path.is_file():
        h.update(str(path.relative_to(repo)).encode() + b'\0')
        h.update(path.read_bytes())
print(h.hexdigest())
PY
)"
PREVIOUS="$(cat "$STATE/backend-fingerprint" 2>/dev/null || true)"
systemd-analyze --user verify "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/resense-web.service"
if [ "$CHANGED" = 1 ]; then systemctl --user daemon-reload; RESTART=1; fi
if [ "$FINGERPRINT" != "$PREVIOUS" ]; then RESTART=1; fi
systemctl --user enable resense-web.service >/dev/null
if ! systemctl --user is-active --quiet resense-web.service; then
  systemctl --user start resense-web.service
elif [ "$RESTART" = 1 ]; then
  systemctl --user restart resense-web.service
fi
"$PY" - "$PORT" <<'PY'
import json, sys, time, urllib.error, urllib.request
url = f'http://127.0.0.1:{sys.argv[1]}/api/health'
for _ in range(100):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            if json.load(r).get('ok') is True:
                break
    except (OSError, urllib.error.URLError):
        pass
    time.sleep(.2)
else:
    raise SystemExit('Backend did not become healthy; inspect journalctl --user -u resense-web.')
PY

"$PY" - "$REPO" "$RELEASE/frontend" "$STATE/site" "$FINGERPRINT" "$PUBLIC_URL" <<'PY'
import hashlib, json, os, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
repo, built, site = map(Path, sys.argv[1:4])
for source in sorted(built.rglob('*')):
    relative = source.relative_to(built)
    if source.name == 'index.html':
        continue
    target = site / relative
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        temp_asset = target.with_name('.' + target.name + '.new')
        shutil.copy2(source, temp_asset)
        os.replace(temp_asset, target)
# Retain previous hashed assets so open tabs can load their lazy routes after a deploy.
temp = site / '.index.html.new'
shutil.copy2(built / 'index.html', temp)
os.replace(temp, site / 'index.html')
git = lambda *args: subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
manifest = {
    'commit': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
    'dirty': bool(git('status', '--porcelain')), 'deployedAt': datetime.now(timezone.utc).isoformat(),
    'frontendIndexSha256': hashlib.sha256((site / 'index.html').read_bytes()).hexdigest(),
    'backendFingerprint': sys.argv[4], 'url': sys.argv[5],
}
temp = site / '.deployment.json.new'
temp.write_text(json.dumps(manifest, indent=2) + '\n')
os.replace(temp, site / 'deployment.json')
print(f"Published {manifest['commit'][:7]} to {manifest['url']}")
PY
printf '%s\n' "$FINGERPRINT" > "$STATE/backend-fingerprint"
echo "Health: http://127.0.0.1:$PORT/api/health"
echo "Version: $PUBLIC_URL/deployment.json"
