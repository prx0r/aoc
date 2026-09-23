# BACKUP — carousels to R2, verified, receipted

## Setup (once)

Credentials live in `.env` (gitignored, never committed) or the environment:

```
R2_ACCOUNT_ID=…
R2_ACCESS_KEY_ID=…
R2_SECRET_ACCESS_KEY=…
R2_BUCKET=aoc-assets
```

`.env.example` shows the shape with empty values.

## What gets backed up

`store/<short-id>/` → `s3://aoc-assets/aoc/<content_id>/`:
PNGs + ZIP + `script.json` + `manifest.json` + `contact_sheet.jpg`.
Verify-after-write via a single bucket listing (R2 rejects HEAD) —
every key must exist at the exact byte count or the run fails.
A `backed_up` receipt records bucket, prefix, per-file sha256, total bytes.

## Use

```bash
# one carousel
python3 mcp_server.py aoc_backup '{"content_id": "AOC:…"}'
# or: echo '{"jsonrpc":"2.0","id":1,"method":"tools/call",
#   "params":{"name":"aoc_backup","arguments":{"content_id":"AOC:…"}}}' | python3 mcp_server.py
```

## Implementation notes

- Stdlib only (`urllib` SigV4, no boto) — `core/backup.py`.
- R2 quirks found by testing: HEAD fails, empty-payload hash rejected
  (use `UNSIGNED-PAYLOAD` for bodyless calls), query params must be
  sorted + identically encoded in URL and canonical string.
- Short dir names (`AOC-XXXXXXXX`) resolve via `manifest.json:content_id`.
