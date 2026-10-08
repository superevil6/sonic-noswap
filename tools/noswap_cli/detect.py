"""`noswap detect`: find the sprites on a sheet and propose frame rectangles (docs/toolset-cli.md).

Nothing here changes a pixel: it only reads the sheet and proposes [x, y, w, h] boxes trimmed tight to the drawn pixels
(what the build's own trimming, sheet2ani.cut_frame, would keep).

The steps:
1. Background: the sheet's `background` colours (guessed from the corners when there are none) and fully transparent
   pixels. Cell fills are found too: a colour that isn't background but forms large solid rectangles with sprites inside
   (boxes / cells) counts as background, so the sprite inside a box is found rather than the box.
2. Connected pieces of the remaining pixels (8-connectivity), labelled run by run (Pillow only, no numpy).
3. Text and lines first: rows of three or more small glyphs of similar height in a line are one "text" proposal; thin
   lines (underlines, section rules) and box outlines are "line". They're kept but marked, so the UI can hide them.
4. Merging: a small piece (sweat drop, spark, detached hand, held item) joins the nearest bigger body within `merge` px
   (pixel distance, 8-way), never across two different cells.
5. Tiny specks (both sides under `min_size` px) are marked "tiny".
6. Reading order: rows of proposals by vertical overlap, then left to right; names ROW<r>_<i> that don't clash with
   existing frames. A proposal over an existing frame (it overlaps that frame's drawn part) says which one.

Kinds: "sprite" (a body, maybe with merged bits), "small" (a lone piece below body size: an effect, an icon, ...),
"tiny", "text", "line". Confidence 0..1 is a rough "how sure this is a frame".
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops

DEFAULT_MERGE = 3      # px: small bits this close to a body join it
DEFAULT_MIN_SIZE = 3   # px: pieces whose width and height are both under this are "tiny"
BODY_PX = 48           # pixels a piece needs to count as a body others merge into
TEXT_MAX_H = 14        # glyphs up to this tall can be text whatever their colours
BIG_TEXT_H = 32        # taller glyphs (titles) up to this, when drawn in at most BIG_TEXT_COLOURS colours
BIG_TEXT_COLOURS = 2   # (a letter's fill and outline; a spin ball has 3+ and is as wide as it's tall)


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def guess_background(img):
    """The corners' colours (opaque ones), most common first."""
    rgba = img.convert("RGBA")
    W, H = rgba.size
    seen = []
    for p in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)):
        px = rgba.getpixel(p)
        if px[3] and _hex(px) not in seen:
            seen.append(_hex(px))
    return seen


def _mask(rgb, alpha, colours):
    """'L' image: 255 where a pixel is drawn (opaque and not one of the colours)."""
    m = alpha.point(lambda a: 255 if a else 0) if alpha is not None else Image.new("L", rgb.size, 255)
    for c in colours:
        d = ImageChops.difference(rgb, Image.new("RGB", rgb.size, _rgb(c)))
        r, g, b = d.split()
        m = ImageChops.darker(m, ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v else 0))
    return m


class _Pieces:
    """Connected components of a mask, from its runs. pieces: [{bbox [x0, y0, x1, y1] (inclusive), px, runs}]."""

    def __init__(self, mask):
        W, H = mask.size
        data = mask.point(lambda v: 1 if v else 0).tobytes()
        run_re = re.compile(rb"\x01+")
        parent = []

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        runs = []  # (y, x0, x1) inclusive
        prev = []  # (x0, x1, id) of the row above
        for y in range(H):
            row = data[y * W:(y + 1) * W]
            cur = []
            j = 0
            for m in run_re.finditer(row):
                x0, x1 = m.start(), m.end() - 1
                rid = len(runs)
                runs.append((y, x0, x1))
                parent.append(rid)
                while j < len(prev) and prev[j][1] < x0 - 1:
                    j += 1
                k = j
                while k < len(prev) and prev[k][0] <= x1 + 1:
                    a, b = find(rid), find(prev[k][2])
                    if a != b:
                        parent[max(a, b)] = min(a, b)
                    k += 1
                cur.append((x0, x1, rid))
            prev = cur
        groups = {}
        for rid, (y, x0, x1) in enumerate(runs):
            g = groups.get(find(rid))
            if g is None:
                groups[find(rid)] = {"bbox": [x0, y, x1, y], "px": x1 - x0 + 1, "runs": [(y, x0, x1)]}
            else:
                b = g["bbox"]
                b[0], b[2], b[3] = min(b[0], x0), max(b[2], x1), y
                g["px"] += x1 - x0 + 1
                g["runs"].append((y, x0, x1))
        self.pieces = list(groups.values())


