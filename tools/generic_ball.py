"""The spin ball for extras whose sheets have none: Sonic Mania's own plain spin ball (SEGA / Sonic Team), in each
character's colours.

The frames are the first two of Mania Sonic's "Jump" (Data/Sprites/Players/Sonic1.gif (153,81) and (186,81), 32x32:
a plain sphere with a sparkle, no Sonic features), kept in the repo as testmods/_shared/mania_ball.png (SOURCE.txt
there), exact pixels. They replaced NoSwap's own drawn ball (the user, 2026-09-30: no AI-drawn art). Each is cut to
the ball's own 30x30 box (the old ball's size) and mapped BY INDEX to 5 roles, 1 outline, 2 dark, 3 mid, 4 light,
5 shine (0 = clear):

    Mania index   64 65 (darkest blues: the shadow crescent and rim)  -> 1 outline
                  66    (the shading band)                            -> 2 dark
                  67    (the main fill, Sonic's main blue)            -> 3 mid
                  68 69 (the lit edge round the sparkle)              -> 4 light
                  11 41 (the sparkle: pale cyan glint, white centre)  -> 5 shine

Each character fills the 5 roles with colours from their OWN palette (exact values, so nothing new needs a slot). A
config uses it like tools/sonic_ball.py's borrowed balls:

    ball = generic_ball.source_with_ball(sheet, colours, background, out_path)   # the working sheet + frame specs
    cfg = generic_ball.apply(cfg, ball, game)                                    # jump, Spin Dash, special stages

`colours` is {"outline", "dark", "mid", "light", "shine"} -> "#rrggbb" (or a 5-list in that order): pick them with
colours(...) from the character's palette (the outline, if not given, is a shade just darker than the body from the
palette passed: outline_for), or give all five explicitly. The config then carries "ball": "generic" (a marker,
ignored by sheet2ani) so it's clear where its ball came from.

Size: 30 px (the frames as ripped). Another size (Bomb 24, Big 40; the user, 2026-09-30) is a nearest-neighbour
resize of the same pixels: hard pixels, the same indices, nothing redrawn or smoothed.

Run it on its own for a preview of the characters that use it (ball_preview.png in the working directory).
"""
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "testmods" / "_shared" / "mania_ball.png"  # the two frames, 32x32 each, side by side
BOX = (1, 1, 31, 31)  # the ball inside each 32x32 frame
SIZE = 30
FRAMES = 2
ROLES = ("outline", "dark", "mid", "light", "shine")  # role indices 1-5
MANIA_TO_ROLE = {64: 1, 65: 1, 66: 2, 67: 3, 68: 4, 69: 4, 11: 5, 41: 5}
S3K_JUMP = [0, 0, 1, 1] * 2  # S3&K's Jump has 8 frames (the game's code counts them); each shown twice: half speed
S3K_SPINDASH = [0, 0, 1, 1, 0, 0, 1, 1, 0, 0]  # and its Spindash 10


def frame(k, n=FRAMES, size=SIZE):
    """Frame k (0 or 1): a paletted size x size image in role indices 0-5; 30 px as ripped, another size resized
    nearest-neighbour."""
    src = Image.open(SOURCE)
    x = 32 * (k % FRAMES)
    cut = src.crop((x + BOX[0], BOX[1], x + BOX[2], BOX[3]))
    img = Image.new("P", cut.size, 0)
    a, b = cut.load(), img.load()
    for yy in range(cut.height):
        for xx in range(cut.width):
            if a[xx, yy]:
                b[xx, yy] = MANIA_TO_ROLE[a[xx, yy]]
    if size != SIZE:
        img = img.resize((size, size), Image.NEAREST)
    return img


def frames(n=FRAMES, size=SIZE):
    return [frame(k, n, size) for k in range(n)]


def colours(outline=None, dark=None, mid=None, light=None, shine="#ffffff", palette=()):
    """The 5 colours from a character's own palette: the outline (the ball's shadow crescent and rim), 3 shades of the
    main body colour (dark to light) and the shine (white or the lightest colour). The outline (None) defaults to
    outline_for(dark, palette): a shade just darker than the body, not black; give one to override it."""
    if outline is None:
        outline = outline_for(dark, palette)
    return dict(zip(ROLES, (outline, dark, mid, light, shine)))


