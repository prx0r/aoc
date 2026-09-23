"""R2 backup — carousel artifacts to Cloudflare R2. Stdlib + boto-free.

Reads credentials ONLY from the environment (never committed, never logged):
    R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
    R2_BUCKET (default aoc-assets), R2_ENDPOINT (derived if unset)

Layout:  s3://<bucket>/aoc/<content_id>/<filename>
Verify-after-write by byte count. Receipt records what landed.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def _env() -> dict:
    account = os.environ.get("R2_ACCOUNT_ID", "")
    key = os.environ.get("R2_ACCESS_KEY_ID", "")
    secret = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    if not (account and key and secret):
        raise RuntimeError("R2 credentials missing from environment "
                           "(R2_ACCOUNT_ID/R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY)")
    endpoint = os.environ.get(
        "R2_ENDPOINT", f"https://{account}.r2.cloudflarestorage.com")
    return {"account": account, "key": key, "secret": secret,
            "endpoint": endpoint,
            "bucket": os.environ.get("R2_BUCKET", "aoc-assets")}


def _sign(key: str, msg: str) -> bytes:
    return hmac.new(key.encode() if isinstance(key, str) else key,
                    msg.encode(), hashlib.sha256).digest()


def _s3_headers(method: str, url: str, payload_hash: str, content_type: str,
                key: str, secret: str, region: str = "auto") -> dict:
    """Minimal SigV4 for R2 (unsigned payload + path-style URL)."""
    from urllib.parse import urlparse
    u = urlparse(url)
    now = datetime.now(timezone.utc)
    amz = now.strftime("%Y%m%dT%H%M%SZ")
    scope = f"{now.strftime('%Y%m%d')}/{region}/s3/aws4_request"
    headers = {"host": u.netloc, "x-amz-content-sha256": payload_hash,
               "x-amz-date": amz}
    if content_type:
        headers["content-type"] = content_type
    # NOTE: never sign empty headers — urllib drops them and R2 rejects
    # the signature with 403 (failures surface as verify mismatches).
    # SigV4 requires the query string sorted by param name, each encoded.
    import urllib.parse as _up
    pairs = _up.parse_qsl(u.query, keep_blank_values=True)
    canon_qs = "&".join(f"{_up.quote(k, safe='')}={_up.quote(v, safe='')}"
                        for k, v in sorted(pairs))
    signed = ";".join(sorted(headers))
    canonical = "\n".join([
        method, u.path or "/", canon_qs,
        "".join(f"{k}:{headers[k]}\n" for k in sorted(headers)),
        signed, payload_hash])
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz, scope,
        hashlib.sha256(canonical.encode()).hexdigest()])
    k_date = _sign("AWS4" + secret, now.strftime("%Y%m%d"))
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, "s3")
    k_sign = _sign(k_service, "aws4_request")
    sig = hmac.new(k_sign, string_to_sign.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={key}/{scope}, "
        f"SignedHeaders={signed}, Signature={sig}")
    return headers


def _put(url: str, data: bytes, content_type: str, env: dict) -> None:
    h = hashlib.sha256(data).hexdigest()
    req = urllib.request.Request(
        url, data=data, method="PUT",
        headers=_s3_headers("PUT", url, h, content_type,
                            env["key"], env["secret"]))
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status not in (200, 201, 204):
            raise RuntimeError(f"PUT {url} -> HTTP {r.status}")


def _list_prefix(bucket_url: str, prefix: str, env: dict) -> dict[str, int]:
    """ListObjectsV2 under a prefix. Returns {key: size}. R2 rejects HEAD;
    a single listing verifies every upload instead."""
    import xml.etree.ElementTree as _et
    # Encode params once, identically, for URL and canonical string.
    qs = "&".join(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
                  for k, v in sorted([("list-type", "2"), ("prefix", prefix),
                                       ("max-keys", "1000")]))
    url = f"{bucket_url}?{qs}"
    req = urllib.request.Request(
        url, method="GET",
        headers=_s3_headers("GET", url, "UNSIGNED-PAYLOAD",
                            "", env["key"], env["secret"]))
    with urllib.request.urlopen(req, timeout=60) as r:
        root = _et.fromstring(r.read())
    out = {}
    ns = "{http://s3.amazonaws.com/doc/2006-03-01/}"
    for obj in root.findall(f"{ns}Contents"):
        key = obj.findtext(f"{ns}Key", "")
        size = obj.findtext(f"{ns}Size", "-1")
        out[key] = int(size)
    return out


def backup_carousel(out_dir: Path | str, content_id: str,
                    extra: dict | None = None) -> dict:
    """Upload a built carousel dir to R2. Returns manifest of what landed."""
    env = _env()
    out_dir = Path(out_dir)
    files = sorted(p for p in out_dir.iterdir()
                   if p.is_file() and p.suffix.lower() in
                   (".jpg", ".jpeg", ".png", ".zip", ".json"))
    if not files:
        raise ValueError(f"nothing to back up in {out_dir}")
    uploaded = []
    for fp in files:
        data = fp.read_bytes()
        ctype = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                 "png": "image/png", "zip": "application/zip",
                 "json": "application/json"}.get(fp.suffix.lower().lstrip("."), "application/octet-stream")
        key = f"aoc/{content_id}/{fp.name}"
        url = f"{env['endpoint']}/{env['bucket']}/{urllib.parse.quote(key)}"
        _put(url, data, ctype, env)
        uploaded.append({"key": key, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
    # verify-after-write: one listing must show every key at the right size
    remote = _list_prefix(f"{env['endpoint']}/{env['bucket']}", f"aoc/{content_id}/", env)
    for f in uploaded:
        if remote.get(f["key"]) != f["bytes"]:
            raise RuntimeError(f"verify failed for {f['key']}: "
                               f"local {f['bytes']} vs remote {remote.get(f['key'])}")
    return {"bucket": env["bucket"], "prefix": f"aoc/{content_id}/",
            "files": uploaded, "total_bytes": sum(f["bytes"] for f in uploaded)}


def backup_store(content_id: str, store_dir: Path | str = "store",
                 receipts_path: Path | str = "receipts/content.jsonl") -> dict:
    """Back up one built carousel by content_id + write the receipt."""
    import json
    from core.receipt import append_receipt
    store = Path(store_dir)
    out_dir = store / content_id
    if not out_dir.exists():
        # dirs use the short display form — resolve via manifest content_id
        out_dir = None
        for manifest_fp in sorted(store.glob("*/manifest.json")):
            try:
                if json.loads(manifest_fp.read_text()).get("content_id") == content_id:
                    out_dir = manifest_fp.parent
                    break
            except (json.JSONDecodeError, OSError):
                continue
    if out_dir is None or not out_dir.exists():
        raise ValueError(f"no local build for content_id {content_id[:24]}…")
    manifest = backup_carousel(out_dir, content_id)
    receipt = append_receipt(receipts_path, "backed_up",
                             {"content_id": content_id, **manifest})
    return {"manifest": manifest, "receipt": receipt}
