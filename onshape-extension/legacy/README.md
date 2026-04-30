# Legacy iframe extension (CadQuery → STEP → Onshape import)

**Deprecated 2026-04-30.** Replaced by the Jarvis Onshape MCP path. See
`../MIGRATION.md` for the why and `../CLIENT-SETUP.md` for the new client config.

This directory is preserved as a fallback. The systemd unit
`/etc/systemd/system/onshape-cadgen.service` was disabled and stopped on
2026-04-30; the canonical copy lives here in `onshape-cadgen.service`.

## Re-enable for fallback

```bash
# 1. Reinstall the unit (paths now point at legacy/)
sudo cp legacy/onshape-cadgen.service /etc/systemd/system/onshape-cadgen.service
sudo systemctl daemon-reload

# 2. Start
sudo systemctl enable --now onshape-cadgen
systemctl status onshape-cadgen
curl http://127.0.0.1:8420/api/health   # {"status":"ok","cadquery":true}

# 3. Re-expose via Tailscale Funnel (was on port 10000 historically)
tailscale serve --bg --funnel=true --https=10000 http://127.0.0.1:8420
```

## What's in here

- `backend/` — FastAPI app, routers (generate, materials, onshape_upload, health),
  services (claude_service, cadquery_service, reference_loader, skill_loader).
- `frontend/` — `index.html`, `app.js`, `onshape-api.js`, `style.css` —
  the iframe UI shown inside Onshape.
- `onshape-cadgen.service` — systemd unit (`WorkingDirectory` updated to
  point at this `legacy/` dir).
- `run.sh` — local dev launcher (still works from this dir).

## Known issues at deprecation time

1. **`Derived feature status=ERROR`** — last successful upload (2026-03-10)
   ended with the `importDerived` feature failing to regenerate. Logging was
   improved on 2026-04-30 to capture `featureState.featureError`, but root
   cause not investigated further. If you re-enable this path, fix that
   first by running an upload and reading `journalctl -u onshape-cadgen`.

2. **Service was dead 13 Mar–30 Apr 2026.** Killed with SIGTERM on
   2026-03-13 06:02; not restarted until manual `systemctl start` on
   2026-04-30.

3. **No persistent Claude session.** Every `/api/generate` POST spawns a
   fresh `claude --print` subprocess (3–5 s cold start). Iterations
   re-run the full prompt from scratch.

These are exactly the reasons the project moved to the MCP path.