def outline_for(dark, palette=()):
    """The ball's outline: the next darker shade of the body's dark shade's hue among `palette` (the character's own
    colours, "#rrggbb"), or the dark shade itself when there's none. Never black (nor a near-black), unless the body
    itself is (Bomb)."""
    import colorsys
    hsv = lambda h: colorsys.rgb_to_hsv(*(c / 255 for c in _rgb(h)))
    dh, ds, _ = hsv(dark)

    def same_hue(c):
        h, s, v = hsv(c)
        if ds < 0.15 or s < 0.15:  # greys go with greys
            return ds < 0.15 and s < 0.15
        return min(abs(h - dh), 1 - abs(h - dh)) < 30 / 360

    luma = lambda c: sum(k * v for k, v in zip((0.299, 0.587, 0.114), _rgb(c)))  # how light it looks
    darker = [c for c in palette if luma(c) < luma(dark) and max(_rgb(c)) > 0x10 and same_hue(c)]
    return max(darker, key=luma) if darker else dark


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def coloured(img, cols):
    """A role-indexed frame in the character's colours, as RGB on a transparent (RGBA) canvas."""
    if not isinstance(cols, dict):
        cols = dict(zip(ROLES, cols))
    lut = {i: _rgb(cols[r]) + (255,) for i, r in enumerate(ROLES, 1)}
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    src, dst = img.load(), out.load()
    for y in range(img.height):
        for x in range(img.width):
            if src[x, y]:
                dst[x, y] = lut[src[x, y]]
    return out


def source_with_ball(sheet, cols, background, out_path, size=SIZE):
    """Write `sheet` (a path, or an RGB image) with the ball's frames, in `cols`, in a strip underneath to out_path
    (the sheet file itself is untouched). Returns the frame specs in frame order ([{"rect", "anchor_box"}, ...]; the
    anchor box is the whole size x size frame, so every frame sits exactly where the last did). size: the ball's
    diameter in px (30: as ripped; Bomb 24, Big 40: nearest-neighbour resizes)."""
    src = sheet if isinstance(sheet, Image.Image) else Image.open(sheet)
    src = src.convert("RGB")
    bg = _rgb(background)
    y = src.height + 2
    out = Image.new("RGB", (max(src.width, 2 + FRAMES * (size + 2)), y + size + 2), bg)
    out.paste(src, (0, 0))
    specs = []
    for k, img in enumerate(frames(size=size)):
        x = 2 + k * (size + 2)
        rgba = coloured(img, cols)
        out.paste(rgba, (x, y), rgba)
        r = [x, y, size, size]
        specs.append({"rect": r, "anchor_box": r})
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)
    return specs


def apply(cfg, ball, game):
    """Give a sheet2ani config (Sonic's template) the ball: Jumping (centred on the player, like Sonic's ball) and Spin
    Dash (the same frames, on his feet line), in every game; S1's special stage (its extra_anis "Special Stage", if the
    config has one; S2's, CD's and S3&K's come from Jumping); CD's own names and S3&K's frame counts from the Sonic 2
    config (cd_animations / s3k_animations)."""
    # each of the 2 frames twice: at the games' ball speeds a 2-frame flicker ran far too fast (the user, 2026-09-30)
    slow = [f for f in ball for _ in (0, 1)]
    jump = {"frames": slow, "anchor": "center"}
    spin = {"frames": slow}
    cfg["ball"] = "generic"
    cfg["animations"]["Jumping"] = jump
    cfg["animations"]["Spin Dash"] = spin
    for extra in cfg.get("extra_anis", []):
        if "Special Stage" in extra.get("animations", {}):
            extra["animations"]["Special Stage"] = jump
    if game == "Sonic2":
        cfg.setdefault("cd_animations", {}).update({"Jumping": jump, "Spin Dash": spin})
        cfg.setdefault("s3k_animations", {}).update({
            "Jump": {"frames": [ball[k] for k in S3K_JUMP], "anchor": "center"},
            "Spindash": {"frames": [ball[k] for k in S3K_SPINDASH]}})
    return cfg


# ---------------------------------------------------------------- character.json "ball" (tools/character_json.py)

SIZES = {"small": 24, "medium": 30, "large": 40}  # (Bomb's, everyone's, Big's)
USE_FOR = ("Spin Dash", "Jumping", "Rolling", "Special Stage")
DEFAULT_USE_FOR = ("Spin Dash",)


