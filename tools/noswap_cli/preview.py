"""`noswap preview <folder>`: a character's frames and animations as labelled PNGs, no game needed.

Frames are cut exactly as the build cuts them (tools/sheet2ani.py's cut_frame / cut_spec / cut_layered: trimmed, turned,
mirrored, layered) and drawn in the game's colours (Sonic 1/2's player palette with his own colours in, through the same
colour mapping as the build) unless --raw. In the animation strips each frame stands where the game puts it: on the
ground line ("feet", the default) or centred on the hitbox ("center"); its pivot is the cell's cross-hair.
"""
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .model import CharacterError, frame_label, load

BG = (40, 44, 52)
CELL_BG = (58, 64, 76)
GROUND = (120, 200, 120)
PIVOT = (230, 120, 120)
TEXT = (235, 235, 235)
DIM = (160, 166, 178)


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except Exception:  # (an old Pillow without FreeType: the fixed bitmap font)
        return ImageFont.load_default()


class Cutter:
    """Cuts frame specs the way sheet2ani does, coloured as the game draws them."""

    def __init__(self, ch, raw):
        import sheet2ani
        self.s2a = sheet2ani
        self.src = Image.open(ch.sheet).convert("RGBA")
        self.background = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in ch.background}
        self.cache = {}
        self.palette = None if raw else self._palette(ch)
        self.colour_map = self._colour_map(ch) if self.palette else None

    def _palette(self, ch):
        from .model import REPO
        tpl = REPO / "extracted" / "Sonic1" / "Data" / "Sprites" / "Players" / "Sonic1.gif"
        if not tpl.exists():
            return None
        raw = Image.open(tpl).getpalette()
        raw += [0] * (768 - len(raw))
        for s, col in ch.own.items():
            raw[3 * s:3 * s + 3] = [int(col[i:i + 2], 16) for i in (1, 3, 5)]
        return [tuple(raw[3 * i:3 * i + 3]) for i in range(256)]

    def _colour_map(self, ch):
        keyed = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)): s for c, s in ch.colours.items()}
        if ch.other_colours != "nearest" or not keyed:
            return keyed
        out = dict(keyed)
        for _, rgb in self.src.convert("RGB").getcolors(1 << 20) or []:
            if rgb not in out and rgb not in self.background:
                out[rgb] = keyed[min(keyed, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))]
        return out

    def cut(self, spec):
        """(RGBA image, anchor box (x, y, w, h)) or (None, None) for a frame that can't be cut."""
        key = json.dumps(self.s2a.frame_key(spec), sort_keys=True)  # (an "offset" moves the frame, not its pixels)
        if key not in self.cache:
            self.cache[key] = self._cut(spec)
        return self.cache[key]

    def _cut(self, spec):
        s2a = self.s2a
        try:
            if isinstance(spec, dict) and "layers" in spec:
                img, mask, anchor = s2a.cut_layered(self.src, spec, self.background)
            elif isinstance(spec, dict):
                img, mask, anchor = s2a.cut_spec(self.src, spec, self.background)
            else:
                img, mask = s2a.cut_frame(self.src, tuple(spec), self.background)
                anchor = None
        except (SystemExit, Exception):
            return None, None
        anchor = anchor or (0, 0, img.width, img.height)
        if self.palette:
            indexed, _ = s2a.to_indexed(img, mask, self.colour_map, self.palette)
            flat = [c for rgb in self.palette for c in rgb]
            indexed.putpalette(flat)
            rgba = indexed.convert("RGBA")
            rgba.putalpha(mask)
            return rgba, anchor
        out = img.copy()
        out.putalpha(mask)
        return out, anchor


