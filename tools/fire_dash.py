"""S3&K's fire dash flame (the Fire Shield's "Fire Attack"), layered behind an extra's dash frames.

`source_with_fire` writes a working copy of the extra's sheet with the flame frames added in a strip
underneath (the original sheet file is untouched), turned 45 degrees for the up / down dashes, and returns
layered frame specs for a config: the flame behind, the extra's pose in front, placed as S3&K places the
flame around Sonic. The flame follows S3&K's own frame order; each flame drawing has its own pose under it, so repeats of a
drawing are the same frame (less sprite memory).

The sheet draws the flame in palette slots S3&K colours at runtime; FLAME maps those slots to colours.
"""
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SHIELDS = REPO / "extracted" / "Sonic3K" / "Data" / "Sprites" / "3K_Global" / "Shields"

# 3K_Global/Shields.bin "Fire Attack": (x, y, w, h, pivot x, pivot y) of its 4 drawings, and the order
# the animation plays them in (2 game frames each)
FIRE = [(64, 175, 20, 43, 8, -22), (85, 175, 48, 46, -20, -23), (135, 175, 56, 38, -28, -19),
        (192, 166, 63, 47, -32, -24)]
ORDER = [0, 1, 2, 0, 2, 3]
FLAME = {6: "#e00000", 10: "#fc9000", 16: "#fcfc00"}  # outline red, orange rim, yellow core

hexrgb = lambda h: tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))


def flame(k, angle):
    """Flame drawing k turned `angle` degrees (counter-clockwise) about the player's centre.
    Returns (RGBA image, (x, y) of its top-left relative to the player's centre)."""
    sheet = Image.open(SHIELDS.with_suffix(".gif"))
    x, y, w, h, px, py = FIRE[k]
    src = sheet.crop((x, y, x + w, y + h))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for yy in range(h):
        for xx in range(w):
            i = src.getpixel((xx, yy))
            if i:
                img.putpixel((xx, yy), hexrgb(FLAME[i]) + (255,))
    c = 96  # a canvas around the player's centre, so the turn is about that point
    canvas = Image.new("RGBA", (2 * c, 2 * c), (0, 0, 0, 0))
    canvas.paste(img, (c + px, c + py))
    if angle:
        canvas = canvas.rotate(angle, resample=Image.NEAREST)
    box = canvas.getbbox()
    return canvas.crop(box), (box[0] - c, box[1] - c)


def source_with_fire(sheet, background, out_path, dashes):
    """dashes: {slot: (pose rects, angle)}. Returns {slot: [layered frame spec, ...]}."""
    src = Image.open(sheet).convert("RGB")
    bg = hexrgb(background)
    pieces, specs = [], {}
    x, y, row_h = 2, src.height + 2, 0
    for slot, (poses, angle) in dashes.items():
        specs[slot] = []
        drawn = {}  # flame drawing -> (rect in the strip, offset): each is added once
        for k in ORDER:
            if k not in drawn:
                img, offset = flame(k, angle)
                if x + img.width + 2 > src.width:
                    x, y, row_h = 2, y + row_h + 2, 0
                drawn[k] = ([x, y, img.width, img.height], offset)
                pieces.append((img, (x, y)))
                x += img.width + 2
                row_h = max(row_h, img.height)
            rect, (fx, fy) = drawn[k]
            pose = poses[k % len(poses)]
            # the pose is centred on the player (the "center" anchor); the flame sits where S3&K puts it
            at = [fx + pose[2] // 2, fy + pose[3] // 2]
            specs[slot].append({"layers": [{"rect": rect, "at": at}, {"rect": pose, "at": [0, 0]}],
                                "anchor_layer": 1})
    out = Image.new("RGB", (src.width, y + row_h + 2), bg)
    out.paste(src, (0, 0))
    for img, pos in pieces:
        out.paste(img, pos, img)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    return specs
