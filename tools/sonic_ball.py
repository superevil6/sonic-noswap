"""Sonic's own spin ball, recoloured, for extras whose sheets have no curled-up jump frames.

Sonic's jump is curled-up frames alternating with a plain ball; his Spin Dash is a squashed ball. An
extra's config can borrow either: `source_with_ball` writes a working copy of the extra's sheet with the
recoloured frames added in a strip underneath (the original sheet file is untouched), and returns the
frames to use, positioned exactly like Sonic's (anchor_box = the full frame).

Recolouring is by Sonic's palette index, so every game's ball is taken from that game's own Sonic.
"""
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import sheet2ani  # noqa: E402

# Sonic's palette slots in his sprites: 1 outline, 2-5 blue fur (dark to light), 6-9 white/greys
# (gloves, shoe straps), 10-11 skin, 12-13 red shoes
FUR, SKIN, SHOES = (2, 3, 4, 5), (10, 11), (12, 13)


def sonic_frames(game, anim, who="Sonic"):
    """The game's own frames of `who`'s `anim` (paletted crops): game "Sonic1" / "Sonic2" / "SonicCD" (v4: Data/
    Animations/<who>.ani) or "Sonic3K" (v5: 3K_Players/<who>.bin, S3&K's animation names). Tails' tails are a separate
    object in every one of them: his ball frames are the ball alone."""
    if game == "Sonic3K":
        import ani_v5
        sprites = REPO / "extracted" / "Sonic3K" / "Data" / "Sprites"
        ani = ani_v5.read_bin(sprites / "3K_Players" / f"{who}.bin")
    else:
        sprites = REPO / "extracted" / game / "Data" / "Sprites"
        ani = sheet2ani.read_ani(REPO / "extracted" / game / "Data" / "Animations" / f"{who}.ani")
    a = next(a for a in ani["anims"] if a["name"] == anim)
    sheets = [Image.open(sprites / s) for s in ani["sheets"]]
    return [sheets[f["sheet"]].crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])) for f in a["frames"]]


def recolour(frame, colours, background):
    """colours: {palette index or its "#rrggbb" in the game's sheet: "#rrggbb"} (by colour for a character whose
    indices differ between games: Tails); unlisted colours stay as they are."""
    pal = frame.getpalette()
    out = Image.new("RGB", frame.size, background)
    px, dst = frame.load(), out.load()
    for y in range(frame.height):
        for x in range(frame.width):
            i = px[x, y]
            if i == 0:
                continue
            own = tuple(pal[3 * i:3 * i + 3])
            c = colours.get(i) or colours.get("#%02x%02x%02x" % own)
            dst[x, y] = tuple(int(c[k:k + 2], 16) for k in (1, 3, 5)) if c else own
    return out


def source_with_ball(sheet, game, colours, background, out_path, anims=("Jumping",), scale=1, who="Sonic"):
    """Write `sheet` plus the recoloured frames of Sonic's `anims` to out_path (`scale`: bigger, for big
    characters; this is SEGA's ball, not the extra's art). Returns {anim: [frame spec, ...]} in Sonic's
    frame order, for a config's "frames". `who`: another of the game's characters' ball instead ("Tails": Sticks';
    `game` "Sonic3K" for S3&K's own, by its animation names). `sheet` may be out_path itself, to add another game's
    ball under the first (the rects already handed out stay valid)."""
    src = Image.open(sheet).convert("RGB")
    bg = tuple(int(background[k:k + 2], 16) for k in (1, 3, 5))
    strips, frames = [], {}
    y = src.height + 2
    for anim in anims:
        x, row_h, seen = 2, 0, {}
        frames[anim] = []
        for f in sonic_frames(game, anim, who):
            key = f.tobytes()
            if key not in seen:  # Sonic's jump repeats its plain ball: cut it once
                img = recolour(f, colours, bg)
                if scale != 1:
                    img = img.resize((round(f.width * scale), round(f.height * scale)), Image.NEAREST)
                seen[key] = [x, y, img.width, img.height]
                strips.append((img, (x, y)))
                x += img.width + 2
                row_h = max(row_h, img.height)
            r = seen[key]
            frames[anim].append({"rect": r, "anchor_box": r})
        y += row_h + 2
    out = Image.new("RGB", (max(src.width, max(p[0] + i.width for i, p in strips) + 2), y), bg)
    out.paste(src, (0, 0))
    for img, pos in strips:
        out.paste(img, pos)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    return frames
