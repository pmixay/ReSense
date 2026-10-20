# Role 2 — publication on 20 October 2026

**Live URL:** https://resense.amdm.life/

The user requested “push and publish everything”, then supplied
`resense.amdm.life` as the target. It resolves to this server (`5.83.140.123`).
The former documented `hack.amdm.life` resolves to a different host; the initial
blocker in [README.md](README.md) is superseded by this publication.

## Published work

- Code integration `c1a7614ded81302b6388badba7bb0926d5c30d42` was pushed to
  `origin/ui-improvement` and verified with `git ls-remote`.
- Installed a dedicated Python 3.12 runtime with the verified NumPy/SciPy/sklearn
  versions and pinned web-runtime packages. `pip check` passes.
- Installed Node 22.23.3 persistently under `/opt`.
- Configured the deployment URL/port/state path in
  `/root/.config/resense/deploy.env` and ran
  `PIP_NO_CACHE_DIR=1 scripts/deploy_webapp.sh --install`.
- The `resense-web` user service is enabled and active. User lingering is enabled.
  Persistent SQLite/uploads/recordings/runs live under
  `/root/.local/share/resense/data`.
- Added the domain to the existing Caddy HTTPS proxy, validated the configuration
  and reloaded it. Caddy manages TLS and forwards HTTP/WebSockets to
  `127.0.0.1:8090`.
- Updated the maintained deployment links and recorded this receipt. The final
  documentation commit is pushed and republished with the normal deploy command;
  `/deployment.json` identifies the exact checkout served.

## Public verification

Initial code publication reported:

```json
{
  "commit": "c1a7614ded81302b6388badba7bb0926d5c30d42",
  "branch": "ui-improvement",
  "dirty": false,
  "deployedAt": "2026-10-20T12:30:29.155670+00:00",
  "url": "https://resense.amdm.life"
}
```

Checks performed over the public HTTPS/WSS origin:

| Check | Result |
|---|---|
| `/api/health` | HTTP 200, `{"ok":true}` |
| `/deployment.json` | Commit equals checkout, branch `ui-improvement`, `dirty=false` |
| `/api/system` | Detector 1.2.0, bag reader/clouds/native kernels available, persistent state directory selected |
| Real demo → queued worker → run | PASS: ten frames processed, clouds stored |
| WSS paused replay | PASS: wait longer than the ten-frame recording at 10×, seek to frame 8, then play frame 9 |
| Desktop browser at 1280×800 | PASS: real run's 3D Player and frame slider, About page, no horizontal overflow or browser errors |
| Test-data cleanup | Only the smoke test's own run/job/recording removed through the API |

The smoke check used `/tmp/opencode/resense_publish_smoke.py`. The full application
checks and inherited detector-release limitations are in [README.md](README.md).
This publishes the web preview; the captain's detector reseal/release process
retains its separate acceptance requirements.
