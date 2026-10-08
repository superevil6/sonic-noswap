#!/usr/bin/env python3
"""Convert a character sprite sheet into Retro Engine v4 player sprites + animation file.

Usage: sheet2ani.py <config.json>

The config describes where each frame sits on the source sheet and which game
animation it belongs to. Animation names, speeds, loop points and hitboxes are
taken from a template .ani (normally the base character's, e.g. Sonic.ani), so
the new character plugs into the same player code.

Output:
  <out_dir>/Data/Sprites/Players/<name>_<n>.gif   indexed 256x256 sheets
  <out_dir>/Data/Animations/<name>.ani
  An animation's "align": true nudges its frames sideways to overlap the first (see align_x); a list
  [[n, true / false], ...] does so per run of n frames, each on its own first frame (runs of separate poses).
  An appended animation's "like": "<name>" takes that (already built) animation's speed, loop, rotation and hitbox.
  An animation's "hold": N shows each frame N times in a row (for speeds the script sets, e.g. Tails' flight).
  Frames are a rect [x, y, w, h] or a dict: {"layers": [...]} (layered, see cut_layered),
  {"rect": R, "rotate": 90} (turned by a multiple of 90 degrees, e.g. a spin ball), {"rect": R, "circle":
  [cx, cy, r]} (only the pixels within that circle of the rect, e.g. a body cropped into a ball), {"rect": R,
  "flip": true} (mirrored, for a pose drawn facing left), or
  {"rect": R, "anchor_box": A} (positioned by the sheet rect A inside R, e.g. the body under an umbrella), or
  {"rect": R, "drop": [[x, y, w, h], ...]} (those sheet rects left out: a neighbour's pixels poking into R, a crop).
  Any frame dict may add "offset": [dx, dy] (px, +x right, +y down, in the frame as drawn: after its flip / turn):
  that use of the frame moves by that much after every automatic placement (anchor, align, a ball's ground line),
  see frame_offset. The cut is shared with the same frame without an offset (frame_key leaves it out).
  "palette" ({slot: "#rrggbb"}) gives the character colours of its own in extra palette slots, which
  the game script writes into the global palette; "colours" may then map sheet colours to those slots
  plus one .ani per entry in "extra_anis" (e.g. the special stage file), sharing the same sheets
  plus, if "ui" is given, <out_dir>/Data/Sprites/Players/<ui.name>.gif holding HUD / signpost /
  monitor art, and a manifest (<ui.manifest>) listing where each element landed on that sheet
"""
import json
import statistics
import struct
import sys
from pathlib import Path

from PIL import Image
from gifio import save_sheet

SHEET_SIZE = 256
ANCHORS = {}  # layered frame key -> (x, y, w, h) of its anchor layer on the composite
PAD = 1


# ---------------------------------------------------------------- .ani format

def read_ani(path):
    d = Path(path).read_bytes()
    p = 0

    def u8():
        nonlocal p
        p += 1
        return d[p - 1]

    def s8():
        v = u8()
        return v - 256 if v > 127 else v

    def string():
        nonlocal p
        n = u8()
        p += n
        return d[p - n:p].decode()

    sheets = [string() for _ in range(u8())]
    anims = []
    for _ in range(u8()):
        name = string()
        count, speed, loop, rot = u8(), u8(), u8(), u8()
        frames = [dict(sheet=u8(), hitbox=u8(), x=u8(), y=u8(), w=u8(), h=u8(), px=s8(), py=s8())
                  for _ in range(count)]
        anims.append(dict(name=name, speed=speed, loop=loop, rot=rot, frames=frames))
    hitboxes = [[s8() for _ in range(32)] for _ in range(u8())]
    if p != len(d):
        sys.exit(f"{path}: {len(d) - p} trailing bytes, unknown .ani layout")
    return dict(sheets=sheets, anims=anims, hitboxes=hitboxes)


