"""
qr.py — QR code generator and scanner (CLI).

Generate:
    python qr.py gen "https://homso.ru"                     -> qr.png
    python qr.py gen "hello" -o hello.png --fg "#6c8cff"    -> colored QR
    python qr.py gen "hello" --ec H --box 12                -> larger modules
    python qr.py gen "https://t.me/hatuj" --logo me.png     -> QR with logo in the middle
    python qr.py gen "wi-fi" --svg out.svg                  -> vector output

Scan:
    python qr.py scan qr.png
    python qr.py scan photo.jpg --draw scan_drawn.png       -> annotated preview
    python qr.py scan folder/ --all                         -> every image in a folder
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import qrcode
from PIL import Image, ImageDraw
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q

EC_LEVELS = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M, "Q": ERROR_CORRECT_Q, "H": ERROR_CORRECT_H}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


# ---------------------------------------------------------------- colors


def parse_color(value: str) -> tuple[int, int, int]:
    """Parse '#rgb', '#rrggbb', 'rrggbb' or 'r,g,b' into an RGB tuple."""
    named = {"white": "#ffffff", "black": "#000000", "blue": "#6c8cff", "red": "#ff3b3b"}
    v = named.get(value.lower(), value).lstrip("#")
    if "," in v:
        parts = [int(p) for p in v.split(",")]
        if len(parts) != 3 or any(not 0 <= p <= 255 for p in parts):
            raise ValueError(f"Bad RGB color: {value}")
        return tuple(parts)  # type: ignore[return-value]
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6:
        raise ValueError(f"Bad hex color: {value}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


# ------------------------------------------------------------- generator


def build_qr(data: str, ec: str = "M", box: int = 10, border: int = 4,
             fg: tuple[int, int, int] = (0, 0, 0), bg: tuple[int, int, int] = (255, 255, 255),
             logo: Path | None = None, logo_ratio: float = 0.22) -> Image.Image:
    """Return a ready-to-save QR image (RGB)."""
    if not data.strip():
        raise ValueError("Empty data: nothing to encode")
    if ec not in EC_LEVELS:
        raise ValueError(f"EC level must be one of {', '.join(EC_LEVELS)}")
    if not 1 <= box <= 100:
        raise ValueError("box must be between 1 and 100")

    qr = qrcode.QRCode(version=None, error_correction=EC_LEVELS[ec], box_size=box, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fg, back_color=bg).convert("RGB")

    if logo is not None:
        img = _paste_logo(img, logo, logo_ratio, bg)
    return img


def _paste_logo(img: Image.Image, logo_path: Path, ratio: float, bg: tuple[int, int, int]) -> Image.Image:
    """Paste a logo into the center on a rounded white plate so the QR stays scannable."""
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except OSError as exc:
        raise ValueError(f"Cannot open logo: {logo_path}") from exc

    side = int(min(img.size) * max(0.05, min(ratio, 0.35)))
    logo.thumbnail((side, side), Image.LANCZOS)

    plate_pad = max(4, side // 12)
    pw, ph = logo.width + plate_pad * 2, logo.height + plate_pad * 2
    plate = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=plate_pad,
                                            fill=(*bg, 255))
    plate.alpha_composite(logo, (plate_pad, plate_pad))

    out = img.convert("RGBA")
    pos = ((img.width - pw) // 2, (img.height - ph) // 2)
    out.alpha_composite(plate, pos)
    return out.convert("RGB")


def save(img: Image.Image, out: Path, fmt: str = "png") -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt.lower() == "svg":
        raise ValueError("Use save_svg() for SVG output")
    img.save(out, format="PNG", optimize=True)
    return out


def save_svg(img: Image.Image, out: Path) -> Path:
    """Embed the raster QR into an SVG wrapper (simple and dependency-free)."""
    import base64
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    w, h = img.size
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'viewBox="0 0 {w} {h}" shape-rendering="crispEdges">\n'
           f'  <image width="{w}" height="{h}" '
           f'href="data:image/png;base64,{b64}"/>\n</svg>\n')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    return out


# --------------------------------------------------------------- scanner


def decode_image(img: Image.Image) -> list[str]:
    """Decode every QR/barcode found in a PIL image."""
    arr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    results: list[str] = []

    # 1) multi-code detection first (accurate and returns positions)
    try:
        ok, decoded, _, _ = detector.detectAndDecodeMulti(arr)
        if ok:
            results = [d for d in decoded if d]
    except cv2.error:
        pass

    # 2) single-code fallback (handles some perspective-distorted photos)
    if not results:
        try:
            data, _, _ = detector.detectAndDecode(arr)
            if data:
                results = [data]
        except cv2.error:
            pass
    return results


def draw_boxes(img: Image.Image, points) -> Image.Image:
    """Draw green outlines around found QR codes."""
    arr = np.array(img.convert("RGB")).copy()
    detector = cv2.QRCodeDetector()
    try:
        ok, _, pts, _ = detector.detectAndDecodeMulti(arr)
    except cv2.error:
        return Image.fromarray(arr)
    if not ok or pts is None:
        return Image.fromarray(arr)
    for quad in pts:
        poly = quad.astype(int).reshape(-1, 2)
        cv2.polylines(arr, [poly], isClosed=True, color=(0, 220, 130), thickness=3)
    return Image.fromarray(arr)


# ------------------------------------------------------------ interactive

BANNER = """
  ========================================
   QR Toolkit - генератор и сканер кодов
  ========================================
