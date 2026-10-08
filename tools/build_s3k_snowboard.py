#!/usr/bin/env python3
"""Ice Cap Zone act 1's snowboard intro with each Sonic-based extra's own art on the official board.

Usage: build_s3k_snowboard.py [extra folder name ...] [--preview DIR]
  (no names: every Sonic-based extra. The files go in s3k_build(extra), or with --preview in DIR/files/<extra>, with a
  picture of each extra's frames and one of everyone's Ground frames. build_packages.py calls write_placeholder and
  build(extra, out) itself, straight into each package)

The game (S3K_ICZ1Intro, its stageLoad) loads 3K_ICZ/Snowboard.bin, whose rider frames are Sonic and the board drawn
together; its riding states set the player's animator to animation 3 * characterID - 2 / - 1 / + 0 (Ground / Air /
Sidewind). A Sonic-based extra plays as characterID 1 (Sonic's), so his three play. The NoSwap DLL loads the extra's
3K_ICZ/Snowboard_Extra.bin instead (NoSwapS3K.cpp SWAPS, Sonic-based extras only: Tails and Knuckles never get the
board), built here from the official file:
- Snowboard Spin (the board alone, flying off) and Dust stay exactly as they are (the same pixels at the same place).
- Every frame of Sonic Ground / Air / Sidewind becomes the extra's own pose standing on a board-only frame from Snowboard
  Spin (flat, 45 degrees or upright: BOARD, the one closest to the angle of the board in Sonic's frame). Where Sonic's
  board IS one of those (Ground 1 and 4, Air 1), it goes exactly where it was. Elsewhere it goes under Sonic's feet
  (his red shoes, measured per frame): its middle under them, its top one row above their bottom, as in the frames
  where it fits exactly. The extra's feet (the middle of his bottom rows) go where Sonic's are, and he's lowered onto
  the board until a foot touches it (his bottom row over the board's top row, like Sonic's shoes).
  Sidewind's twirl seen from above (frames 1-5, OVERHEAD): the board's middle under Sonic's shoes, the extra's
  bottom on their bottom, drawn over the board.
- The Tails / Knux animations (never played by a Sonic-based extra; the file points them at Sonic's frames) point at
  the same new frames.
- Poses (sheet2ani frames from the extra's Sonic 2 config): its "snowboard" {"ground": [...], "air": [...],
  "sidewind": [...]} (character.json "snowboard"), each spread over the official frame count; or, left out: Ground
  his ducking ("Looking Down", its last frame), Air his spring pose ("Bouncing", else "Jumping"), Sidewind his twirl
  ("Twirl H", else "Skidding") in frames 1-5 with the ducking pose before and after (as Sonic's starts and ends on his
  Ground pose). A frame's "offset" [dx, dy] moves the pose on its board.
- Colours: the board keeps the official sheet's slots (129-143, the stage's copy of Sonic's colours); the extra's
  pixels get exactly the slots his S3&K player sheet uses (build_s3k_art: his own 74-95, the rest Sonic's 2-16), so
  both come out as they do in play.
The sheet is the official one with the rider frames (rows 0-114, nothing else is there) cleared and the new frames
packed into the free space: 512x256 like the game's, taller only if they don't fit.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import ani_v5
import sheet2ani
from extras import EXTRAS, s3k_build
from gifio import save_sheet

REPO = Path(__file__).resolve().parent.parent
S3K = REPO / "extracted" / "Sonic3K" / "Data" / "Sprites"
GAME_BIN = "3K_ICZ/Snowboard.bin"
FIXED_BIN, FIXED_GIF = "3K_ICZ/Snowboard_Extra.bin", "3K_ICZ/Snowboard_Extra.gif"  # (the DLL's SWAPS names)
RIDER_ROWS = 115  # the official sheet's rows 0-114 hold only rider frames; Snowboard Spin and Dust are below
SHOE = (134, 135)  # Sonic's red shoes in the official sheet (bank 0 row 8: the stage's copy of his colours)
# The Snowboard Spin frame (board alone: 0 "/", 1 flat, 2 "\", 3 upright) under each official frame, by the angle of
# the board in it (measured on the official frames; Ground is picked by slope, steep 0 to flat 4):
#   Ground 0 ~65 deg "\", 1 45 (exact), 2 ~25, 3 ~13, 4 flat (exact); Air 0 flat (exact), 1 ~-8, 2 ~-14;
#   Sidewind 0 / 6 ~25 (Ground 2's frame), the twirl from above 1 "\", 2 upright, 3 "/", 4 ~60 "/", 5 ~60 "\"
BOARD = {"Ground": [2, 2, 2, 1, 1], "Air": [1, 1, 1], "Sidewind": [2, 2, 3, 0, 0, 2, 2]}
OVERHEAD = {("Sidewind", k) for k in range(1, 6)}
KINDS = ("Ground", "Air", "Sidewind")
OVERRIDE = {"Ground": "ground", "Air": "air", "Sidewind": "sidewind"}  # the config's "snowboard" keys


def s2_config(extra):
    found = list(extra["art"].glob("*_s2.json"))
    if len(found) != 1:
        sys.exit(f"{extra['art'].name}: expected one Sonic 2 config, found {len(found)}")
    return found[0]


def official():
    """The official file and sheet (indices; its white surround as 0)."""
    tpl = ani_v5.read_bin(S3K / GAME_BIN)
    img = Image.open(S3K / tpl["sheets"][0])
    return tpl, img


def crop(sheet, f):
    a = sheet[f["y"]:f["y"] + f["h"], f["x"]:f["x"] + f["w"]].copy()
    a[a == 255] = 0
    return a


def find_exact(o, b):
    """Where the board-only frame `b` sits in the official frame `o` with every pixel the same, or None."""
    ys, xs = np.nonzero(b)
    vals = b[ys, xs]
    for dy in range(o.shape[0] - b.shape[0] + 1):
        for dx in range(o.shape[1] - b.shape[1] + 1):
            if np.array_equal(o[ys + dy, xs + dx], vals):
                return dx, dy
    return None


def board_plans(tpl, sheet):
    """Per official rider frame (kind, k): the board frame's array and its top-left in the frame's pivot space, and
    Sonic's feet there (shoes' middle x, middle y, bottom y)."""
    spin = tpl["anims"][0]["frames"]
    plans = {}
    for kind in KINDS:
        a = next(a for a in tpl["anims"] if a["name"] == f"Sonic {kind}")
        if len(a["frames"]) != len(BOARD[kind]):
            sys.exit(f"{GAME_BIN}: Sonic {kind} has {len(a['frames'])} frames, BOARD expects {len(BOARD[kind])}")
        for k, f in enumerate(a["frames"]):
            o = crop(sheet, f)
            ys, xs = np.nonzero(np.isin(o, SHOE))
            rx, ry, rb = round(xs.mean()) + f["px"], round(ys.mean()) + f["py"], ys.max() + f["py"]
            bf = spin[BOARD[kind][k]]
            b = crop(sheet, bf)
            exact = find_exact(o, b)
            if exact:
                bx, by = f["px"] + exact[0], f["py"] + exact[1]
            elif (kind, k) in OVERHEAD:
                bx, by = rx - b.shape[1] // 2, ry - b.shape[0] // 2
            else:  # its middle under the shoes, its top one row above their bottom (as where it fits exactly)
                bx = rx - b.shape[1] // 2
                col = rx - bx
                cols = [c for c in range(b.shape[1]) if b[:, c].any()]
                col = min(cols, key=lambda c: abs(c - col))
                by = rb - 1 - int(np.nonzero(b[:, col])[0].min())
            plans[(kind, k)] = dict(board=b, bx=bx, by=by, rx=rx, rb=rb, exact=bool(exact))
    return plans


def colour_mapper(cfg):
    """Sheet colour -> the slot the extra's S3&K player sheet gives it (build_s3k_art.build: his own slots, the rest the
    nearest of Sonic's S3&K colours)."""
    tpl = Image.open(S3K / "3K_Players" / "Sonic.gif")
    pal = tpl.getpalette()
    slots = sorted(i for _, i in tpl.getcolors(256) if i not in (0, 255))
    own = {sheet2ani.hexrgb(c): int(s) for s, c in cfg.get("palette", {}).items()}
    memo = {}

    def index_of(c):
        if c in own:
            return own[c]
        if c not in memo:
            memo[c] = min(slots, key=lambda i: sum((a - b) ** 2 for a, b in zip(c, pal[3 * i:3 * i + 3])))
        return memo[c]
    colours = {i: tuple(pal[3 * i:3 * i + 3]) for i in slots}
    colours.update({s: c for c, s in own.items()})
    return index_of, colours