def write_ani(path, ani):
    out = bytearray()

    def string(s):
        b = s.encode()
        out.append(len(b))
        out.extend(b)

    out.append(len(ani["sheets"]))
    for s in ani["sheets"]:
        string(s)
    out.append(len(ani["anims"]))
    for a in ani["anims"]:
        string(a["name"])
        out.extend(bytes([len(a["frames"]), a["speed"], a["loop"], a["rot"]]))
        for f in a["frames"]:
            out.extend(struct.pack("<BBBBBBbb", f["sheet"], f["hitbox"], f["x"], f["y"], f["w"], f["h"], f["px"], f["py"]))
    out.append(len(ani["hitboxes"]))
    for hb in ani["hitboxes"]:
        out.extend(struct.pack("<32b", *hb))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(bytes(out))


# ---------------------------------------------------------------- sprites

def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def scale_nearest(img, factor):
    """`img` enlarged by `factor` (not necessarily whole), nearest-neighbour: every output pixel is one of the source's,
    no new colours. round(size * factor) pixels each way, all sampled at exactly `factor` (so frames of different sizes
    get the same scale), columns counted from the left and rows from the bottom (so frames standing on their bottom
    row double the same rows above it). Any mode (P keeps its palette). Sticks' 1.2x (the user's exception to the
    faithful art rule, for her only)."""
    import math
    w, h = img.size
    W, H = round(w * factor), round(h * factor)
    cols = [min(w - 1, math.floor((x + 0.5) / factor)) for x in range(W)]
    rows = [h - 1 - min(h - 1, math.floor((H - 1 - y + 0.5) / factor)) for y in range(H)]
    out = Image.new(img.mode, (W, H))
    if img.mode == "P":
        out.putpalette(img.getpalette())
    src, dst = img.load(), out.load()
    for y in range(H):
        for x in range(W):
            dst[x, y] = src[cols[x], rows[y]]
    if "transparency" in img.info:
        out.info["transparency"] = img.info["transparency"]
    return out


def cut_frame(src, rect, background, trim=True):
    """Crop a rect from the sheet and (optionally) trim it to the pixels that aren't background."""
    x, y, w, h = rect
    img = src.crop((x, y, x + w, y + h))
    mask = Image.new("L", img.size, 0)
    px, mp = img.load(), mask.load()
    for yy in range(img.height):
        for xx in range(img.width):
            if px[xx, yy][:3] not in background and px[xx, yy][3] != 0:
                mp[xx, yy] = 255
    box = mask.getbbox() if trim else (0, 0, w, h)
    if mask.getbbox() is None:
        sys.exit(f"frame at {rect} is empty")
    return img.crop(box), mask.crop(box)


def frame_key(fr):
    """Frames are either a rect [x, y, w, h] or a layered composite (dict); both need a hashable key. An "offset" only
    moves a frame's placement, not its pixels: it's left out, so the frame is cut (and packed) once, and {"rect": R,
    "offset": ...} is the same cut as the plain rect R."""
    if isinstance(fr, dict) and "offset" in fr:
        fr = {k: v for k, v in fr.items() if k != "offset"}
        if set(fr) == {"rect"}:
            return tuple(fr["rect"])
    return json.dumps(fr, sort_keys=True) if isinstance(fr, dict) else tuple(fr)


def frame_offset(fr):
    """A frame's own "offset" ({"rect": R, "offset": [dx, dy]}; from character.json's {"frame": NAME, "offset": ...}):
    (dx, dy) px added to its pivot after the automatic placement. (0, 0) for none. Its x is in the frame as drawn (as
    the game shows it facing right; a "flip" frame's dx too)."""
    off = fr.get("offset") if isinstance(fr, dict) else None
    if off is None:
        return 0, 0
    if not (isinstance(off, (list, tuple)) and len(off) == 2 and all(isinstance(v, int) for v in off)):
        sys.exit(f"frame {fr.get('rect', '')}: \"offset\" must be [dx, dy] in whole px, not {off!r}")
    return off[0], off[1]


