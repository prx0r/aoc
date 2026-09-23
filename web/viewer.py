"""AOC viewer — local gallery + review queue. Stdlib only, localhost only.

What /content's watch.moltwork.com does, running here instead of hosted:
contact sheets per segment, pending-human queue, approve/revise/reject
buttons that write sign_off receipts. No auth (localhost bind); put
Cloudflare Access in front if you ever tunnel it.

Usage:
    python3 -m web.viewer            # http://127.0.0.1:8798
    python3 -m web.viewer --port 8800
"""

from __future__ import annotations

import html
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent.parent


def _receipts() -> list[dict]:
    p = ROOT / "receipts/content.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


def _builds() -> list[dict]:
    """Latest carousel_built receipt per content_id, with review state."""
    seen: dict[str, dict] = {}
    reviewed: dict[str, dict] = {}
    for r in _receipts():
        d = r.get("data", {})
        cid = d.get("content_id", "")
        if r.get("event") == "carousel_built" and cid:
            seen[cid] = {"receipt": r, **d}
        elif r.get("event") in ("reviewed",):
            reviewed[cid] = d
    out = []
    for cid, b in seen.items():
        out.append({**b, "review": reviewed.get(cid)})
    out.sort(key=lambda b: b.get("receipt", {}).get("at", ""), reverse=True)
    return out