def _strip(cutter, title, frames, anchor, feet_y, scale, names, font, small):
    """One animation: its title, then each frame in a cell on a shared ground line, labelled."""
    cut = [cutter.cut(f) for f in frames]
    ok = [(img, a) for img, a in cut if img is not None]
    if not ok:
        return None
    # pivots: as sheet2ani.build_anims places them (px, py relative to the object's position)
    pivots = []
    for img, (ax, ay, aw, ah) in [c if c[0] is not None else (Image.new("RGBA", (8, 8)), (0, 0, 8, 8)) for c in cut]:
        py = feet_y - (ay + ah) if anchor == "feet" else -(ay + ah // 2)
        pivots.append((-(ax + aw // 2), py))
    # each frame's own "offset" (sheet2ani.frame_offset), after the anchor
    pivots = [(px + dx, py + dy) for (px, py), (dx, dy) in zip(pivots, map(cutter.s2a.frame_offset, frames))]
    left = max(-px for px, _ in pivots)
    right = max(px + img.width for (px, _), (img, _) in zip(pivots, [c if c[0] is not None else ok[0] for c in cut]))
    top = max(-py for _, py in pivots)
    bottom = max(py + img.height for (_, py), (img, _) in zip(pivots, [c if c[0] is not None else ok[0] for c in cut]))
    cw, chh = (left + right + 8) * scale, (top + bottom + 8) * scale
    label_h = 18 + 14
    W = max(len(frames) * (cw + 6) + 6, 360)
    H = label_h + chh + 18
    out = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(out)
    d.text((6, 4), title, fill=TEXT, font=font)
    for i, (spec, (img, _), (px, py)) in enumerate(zip(frames, cut, pivots)):
        x0, y0 = 6 + i * (cw + 6), label_h
        d.rectangle([x0, y0, x0 + cw - 1, y0 + chh - 1], fill=CELL_BG + (255,))
        ox, oy = x0 + (left + 4) * scale, y0 + (top + 4) * scale  # the object's position (the pivot)
        if anchor == "feet":
            gy = oy + feet_y * scale
            d.line([x0, gy, x0 + cw - 1, gy], fill=GROUND + (255,))
        d.line([ox - 3, oy, ox + 3, oy], fill=PIVOT + (255,))
        d.line([ox, oy - 3, ox, oy + 3], fill=PIVOT + (255,))
        if img is None:
            d.text((x0 + 4, y0 + 4), "can't cut", fill=PIVOT, font=small)
        else:
            big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
            out.alpha_composite(big, (ox + px * scale, oy + py * scale))
        d.text((x0 + 2, y0 + chh + 2), f"{i} {frame_label(spec, names)}"[:max(4, cw // 6)], fill=DIM, font=small)
    return out


def _stack(images, width=None):
    images = [i for i in images if i is not None]
    W = width or max(i.width for i in images)
    H = sum(i.height for i in images) + 4 * len(images)
    out = Image.new("RGBA", (W, H), BG + (255,))
    y = 0
    for i in images:
        out.alpha_composite(i, (0, y))
        y += i.height + 4
    return out


def _wrap(images, max_width=2400):
    """Images left to right, wrapping at max_width."""
    rows, row, w = [], [], 0
    for i in images:
        if row and w + i.width > max_width:
            rows.append(row)
            row, w = [], 0
        row.append(i)
        w += i.width + 4
    if row:
        rows.append(row)
    lines = []
    for r in rows:
        line = Image.new("RGBA", (sum(i.width + 4 for i in r), max(i.height for i in r)), BG + (255,))
        x = 0
        for i in r:
            line.alpha_composite(i, (x, 0))
            x += i.width + 4
        lines.append(line)
    return _stack(lines)


def _animations(ch):
    """[(title, frames, anchor)]: Sonic 2's list (the fullest: S1's plus S2's own), the ability slots, Sonic 1's special
    stage and the S3&K act clear."""
    out = []
    for name, a in ch.anims["Sonic2"].items():
        out.append((name, a["frames"], a.get("anchor", "feet"), a))
    for name, a in ch.anims["Sonic1"].items():
        if name not in ch.anims["Sonic2"]:
            out.append((f"{name} (Sonic 1)", a["frames"], a.get("anchor", "feet"), a))
    for slot, a in sorted(ch.ability_anims.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 999):
        out.append((f"{slot} {a.get('name', '')}", a["frames"], a.get("anchor", "feet"), a))
    for name, a in ch.special_stage.items():
        out.append((f"{name} (Sonic 1)", a["frames"], a.get("anchor", "center"), a))
    if ch.s3k_victory:
        out.append(("S3&K act clear", ch.s3k_victory["frames"], "feet", ch.s3k_victory))
    return out


def _title(name, a, n):
    bits = [f"{n} frame{'s' * (n != 1)}"]
    for k in ("speed", "loop", "rot", "anchor"):
        if k in a:
            bits.append(f"{k} {a[k]}")
    return f"{name}  ({', '.join(bits)})"


def run(folder, anim=None, out=None, scale=3, raw=False):
    ch = load(folder)
    if not ch.sheet.exists():
        raise CharacterError(f"{ch.sheet} doesn't exist")
    cutter = Cutter(ch, raw)
    font, small = _font(14), _font(10)
    names = ch.frame_names
    anims = _animations(ch)
    paths = []
    from . import kit
    default_dir = (kit.data_root() / "previews" if kit.active() else Path(tempfile.gettempdir()) / "noswap-preview") / ch.id
    if anim:
        pick = [x for x in anims if x[0] == anim or x[0].split("  ")[0] == anim or x[0].split(" ")[0] == anim
                or x[0].startswith(f"{anim} (")]
        if not pick:
            raise CharacterError(f"{ch.id} has no animation {anim!r}: " + ", ".join(x[0] for x in anims))
        title, frames, anchor, a = pick[0]
        img = _strip(cutter, _title(title, a, len(frames)), frames, anchor, ch.feet_y, scale, names, font, small)
        path = Path(out) if out and Path(out).suffix else (Path(out) if out else default_dir) / f"{ch.id}-{_slug(anim)}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        return [path]
    out_dir = Path(out) if out else default_dir
    if out_dir.suffix:
        raise CharacterError("without --anim, --out is a directory (two files are written)")
    out_dir.mkdir(parents=True, exist_ok=True)
    strips = [_strip(cutter, _title(t, a, len(f)), f, an, ch.feet_y, scale, names, font, small) for t, f, an, a in anims]
    sheet = _stack(strips)
    p = out_dir / f"{ch.id}-animations.png"
    sheet.save(p)
    paths.append(p)
    # every frame: the named ones (character.json), or each distinct one the animations use (make_configs.py)
    cells = []
    if ch.kind == "json":
        specs = [(n, r) for n, r in ch.frames.items()]
    else:
        specs = list(ch.frames.items())
    for name, spec in specs:
        img, _ = cutter.cut(spec)
        if img is None:
            continue
        big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
        cell = Image.new("RGBA", (max(big.width, 60) + 8, big.height + 26), CELL_BG + (255,))
        cell.alpha_composite(big, (4, 4))
        ImageDraw.Draw(cell).text((4, big.height + 8), name, fill=TEXT, font=small)
        cells.append(cell)
    if cells:
        p = out_dir / f"{ch.id}-frames.png"
        _wrap(cells).save(p)
        paths.append(p)
    return paths


def _slug(s):
    return "".join(c if c.isalnum() else "-" for c in s).strip("-").lower()