def apply_offsets(frames, specs):
    """Move each built frame (a dict with px / py) by its spec's frame_offset: the last step of placement."""
    for f, fr in zip(frames, specs):
        dx, dy = frame_offset(fr)
        f["px"] += dx
        f["py"] += dy


def cut_layered(src, spec, background):
    """Paste trimmed layers onto one canvas, first layer at the back. `at` is where each layer's
    top-left goes relative to the anchor layer's top-left. Returns (image, mask, anchor box)."""
    layers = [cut_frame(src, tuple(l["rect"]), background) for l in spec["layers"]]
    offsets = [tuple(l.get("at", (0, 0))) for l in spec["layers"]]
    x0 = min(dx for dx, _ in offsets)
    y0 = min(dy for _, dy in offsets)
    x1 = max(dx + img.width for (dx, _), (img, _m) in zip(offsets, layers))
    y1 = max(dy + img.height for (_, dy), (img, _m) in zip(offsets, layers))
    canvas = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    mask = Image.new("L", canvas.size, 0)
    for (dx, dy), (img, m) in zip(offsets, layers):
        canvas.paste(img, (dx - x0, dy - y0), m)
        mask.paste(m, (dx - x0, dy - y0), m)
    a = spec.get("anchor_layer", len(layers) - 1)
    ax, ay = offsets[a]
    anchor = (ax - x0, ay - y0, layers[a][0].width, layers[a][0].height)
    if "pivot_x" in spec:  # the pivot this many px right of the anchor layer's left edge (not its middle)
        anchor = (anchor[0] + spec["pivot_x"], anchor[1], 1, anchor[3])
    return canvas, mask, anchor


def cut_spec(src, spec, background):
    """Cut a dict frame that isn't layered. Returns (image, mask, anchor box or None)."""
    x, y, w, h = spec["rect"]
    if "circle" in spec:  # [cx, cy, r] within the rect: only the pixels inside that circle (a crop, not an edit)
        cx, cy, r = spec["circle"]
        img, mask = cut_frame(src, tuple(spec["rect"]), background, trim=False)
        mp = mask.load()
        for yy in range(mask.height):
            for xx in range(mask.width):
                if (xx - cx) ** 2 + (yy - cy) ** 2 > r * r + r:
                    mp[xx, yy] = 0
        box = mask.getbbox()
        img, mask = img.crop(box), mask.crop(box)
    elif "drop" in spec:  # [[x, y, w, h], ...] sheet rects left out (a neighbour's pixels poking into the rect: a crop)
        img, mask = cut_frame(src, tuple(spec["rect"]), background, trim=False)
        for dx, dy, dw, dh in spec["drop"]:
            mask.paste(0, (dx - x, dy - y, dx - x + dw, dy - y + dh))
        box = mask.getbbox()
        img, mask = img.crop(box), mask.crop(box)
    else:
        img, mask = cut_frame(src, tuple(spec["rect"]), background)
    anchor = None
    trimmed = img.size  # before turning, which is what an anchor box is measured on
    if "rotate" in spec:
        img = img.rotate(-spec["rotate"], expand=True)
        mask = mask.rotate(-spec["rotate"], expand=True)
    if spec.get("flip"):  # mirrored left-right (a pose drawn facing the other way)
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        mask = mask.transpose(Image.FLIP_LEFT_RIGHT)
    if "anchor_box" in spec:
        # where the trimmed image starts inside the rect, to place the anchor box relative to it
        full = src.crop((x, y, x + w, y + h))
        bx, by = min(i for i in range(w) for j in range(h) if full.getpixel((i, j))[:3] not in background and full.getpixel((i, j))[3]), \
                 min(j for j in range(h) for i in range(w) if full.getpixel((i, j))[:3] not in background and full.getpixel((i, j))[3])
        ax, ay, aw, ah = spec["anchor_box"]
        anchor = (ax - x - bx, ay - y - by, aw, ah)
        # turned and mirrored with the frame (clockwise quarter turns, then the flip, as above), so a turned set
        # keeps the artist's alignment too
        w, h = trimmed
        for _ in range(spec.get("rotate", 0) // 90 % 4):
            ax, ay, aw, ah = anchor
            anchor, w, h = (h - ay - ah, ax, ah, aw), h, w
        if spec.get("flip"):
            ax, ay, aw, ah = anchor
            anchor = (w - ax - aw, ay, aw, ah)
    return img, mask, anchor


def to_indexed(img, mask, colour_map, palette):
    """Map RGB pixels onto the base character's palette indices (0 = transparent). Colours missing
    from `colour_map` get the nearest of slots 1-15 and the slots `colour_map` uses."""
    candidates = sorted(set(range(1, 16)) | set(colour_map.values()))
    out = Image.new("P", img.size, 0)
    src, dst, mp = img.load(), out.load(), mask.load()
    unknown = {}
    for y in range(img.height):
        for x in range(img.width):
            if not mp[x, y]:
                continue
            rgb = src[x, y][:3]
            idx = colour_map.get(rgb)
            if idx is None:
                idx = min(candidates, key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb, palette[i])))
                unknown[rgb] = unknown.get(rgb, 0) + 1
            dst[x, y] = idx
    return out, unknown