"""

PRESETS = {
    "1": ("Ссылка / текст", None, None),
    "2": ("Telegram-ссылка", "https://t.me/your_channel", None),
    "3": ("Wi-Fi (SSID + пароль)", None, "wifi"),
    "4": ("Контакт (vCard)", None, "vcard"),
    "5": ("EC (email)", None, "email"),
}


def _ask(prompt: str, default: str = "") -> str:
    """input() that returns ``default`` on empty input and never raises EOFError."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        return default
    return value or default


def _ask_yes(prompt: str, default: bool = False) -> bool:
    v = _ask(f"{prompt} (д/н)", "д" if default else "н").lower()
    return v in {"д", "да", "y", "yes", "1"}


def _pick(title: str, options: list[tuple[str, str]], default: str) -> str:
    """Numbered choice prompt. Returns the selected key."""
    print(f"\n{title}")
    for key, label in options:
        mark = " (по умолчанию)" if key == default else ""
        print(f"  {key}) {label}{mark}")
    keys = {k for k, _ in options}
    while True:
        choice = _ask("Выбор", default)
        if choice in keys:
            return choice
        print("  ! Введите номер из списка")


def _wifi_payload() -> str | None:
    ssid = _ask("Имя сети (SSID)")
    if not ssid:
        print("  ! SSID обязателен")
        return None
    enc = _ask("Шифрование (WPA/WEP/nopass)", "WPA").upper()
    pwd = "" if enc == "NOPASS" else _ask("Пароль")
    esc = lambda s: s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")
    return f"wifi:T:{enc};S:{esc(ssid)};P:{esc(pwd)};;" if pwd else f"wifi:T:{enc};S:{esc(ssid)};;"


def _vcard_payload() -> str | None:
    name = _ask("Имя и фамилия")
    if not name:
        print("  ! Имя обязательно")
        return None
    phone = _ask("Телефон", "")
    email = _ask("Email", "")
    org = _ask("Компания", "")
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{name}", f"FN:{name}"]
    if phone:
        lines.append(f"TEL;TYPE=CELL:{phone}")
    if email:
        lines.append(f"EMAIL:{email}")
    if org:
        lines.append(f"ORG:{org}")
    lines.append("END:VCARD")
    return "\n".join(lines)


def _email_payload() -> str | None:
    to = _ask("Кому (email)")
    if not to:
        print("  ! Email обязателен")
        return None
    subject = _ask("Тема", "")
    body = _ask("Текст", "")
    from urllib.parse import quote
    url = f"mailto:{to}"
    params = []
    if subject:
        params.append("subject=" + quote(subject))
    if body:
        params.append("body=" + quote(body))
    return url + ("?" + "&".join(params) if params else "")


def interactive() -> int:
    """Menu-driven mode: run without arguments to pick what to do."""
    print(BANNER)
    print("Что сделать?")
    print("  1) Сгенерировать QR")
    print("  2) Сканировать изображение")
    print("  0) Выход")

    action = _pick("Действие", [("1", "Сгенерировать"), ("2", "Сканировать"), ("0", "Выход")], "1")
    if action == "0":
        print("Пока!")
        return 0
    if action == "2":
        return _interactive_scan()
    return _interactive_gen()


