"""Backup tests: signing, verify logic, receipts. No network."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import backup as B  # noqa: E402


def test_sigv4_headers_shape():
    h = B._s3_headers("GET", "https://x.r2.cloudflarestorage.com/bkt?list-type=2",
                      "UNSIGNED-PAYLOAD", "", "KEY", "SECRET")
    assert h["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=KEY/")
    assert "SignedHeaders=" in h["Authorization"]
    assert h["x-amz-content-sha256"] == "UNSIGNED-PAYLOAD"


def test_canonical_query_sorted():
    # query order in URL must not matter — canonical form sorts
    h1 = B._s3_headers("GET", "https://h/b?b=2&a=1", "UNSIGNED-PAYLOAD", "", "K", "S")
    h2 = B._s3_headers("GET", "https://h/b?a=1&b=2", "UNSIGNED-PAYLOAD", "", "K", "S")
    assert h1["Authorization"] == h2["Authorization"]


def test_missing_creds_fail_closed(monkeypatch):
    for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)
    try:
        B._env()
    except RuntimeError as e:
        assert "missing" in str(e).lower()
    else:
        raise AssertionError("no creds accepted")


def test_backup_carousel_uses_manifest_hashes(tmp_path):
    import json
    out = tmp_path / "c"
    out.mkdir()
    (out / "slide_00.jpg").write_bytes(b"\xff\xd8fake!")
    (out / "script.json").write_text("{}")
    calls = {}

    class FakeResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return (b'<?xml version="1.0"?><ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                    b'<Contents><Key>aoc/x/slide_00.jpg</Key><Size>7</Size></Contents>'
                    b'<Contents><Key>aoc/x/script.json</Key><Size>2</Size></Contents>'
                    b'</ListBucketResult>')

    import urllib.request as _u
    orig = _u.urlopen
    seen_puts = []

    def fake_open(req, timeout=None):
        calls.setdefault("n", 0)
        calls["n"] += 1
        if req.get_method() == "PUT":
            seen_puts.append(req.full_url)
            return FakeResp()
        return FakeResp()

    _u.urlopen = fake_open
    try:
        import os
        os.environ["R2_ACCOUNT_ID"] = "a"
        os.environ["R2_ACCESS_KEY_ID"] = "k"
        os.environ["R2_SECRET_ACCESS_KEY"] = "s"
        os.environ["R2_BUCKET"] = "bkt"
        m = B.backup_carousel(out, "x")
    finally:
        _u.urlopen = orig
        for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
            os.environ.pop(k, None)
    assert m["bucket"] == "bkt"
    assert m["total_bytes"] == 9
    assert len(seen_puts) == 2


def test_backup_store_resolves_short_dirs(tmp_path):
    import json
    store = tmp_path / "store"
    d = store / "AOC-ABC123"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"content_id": "AOC:full:hash"}))
    (d / "slide_00.jpg").write_bytes(b"\xff\xd8fake")
    import core.backup as _b
    orig = _b.backup_carousel
    seen = {}

    def fake_backup(out_dir, cid):
        seen["dir"] = out_dir
        return {"bucket": "b", "files": [], "total_bytes": 0}

    _b.backup_carousel = fake_backup
    try:
        _b.backup_store("AOC:full:hash", store_dir=store, receipts_path=tmp_path / "r.jsonl")
    finally:
        _b.backup_carousel = orig
    assert Path(seen["dir"]).name == "AOC-ABC123"
