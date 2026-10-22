# Note on capture.json

`capture.json` records what was captured on 2026-10-19 and is left unchanged. Its `restoredFiles`
entry `webapp/frontend/src/player/trainInterior.ts` no longer exists: the file was removed in commit
`7017a02` (Player as a metro driver's cab). The saloon-wall display it built was replaced by the
cab, built in `webapp/frontend/src/player/cabEntry.ts` and `webapp/frontend/src/player/cockpit.ts`.
`screenDisplay.ts` still exists, rewritten for the cab. Current captures: `../player-cab/`.
