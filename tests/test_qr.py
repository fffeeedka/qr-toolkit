"""Tests for qr.py — run with: python -m pytest -q"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

import qr


# ------------------------------------------------------------ colors


def test_parse_color_named():
    assert qr.parse_color("black") == (0, 0, 0)
    assert qr.parse_color("white") == (255, 255, 255)
    assert qr.parse_color("blue") == (108, 140, 255)


def test_parse_color_hex_variants():
    assert qr.parse_color("#6c8cff") == (108, 140, 255)
    assert qr.parse_color("6c8cff") == (108, 140, 255)
    assert qr.parse_color("#fff") == (255, 255, 255)


def test_parse_color_rgb():
    assert qr.parse_color("10,20,30") == (10, 20, 30)


@pytest.mark.parametrize("bad", ["#12", "nope", "300,0,0", "1,2"])
def test_parse_color_invalid(bad: str):
    with pytest.raises(ValueError):
        qr.parse_color(bad)


# --------------------------------------------------------- generator


def test_build_qr_returns_rgb_image():
    img = qr.build_qr("https://example.com")
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.width == img.height


def test_box_size_changes_output_size():
    small = qr.build_qr("hello", box=5)
    big = qr.build_qr("hello", box=15)
    assert big.width > small.width


def test_longer_data_needs_bigger_matrix():
    short = qr.build_qr("hi", box=1, border=0)
    long = qr.build_qr("x" * 500, box=1, border=0)
    assert long.width > short.width


def test_empty_data_rejected():
    with pytest.raises(ValueError):
        qr.build_qr("   ")


def test_invalid_ec_level():
    with pytest.raises(ValueError):
        qr.build_qr("hello", ec="X")


def test_generated_qr_is_decodable(tmp_path: Path):
    img = qr.build_qr("https://homso.ru", ec="M", box=8)
    p = tmp_path / "qr.png"
    qr.save(img, p)
    assert qr.decode_image(Image.open(p)) == ["https://homso.ru"]


def test_logo_qr_still_decodable(tmp_path: Path):
    logo = Image.new("RGBA", (100, 100), (108, 140, 255, 255))
    logo_path = tmp_path / "logo.png"
    logo.save(logo_path)

    img = qr.build_qr("https://t.me/hatuj", ec="H", box=8, logo=logo_path)
    p = tmp_path / "with_logo.png"
    qr.save(img, p)
    assert qr.decode_image(Image.open(p)) == ["https://t.me/hatuj"]


def test_missing_logo_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        qr.build_qr("data", logo=tmp_path / "nope.png")


# ------------------------------------------------------------ output


def test_save_svg_creates_file(tmp_path: Path):
    img = qr.build_qr("hello", box=4)
    out = qr.save_svg(img, tmp_path / "qr.svg")
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<svg")
    assert "base64" in text


# ----------------------------------------------------------- scanner


def test_decode_blank_image_returns_empty(tmp_path: Path):
    blank = Image.new("RGB", (200, 200), (255, 255, 255))
    assert qr.decode_image(blank) == []


def test_scan_cli_folder(tmp_path: Path, capsys):
    qr.save(qr.build_qr("one", box=4), tmp_path / "a.png")
    qr.save(qr.build_qr("two", box=4), tmp_path / "b.png")

    args = type("A", (), {"inputs": [tmp_path], "draw": None})()
    assert qr.cmd_scan(args) == 0
    out = capsys.readouterr().out
    assert "one" in out and "two" in out