def pack(frames):
    """Shelf-pack frames into as few 256x256 sheets as needed. Returns [(sheet, x, y)]."""
    order = sorted(range(len(frames)), key=lambda i: -frames[i].height)
    placed = [None] * len(frames)
    sheet, x, y, shelf = 0, PAD, PAD, 0
    for i in order:
        w, h = frames[i].size
        if x + w + PAD > SHEET_SIZE:
            x, y, shelf = PAD, y + shelf + PAD, 0
        if y + h + PAD > SHEET_SIZE:
            sheet, x, y, shelf = sheet + 1, PAD, PAD, 0
        placed[i] = (sheet, x, y)
        x += w + PAD
        shelf = max(shelf, h)
    return placed


# ---------------------------------------------------------------- main

def main():
    cfg_path = Path(sys.argv[1])
    cfg = json.loads(cfg_path.read_text())
    base = cfg_path.parent
    src = Image.open(base / cfg["source"]).convert("RGBA")
    tpl_sheet = Image.open(cfg["template_sheet"])
    raw_pal = tpl_sheet.getpalette()
    raw_pal += [0] * (768 - len(raw_pal))
    for slot, colour in cfg.get("palette", {}).items():  # own colours, so the sheets preview correctly
        raw_pal[3 * int(slot):3 * int(slot) + 3] = hexrgb(colour)
    palette = [tuple(raw_pal[3 * i:3 * i + 3]) for i in range(256)]
    background = {hexrgb(c) for c in cfg["background"]}
    colour_map = {hexrgb(k): v for k, v in cfg["colours"].items()}
    name = cfg["name"]
    out_dir = Path(cfg["out_dir"]) if Path(cfg["out_dir"]).is_absolute() else base / cfg["out_dir"]

    # Cut every distinct rect once
    outputs = [dict(name=name, template_ani=cfg["template_ani"], animations=cfg["animations"],
                    appended_animations=cfg.get("appended_animations", {}))]
    outputs += cfg.get("extra_anis", [])
    rects = {}
    for anim in (a for o in outputs for a in list(o["animations"].values()) + list(o.get("appended_animations", {}).values())):
        for fr in anim["frames"]:
            rects.setdefault(frame_key(fr), fr)
    unknown_total = {}
    cut = {}
    ANCHORS.clear()
    for r, fr in rects.items():
        if isinstance(fr, dict) and "layers" in fr:
            img, mask, ANCHORS[r] = cut_layered(src, fr, background)
        elif isinstance(fr, dict):
            img, mask, anchor = cut_spec(src, fr, background)
            if anchor:
                ANCHORS[r] = anchor
        else:
            img, mask = cut_frame(src, r, background)
        indexed, unknown = to_indexed(img, mask, colour_map, palette)
        for k, v in unknown.items():
            unknown_total[k] = unknown_total.get(k, 0) + v
        cut[r] = indexed
    keys = list(cut)
    placed = dict(zip(keys, pack([cut[k] for k in keys])))

    # Write sheets, using the template sheet's palette so indices mean the same colours
    sheet_count = max(p[0] for p in placed.values()) + 1
    sheet_paths = []
    for s in range(sheet_count):
        sheet = Image.new("P", (SHEET_SIZE, SHEET_SIZE), 0)
        sheet.putpalette(raw_pal)
        for k, (si, x, y) in placed.items():
            if si == s:
                sheet.paste(cut[k], (x, y))
        rel = f"Players/{name}_{s + 1}.gif"
        path = out_dir / "Data" / "Sprites" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        save_sheet(sheet, path)
        sheet_paths.append(rel)
    for s in range(sheet_count + 1, sheet_count + 8):  # a previous build's extra sheets, now unused
        (out_dir / "Data" / "Sprites" / f"Players/{name}_{s}.gif").unlink(missing_ok=True)

    for o in outputs:
        template = read_ani(o["template_ani"])
        feet_y = standing_ground(template, cfg["feet_y"])
        ss_ground = {"Special Stage": template_ground(template, o["template_ani"], "Special Stage")}
        anims, missing = build_anims(template, o["animations"], cut, placed, feet_y, ground=ss_ground)
        append_anims(anims, o.get("appended_animations", {}), cut, placed, feet_y, template["hitboxes"])
        ani_path = out_dir / "Data" / "Animations" / f"{o['name']}.ani"
        # list only the sheets this file's frames use: the game loads every listed sheet, and some
        # screens (the Sonic 1 special stage) are short of sprite memory
        used = sorted({f["sheet"] for a in anims for f in a["frames"]}) or [0]
        for a in anims:
            for f in a["frames"]:
                f["sheet"] = used.index(f["sheet"])
        write_ani(ani_path, dict(sheets=[sheet_paths[s] for s in used], anims=anims, hitboxes=template["hitboxes"]))
        print(f"{o['name']}.ani: {sum(len(a['frames']) for a in anims)} frames")
        if missing:
            print("  animations with no frames (template had some):", ", ".join(missing))

    print(f"{len(cut)} unique frames on {sheet_count} sheet(s)")
    uis = cfg.get("ui", [])
    for ui in (uis if isinstance(uis, list) else [uis]):
        manifest = build_ui(ui, src, background, colour_map, palette, raw_pal, out_dir, base)
        manifest_path = base / ui["manifest"]
        manifest_path.write_text(json.dumps(manifest, indent=1))
        print(f"UI sheet {manifest['sheet']}: {', '.join(manifest['frames'])} -> {manifest_path}")
    if unknown_total:
        print("colours mapped to nearest palette entry:",
              ", ".join(f"#{r:02x}{g:02x}{b:02x} x{n}" for (r, g, b), n in unknown_total.items()))