def _interactive_gen() -> int:
    preset = _pick("Что закодировать?",
                   [(k, label) for k, (label, _, _) in PRESETS.items()], "1")

    label, fixed, kind = PRESETS[preset]
    if kind == "wifi":
        data = _wifi_payload()
    elif kind == "vcard":
        data = _vcard_payload()
    elif kind == "email":
        data = _email_payload()
    else:
        data = _ask("Данные", fixed or "")
    if not data:
        print("  ! Нечего закодировать")
        return 2

    options: dict = {"data": data}

    ec = _ask("Уровень коррекции L/M/Q/H", "H" if kind in {"wifi", "vcard"} else "M").upper()
    options["ec"] = ec if ec in EC_LEVELS else "M"

    custom = _ask_yes("Свои цвета?", False)
    if custom:
        options["fg"] = _ask("Цвет кода", "#0b0d12")
        options["bg"] = _ask("Цвет фона", "#ffffff")

    size = _ask("Размер модуля (пикселей)", "10")
    options["box"] = int(size) if size.isdigit() and 1 <= int(size) <= 100 else 10

    logo = _ask("Путь к логотипу (Enter — без логотипа)", "")
    if logo:
        options["logo"] = Path(logo)
        options["ec"] = "H"  # logo needs strong correction

    as_svg = _ask_yes("Сохранить как SVG?", False)
    out = _ask("Имя файла", "out.svg" if as_svg else "qr.png")

    try:
        img = build_qr(**options)
        path = save_svg(img, Path(out)) if as_svg else save(img, Path(out))
    except (ValueError, OSError) as exc:
        print(f"  ! Ошибка: {exc}")
        return 2

    print(f"\n✓ Готово: {path} ({img.width}x{img.height}px)")

    if _ask_yes("Проверить, что читается?", True):
        codes = decode_image(img)
        print(f"  Считано: {codes[0]}" if codes else "  ! Не распознан (увеличьте размер)")
    return 0


def _interactive_scan() -> int:
    target = _ask("Файл или папка с картинками")
    if not target:
        return 2
    p = Path(target)
    if not p.exists():
        print(f"  ! Не найдено: {p}")
        return 2

    args = argparse.Namespace(inputs=[p], draw=None)
    if _ask_yes("Сохранить превью с контуром?", False):
        args.draw = Path(_ask("Имя превью", "scan.png"))
    return cmd_scan(args)


# -------------------------------------------------------------------- CLI


def cmd_gen(args) -> int:
    try:
        img = build_qr(
            data=args.data,
            ec=args.ec,
            box=args.box,
            border=args.border,
            fg=parse_color(args.fg),
            bg=parse_color(args.bg),
            logo=args.logo,
            logo_ratio=args.logo_ratio,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.svg:
        path = save_svg(img, args.svg)
    else:
        out = args.output or Path("qr.png")
        path = save(img, out)
    print(f"Saved: {path}  ({img.width}x{img.height}px)")
    return 0


def cmd_scan(args) -> int:
    targets: list[Path] = []
    for p in args.inputs:
        if p.is_dir():
            targets.extend(sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXTS))
        else:
            targets.append(p)

    if not targets:
        print("No images to scan.", file=sys.stderr)
        return 2

    found_any = False
    for path in targets:
        if not path.is_file():
            print(f"{path}: file not found", file=sys.stderr)
            continue
        try:
            img = Image.open(path)
        except OSError:
            print(f"{path}: cannot open image", file=sys.stderr)
            continue

        codes = decode_image(img)
        if not codes:
            print(f"{path}: no QR code found")
            continue

        found_any = True
        for i, code in enumerate(codes, 1):
            print(f"{path} [#{i}]: {code}")

        if args.draw:
            out = args.draw if len(targets) == 1 else args.draw.with_stem(
                f"{args.draw.stem}_{path.stem}")
            draw_boxes(img, codes).save(out)
            print(f"  preview: {out}")

    return 0 if found_any else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="QR code generator and scanner.")
    sub = ap.add_subparsers(dest="command", required=False)

    g = sub.add_parser("gen", help="generate a QR code")
    g.add_argument("data", help="text or URL to encode")
    g.add_argument("-o", "--output", type=Path, help="output PNG path (default qr.png)")
    g.add_argument("--svg", type=Path, help="write SVG instead of PNG")
    g.add_argument("--ec", default="M", choices=list(EC_LEVELS),
                   help="error correction level: L, M, Q, H (default M)")
    g.add_argument("--box", type=int, default=10, help="module size in pixels (default 10)")
    g.add_argument("--border", type=int, default=4, help="quiet zone in modules (default 4)")
    g.add_argument("--fg", default="black", help="foreground color")
    g.add_argument("--bg", default="white", help="background color")
    g.add_argument("--logo", type=Path, help="logo image to place in the center")
    g.add_argument("--logo-ratio", type=float, default=0.22,
                   help="logo size relative to QR side (default 0.22)")
    g.set_defaults(func=cmd_gen)

    s = sub.add_parser("scan", help="decode QR codes from images")
    s.add_argument("inputs", nargs="+", type=Path, help="image files or folders")
    s.add_argument("--draw", type=Path, help="save an annotated preview")
    s.set_defaults(func=cmd_scan)

    args = ap.parse_args()
    if not args.command:
        return interactive()
    return args.func(args)


def _force_utf8_console() -> None:
    """Windows consoles default to cp1251; make sure Cyrillic and symbols print."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


if __name__ == "__main__":
    _force_utf8_console()
    raise SystemExit(main())
