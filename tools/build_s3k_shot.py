#!/usr/bin/env python3
"""S3&K shot art: 3K_Players/Shot.bin / Shot.gif, the projectile the NoSwap DLL throws for an extra with a "shot"
(abilities.py; the DLL reuses the game's SuperHammer object, Amy's thrown hammer, with this art).

The DLL plays animation 0 and hits with each frame's hitbox 0, so every frame gets the recipe's hitbox. NoSwap ships a
placeholder under the same names (write_placeholder: the redirect only serves names NoSwap ships); each extra with a
shot gets its own in its package (build, called by build_packages.build_s3k).

Recipes ("art" in the shot):
  flame   S3&K's Fire Shield "Fire Attack" drawings (fire_dash.FIRE; list of drawing numbers, played in turn), shrunk
          by "shrink" with nearest-neighbour (Mario's fireball: the user's one exception to the art rule for him, as in
          his S1/S2 throw, testmods/mario/make_configs.py). The flame's round head is its right end: the pivot is the
          head's centre. Its colours must be the extra's own palette slots (S3&K's bank 0, 64-95: the DLL writes them).
  spark   S3&K's Lightning Shield "Lightning Spark" drawings (Shields.bin; list of drawing numbers, played in turn),
          shrunk by "shrink" (Gamma's bolt; the user asked for it smaller than the game's): each shrink x shrink block
          becomes its brightest pixel, one of the block's own (no new colours, no smoothing; a plain nearest-neighbour
          sample loses the spark's 1 px arms). Round, so it's never turned. Its three colours go to the slots the target
          draws with (frames' palette: the engine's player colours the extra's art uses), each exact where there is
          one and the nearest by RGB otherwise, as build_s3k_art matches an extra's own art.
  dust    S3&K's Spin Dash dust ("Spin Dash" in 3K_Global/Dust.bin, on Explosions.gif; list of drawing numbers,
          played in turn), as drawn: a ground shockwave (Bark's slam, motion "ground"). Its foot sits "floor" px below the
          pivot (the shot's centre, radius above the floor), centred across; "mirror": flipped so its high side leads;
          mirrored with the shot when it runs left.
          Colours as the spark's: the target's slots, exact where there is one, the nearest by RGB otherwise.
  sheet   a loose drawing on the extra's own source sheet ("sheet": its path from the extra's folder, "drawing": its
          box [x, y, w, h]), one frame per entry of "turns" ("none", "flip_x", "flip_y", "rot90", "rot180", "rot270":
          only mirrors and quarter turns, the faithful art rule), played in turn (Sticks' boomerang spinning). The
          sheet's commonest colour is its background. Colours as the spark's: the target's slots, exact where there is
          one, the nearest by RGB otherwise. Pivot: the drawing's centre. "scale": enlarged nearest-neighbour first, as
          the extra's own frames are (Sticks' 1.2x, sheet2ani.scale_nearest). "crop": true takes every non-background
          pixel in the box as-is (a piece cut from a larger drawing, e.g. Sticks' staff tip), not only the loose ones.
          "background": more colours ("#rrggbb") that are background too, with "crop" (the cell a drawing sits in:
          Bean's bomb on its lavender cell) or without it (the loose drawings in a box of its own colour: Flicky's).
          "drawings": several boxes instead of "drawing" (and no "turns"): one frame per box, as drawn (Flicky's Animal
          Drop: a different critter per throw, the shot's "cycle"); a box may take a 5th entry, its turn (one of
          "turns": Fang's cork flipped for the down aims, "aim_frames"). "scales": with "drawings", a whole-number
          nearest-neighbour enlargement per box (pixel-exact; Marine's Electric Blast shrinking through 3x, 2x, 1x of
          her two sparks). "exclude": sheet boxes [x, y, w, h] whose pixels are
          left out of a "crop" (a piece joined to the drawing, cut off: the handle under Robotnik's weight).
          "hitboxes": one box per frame (in the frames' order) instead of the one "hitbox" for all: a shot whose art
          shrinks as it flies hits with a box shrinking with it (Marine's Electric Blast; the frames play once over its
          lifetime when that is ticks x frames - 1). Sonic 1/2 set the box per frame too (abilities.one_shot_looks),
          Sonic CD the shot's reach (shots_v3.update_body_of).
          "own_slots": true lets Sonic 1/2 and CD draw it with all the extra's own palette slots too, not only the
          colours its player sheets use (its script and palette file set them all): a drawing whose colours aren't on any
          of its player frames stays exact (Omega's fireball). S3&K always has them.

A second shot ("shot2", abilities.py: Robotnik's Bomb Drop) is animation 1 of the same Shot.bin (build's shot2); the DLL
plays the one its shot is.
"""
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import ani_v5  # noqa: E402
import fire_dash  # noqa: E402
from gifio import save_sheet  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
S3K = REPO / "extracted" / "Sonic3K" / "Data" / "Sprites"
SHOT = ["3K_Players/Shot.bin", "3K_Players/Shot.gif"]  # (relative to Sonic3ku/Data/Sprites)
HITBOXES = ["Outer Box", "Inner Box"]  # (the game's names; the SuperHammer reads box 0)