def build_ui(ui, src, background, colour_map, palette, raw_pal, out_dir, base):
    """Cut UI elements (life icon, name tag, signpost face...) onto their own sheet.

    An element's "flip": true mirrors it left-right after the cut (before any "scale" and "base" paste), for art drawn
    facing left.

    Some game sheets keep a second copy of the player's colours in other palette slots
    (e.g. the signpost uses 130-133 for Sonic's blues), so each element can remap indices.
    """
    elements = {}
    for key, el in ui["elements"].items():
        if "pixels" in el:  # hand-drawn art: rows of characters, each mapped to a colour
            rows = el["pixels"]
            img = Image.new("RGBA", (max(map(len, rows)), len(rows)), (0, 0, 0, 0))
            for yy, row in enumerate(rows):
                for xx, ch in enumerate(row):
                    if ch in el["pixel_colours"]:
                        img.putpixel((xx, yy), hexrgb(el["pixel_colours"][ch]) + (255,))
            mask = img.split()[3].point(lambda a: 255 if a else 0)
        else:
            img, mask = cut_frame(src, tuple(el["rect"]), background, el.get("trim", True))
        if el.get("flip"):  # mirrored left-right, as a frame's "flip" (art drawn facing left: the faithful-art rule's mirroring)
            img, mask = img.transpose(Image.FLIP_LEFT_RIGHT), mask.transpose(Image.FLIP_LEFT_RIGHT)
        if "scale" in el:  # shrink big art to icon size, or enlarge a pipeline sign face (tools/sign_face.py)
            size = (max(1, round(img.width * el["scale"])), max(1, round(img.height * el["scale"])))
            img, mask = img.resize(size, Image.NEAREST), mask.resize(size, Image.NEAREST)
        indexed, unknown = to_indexed(img, mask, colour_map, palette)
        if "base" in el:  # paste onto a piece of game art (kept in its own palette slots)
            b = el["base"]
            x, y, w, h = b["rect"]
            board = Image.open(b["file"]).crop((x, y, x + w, y + h))
            if "recolour" in b:  # leftovers of the original art outside the cleared area
                rc = {int(k): v for k, v in b["recolour"].items()}
                board = board.point(lambda i: rc.get(i, i))
            if "clear" in b:
                cx, cy, cw, ch, index = b["clear"]
                board.paste(index, (cx, cy, cx + cw, cy + ch))
            ox, oy = el.get("at", (0, 0))
            cw_, ch_ = b.get("clip", (w, h))
            art = indexed.crop((0, 0, min(indexed.width, cw_), min(indexed.height, ch_)))
            m = mask.crop((0, 0, art.width, art.height))
            board.paste(art, (ox, oy), m)
            indexed = board
        remap = {int(k): v for k, v in el.get("remap", {}).items()}
        if unknown:
            print(f"  {key}: colours mapped to nearest palette entry:",
                  ", ".join(f"#{r:02x}{g:02x}{b:02x} x{n}" for (r, g, b), n in unknown.items()))
        if remap:
            indexed = indexed.point(lambda i: remap.get(i, i))
        elements[key] = indexed
    keys = list(elements)
    placed = pack([elements[k] for k in keys])
    if max(p[0] for p in placed) > 0:
        sys.exit("UI elements don't fit on one 256x256 sheet")
    sheet = Image.new("P", (SHEET_SIZE, SHEET_SIZE), 0)
    sheet.putpalette(raw_pal)
    manifest = {"sheet": f"Players/{ui['name']}.gif", "frames": {}}
    for k, (_, x, y) in zip(keys, placed):
        sheet.paste(elements[k], (x, y))
        manifest["frames"][k] = [x, y, *elements[k].size]
    if "out" in ui:  # intermediate sheet for other build steps, outside the mod
        path = base / ui["out"]
        manifest["sheet"] = str(path)
    else:
        path = out_dir / "Data" / "Sprites" / manifest["sheet"]
    path.parent.mkdir(parents=True, exist_ok=True)
    save_sheet(sheet, path)
    return manifest


