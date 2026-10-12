#!/usr/bin/env python3
# The title card's lettering: a serif set in warm white with a soft gold glow, on transparency.
# (The game has one built-in sans font; this renders the title once with Noto Serif, OFL.)
#   python3 tools/title_art.py  ->  assets/title.png
import os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/usr/share/fonts/google-noto-vf/NotoSerif[wght].ttf"
FONT_I = "/usr/share/fonts/google-noto-vf/NotoSerif-Italic[wght].ttf"
W, H = 2048, 560
out = os.path.join(os.path.dirname(__file__), "..", "assets", "title.png")

def font(path, size, weight):
    f = ImageFont.truetype(path, size)
    try: f.set_variation_by_name(weight)
    except Exception: pass
    return f

def spaced(d, x, y, s, f, spacing, fill):
    # draw letter by letter with extra tracking; returns the width
    cx = x
    for ch in s:
        d.text((cx, y), ch, font=f, fill=fill)
        cx += d.textlength(ch, font=f) + spacing
    return cx - x - spacing

def width(d, s, f, spacing):
    return sum(d.textlength(ch, font=f) for ch in s) + spacing * (len(s) - 1)

def layout(d, fill):
    small = font(FONT, 46, b"Medium")
    big = font(FONT, 150, b"SemiBold")
    mid = font(FONT_I, 80, b"Regular")
    top = "THE LEGEND OF JO"
    w = width(d, top, small, 22)
    spaced(d, (W - w) / 2, 30, top, small, 22, fill)
    parts = [("SLOP", big, 10, 0), ("of the", mid, 2, 52), ("WILD", big, 10, 0)]
    gap = 38
    total = sum(width(d, s, f, sp) for s, f, sp, _ in parts) + gap * 2
    x = (W - total) / 2
    for s, f, sp, dy in parts:
        x += spaced(d, x, 120 + dy, s, f, sp, fill) + gap
    # a thin rule with a diamond under it
    y = 340
    d.line([(W / 2 - 330, y), (W / 2 - 22, y)], fill=fill, width=3)
    d.line([(W / 2 + 22, y), (W / 2 + 330, y)], fill=fill, width=3)
    d.polygon([(W / 2, y - 12), (W / 2 + 12, y), (W / 2, y + 12), (W / 2 - 12, y)], fill=fill)

glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
layout(ImageDraw.Draw(glow), (255, 196, 110, 150))
glow = glow.filter(ImageFilter.GaussianBlur(14))
shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
layout(ImageDraw.Draw(shade), (40, 28, 12, 110))
shade = shade.filter(ImageFilter.GaussianBlur(5))
img = Image.alpha_composite(glow, shade)
letters = Image.new("RGBA", (W, H), (0, 0, 0, 0))
layout(ImageDraw.Draw(letters), (255, 248, 230, 255))
img = Image.alpha_composite(img, letters)
img = img.crop(img.getbbox())
img.save(out)
print("wrote", out, img.size)
