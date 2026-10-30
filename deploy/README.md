# Live preview on this server

Current HTTPS preview: **https://resense.arbuz.lol/** (22 October 2026: it serves the ReSense page, title "ReSense"; the earlier preview host, configured 20 October, now serves another app).

`scripts/deploy_webapp.sh` builds and publishes the current checkout to the running
preview. The server-specific URL is in `~/.config/resense/deploy.env` and is printed
by the command. `/deployment.json` reports the deployed commit, branch, timestamp,
dirty-worktree flag and frontend index hash.

```bash
scripts/deploy_webapp.sh             # build, health-check and publish
scripts/deploy_webapp.sh --install   # first install or dependency refresh
scripts/deploy_webapp.sh --restart   # explicitly reload the backend too
systemctl --user status resense-web
journalctl --user -u resense-web -n 100
```

## Persistent layout

Default root: `~/.local/share/resense` (`RESENSE_DEPLOY_HOME` can override it).

- `venv/`: dedicated backend Python runtime.
- `data/`: persistent SQLite database, uploads, recordings and runs.
- `server-data/`: sandboxed server-folder source for the upload browser.
- `site/`: live frontend, separate from the development `dist/` directory.
- `releases/`: timestamped frontend builds and build logs.
- `backend-fingerprint`: last successfully deployed backend/configuration digest.

Builds occur in a new release directory. Hashed assets are copied before an atomic
index replacement, and old hashed assets are retained for already-open lazy routes.
UI-only updates preserve running processing jobs and WebSocket sessions. Backend or
runtime configuration changes reload the single `resense-web` user service.

The user service is enabled at login/boot; user lingering keeps it running after
logout. On this server, the existing Caddy container proxies HTTPS/WebSockets to
the loopback backend and manages certificate renewal.

## Current server configuration

`resense.arbuz.lol` resolves to `5.83.140.121` (checked 22.10 from the documentation session; whether that is this host was not checked; the earlier preview host resolved to `5.83.140.123` on 20.10 and now serves another app). The deployment runs as
`root`, with settings in `/root/.config/resense/deploy.env`:

```bash
RESENSE_PUBLIC_URL=https://resense.arbuz.lol
RESENSE_WEB_PORT=8090
RESENSE_DEPLOY_HOME=/root/.local/share/resense
```

The dedicated Python runtime is `~/.local/share/resense/venv`; installation uses
`~/.local/share/resense/runtime-constraints.txt` to retain the verified numerical
and web-runtime versions. Node 22.23.3 is installed under `/opt`, with `node`,
`npm` and `npx` available in `/usr/local/bin`.

The domain's block in `/etc/codex-lb/Caddyfile`, mounted by `codex-lb-https`, as recorded on 20.10 for the earlier host (the host name below is the current preview's; the real Caddyfile entry for it was not inspected on 22.10):

```caddyfile
resense.arbuz.lol {
    reverse_proxy 127.0.0.1:8090 {
        flush_interval -1
    }
}
```

After editing the host proxy configuration:

```bash
docker exec codex-lb-https caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec codex-lb-https caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

Normal application updates still use only `scripts/deploy_webapp.sh`. Publication
and public smoke checks: [20 October receipt](../docs/evidence/p2_2026-10-20/PUBLISH.md).

## Provisioning a separate nginx host

The nginx/Certbot provisioner is for hosts using nginx. Install the runtime,
configure `~/.config/resense/deploy.env`, and publish first.
Then run the root provisioning command with a domain whose DNS points to this host:

```bash
sudo scripts/provision_webapp_host.sh --domain YOUR_DOMAIN --user YOUR_USER --port 8090
```

`--http-only` installs the initial HTTP/challenge route for reachability checks.
`--replace-site FILE` moves the explicitly selected existing enabled vhost into the
backup directory before activation, with restoration if validation fails.
The managed vhost is `/etc/nginx/sites-available/resense-preview.conf`; its prior
versions are backed up and nginx configuration is validated before each reload.
The normal deployment command runs entirely as the application user.
