# Client setup — Claude Code + Jarvis Onshape MCP

Connect a local Claude Code instance (any laptop/workstation on the Tailscale
network) to the Jarvis Onshape MCP server hosted on **nativedev**.

## Prerequisites

- Active Claude Code subscription (Max/Pro). Run `claude login` once.
- Tailscale connected (`tailscale status` shows `nativedev` as a peer).
- `npx` available (Node 18+).

## Configure the MCP bridge

`mcp-remote` is the recommended npm wrapper that bridges stdio (what Claude
Code speaks) to SSE (what the remote Jarvis server speaks).

### Option A — global (all projects)

Edit `~/.claude.json` and add the entry (or use `claude mcp add`):

```bash
claude mcp add --scope user onshape \
  --command npx \
  --args "-y mcp-remote https://nativedev.tail7d3518.ts.net:10001/sse"
```

### Option B — project-scoped

In a repo, create `.mcp.json`:

```json
{
  "mcpServers": {
    "onshape": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://nativedev.tail7d3518.ts.net:10001/sse"]
    }
  }
}
```

## Verify

```bash
claude
> /mcp
```

You should see `onshape` listed as **connected**, exposing ~60 tools
(create_sketch_*, create_extrude, create_fillet, create_mate_*,
render_part_studio_views, eval_featurescript, …).

Smoke test:

```
> use the onshape tool to list my documents
```

The first call after a server restart pays a ~14 s import cost (Pillow,
loguru, pytesseract). Steady-state per-tool latency: ~200–500 ms RTT
nativedev → Onshape Cloud + LLM thinking.

## Auth model

- **Claude side:** your local `claude login` — model calls go through your
  subscription, never through nativedev.
- **Onshape side:** API keys live on nativedev in `~/.config/onshape-mcp/jarvis.env`
  (mode 600, owned by the systemd user). Multi-user support is via the
  systemd template `onshape-mcp@<user>.service` — each user gets their own
  service instance and their own keys file.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `/mcp` shows onshape as **failed** | `tailscale ping nativedev`; then `curl -m 5 https://nativedev.tail7d3518.ts.net:10001/sse` should print `event: endpoint` |
| Tools list empty | Server logs: `ssh nativedev journalctl -u onshape-mcp@tommaso -n 50` |
| Onshape API errors (401/403) | Re-issue keys at https://dev-portal.onshape.com and update `~/.config/onshape-mcp/jarvis.env` on nativedev, then `sudo systemctl restart onshape-mcp@tommaso` |
| Server unreachable from a new node | New Tailscale nodes are auto-allowed by the existing ACL — verify with `tailscale ping nativedev` |

## Server-side admin (on nativedev)

```bash
# Status
systemctl status onshape-mcp@tommaso

# Logs
journalctl -u onshape-mcp@tommaso -f

# Restart after key rotation
sudo systemctl restart onshape-mcp@tommaso

# Add a new user (e.g. `pietro`)
sudo mkdir -p /home/pietro/.config/onshape-mcp
# pietro adds his keys + a unique MCP_PORT (e.g. 3001) to jarvis.env
sudo systemctl enable --now onshape-mcp@pietro
tailscale serve --bg --https=10002 http://127.0.0.1:3001
```