def _contact_sheet_path(content_id: str) -> Path | None:
    for manifest in sorted((ROOT / "store").glob("*/manifest.json")):
        try:
            m = json.loads(manifest.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if m.get("content_id") == content_id:
            sheet = manifest.parent / "contact_sheet.jpg"
            return sheet if sheet.exists() else None
    return None


def _esc(s: object) -> str:
    return html.escape(str(s or ""), quote=True)


CARD = """
<div class="card">
<a href="/view?cid={cid}"><img loading="lazy" src="/sheet?cid={cid}" alt="{hook}"></a>
<div class="meta"><b>{segment}</b> · {template} · {kind} · {slides} slides<br>
<span class="hook">{hook}</span><br>
gates: {gates} · review: {review}
</div></div>
"""


def page_gallery(builds: list[dict]) -> str:
    cards = []
    for b in builds:
        gates = (b.get("gates") or {})
        g_ok = all(g.get("ok") for g in gates.values()) if gates else None
        cards.append(CARD.format(
            cid=_esc(b.get("content_id")),
            hook=_esc((b.get("hook") or "")[:70]),
            segment=_esc(b.get("segment")), template=_esc(b.get("template")),
            kind=_esc(b.get("kind", "organic")), slides=_esc(b.get("slides")),
            gates="pass" if g_ok else ("fail" if g_ok is False else "?"),
            review=_esc((b.get("review") or {}).get("decision", "pending")),
        ))
    return _shell("AOC gallery", f"<h1>AOC — {len(builds)} carousels</h1>"
                  f'<p><a href="/queue">review queue</a> · <a href="/api/status">status json</a></p>'
                  f'<div class="grid">{"".join(cards)}</div>')


def page_queue(builds: list[dict]) -> str:
    pending = [b for b in builds if not b.get("review")]
    rows = []
    for b in pending:
        cid = _esc(b.get("content_id"))
        rows.append(
            f'<div class="card"><a href="/view?cid={cid}">{cid[:18]}…</a><br>'
            f'<span class="hook">{_esc((b.get("hook") or "")[:80])}</span><br>'
            f'{_esc(b.get("segment"))} · {_esc(b.get("template"))}<br>'
            f'<form method="POST" action="/api/signoff">'
            f'<input type="hidden" name="content_id" value="{cid}">'
            f'<select name="decision"><option>approved</option>'
            f'<option>revise</option><option>rejected</option></select><br>'
            f'<input name="reason" placeholder="reason (required)" size="40" required><br>'
            f'<button>record verdict</button></form></div>')
    body = f"<h1>Review queue — {len(pending)} pending</h1>" + (
        "".join(rows) if rows else "<p>Queue clear. Nothing awaiting human eyes.</p>")
    return _shell("AOC review queue", body + '<p><a href="/">gallery</a></p>')


def page_view(cid: str) -> str:
    builds = {b.get("content_id"): b for b in _builds()}
    b = builds.get(cid)
    if not b:
        return _shell("not found", "<h1>unknown content_id</h1>")
    sheet = _contact_sheet_path(cid)
    rev = b.get("review") or {}
    return _shell("AOC view", f"""
<h1>{_esc((b.get('hook') or '')[:90])}</h1>
<p>{_esc(b.get('segment'))} · {_esc(b.get('template'))} · {_esc(b.get('kind', 'organic'))}
· <a href="/zip?cid={_esc(cid)}">download ZIP</a></p>
{"<img class='sheet' src='/sheet?cid=" + _esc(cid) + "'>" if sheet else "<p>no contact sheet</p>"}
<h2>gates</h2><pre>{_esc(json.dumps(b.get('gates'), indent=1, default=str))}</pre>
<h2>review</h2><pre>{_esc(json.dumps(rev, indent=1, default=str) or 'pending')}</pre>
<p><a href="/queue">back to queue</a> · <a href="/">gallery</a></p>""")


def _shell(title: str, body: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title>
<style>body{{background:#0b0b0c;color:#f5f5f4;font-family:system-ui;margin:16px}}
a{{color:#ffb224}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}}
.card{{background:#161617;border:1px solid #2a2a2c;border-radius:10px;padding:8px}}
.card img{{width:100%;border-radius:6px}}.hook{{color:#ffd88a}}
.sheet{{max-width:520px;width:100%}}pre{{background:#161617;padding:8px;overflow:auto}}
button{{background:#ffb224;border:0;border-radius:6px;padding:6px 10px;margin-top:4px}}
input,select{{margin:2px 0}}</style></head><body>{body}</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body: bytes, ctype: str = "text/html"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj: object):
        self._send(json.dumps(obj, indent=2, default=str).encode(), "application/json")

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        cid = (q.get("cid") or [""])[0]
        if url.path == "/":
            self._send(page_gallery(_builds()).encode())
        elif url.path == "/queue":
            self._send(page_queue(_builds()).encode())
        elif url.path == "/view":
            self._send(page_view(cid).encode())
        elif url.path == "/sheet":
            sheet = _contact_sheet_path(cid) if cid else None
            if sheet:
                self._send(sheet.read_bytes(), "image/jpeg")
            else:
                self.send_response(404); self.end_headers()
        elif url.path == "/zip":
            builds = {b.get("content_id"): b for b in _builds()}
            z = (builds.get(cid) or {}).get("zip", "") if cid else ""
            zp = Path(z) if z else None
            if zp and zp.exists():
                self._send(zp.read_bytes(), "application/zip")
            else:
                self.send_response(404); self.end_headers()
        elif url.path == "/api/status":
            builds = _builds()
            self._send_json({
                "carousels": len(builds),
                "pending_review": sum(1 for b in builds if not b.get("review")),
                "by_segment": {s: sum(1 for b in builds if (b.get("segment") or "?") == s)
                               for s in sorted({b.get("segment") or "?" for b in builds})},
            })
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/api/signoff":
            self.send_response(404); self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode())
        cid = (form.get("content_id") or [""])[0]
        decision = (form.get("decision") or [""])[0]
        reason = (form.get("reason") or [""])[0]
        sys.path.insert(0, str(ROOT))
        try:
            from core.review import sign_off
            receipt = sign_off(ROOT / "receipts/content.jsonl", cid, decision, reason)
            body = f"recorded: {receipt['receipt_id']} — <a href='/queue'>queue</a>"
        except ValueError as e:
            body = f"rejected: {html.escape(str(e))} — <a href='/queue'>queue</a>"
        self._send(_shell("sign-off", f"<h1>sign-off</h1><p>{body}</p>").encode())


def main() -> None:
    import sys as _sys
    port = 8798
    if "--port" in _sys.argv:
        port = int(_sys.argv[_sys.argv.index("--port") + 1])
    srv = HTTPServer(("127.0.0.1", port), Handler)
    print(f"aoc viewer on http://127.0.0.1:{port}/  (localhost only — tunnel via Cloudflare Access, never raw)")
    srv.serve_forever()


if __name__ == "__main__":
    import sys
    main()