def animations_for(ball, use_for):
    """What a character.json "ball" sets, as apply() does for the make_configs.py characters but only for the
    animations in use_for: {"animations": S1/S2 names, "special": Sonic 1's special stage, "appended": ability slots
    ("Rolling" is slot 49, with extras.py "roll"), "cd": cd_animations, "s3k": s3k_animations}. Each of the 2 frames
    is shown twice (apply's "slow"); S3&K keeps its own frame counts (S3K_JUMP / S3K_SPINDASH)."""
    slow = [f for f in ball for _ in (0, 1)]
    jump = {"frames": slow, "anchor": "center"}
    spin = {"frames": slow}
    out = {"animations": {}, "special": {}, "appended": {}, "cd": {}, "s3k": {}}
    if "Jumping" in use_for:
        out["animations"]["Jumping"] = out["cd"]["Jumping"] = jump
        out["s3k"]["Jump"] = {"frames": [ball[k] for k in S3K_JUMP], "anchor": "center"}
    if "Spin Dash" in use_for:
        out["animations"]["Spin Dash"] = out["cd"]["Spin Dash"] = spin
        out["s3k"]["Spindash"] = {"frames": [ball[k] for k in S3K_SPINDASH]}
    if "Rolling" in use_for:  # (the speed: Mario's own curl's, the one other slot 49)
        out["appended"]["49"] = {"name": "Rolling", "frames": slow, "anchor": "center", "speed": 240}
    if "Special Stage" in use_for:
        out["special"]["Special Stage"] = jump
    return out


def _luma(c):
    return sum(k * v for k, v in zip((0.299, 0.587, 0.114), _rgb(c)))


def same_hue(a, b):
    """outline_for's test: two colours of one hue (within 30 degrees), or both greys."""
    import colorsys
    (ha, sa, _), (hb, sb, _) = (colorsys.rgb_to_hsv(*(x / 255 for x in _rgb(c))) for c in (a, b))
    if sa < 0.15 or sb < 0.15:
        return sa < 0.15 and sb < 0.15
    return min(abs(ha - hb), 1 - abs(ha - hb)) < 30 / 360


def _saturation(c):
    import colorsys
    return colorsys.rgb_to_hsv(*(x / 255 for x in _rgb(c)))[1]


def auto_colours(counts, palette):
    """The 5 ball colours picked from a character's own colours ("colours": "auto"). counts: {"#rrggbb": pixels} over
    his frames, in palette colours; palette: every colour he has. The main body colour is his most used colour
    (near-whites left out: shines, eyes, gloves); dark / mid / light are the darkest, the most used and the lightest
    of its shades (his colours of the same hue, same_hue). A body with fewer than 3 shades (a black or grey body:
    Bomb) also takes his greyish colours (low saturation) for the lit side. The outline is outline_for(dark),
    the shine his lightest colour."""
    pale = lambda c: min(_rgb(c)) >= 0xd0
    body = {c: n for c, n in counts.items() if n and not pale(c)} or dict(counts)
    if not body:
        raise ValueError("no colours to pick a ball from")
    seed = max(body, key=lambda c: (body[c], c))
    shades = [c for c in body if same_hue(seed, c)]
    if len(shades) < 3:
        shades += [c for c in body if c not in shades and _saturation(c) < 0.35 and _luma(c) > _luma(seed)]
    shades.sort(key=_luma)
    dark, light = shades[0], shades[-1]
    mid = seed
    if mid in (dark, light) and len(shades) >= 3:
        mid = max(shades[1:-1], key=lambda c: body[c])
    elif len(shades) == 2:
        mid = light if seed == dark else seed
    shine = max(palette, key=_luma) if palette else light
    if _luma(shine) <= _luma(light):
        shine = light
    return colours(dark=dark, mid=mid, light=light, shine=shine, palette=list(palette))


def _config_colours():
    """Each user's BALL_COLOURS and size, read from their make_configs.py (for the preview)."""
    import importlib.util
    import sys
    sys.path.insert(0, str(REPO / "tools"))
    out = {}
    for name in ("big", "bomb", "chaos", "emerl", "heavy", "mephiles", "robotnik"):
        path = REPO / "testmods" / name / "make_configs.py"
        spec = importlib.util.spec_from_file_location(f"_ball_{name}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out[name] = (mod.BALL_COLOURS, getattr(mod, "BALL_SIZE", 40 if name == "big" else SIZE))
    return out


def preview(path="ball_preview.png", scale=4):
    """Every user's ball, both frames at their size (rows), plus the Mania original (top row)."""
    rows = _config_colours()
    cell = max(s for _, s in rows.values()) + 4
    sheet = Image.new("RGB", (FRAMES * cell + 4, (len(rows) + 1) * cell + 4), (40, 40, 60))
    src = Image.open(SOURCE).convert("RGBA")
    sheet.paste(src, (4, 4), src)
    for r, (cols, size) in enumerate(rows.values(), 1):
        for k, f in enumerate(frames(size=size)):
            rgba = coloured(f, cols)
            sheet.paste(rgba, (4 + k * cell, 4 + r * cell), rgba)
    sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST).save(path)
    return path


if __name__ == "__main__":
    print(preview())
