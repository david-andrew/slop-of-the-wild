#!/usr/bin/env python3
# The place names the game shows on arrival, set once in Noto Serif (OFL) like the title card:
# one line each in an atlas, with a soft shadow, and a list of where each one is.
#   python3 tools/names_art.py  ->  assets/names.png, assets/names.txt
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/usr/share/fonts/google-noto-vf/NotoSerif[wght].ttf"
FONT_I = "/usr/share/fonts/google-noto-vf/NotoSerif-Italic[wght].ttf"
here = os.path.join(os.path.dirname(__file__), "..", "assets")
names = ["Grate Plateau", "Temple of Thyme", "Forest of Sprites", "Eastern Abbey", "Mount Jolia",
         "River of the Dread", "Grate Plateau Tower", "Hopper Pond", "Shrine of Reheating",
         "Woodcutter's House", "Ohman Ow Shrine", "Jaba Badge Shrine", "Owa Dime Shrine", "Kay Nomut Shrine"]
subs = ["Magnet Trial", "Bomb Trial", "Pause Trial", "Ice Block Trial"]

def font(path, size, weight):
    f = ImageFont.truetype(path, size)
    try: f.set_variation_by_name(weight)
    except Exception: pass
    return f

big = font(FONT, 64, b"Medium")
small = font(FONT_I, 40, b"Regular")
LH = 100
W = 1400
lines = [(n, big) for n in names] + [(s, small) for s in subs] + [("Game Over", big)]
img = Image.new("RGBA", (W, LH * len(lines)), (0, 0, 0, 0))
rects = []
for i, (s, f) in enumerate(lines):
    line = Image.new("RGBA", (W, LH), (0, 0, 0, 0))
    d = ImageDraw.Draw(line)
    w = d.textlength(s, font=f)
    x = (W - w) / 2
    shade = Image.new("RGBA", (W, LH), (0, 0, 0, 0))
    ImageDraw.Draw(shade).text((x, 14), s, font=f, fill=(20, 16, 10, 150))
    shade = shade.filter(ImageFilter.GaussianBlur(4))
    d.text((x, 14), s, font=f, fill=(255, 250, 236, 255))
    line = Image.alpha_composite(shade, line)
    bb = line.getbbox()
    img.paste(line, (0, i * LH))
    rects.append((s, bb[0], i * LH + bb[1], bb[2] - bb[0], bb[3] - bb[1]))
img.save(os.path.join(here, "names.png"))
with open(os.path.join(here, "names.txt"), "w") as fo:
    for r in rects: fo.write("%s\t%d\t%d\t%d\t%d\n" % r)
print("wrote names.png", img.size, len(rects), "names")
