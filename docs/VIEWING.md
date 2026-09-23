# VIEWING — how to see everything

## Local viewer (this repo, stdlib only)

```bash
cd /root/aoc && python3 -m web.viewer
# http://127.0.0.1:8798/
```

- `/` — gallery: every carousel's contact sheet, segment, template, gates, review state
- `/queue` — pending-human queue with approve/revise/reject forms (reason required)
- `/view?cid=…` — one carousel: sheet, gates JSON, review state, ZIP download
- `/api/status` — JSON counts for powops-style polling

Localhost bind only. To expose it, put Cloudflare Access in front —
never serve it raw (no auth by design, like a local tool should be).

## What was (not) stolen from /content

- **Dashboard**: `watch.moltwork.com` is hosted externally — no code in the
  repo to steal. The viewer above rebuilds its job (queue → review → approve
  writes receipt) locally in one stdlib file.
- **Pi extension**: ported 1:1 into `pi-extension/aoc-sensor.ts` — same
  spawn-stdio shape, same timeout/queue pattern, 6 tools mapped to aoc verbs
  (hooks, build, validate, queue→lineage, signoff, status). Set
  `AOC_MCP_PATH=/root/aoc/mcp_server.py` (or install to `~/.pi/agent/extensions/`).

## CLI / MCP equivalents (no browser)

```bash
python3 mcp_server.py aoc_status '{}'
python3 mcp_server.py aoc_lineage '{"limit": 20}'
python3 mcp_server.py aoc_rank '{}'
cat store/campaigns.json | python3 -m json.tool | head -n 40
```