def poses(cfg):
    """{kind: [sheet2ani frame per official frame]} (see the docstring)."""
    anims = cfg["animations"]

    def first(*names):
        return next((anims[n]["frames"] for n in names if anims.get(n, {}).get("frames")), None)

    def spread(frames, m):
        return [frames[k * len(frames) // m] for k in range(m)]
    duck = first("Looking Down", "Stopped")[-1]
    out = {"Ground": [duck] * len(BOARD["Ground"]),
           "Air": spread(first("Bouncing", "Jumping", "Stopped"), len(BOARD["Air"])),
           "Sidewind": [duck] + spread(first("Twirl H", "Skidding", "Stopped"), len(BOARD["Sidewind"]) - 2) + [duck]}
    own = cfg.get("snowboard") or {}
    for kind, key in OVERRIDE.items():
        if own.get(key):
            out[kind] = spread(own[key], len(BOARD[kind]))
    return out


def cut_pose(src, fr, background, index_of, memo):
    key = sheet2ani.frame_key(fr)
    if key not in memo:
        if isinstance(fr, dict) and "layers" in fr:
            img, mask, _ = sheet2ani.cut_layered(src, fr, background)
        elif isinstance(fr, dict):
            img, mask, _ = sheet2ani.cut_spec(src, fr, background)
        else:
            img, mask = sheet2ani.cut_frame(src, tuple(fr), background)
        a = np.zeros((img.height, img.width), np.uint8)
        px, mp = img.load(), mask.load()
        for y in range(img.height):
            for x in range(img.width):
                if mp[x, y]:
                    a[y, x] = index_of(px[x, y][:3])
        ys, xs = np.nonzero(a)  # (trimmed to its pixels)
        memo[key] = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return memo[key]


def composite(plan, pose, offset, overhead):
    """The extra's pose on the plan's board: (array, px, py). His feet (the middle of his bottom rows; his bottom) go
    where Sonic's shoes are. Side views: the board is raised until it touches a foot (its top row under his bottom
    row), and slid along its own line so its middle is under the foot (feet) touching it: on a 45-degree board an
    upright pose stands on it by its lower foot (slid further down the line while its upper end would show above the
    pose's middle, so it doesn't stick out over a short pose). From above (the twirl): the board's middle under Sonic's shoes, its
    top no higher than a third of the way down the pose (a short, wide pose doesn't get a board sticking out above)."""
    b, bx, by = plan["board"], plan["bx"], plan["by"]
    h, w = pose.shape
    feet = np.nonzero(pose[max(0, h - 3):])[1]
    ex, ey = plan["rx"] - round(feet.mean()) + offset[0], plan["rb"] - (h - 1) + offset[1]
    tops = {c: int(np.nonzero(b[:, c])[0].min()) for c in range(b.shape[1]) if b[:, c].any()}
    middle = min(tops, key=lambda j: abs(j - b.shape[1] // 2))
    if overhead:
        by = max(by, ey + h // 3)
    else:
        low = {c: int(np.nonzero(pose[:, c])[0].max()) for c in range(w) if pose[:, c].any()}
        low = {c: y for c, y in low.items() if y >= h - 2}  # (his feet: the columns reaching his bottom rows)

        def need(bx):  # per foot column: the board's y for its top row to be under that column's bottom
            return {c: ey + y - tops[ex + c - bx] for c, y in low.items() if ex + c - bx in tops}
        n = need(bx)
        if n:
            by = min(n.values())
            touch = [ex + c for c, v in n.items() if v <= by + 2]
            cx = round(sum(touch) / len(touch))
            surface = by + tops[min(tops, key=lambda j: abs(j - (cx - bx)))]
            bx, by = cx - middle, surface - tops[middle]
            # a tilted board's upper half no higher than halfway down the pose (it showed over a short pose's head):
            # slid on down its line, as long as it stays under the foot
            first, last = min(tops), max(tops)
            down = 1 if tops[last] > tops[first] + 4 else -1 if tops[first] > tops[last] + 4 else 0
            while down and by + min(tops.values()) < ey + h // 2 and cx - (bx + down) in tops:
                bx += down
                by = surface - tops[cx - bx]
            n = need(bx)
            if n:
                by = min(n.values())
    x0, y0 = min(bx, ex), min(by, ey)
    x1, y1 = max(bx + b.shape[1], ex + w), max(by + b.shape[0], ey + h)
    out = np.zeros((y1 - y0, x1 - x0), np.uint8)
    out[by - y0:by - y0 + b.shape[0], bx - x0:bx - x0 + b.shape[1]] = b
    region = out[ey - y0:ey - y0 + h, ex - x0:ex - x0 + w]
    region[pose != 0] = pose[pose != 0]
    return out, x0, y0


def pack(sizes, taken, width=512, height=256):
    """Top-left corners for each (w, h) in `sizes` on a sheet where the rects `taken` are in use (1 px apart), first
    fit scanning down; the sheet grows taller if they don't fit."""
    used = [(x - 1, y - 1, x + w + 1, y + h + 1) for x, y, w, h in taken]
    out = []
    for w, h in sizes:
        y = 1
        while True:
            x = 1
            spot = None
            while x + w + 1 <= width:
                clash = next((u for u in used if x < u[2] and u[0] < x + w and y < u[3] and u[1] < y + h), None)
                if clash is None:
                    spot = (x, y)
                    break
                x = clash[2] + 1
            if spot:
                break
            y += 1
        out.append(spot)
        used.append((spot[0] - 1, spot[1] - 1, spot[0] + w + 1, spot[1] + h + 1))
        height = max(height, spot[1] + h + 1)
    return out, height


def build(extra, out=None):
    """The extra's 3K_ICZ/Snowboard_Extra.bin / .gif in `out` (default s3k_build(extra)). Returns the composites
    [(kind, k, array, px, py)] and the sheet's palette, for previews."""
    out = Path(out) if out else s3k_build(extra)
    cfg_path = s2_config(extra)
    cfg = json.loads(cfg_path.read_text())
    src = Image.open(cfg_path.parent / cfg["source"]).convert("RGBA")
    background = {sheet2ani.hexrgb(c) for c in cfg["background"]}
    index_of, colours = colour_mapper(cfg)
    tpl, img = official()
    sheet = np.array(img)
    plans = board_plans(tpl, sheet)
    chosen = poses(cfg)
    memo, made = {}, []
    for kind in KINDS:
        for k, fr in enumerate(chosen[kind]):
            pose = cut_pose(src, fr, background, index_of, memo)
            a, px, py = composite(plans[(kind, k)], pose, sheet2ani.frame_offset(fr), (kind, k) in OVERHEAD)
            made.append((kind, k, a, px, py))

    # the sheet: the official one with the rider rows cleared, the composites (each different one once) packed in
    keep = [f for a in tpl["anims"] if not a["name"].startswith(("Sonic ", "Tails ", "Knux ")) for f in a["frames"]]
    if any(f["w"] and f["y"] < RIDER_ROWS for f in keep):
        sys.exit(f"{GAME_BIN}: a board or dust frame is in the rider rows (0-{RIDER_ROWS - 1})")
    unique = {}
    for kind, k, a, px, py in made:
        unique.setdefault(a.tobytes() + bytes(str(a.shape), "ascii"), a)
    keys = sorted(unique, key=lambda u: -unique[u].shape[0])
    spots, height = pack([(unique[u].shape[1], unique[u].shape[0]) for u in keys],
                         [(f["x"], f["y"], f["w"], f["h"]) for f in keep if f["w"]], img.width, img.height)
    new = np.zeros((height, img.width), np.uint8)
    new[:img.height] = sheet
    new[:RIDER_ROWS] = 0
    where = {}
    for u, (x, y) in zip(keys, spots):
        a = unique[u]
        new[y:y + a.shape[0], x:x + a.shape[1]] = a
        where[u] = (x, y)
    pal = img.getpalette() + [0] * (768 - len(img.getpalette()))
    for i, c in colours.items():  # (the extra's colours, for viewing: in game they come from the player palette)
        pal[3 * i:3 * i + 3] = c
    out_img = Image.fromarray(new, "P")
    out_img.putpalette(pal)
    (out / FIXED_GIF).parent.mkdir(parents=True, exist_ok=True)
    save_sheet(out_img, out / FIXED_GIF)

    rect = {}  # (kind, k) -> (x, y, w, h, px, py)
    for kind, k, a, px, py in made:
        x, y = where[a.tobytes() + bytes(str(a.shape), "ascii")]
        rect[(kind, k)] = (x, y, a.shape[1], a.shape[0], px, py)
    sonic = {kind: next(a for a in tpl["anims"] if a["name"] == f"Sonic {kind}") for kind in KINDS}
    anims = []
    for a in tpl["anims"]:
        who, _, kind = a["name"].partition(" ")
        if who not in ("Sonic", "Tails", "Knux") or kind not in KINDS:
            anims.append(a)
            continue
        frames = []
        for k, f in enumerate(a["frames"]):
            if who == "Sonic":
                sk, sf = k, f
            else:  # (Tails' and Knuckles' point at Sonic's pictures: the extra's frame that replaced that picture)
                same = lambda s: (s["x"], s["y"], s["w"], s["h"]) == (f["x"], f["y"], f["w"], f["h"])
                sk = next((j for j, s in enumerate(sonic[kind]["frames"]) if same(s)), None)
                if sk is None:
                    sk = min(k, len(sonic[kind]["frames"]) - 1)
                sf = sonic[kind]["frames"][sk]
            x, y, w, h, px, py = rect[(kind, sk)]
            frames.append(dict(f, x=x, y=y, w=w, h=h, px=px + f["px"] - sf["px"], py=py + f["py"] - sf["py"]))
        anims.append(dict(a, frames=frames))
    ani_v5.write_bin(out / FIXED_BIN, dict(sheets=[FIXED_GIF], hitboxes=tpl["hitboxes"], anims=anims))
    return made, pal, height


def write_placeholder(out):
    """NoSwap's own files under the fixed names (only there so each package's own can be served: the redirect only
    serves names NoSwap ships): the game's Snowboard.bin as it is (naming the game's sheet) and a blank sheet."""
    (out / FIXED_BIN).parent.mkdir(parents=True, exist_ok=True)
    (out / FIXED_BIN).write_bytes((S3K / GAME_BIN).read_bytes())
    sheet = Image.new("P", (4, 4), 0)
    sheet.putpalette(Image.open(S3K / "3K_ICZ" / "Snowboard.gif").getpalette())
    save_sheet(sheet, out / FIXED_GIF)


def sonic_based():
    return [e for e in EXTRAS if e["base"] == "sonic"]


# ---------------------------------------------------------------- previews (not part of the build)

def render(a, pal, scale):
    rgb = np.zeros(a.shape + (3,), np.uint8)
    for i in map(int, np.unique(a)):
        if i:
            rgb[a == i] = pal[3 * i:3 * i + 3]
    im = Image.fromarray(rgb, "RGB")
    m = Image.fromarray(((a != 0) * 255).astype(np.uint8), "L")
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST), \
        m.resize((m.width * scale, m.height * scale), Image.NEAREST)


def preview_strip(extra, made, pal, path, scale=3, cell=80):
    """Every composite on a snow-blue cell, pivot at the cell's middle (yellow dot), one row per animation, with the
    official frame left of each row."""
    tpl, img = official()
    sheet, opal = np.array(img), img.getpalette()
    rows = [[m for m in made if m[0] == kind] for kind in KINDS]
    cols = max(len(r) for r in rows) + 1
    out = Image.new("RGB", (cols * cell * scale, len(rows) * cell * scale + 14), (20, 20, 30))
    d = ImageDraw.Draw(out)
    d.text((4, 2), f"{extra['art'].name}: official | Ground (5), Air (3), Sidewind (7) rows", fill=(255, 255, 255))
    for r, row in enumerate(rows):
        f = next(a for a in tpl["anims"] if a["name"] == f"Sonic {KINDS[r]}")["frames"][0]
        items = [(crop(sheet, f), f["px"], f["py"], opal)] + [(a, px, py, pal) for _, _, a, px, py in row]
        for c, (a, px, py, p) in enumerate(items):
            ox, oy = c * cell * scale, r * cell * scale + 14
            d.rectangle((ox, oy, ox + cell * scale - 2, oy + cell * scale - 2), fill=(150, 190, 230) if c else (110, 140, 170))
            im, m = render(a, p, scale)
            out.paste(im, (ox + (cell // 2 + px) * scale, oy + (cell // 2 + py) * scale), m)
            d.rectangle((ox + cell // 2 * scale, oy + cell // 2 * scale, ox + cell // 2 * scale + scale - 1,
                         oy + cell // 2 * scale + scale - 1), fill=(255, 255, 0))
    out.save(path)


def preview_ground_sheet(results, path, scale=2, cell=72):
    """Every extra's 5 Ground frames, one row each, named."""
    out = Image.new("RGB", (120 + 5 * cell * scale, len(results) * cell * scale), (20, 20, 30))
    d = ImageDraw.Draw(out)
    for r, (extra, made, pal) in enumerate(results):
        oy = r * cell * scale
        d.text((4, oy + cell * scale // 2), extra["art"].name, fill=(255, 255, 255))
        for c, (_, _, a, px, py) in enumerate(m for m in made if m[0] == "Ground"):
            ox = 120 + c * cell * scale
            d.rectangle((ox, oy, ox + cell * scale - 2, oy + cell * scale - 2), fill=(150, 190, 230))
            im, m = render(a, pal, scale)
            out.paste(im, (ox + (cell // 2 + px) * scale, oy + (cell // 2 + py) * scale), m)
    out.save(path)


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = None
    if "--preview" in args:
        i = args.index("--preview")
        preview = Path(args[i + 1])
        del args[i:i + 2]
    chosen = [e for e in sonic_based() if not args or e["art"].name in args]
    results = []
    for e in chosen:
        made, pal, height = build(e, preview / "files" / e["art"].name if preview else None)
        results.append((e, made, pal))
        print(f"{e['art'].name}: {FIXED_BIN} ({len({a.tobytes() for _, _, a, _, _ in made})} new frames, sheet 512x{height})")
        if preview:
            preview.mkdir(parents=True, exist_ok=True)
            preview_strip(e, made, pal, preview / f"snowboard_{e['art'].name}.png")
    if preview and len(results) > 1:
        preview_ground_sheet(results, preview / "snowboard_all_ground.png")