def align_x(images, pivots, reach=12):
    """"align": nudge each frame sideways (px) to best overlap the first frame's shape, so the body stays
    put while legs, flames or effects change around it. images: indexed frames (0 = transparent);
    pivots: [(px, py)]. Returns the adjusted px list."""
    def cells(img, px, py):
        w, h = img.size
        data = img.load()
        return {(x + px, y + py) for y in range(h) for x in range(w) if data[x, y]}
    base = cells(images[0], *pivots[0])
    out = [pivots[0][0]]
    for img, (px, py) in zip(images[1:], pivots[1:]):
        own = cells(img, px, py)
        best = max(range(-reach, reach + 1), key=lambda dx: (len({(x + dx, y) for x, y in own} & base), -abs(dx)))
        out.append(px + best)
    return out


# Balls that touch the ground (rolling uses Jumping; Mario's own curl is the appended "Rolling"): whatever their
# config's anchor, their bottom goes on the ground line of the hitbox the frame uses (its box's bottom), so any size
# of ball rolls on the floor as Sonic's does. Centred ("center"), a small ball floated and a big one sank.
GROUNDED_BALLS = {"Jumping", "Spin Dash", "Rolling"}


def standing_ground(template, default):
    """The base's feet line: the bottom of its standing ("Stopped") hitbox (Sonic and Knuckles 20, Tails 16), or
    `default` (the config's feet_y) for a template without one (the Sonic 1 special stage file)."""
    t = next((a for a in template["anims"] if a["name"] == "Stopped" and a["frames"]), None)
    return template["hitboxes"][t["frames"][0]["hitbox"]][3] if t else default