def _w(b):
    return b[2] - b[0] + 1


def _h(b):
    return b[3] - b[1] + 1


def _gap(a, b):
    """Chebyshev gap between two inclusive boxes (0: touching or overlapping)."""
    return max(0, b[0] - a[2] - 1, a[0] - b[2] - 1, b[1] - a[3] - 1, a[1] - b[3] - 1)


def _run_distance(small, rows, limit):
    """Smallest 8-way pixel distance (1 = adjacent) from a piece's runs to the runs indexed by row, up to limit."""
    best = limit + 1
    for y, x0, x1 in small["runs"]:
        for yy in range(y - limit, y + limit + 1):
            for bx0, bx1 in rows.get(yy, ()):
                dx = max(0, bx0 - x1, x0 - bx1)
                d = max(dx, abs(yy - y))
                if d < best:
                    best = d
                    if best <= 1:
                        return best
    return best


def find_fills(rgb, alpha, background, min_side=16):
    """Colours that aren't background but make large solid rectangles (cell boxes): {colour: [boxes]}."""
    W, H = rgb.size
    colours = rgb.getcolors(W * H) if alpha is None else None
    if colours is None:
        opaque = rgb.copy()
        if alpha is not None:  # transparent pixels: paint them a background colour so they don't count
            opaque.paste(_rgb(background[0]) if background else (0, 0, 0), mask=alpha.point(lambda a: 0 if a else 255))
        colours = opaque.getcolors(W * H)
    bg = {c.lower() for c in background}
    cand = sorted(((n, _hex(c)) for n, c in colours if _hex(c) not in bg and n >= min_side * min_side * 2), reverse=True)[:10]
    fills = {}
    for n, col in cand:
        only = ImageChops.invert(_mask(rgb, alpha, [col]))  # 255 where the colour is
        if alpha is not None:
            only = ImageChops.darker(only, alpha.point(lambda a: 255 if a else 0))
        boxes = []
        for p in _Pieces(only).pieces:
            b = p["bbox"]
            w, h = _w(b), _h(b)
            if w < min_side or h < min_side or p["px"] < 0.3 * w * h:
                continue
            # a cell's edges are mostly its own colour; a sprite's colour patch rarely fills its bbox's outline
            edge = rgb.crop((b[0], b[1], b[2] + 1, b[3] + 1))
            on = total = 0
            for strip in (edge.crop((0, 0, w, 1)), edge.crop((0, h - 1, w, h)), edge.crop((0, 0, 1, h)), edge.crop((w - 1, 0, w, h))):
                on += sum(cnt for cnt, c in strip.getcolors(max(w, h) + 1) or [] if _hex(c) == col)
                total += strip.width * strip.height
            # and a cell holds a drawing: several other colours inside (a block letter's colour patch holds 1-3)
            inner = [_hex(c) for _, c in edge.getcolors(w * h) or []]
            if on / total >= 0.5 and len([c for c in inner if c != col and c not in bg]) >= 5:
                boxes.append([b[0], b[1], w, h])
        # it's a fill when the boxes hold most of the colour's pixels (a sprite colour is mostly elsewhere)
        if boxes and sum(bw * bh for _, _, bw, bh in boxes) >= 0.6 * n:
            fills[col] = boxes
    return fills


def box_colours(img, background, rects):
    """Cell-box colours behind the frames: colours that aren't background but fill large rectangles (find_fills) one of
    `rects` ([x, y, w, h]: the frames, HUD and ending rects) lies in or overlaps. Each would be drawn in game as a box
    behind the sprite. -> {colour: number of such boxes}"""
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    alpha = None if alpha.getextrema()[0] == 255 else alpha
    fills = find_fills(rgba.convert("RGB"), alpha, [c.lower() for c in background])
    out = {}
    for col, boxes in fills.items():
        n = sum(1 for bx, by, bw, bh in boxes
                if any(x < bx + bw and bx < x + w and y < by + bh and by < y + h for x, y, w, h in rects))
        if n:
            out[col] = n
    return out


