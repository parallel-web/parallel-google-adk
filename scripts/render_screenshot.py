"""Render docs/screenshot.txt to a brand-styled PNG for the adk-docs PR.

Reads docs/screenshot.txt, lays it out in FT System Mono on Off-white using
Parallel's brand palette (per assets.parallel.ai/llms.txt style guide), and
writes docs/assets/research_agent.png.

Fonts and intermediate brand assets are downloaded on demand from
assets.parallel.ai (gitignored). The committed outputs are docs/assets/parallel.png
(the symbol logo) and docs/assets/research_agent.png (the rendered screenshot).

Run:
    .venv/bin/python scripts/render_screenshot.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "screenshot.txt"
DST = ROOT / "docs" / "assets" / "research_agent.png"

# Parallel brand palette (assets.parallel.ai/llms.txt).
OFF_WHITE = "#fcfcfa"
INDEX_BLACK = "#1d1b16"
NEURAL = "#d8d0bf"
SIGNAL = "#fb631b"

FONT_REGULAR = ROOT / "docs" / "assets" / "FTSystemMono-Regular.ttf"
FONT_BOLD = ROOT / "docs" / "assets" / "FTSystemMono-Bold.ttf"

FONT_URLS = {
    FONT_REGULAR: "https://assets.parallel.ai/FTSystemMono-Regular.ttf",
    FONT_BOLD: "https://assets.parallel.ai/FTSystemMono-Bold.ttf",
}


def ensure_fonts() -> None:
    """Download the brand fonts if they aren't already cached locally.

    assets.parallel.ai's CDN rejects the default urllib User-Agent (403);
    pass a browser-style UA so the request goes through.
    """
    for path, url in FONT_URLS.items():
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"fetching {url}", file=sys.stderr)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, path.open("wb") as fp:
            fp.write(resp.read())

# Layout.
WIDTH = 1400
PADDING_X = 70
PADDING_Y = 60
FONT_SIZE = 22
LINE_HEIGHT = int(FONT_SIZE * 1.55)
WRAP_WIDTH = 78  # chars

# Window-chrome dots (subtle, no labels).
DOT_RADIUS = 7
DOT_GAP = 22


def wrap(text: str, width: int) -> list[str]:
    """Word-wrap a single line of text to a max char width, preserving runs."""
    if len(text) <= width:
        return [text]
    out: list[str] = []
    line = ""
    for word in text.split(" "):
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= width:
            line = f"{line} {word}"
        else:
            out.append(line)
            line = word
    if line:
        out.append(line)
    return out


def color_for_line(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("$ "):
        return SIGNAL
    if stripped.startswith(">>>"):
        return SIGNAL
    if stripped.startswith("---"):
        return NEURAL
    if stripped.startswith("{"):
        return NEURAL
    return INDEX_BLACK


def font_for_line(line: str, regular: ImageFont.FreeTypeFont, bold: ImageFont.FreeTypeFont) -> ImageFont.FreeTypeFont:
    s = line.strip()
    if s.startswith("$ ") or s.startswith(">>>"):
        return bold
    return regular


def main() -> int:
    if not SRC.exists():
        print(f"missing: {SRC}", file=sys.stderr)
        return 1
    ensure_fonts()

    raw = SRC.read_text().splitlines()

    # Wrap long lines once for layout.
    lines: list[str] = []
    for line in raw:
        if not line:
            lines.append("")
        else:
            lines.extend(wrap(line, WRAP_WIDTH))

    regular = ImageFont.truetype(str(FONT_REGULAR), FONT_SIZE)
    bold = ImageFont.truetype(str(FONT_BOLD), FONT_SIZE)

    # Compute height: window-chrome row + padding + text + padding.
    chrome_height = PADDING_Y - 10
    text_height = max(LINE_HEIGHT * len(lines), 100)
    height = chrome_height + PADDING_Y + text_height + PADDING_Y

    img = Image.new("RGB", (WIDTH, height), OFF_WHITE)
    draw = ImageDraw.Draw(img)

    # Window chrome dots.
    cy = chrome_height // 2 + 18
    cx = PADDING_X + DOT_RADIUS
    for i in range(3):
        x = cx + i * DOT_GAP
        draw.ellipse(
            [(x - DOT_RADIUS, cy - DOT_RADIUS), (x + DOT_RADIUS, cy + DOT_RADIUS)],
            outline=NEURAL,
            width=2,
        )

    # Hairline separator between chrome and text.
    sep_y = chrome_height + PADDING_Y // 2
    draw.line(
        [(PADDING_X, sep_y), (WIDTH - PADDING_X, sep_y)],
        fill=NEURAL,
        width=1,
    )

    # Text.
    y = sep_y + PADDING_Y // 2
    for line in lines:
        if line == "":
            y += LINE_HEIGHT
            continue
        font = font_for_line(line, regular, bold)
        color = color_for_line(line)
        draw.text((PADDING_X, y), line, font=font, fill=color)
        y += LINE_HEIGHT

    DST.parent.mkdir(parents=True, exist_ok=True)
    img.save(DST, optimize=True)
    print(f"wrote {DST} ({img.size[0]}x{img.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