def put_on_ground(frames, images, grounds):
    """Move a ball's frames up or down together (so they keep the places their anchor gave them relative to each
    other, and a ball that was already right doesn't move) until their bottom is on the row above their frames'
    ground line, as Sonic's ball rolls on the floor. Their bottom: the median one (the lower middle), as a frame or
    two of a spin can be a little taller or shorter than the rest."""
    shift = ground_shift(frames, images, grounds)
    for f in frames:
        f["py"] -= shift


def ground_shift(frames, images, grounds):
    """How far down put_on_ground's frames are from their ground line (negative: up), by their median bottom."""
    return statistics.median_low([f["py"] + img.getbbox()[3] - g for f, img, g in zip(frames, images, grounds)
                                  if img.getbbox()] or [0])


def template_ground(template, template_path, name):
    """One more than the lowest pixel of the template's own `name` frames (Sonic's ball in the Sonic 1 special
    stage file, whose ground line its hitbox doesn't give), or None."""
    t = next((a for a in template["anims"] if a["name"] == name and a["frames"]), None)
    if not t:
        return None
    sprites = Path(template_path).parent.parent / "Sprites"
    low = None
    for f in t["frames"]:
        sheet = Image.open(sprites / template["sheets"][f["sheet"]])
        box = sheet.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])).getbbox()
        if box:
            low = max(low if low is not None else -999, f["py"] + box[3])
    return low


