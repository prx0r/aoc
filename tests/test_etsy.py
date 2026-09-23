"""Etsy packet + photo QC tests. Synthetic fixtures only (no real photos yet)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.etsy_packet import build_packet, validate_copy  # noqa: E402
from core.photo_qc import check_packet_photos, check_photo  # noqa: E402


def test_all_hero_listings_pass_copy_rules():
    root = Path(__file__).parent.parent / "segments/garden_familiars/etsy"
    for fp in sorted(root.glob("*.md")):
        v = validate_copy(fp)
        assert v["passed"], (fp.name, {k: x for k, x in v["checks"].items() if not x["ok"]})


def test_packet_has_ten_slots_and_video():
    p = build_packet("garden_familiars", "sir-hopsalot",
                     Path(__file__).parent.parent / "segments/garden_familiars/etsy/sir-hopsalot.md")
    assert len(p["slots"]) == 10
    assert p["copy_valid"]
    assert "video" in p and "MP4" in p["video"]["builder"] or "mp4" in str(p["video"]).lower()


def _sharp_image(path: Path, blur: bool = False):
    from PIL import Image, ImageDraw, ImageFilter
    im = Image.new("RGB", (2100, 2100), (30, 60, 30))
    d = ImageDraw.Draw(im)
    for i in range(0, 2100, 40):
        d.line([(i, 0), (i, 2100)], fill=(200, 220, 200), width=6)
        d.line([(0, i), (2100, i)], fill=(200, 220, 200), width=6)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(8))
    im.save(path, "JPEG", quality=92)


def test_photo_qc_passes_sharp_rejects_blurry(tmp_path):
    sharp = tmp_path / "sharp.jpg"
    blurry = tmp_path / "blurry.jpg"
    tiny = tmp_path / "tiny.jpg"
    _sharp_image(sharp)
    _sharp_image(blurry, blur=True)
    from PIL import Image
    Image.new("RGB", (400, 400), (10, 10, 10)).save(tiny)
    assert check_photo(sharp)["ok"]
    r = check_photo(blurry)
    assert not r["ok"] and "blurry" in r["issues"]
    r = check_photo(tiny)
    assert not r["ok"] and any("below_etsy_minimum" in i for i in r["issues"])


def test_packet_photo_gate(tmp_path):
    sharp = tmp_path / "a.jpg"
    _sharp_image(sharp)
    r = check_packet_photos([sharp, sharp, sharp])
    assert r["verdict"] == "PASS" and r["ok_photos"] == 3
    r = check_packet_photos([sharp])
    assert r["verdict"] == "NEEDS_REPLACEMENT"
