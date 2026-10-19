# Live preview on this server

Current HTTPS preview: **https://hack.amdm.life/**.

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

The user service is enabled at login/boot; one-time host provisioning enables user
lingering so it also stays up after logout. nginx proxies HTTP/WebSockets to the
loopback backend. Certbot uses a webroot challenge and a stored nginx reload hook.

## One-time host setup

Install the runtime, configure `~/.config/resense/deploy.env`, and publish first.
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