def build_anims(template, animations, cut, placed, feet_y, hitboxes=None, ground=None):
    """Build the animation list in the template's order. feet_y: the base's standing ground line; ground: {animation
    name: its ground line} where the hitbox doesn't give it (the Sonic 1 special stage)."""
    hitboxes = hitboxes or template.get("hitboxes")
    ground = ground or {}
    anims = []
    missing = []
    for t in template["anims"]:
        spec = animations.get(t["name"])
        tpl_hitbox = t["frames"][0]["hitbox"] if t["frames"] else 0
        if spec is None:
            if t["frames"]:
                missing.append(t["name"])
            anims.append(dict(name=t["name"], speed=t["speed"], loop=0, rot=t["rot"], frames=[]))
            continue
        frames = []
        for fr in spec["frames"]:
            key = frame_key(fr)
            img = cut[key]
            si, x, y = placed[key]
            w, h = img.size
            # a layered frame is positioned by its anchor layer, so extra layers don't shift the body
            ax, ay, aw, ah = ANCHORS.get(key, (0, 0, w, h))
            anchor = spec.get("anchor", "feet")
            hitbox = spec.get("hitbox", tpl_hitbox)
            if anchor == "feet":  # stand on the ground: bottom edge on the base's feet line (Sonic's +20)
                px, py = -(ax + aw // 2), feet_y - (ay + ah)
            else:  # "center": hurt, death, mid-air poses
                px, py = -(ax + aw // 2), -(ay + ah // 2)
            frames.append(dict(sheet=si, hitbox=hitbox, x=x, y=y, w=w, h=h, px=px, py=py))
        align = spec.get("align")
        # (a list: [[frame count, align], ...], runs of frames each aligned on its own first frame, or left as placed:
        # Sonic CD's one melee animation holding the melee's own frames, then melee_run's and melee_up's, cd_config.py)
        runs = align if isinstance(align, list) else [[len(frames), bool(align)]]
        if sum(n for n, _ in runs) != len(frames):
            sys.exit(f"{t['name']}: \"align\" runs cover {sum(n for n, _ in runs)} frames of {len(frames)}")
        at = 0
        for n, on in runs:
            if on and n > 1:
                xs = align_x([cut[frame_key(fr)] for fr in spec["frames"][at:at + n]],
                             [(f["px"], f["py"]) for f in frames[at:at + n]])
                for f, px in zip(frames[at:at + n], xs):
                    f["px"] = px
            at += n
        if frames and t["name"] in GROUNDED_BALLS and hitboxes:
            put_on_ground(frames, [cut[frame_key(fr)] for fr in spec["frames"]], [hitboxes[f["hitbox"]][3] for f in frames])
        elif frames and t["name"] == "Special Stage" and ground.get(t["name"]) is not None:
            put_on_ground(frames, [cut[frame_key(fr)] for fr in spec["frames"]], [ground[t["name"]]] * len(frames))
        # a frame's own "offset" last, after the anchor, align and the ground line, so what was nudged stays put
        apply_offsets(frames, spec["frames"])
        loop = spec.get("loop", t["loop"] if t["loop"] < len(frames) else 0)
        if spec.get("hold", 1) > 1:
            # "hold": each frame shown this many times in a row: slows an animation whose speed the player script sets
            # every frame (Tails' flight: 240 rising, 120 falling), where the .ani's own speed is never used
            hold = spec["hold"]
            frames = [f for f in frames for _ in range(hold)]
            loop *= hold
        anims.append(dict(name=t["name"], speed=spec.get("speed", t["speed"]), loop=loop,
                          rot=spec.get("rot", t["rot"]), frames=frames))
    return anims, missing


def append_anims(anims, appended, cut, placed, feet_y, hitboxes=None):
    """Ability animations beyond the base character's list, at fixed slots (empty slots pad the gap). A slot
    inside the list replaces that animation (Tails' list is longer than Sonic's: a Tails-based extra's
    attack takes slot 41, Fly Lift Tired, which a solo player never uses)."""
    for slot in sorted(appended, key=int):
        spec = appended[slot]
        while len(anims) < int(slot):
            anims.append(dict(name="(unused)", speed=0, loop=0, rot=0, frames=[]))
        like = next((a for a in anims if a["name"] == spec.get("like")), None) if "like" in spec else None
        if like:  # "like": <an animation built already>: its speed, loop, rotation and hitbox unless given (a copy of it
            # with other frames: Emerl's copy heads)
            tpl = dict(name=spec["name"], speed=spec.get("speed", like["speed"]), loop=spec.get("loop", like["loop"]),
                       rot=spec.get("rot", like["rot"]),
                       frames=[dict(hitbox=spec.get("hitbox", like["frames"][0]["hitbox"] if like["frames"] else 0))])
        elif "like" in spec:
            sys.exit(f"appended animation {slot}: no animation {spec['like']!r} to be like")
        else:
            tpl = dict(name=spec["name"], speed=spec.get("speed", 60), loop=spec.get("loop", 0),
                       rot=spec.get("rot", 0), frames=[dict(hitbox=spec.get("hitbox", 0))])
        built, _ = build_anims(dict(anims=[tpl]), {spec["name"]: spec}, cut, placed, feet_y, hitboxes)
        if int(slot) < len(anims):
            anims[int(slot)] = built[0]
        else:
            anims.append(built[0])


if __name__ == "__main__":
    main()