def base_palette(extra_palette):
    """Sonic's S3&K sheet palette with the extra's own colours in their slots (as build_s3k_art gives Extra.gif)."""
    pal = list(Image.open(S3K / "3K_Players" / "Sonic.gif").getpalette())
    pal += [0] * (768 - len(pal))
    for slot, rgb in extra_palette.items():
        pal[3 * slot:3 * slot + 3] = [(rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF]
    return pal


def flame_frames(art, extra):
    """[(P-mode image in the extra's slots, pivot x, pivot y)] for the recipe's flame drawings."""
    slots = {rgb: slot for slot, rgb in extra["palette"].items()}
    out = []
    for k in art["flame"]:
        img, _ = fire_dash.flame(k, 0)
        s = art.get("shrink", 1)
        img = img.resize((img.width // s, img.height // s), Image.NEAREST)
        img = img.crop(img.getbbox())
        p = Image.new("P", img.size, 0)
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = img.getpixel((x, y))
                if not a:
                    continue
                rgb = (r << 16) | (g << 8) | b
                if rgb not in slots:
                    sys.exit(f"{extra['name']}: shot flame colour #{rgb:06X} isn't one of its own palette slots")
                p.putpixel((x, y), slots[rgb])
        head = img.height // 2  # the round head at its right end: its centre, a head's half-height in from there
        out.append((p, -(img.width - 1 - head), -(img.height // 2)))
    return out


SHIELDS = S3K / "3K_Global" / "Shields"  # (.bin / .gif: the game's shields, the spark's source)
SPARK_ANIM = "Lightning Spark"


def spark_frames(art, extra, palette):
    """[(P-mode image in palette's slots, pivot x, pivot y)] for the recipe's spark drawings (the module's notes).
    palette: {slot: 0xRRGGBB} the target can draw with."""
    sheet = Image.open(SHIELDS.with_suffix(".gif"))
    src = sheet.getpalette()
    rgb = lambda i: (src[3 * i] << 16) | (src[3 * i + 1] << 8) | src[3 * i + 2]
    anim = next((a for a in ani_v5.read_bin(SHIELDS.with_suffix(".bin"))["anims"] if a["name"] == SPARK_ANIM), None)
    if not anim:
        sys.exit(f"shot: no {SPARK_ANIM!r} in {SHIELDS.with_suffix('.bin')}")
    drawings = [f for f in anim["frames"] if f["w"] and f["h"]]  # (its blank frame left out)

    def slot(i):
        c = rgb(i)
        exact = [s for s, v in palette.items() if v == c]
        if exact:
            return min(exact)
        dist = lambda v: sum((((c >> k) & 0xFF) - ((v >> k) & 0xFF)) ** 2 for k in (16, 8, 0))
        return min(palette, key=lambda s: (dist(palette[s]), s))

    bright = lambda i: sum((rgb(i) >> k) & 0xFF for k in (16, 8, 0))
    s = art.get("shrink", 1)
    out = []
    for k in art["spark"]:
        f = drawings[k]
        img = sheet.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
        w, h = -(-img.width // s), -(-img.height // s)
        p = Image.new("P", (w, h), 0)
        for y in range(h):
            for x in range(w):
                block = [img.getpixel((xx, yy)) for yy in range(y * s, min(img.height, y * s + s))
                         for xx in range(x * s, min(img.width, x * s + s))]
                block = [i for i in block if i]
                if block:
                    p.putpixel((x, y), slot(max(block, key=lambda i: (bright(i), -i))))
        p = p.crop(p.getbbox())
        out.append((p, -(p.width // 2), -(p.height // 2)))  # (round: its centre)
    return out


DUST = S3K / "3K_Global" / "Dust"  # (.bin: the game's dust puffs, their drawings on 3K_Global/Explosions.gif)
DUST_ANIM = "Spin Dash"


def dust_frames(art, extra, palette):
    """[(P-mode image in palette's slots, pivot x, pivot y)] for the recipe's dust drawings (the module's notes)."""
    anim = next((a for a in ani_v5.read_bin(DUST.with_suffix(".bin"))["anims"] if a["name"] == DUST_ANIM), None)
    if not anim:
        sys.exit(f"shot: no {DUST_ANIM!r} in {DUST.with_suffix('.bin')}")
    sheet = Image.open(S3K / "3K_Global" / "Explosions.gif")
    src = sheet.getpalette()
    rgb = lambda i: (src[3 * i] << 16) | (src[3 * i + 1] << 8) | src[3 * i + 2]

    def slot(i):
        c = rgb(i)
        exact = [s for s, v in palette.items() if v == c]
        if exact:
            return min(exact)
        dist = lambda v: sum((((c >> k) & 0xFF) - ((v >> k) & 0xFF)) ** 2 for k in (16, 8, 0))
        return min(palette, key=lambda s: (dist(palette[s]), s))

    out = []
    for k in art["dust"]:
        f = anim["frames"][k]
        img = sheet.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
        p = Image.new("P", img.size, 0)
        for y in range(img.height):
            for x in range(img.width):
                i = img.getpixel((x, y))
                if i:
                    p.putpixel((x, y), slot(i))
        p = p.crop(p.getbbox())
        if art.get("mirror"):  # (the cloud's high side leading: the game draws it trailing the Spin Dash)
            p = p.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        out.append((p, -(p.width // 2), art.get("floor", 8) - p.height))
    return out


TURNS = {"none": None, "flip_x": Image.Transpose.FLIP_LEFT_RIGHT, "flip_y": Image.Transpose.FLIP_TOP_BOTTOM,
         "rot90": Image.Transpose.ROTATE_90, "rot180": Image.Transpose.ROTATE_180, "rot270": Image.Transpose.ROTATE_270}


def loose_pixels(src, bg, x, y, w, h, more_bg=()):
    """The pixels (relative to x, y) of the drawings wholly inside the box: 8-connected blobs of non-background pixels
    that don't reach past it (a neighbouring frame overlapping the box is left out). more_bg: other background colours
    (RGBA tuples)."""
    W, H = src.size
    bgs = {bg, *more_bg}
    solid = lambda a, b: 0 <= a < W and 0 <= b < H and src.getpixel((a, b))[3] and src.getpixel((a, b)) not in bgs
    seen, out = set(), []
    for sy in range(y, y + h):
        for sx in range(x, x + w):
            if (sx, sy) in seen or not solid(sx, sy):
                continue
            blob, stack, inside = [], [(sx, sy)], True
            seen.add((sx, sy))
            while stack:
                a, b = stack.pop()
                blob.append((a, b))
                inside &= x <= a < x + w and y <= b < y + h
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        n = (a + da, b + db)
                        if n not in seen and solid(*n):
                            seen.add(n)
                            stack.append(n)
            if inside:
                out += [(a - x, b - y) for a, b in blob]
    if not out:
        sys.exit(f"shot: no loose drawing wholly inside {[x, y, w, h]}")
    return out


def sheet_frames(art, extra, palette):
    """[(P-mode image in palette's slots, pivot x, pivot y)] for the "sheet" recipe (the module's notes). palette:
    {slot: 0xRRGGBB} the target can draw with."""
    src = Image.open(extra["art"] / art["sheet"]).convert("RGBA")
    bg = max(src.getcolors(1 << 24), key=lambda c: c[0])[1]
    if "drawings" in art:  # several boxes: one frame each, as drawn (no turns); "scales": each one's own enlargement
        scales = art.get("scales", [art.get("scale", 1)] * len(art["drawings"]))
        if len(scales) != len(art["drawings"]) or any(s != int(s) or s < 1 for s in scales if "scales" in art):
            sys.exit(f"{extra['name']}: shot \"scales\": one whole number (1 or more) per drawing")
        return [f for box, sc in zip(art["drawings"], scales)  # (a box's optional 5th entry: its turn, as in "turns")
                for f in sheet_frames(dict({k: v for k, v in art.items() if k not in ("drawings", "scales")}, drawing=box[:4],
                                           turns=[box[4] if len(box) > 4 else "none"], scale=sc), extra, palette)]
    x, y, w, h = art["drawing"]
    crop = src.crop((x, y, x + w, y + h))
    near = {}

    def slot(c):
        exact = [s for s, v in palette.items() if v == c]
        if exact:
            return min(exact)
        dist = lambda v: sum((((c >> k) & 0xFF) - ((v >> k) & 0xFF)) ** 2 for k in (16, 8, 0))
        near[c] = min(palette, key=lambda s: (dist(palette[s]), s))
        return near[c]

    base = Image.new("P", crop.size, 0)
    bgs = {bg} | {tuple(int(c[k:k + 2], 16) for k in (1, 3, 5)) + (255,) for c in art.get("background", [])}
    if art.get("crop"):  # every non-background pixel in the box (a piece of a larger drawing, cut out as-is)
        pixels = [(a, b) for b in range(h) for a in range(w) if crop.getpixel((a, b))[3] and crop.getpixel((a, b)) not in bgs]
        cut = [(ex, ey, ew, eh) for ex, ey, ew, eh in art.get("exclude", [])]  # (sheet boxes left out: a joined piece)
        pixels = [(a, b) for a, b in pixels
                  if not any(ex <= x + a < ex + ew and ey <= y + b < ey + eh for ex, ey, ew, eh in cut)]
    else:
        pixels = loose_pixels(src, bg, x, y, w, h, bgs - {bg})
    for xx, yy in pixels:
        px = crop.getpixel((xx, yy))
        base.putpixel((xx, yy), slot((px[0] << 16) | (px[1] << 8) | px[2]))
    if near:
        print(f"{extra['name']}: shot drawing colours not in the target's slots, nearest used: "
              + ", ".join(f"#{c:06X}->{s}" for c, s in near.items()))
    if art.get("scale", 1) != 1:  # enlarged with the extra's frames (Sticks' 1.2x: sheet2ani.scale_nearest)
        from sheet2ani import scale_nearest
        base = scale_nearest(base, art["scale"])
    out = []
    for turn in art["turns"]:
        if turn not in TURNS:
            sys.exit(f"{extra['name']}: shot turn {turn!r} unknown ({', '.join(TURNS)})")
        im = base.transpose(TURNS[turn]) if TURNS[turn] is not None else base.copy()
        out.append((im, -(im.width // 2), -(im.height // 2)))
    return out


def own_palette(extra):
    return dict(extra["palette"])


def base_slots(extra):
    """{slot: 0xRRGGBB}: the S3&K colours an extra's shot can draw with there: the base character's player slots (the
    ones its S3&K sheet uses, as build_s3k_art matches the extra's art to) and the extra's own."""
    from build_s3k_art import BASE_FILE
    img = Image.open(S3K / "3K_Players" / f"{BASE_FILE[extra.get('base', 'sonic')]}.gif")
    pal = img.getpalette()
    out = {i: (pal[3 * i] << 16) | (pal[3 * i + 1] << 8) | pal[3 * i + 2]
           for _, i in img.getcolors(256) if i not in (0, 255)}
    out.update(own_palette(extra))
    return out


def sheet_slots(sheet):
    """{slot: 0xRRGGBB} of the colours a paletted sheet uses (a package's own player sheet: slots valid in that game)."""
    pal = sheet.getpalette()
    return {i: (pal[3 * i] << 16) | (pal[3 * i + 1] << 8) | pal[3 * i + 2] for _, i in sheet.getcolors(256) if i}


def frames(art, extra, palette=None):
    """The recipe's frames (flame, spark or sheet), [(P-mode image, pivot x, pivot y)]; palette: the slots the target
    draws with (spark, sheet; default: the extra's own)."""
    if "flame" in art:
        return flame_frames(art, extra)
    if "spark" in art:
        return spark_frames(art, extra, palette or own_palette(extra))
    if "sheet" in art:
        return sheet_frames(art, extra, palette or own_palette(extra))
    if "dust" in art:
        return dust_frames(art, extra, palette or own_palette(extra))
    sys.exit(f"{extra['name']}: shot art recipe {sorted(art)} unknown (build_s3k_shot.py: flame, spark, sheet)")


def frame_count(art):
    return len(art.get("flame") or art.get("spark") or art.get("dust") or art.get("drawings") or art.get("turns") or [0])


def swap_anims(swaps):
    """Swap shots' animations in Shot.bin (one per monitor_swap entry: John's sub-weapons): [(flight, flames or -1)]:
    entry k's flight is animation k, and a burning one's flames ("burn") follow all the flights, in entry order (the
    DLL reads each one's from its JSON: gen_s3k_header.s3k_json "burn_anim")."""
    out, extra = [], len(swaps)
    for s in swaps:
        out.append((len(out), extra if "burn" in s else -1))
        extra += "burn" in s
    return out


def build(extra, shot, out_dir, shot2=None, swaps=None):
    """Writes Shot.bin / Shot.gif for this extra under out_dir (a package's Sonic3ku/Data/Sprites). shot2: a second
    shot's frames too, as animation 1 ("Shot 2"). swaps: swap shots (abilities.swap_shots: John's sub-weapons) instead,
    their animations as swap_anims says (shot is then the first of them)."""
    shots = [shot] + ([shot2] if shot2 else [])
    if swaps:
        shots = list(swaps) + [dict(s, art=s["burn"]["art"], cycle=False) for s in swaps if "burn" in s]
    sets = [frames(s["art"], extra, base_slots(extra)) for s in shots]
    width = 2 + sum(im.width + 2 for frames_ in sets for im, _, _ in frames_)
    w = 1 << (width - 1).bit_length()
    h = max(im.height for frames_ in sets for im, _, _ in frames_) + 4
    sheet = Image.new("P", (max(w, 16), h), 0)
    sheet.putpalette(base_palette(extra["palette"]))
    anims, x = [], 2
    for k, (s, frames_) in enumerate(zip(shots, sets)):
        art = s["art"]
        ticks = art.get("ticks", 2)
        box = tuple(art.get("hitbox", [-8, -8, 8, 8]))
        boxes = [tuple(b) for b in art["hitboxes"]] if "hitboxes" in art else [box] * len(frames_)
        if len(boxes) != len(frames_):
            sys.exit(f"{extra['name']}: shot \"hitboxes\" has {len(boxes)} boxes for {len(frames_)} frames")
        specs = []
        for (im, px, py), box in zip(frames_, boxes):
            sheet.paste(im, (x, 2))
            specs.append(dict(sheet=0, duration=240, char=0, x=x, y=2, w=im.width, h=im.height, px=px, py=py,
                              boxes=[box, box]))
            x += im.width + 2
        anims.append(dict(name=f"Swap Shot {k}" if swaps else "Shot" if k == 0 else "Shot 2",
                          speed=0 if s.get("cycle") else 240 // ticks, loop=0,
                          rot=0, frames=specs))  # (cycle: a frame per throw, held: the DLL picks it)
    (out_dir / "3K_Players").mkdir(parents=True, exist_ok=True)
    save_sheet(sheet, out_dir / SHOT[1])
    ani_v5.write_bin(out_dir / SHOT[0], dict(sheets=[SHOT[1]], hitboxes=HITBOXES, anims=anims))
    return sum(len(a["frames"]) for a in anims)


def write_placeholder(out_dir):
    """NoSwap's own Shot.bin / .gif: one blank 1x1 frame (no hitbox) on a blank 4x4 sheet, only there so each package's
    can be served (the DLL loads it only for an extra with a shot)."""
    sheet = Image.new("P", (4, 4), 0)
    sheet.putpalette(base_palette({}))
    (out_dir / "3K_Players").mkdir(parents=True, exist_ok=True)
    save_sheet(sheet, out_dir / SHOT[1])
    f = dict(sheet=0, duration=240, char=0, x=0, y=0, w=1, h=1, px=0, py=0, boxes=[(0, 0, 0, 0)] * 2)
    ani_v5.write_bin(out_dir / SHOT[0], dict(sheets=[SHOT[1]], hitboxes=HITBOXES,
                                             anims=[dict(name="Shot", speed=0, loop=0, rot=0, frames=[f])]))
