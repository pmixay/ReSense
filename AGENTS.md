# ReSense working and live-preview workflow

The repository is deployed from the `ui-improvement` checkout on this server.

## After requested application changes

1. Run the checks appropriate to the change and commit the completed work.
2. Run `scripts/deploy_webapp.sh` before reporting completion so the user can check the live site.
3. Verify the live `/api/health` and `/deployment.json`, and confirm the deployed commit matches the checkout.
4. Include the live URL in the completion message.

The server-specific URL and paths are recorded in the deploying user's
`~/.config/resense/deploy.env`. See `deploy/README.md` for the deployment layout.
Frontend updates publish atomically without restarting the backend. The deploy
command restarts the user service when backend/configuration fingerprints change.
Keep persistent database/uploads/runs in the deployment state directory.
