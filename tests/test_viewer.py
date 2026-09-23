"""Viewer tests: gallery, queue, sheets, sign-off roundtrip, status."""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PORT = 18798
BASE = f"http://127.0.0.1:{PORT}"


def _srv():
    proc = subprocess.Popen(
        [sys.executable, "-m", "web.viewer", "--port", str(PORT)],
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/api/status", timeout=1)
            return proc
        except OSError:
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError("viewer did not start")


def test_viewer_endpoints():
    proc = _srv()
    try:
        status = json.load(urllib.request.urlopen(BASE + "/api/status", timeout=5))
        assert status["carousels"] > 50, status
        assert "electrician" in status["by_segment"]

        gallery = urllib.request.urlopen(BASE + "/", timeout=5).read()
        assert b"contact_sheet" in gallery or b"sheet?cid=" in gallery

        queue = urllib.request.urlopen(BASE + "/queue", timeout=5).read()
        assert b"Review queue" in queue

        # sheet for latest build
        receipts = [json.loads(ln) for ln in
                    open(Path(__file__).parent.parent / "receipts/content.jsonl")
                    if ln.strip()]
        built = [r for r in receipts if r.get("event") == "carousel_built"]
        cid = built[-1]["data"]["content_id"]
        with urllib.request.urlopen(BASE + f"/sheet?cid={cid}", timeout=5) as r:
            assert r.status == 200
            assert r.read(2) == b"\xff\xd8"  # JPEG

        # unknown cid 404s, doesn't crash
        try:
            urllib.request.urlopen(BASE + "/sheet?cid=nope", timeout=5)
            raise AssertionError("expected 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        proc.terminate()


def test_signoff_rejects_bad_verdict():
    proc = _srv()
    try:
        import urllib.parse, urllib.error
        data = urllib.parse.urlencode(
            {"content_id": "x", "decision": "maybe", "reason": "x"}).encode()
        body = urllib.request.urlopen(
            urllib.request.Request(BASE + "/api/signoff", data=data), timeout=5).read()
        assert b"rejected" in body  # the HTML page reports the refusal
    finally:
        proc.terminate()