def detect(img, background=None, merge=DEFAULT_MERGE, min_size=DEFAULT_MIN_SIZE, region=None, existing=None,
           fills=True, names=()):
    """Propose frames on a sheet (a PIL image). existing: {name: [x, y, w, h]} drawn parts of the frames already there
    (or their rects). names: more frame names the new names mustn't take. region: [x, y, w, h] to search only inside.
    Returns {"background", "fills", "proposals", ...}."""
    rgba = img.convert("RGBA")
    ox = oy = 0
    if region:
        x, y, w, h = [int(v) for v in region]
        x, y = max(0, x), max(0, y)
        w, h = min(w, rgba.width - x), min(h, rgba.height - y)
        if w <= 0 or h <= 0:
            return {"background": background or [], "fills": {}, "proposals": [], "size": list(img.size)}
        rgba = rgba.crop((x, y, x + w, y + h))
        ox, oy = x, y
    alpha = rgba.getchannel("A")
    alpha = None if alpha.getextrema()[0] == 255 else alpha
    rgb = rgba.convert("RGB")
    guessed = not background
    background = [c.lower() for c in (background or guess_background(img))]
    fill_boxes = find_fills(rgb, alpha, background) if fills else {}
    cells = [b for bs in fill_boxes.values() for b in bs]
    mask = _mask(rgb, alpha, background + list(fill_boxes))
    pieces = _Pieces(mask).pieces

    def colours(b):
        box = (b[0], b[1], b[2] + 1, b[3] + 1)
        crop = Image.composite(rgb.crop(box), Image.new("RGB", (_w(b), _h(b)), _rgb(background[0]) if background else 0),
                               mask.crop(box))
        return len([c for _, c in crop.getcolors(_w(b) * _h(b)) or [] if _hex(c) not in background])

    def cell_of(b):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        for i, (x, y, w, h) in enumerate(cells):
            if x <= cx < x + w and y <= cy < y + h:
                return i
        return None

    for p in pieces:
        b = p["bbox"]
        p["cell"] = cell_of(b)
        p["kind"] = None
        w, h = _w(b), _h(b)
        if w < min_size and h < min_size:
            p["kind"] = "tiny"
        elif max(w, h) >= 12 and (min(w, h) <= 2 or (max(w, h) >= 6 * min(w, h) and p["px"] <= 1.6 * max(w, h))):
            # a rule or underline, maybe with ticks (a label's bracket)
            p["kind"] = "line"
        elif max(w, h) >= 16 and p["px"] < 0.25 * w * h:
            # a box outline or an L-shaped rule: nearly all its pixels lie on its bbox's edges
            edge = 0
            for y, x0, x1 in p["runs"]:
                if y <= b[1] + 1 or y >= b[3] - 1:
                    edge += x1 - x0 + 1
                else:
                    edge += max(0, min(x1, b[0] + 1) - x0 + 1) + max(0, x1 - max(x0, b[2] - 1) + 1)
            if edge >= 0.8 * p["px"]:
                p["kind"] = "line"

    # text: rows of small glyphs of similar height, close together on a line
    glyphs = [p for p in pieces if p["kind"] is None and (
        (_h(p["bbox"]) <= TEXT_MAX_H and _w(p["bbox"]) <= 12 * _h(p["bbox"]) and p["px"] < 0.85 * _w(p["bbox"]) * _h(p["bbox"])) or
        (_h(p["bbox"]) <= BIG_TEXT_H and _w(p["bbox"]) <= _h(p["bbox"]) and colours(p["bbox"]) <= BIG_TEXT_COLOURS) or
        # whole words (letters joined by their outline or anti-aliasing): short, wide, thin strokes
        (_h(p["bbox"]) <= 24 and 1.8 * _h(p["bbox"]) <= _w(p["bbox"]) <= 12 * _h(p["bbox"]) and p["px"] <= 0.55 * _w(p["bbox"]) * _h(p["bbox"])))]
    glyphs.sort(key=lambda p: p["bbox"][0])
    used = set()
    texts = []
    for i, g in enumerate(glyphs):
        if id(g) in used:
            continue
        line = [g]
        b = list(g["bbox"])
        for q in glyphs[i + 1:]:
            if id(q) in used:
                continue
            qb = q["bbox"]
            hq, hl = _h(qb), max(_h(x["bbox"]) for x in line)
            if qb[0] - b[2] - 1 > max(4, hl):  # (sorted by x: a later one may still fit, keep looking)
                continue
            ov = min(b[3], qb[3]) - max(b[1], qb[1]) + 1
            if ov < 0.5 * min(hq, _h(b)) or not (0.4 <= hq / max(1, hl) <= 2.5) or abs(qb[3] - b[3]) > max(3, hl // 2):
                continue
            line.append(q)
            b = [min(b[0], qb[0]), min(b[1], qb[1]), max(b[2], qb[2]), max(b[3], qb[3])]
        hs = sorted(_h(x["bbox"]) for x in line)
        wide = _w(b) >= (1.5 if len(line) >= 4 else 2) * _h(b)
        if len(line) >= 3 and hs[-1] <= max(4, 2 * hs[len(hs) // 2]) and wide:
            for x in line:
                used.add(id(x))
                x["kind"] = "glyph"
            texts.append({"bbox": b, "px": sum(x["px"] for x in line), "kind": "text", "parts": len(line)})

    # dots and accents on a text line (an i's dot, a comma) belong to it
    for p in pieces:
        if p["kind"] in (None, "tiny") and p["px"] < BODY_PX:
            b = p["bbox"]
            for t in texts:
                tb = t["bbox"]
                if b[0] >= tb[0] - 2 and b[2] <= tb[2] + 2 and b[1] >= tb[1] - 3 and b[3] <= tb[3] + 3:
                    p["kind"] = "glyph"
                    t["bbox"] = [min(tb[0], b[0]), min(tb[1], b[1]), max(tb[2], b[2]), max(tb[3], b[3])]
                    t["px"] += p["px"]
                    t["parts"] += 1
                    break

    # merging: small pieces join the nearest body within `merge` px (same cell only)
    live = [p for p in pieces if p["kind"] in (None, "tiny")]  # (a speck next to a body joins it too)
    for p in live:
        p["parts"] = 1
    bodies = [p for p in live if p["px"] >= BODY_PX and max(_w(p["bbox"]), _h(p["bbox"])) >= 8]
    smalls = sorted((p for p in live if p not in bodies), key=lambda p: -p["px"])
    if merge > 0:
        index = {}
        for bd in bodies:
            rows = {}
            for y, x0, x1 in bd["runs"]:
                rows.setdefault(y, []).append((x0, x1))
            index[id(bd)] = rows
        changed = True
        while changed and smalls:
            changed = False
            rest = []
            for s in smalls:
                best, bd_best = merge + 1, None
                for bd in bodies:
                    if bd["cell"] != s["cell"] or _gap(bd["bbox"], s["bbox"]) > merge:
                        continue
                    d = _run_distance(s, index[id(bd)], merge)
                    if d < best or (d == best and bd_best is not None and bd["px"] > bd_best["px"]):
                        best, bd_best = d, bd
                if bd_best is None:
                    rest.append(s)
                    continue
                b, sb = bd_best["bbox"], s["bbox"]
                bd_best["bbox"] = [min(b[0], sb[0]), min(b[1], sb[1]), max(b[2], sb[2]), max(b[3], sb[3])]
                bd_best["px"] += s["px"]
                bd_best["parts"] += s["parts"]
                rows = index[id(bd_best)]
                for y, x0, x1 in s["runs"]:
                    rows.setdefault(y, []).append((x0, x1))
                bd_best["runs"] = bd_best["runs"] + s["runs"]
                changed = True
            smalls = rest
        # a flat piece split off a body by a one-pixel gap (motion lines under the feet) joins it too
        for bd in sorted(bodies, key=lambda p: p["px"]):
            if bd.get("into") or merge < 2:
                continue
            for big in bodies:
                if (big is bd or big.get("into") or big["px"] * 0.35 < bd["px"] or big["cell"] != bd["cell"]
                        or _gap(big["bbox"], bd["bbox"]) > 1 or _run_distance(bd, index[id(big)], 2) > 2):
                    continue
                b, sb = big["bbox"], bd["bbox"]
                big["bbox"] = [min(b[0], sb[0]), min(b[1], sb[1]), max(b[2], sb[2]), max(b[3], sb[3])]
                big["px"] += bd["px"]
                big["parts"] += bd["parts"]
                for y, x0, x1 in bd["runs"]:
                    index[id(big)].setdefault(y, []).append((x0, x1))
                big["runs"] = big["runs"] + bd["runs"]
                bd["into"] = big
                break
        bodies = [bd for bd in bodies if not bd.get("into")]
    out = []
    for p in bodies:
        conf = 0.9 if p["px"] >= BODY_PX * 4 else 0.7
        out.append({"bbox": p["bbox"], "px": p["px"], "kind": "sprite", "parts": p["parts"], "confidence": conf})
    for p in smalls:
        tiny = p["kind"] == "tiny"
        out.append({"bbox": p["bbox"], "px": p["px"], "kind": "tiny" if tiny else "small", "parts": p["parts"],
                    "confidence": 0.05 if tiny else 0.4})
    for p in pieces:
        if p["kind"] == "line":
            out.append({"bbox": p["bbox"], "px": p["px"], "kind": "line", "parts": 1, "confidence": 0.1})
    for t in texts:
        out.append({**t, "confidence": 0.1})

    # reading order: rows by vertical overlap with each row's first frame (a fixed band, so one tall drawing
    # can't chain rows together), then x
    out.sort(key=lambda p: (p["kind"] not in ("sprite", "small"), p["bbox"][1], p["bbox"][0]))
    rows = []
    for p in out:
        b = p["bbox"]
        best, best_ov = None, 0
        for r in rows:
            ov = min(r["y1"], b[3]) - max(r["y0"], b[1]) + 1
            if ov >= 0.5 * min(_h(b), r["y1"] - r["y0"] + 1) and ov > best_ov:
                best, best_ov = r, ov
        if best:
            best["items"].append(p)
        else:
            rows.append({"y0": b[1], "y1": b[3], "items": [p]})
    rows.sort(key=lambda r: r["y0"])
    taken = set(existing or {}) | set(names)
    existing = {n: r for n, r in (existing or {}).items() if isinstance(r, (list, tuple)) and len(r) == 4}
    proposals = []
    rn = 0
    for r in rows:
        frames_here = sorted((p for p in r["items"] if p["kind"] in ("sprite", "small")), key=lambda p: p["bbox"][0])
        others = sorted((p for p in r["items"] if p["kind"] not in ("sprite", "small")), key=lambda p: p["bbox"][0])
        if frames_here:
            rn += 1
        for i, p in enumerate(frames_here + others):
            b = p["bbox"]
            rect = [b[0] + ox, b[1] + oy, _w(b), _h(b)]
            name = None
            if p["kind"] in ("sprite", "small"):
                name = f"ROW{rn}_{i + 1}"
                k = 2
                while name in taken:
                    name = f"ROW{rn}_{i + 1}_{k}"
                    k += 1
                taken.add(name)
            over = _overlaps(rect, existing)
            proposals.append({"rect": rect, "kind": p["kind"], "confidence": p["confidence"], "parts": p["parts"],
                              "px": p["px"], "name": name, "existing": over})
    return {"background": background, "guessed_background": guessed, "fills": fill_boxes, "proposals": proposals,
            "size": list(img.size), "merge": merge, "min_size": min_size, "region": region}


def _overlaps(rect, existing):
    """The existing frame this rect mostly lies on (by its drawn part), or None."""
    x, y, w, h = rect
    best, best_a = None, 0
    for n, (ex, ey, ew, eh) in existing.items():
        iw = min(x + w, ex + ew) - max(x, ex)
        ih = min(y + h, ey + eh) - max(y, ey)
        if iw > 0 and ih > 0:
            a = iw * ih
            if a >= 0.5 * min(w * h, ew * eh) and a > best_a:
                best, best_a = n, a
    return best


def drawn_parts(img, frames, background):
    """{name: the drawn part [x, y, w, h] of each existing frame rect} (sheet2ani's trimming), skipping empty ones."""
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    mask = _mask(rgba.convert("RGB"), alpha, [c.lower() for c in background])
    out = {}
    W, H = rgba.size
    for n, r in frames.items():
        if not (isinstance(r, (list, tuple)) and len(r) == 4):
            continue
        x, y, w, h = [int(v) for v in r]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        b = mask.crop((x0, y0, x1, y1)).getbbox()
        if b:
            out[n] = [x0 + b[0], y0 + b[1], b[2] - b[0], b[3] - b[1]]
    return out


def split(img, rect, background, merge=0):
    """A proposal split into its separate pieces (no merging): [[x, y, w, h], ...] (tiny specks dropped). The cell
    fills are found on the whole sheet (a small area alone may not show they're cells)."""
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    alpha = None if alpha.getextrema()[0] == 255 else alpha
    background = [c.lower() for c in background]
    background += list(find_fills(rgba.convert("RGB"), alpha, background))
    res = detect(img, background, merge=merge, min_size=DEFAULT_MIN_SIZE, region=rect, fills=False)
    return [p["rect"] for p in res["proposals"] if p["kind"] not in ("tiny", "line")]


# ---------------------------------------------------------------- the command

def run(folder, merge=DEFAULT_MERGE, min_size=DEFAULT_MIN_SIZE, as_json=False, show_all=False, region=None):
    import json
    from .model import load
    ch = load(folder)
    if not Path(ch.sheet).is_file():
        print(f"error: the sheet {ch.sheet} doesn't exist", file=sys.stderr)
        return 1
    with Image.open(ch.sheet) as im:
        img = im.convert("RGBA")
    frames = dict(getattr(ch, "frames", {}) or {})
    res = detect(img, ch.background, merge=merge, min_size=min_size, region=region,
                 existing=drawn_parts(img, frames, ch.background or guess_background(img)) if frames else None)
    if as_json:
        print(json.dumps(res, indent=1))
        return 0
    props = res["proposals"]
    new = [p for p in props if p["kind"] in ("sprite", "small") and not p["existing"]]
    print(f"{Path(ch.sheet).name} {res['size'][0]}x{res['size'][1]}, background "
          f"{', '.join(res['background'])}{' (guessed from the corners)' if res['guessed_background'] else ''}"
          + (f", cell fills {', '.join(res['fills'])}" if res["fills"] else ""))
    counts = {}
    for p in props:
        counts[p["kind"]] = counts.get(p["kind"], 0) + 1
    print(f"{len(new)} new frame(s); {sum(1 for p in props if p['existing'])} on existing frames; "
          + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) + f" (merge {merge} px, min size {min_size} px)")
    for p in props:
        if not show_all and (p["kind"] not in ("sprite", "small") or p["existing"]):
            continue
        note = p["kind"] + (f", {p['parts']} pieces" if p["parts"] > 1 else "") + (f", on {p['existing']}" if p["existing"] else "")
        label = json.dumps(p["name"] or p["kind"])
        print(f"  {label + ':':16} [{', '.join(str(v) for v in p['rect'])}],   # {note}")
    if not show_all:
        print("(--all also lists text, lines, tiny specks and pieces on existing frames)")
    listed = {c.lower() for c in ch.background}
    rects = [p["rect"] for p in props if p["kind"] in ("sprite", "small")] + [list(r) for r in frames.values() if isinstance(r, (list, tuple))]
    meets = lambda a, b: a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    # (cells come in numbers and sit behind the sprites: a colour in one or two panels is more likely scenery)
    boxes = [c for c, bs in res["fills"].items() if c.lower() not in listed and len(bs) >= 3
             and any(meets(r, b) for b in bs for r in rects)]
    if boxes:
        bg = list(ch.background or res["background"]) + boxes
        print(f"\nthe cell boxes' colour{'s' if len(boxes) > 1 else ''} {', '.join(boxes)} must be background too, or "
              "the game draws a box behind every frame: in character.json, set\n"
              f'  "background": {json.dumps(bg)}')
    return 0
