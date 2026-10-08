"""Pipeline signpost faces: for an extra whose sheet has no signpost art, a head cut from the sheet goes on the game's
own board (Sonic 1's Items2 Eggman board, its yellow face area 40x24 at 4,5; S3&K's sign is built from the same image).

The head is enlarged nearest-neighbour by a non-integer `scale` so it fills the face area as the game's own faces do
(the user's exception to the faithful-art rule, 2026-09-28: pipeline-made signpost faces only). sheet2ani's UI
"scale" does the resize after the crop; this picks the crop so the enlarged head fits the 40x24 area: its bottom rows
(the chin stays; any trim is at the top, crest or quill tips, as the game's Tails and Knuckles boards cut their ears)
and its middle columns, centred as before.
"""
import math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FACE_W, FACE_H = 40, 24  # the board's face area, at 4,5


def board_face(head, scale=1.0, flip=False):
    """The UI "sign_face" element for the head rect [x, y, w, h] (source sheet coordinates), enlarged by `scale`;
    `flip`: mirrored left-right (a sheet drawn facing left, so the face looks right as in game)."""
    x, y, w, h = head
    ch = min(h, math.floor(FACE_H / scale + 1e-9))
    cw = min(w, math.floor(FACE_W / scale + 1e-9))
    while round(ch * scale) > FACE_H:
        ch -= 1
    while round(cw * scale) > FACE_W:
        cw -= 1
    cx = x + (w - cw) // 2
    cy = y + h - ch
    sw, sh = round(cw * scale), round(ch * scale)
    el = {"rect": [cx, cy, cw, ch], "trim": False, "at": [4 + (FACE_W - sw) // 2, 5 + (FACE_H - sh) // 2],
          "base": {"file": str(REPO / "extracted/Sonic1/Data/Sprites/Global/Items2.gif"),
                   "rect": [34, 182, 48, 32], "clear": [4, 5, FACE_W, FACE_H, 15],
                   "recolour": {"12": 8, "13": 8, "14": 8}}}  # Eggman's red bits on the frame
    if scale != 1.0:
        el["scale"] = scale
    if flip:
        el["flip"] = True
    return el


# ---------------------------------------------------------------- character.json "sign_face" (character_json.sign_face_plan)

WHOLE_SIGN = (44, 28)  # a drawing at least this big both ways is a whole sign (the board is 48x32); smaller is a head
SCALE_RANGE = (1.0, 2.0)  # an explicit "scale" (enlarging only: a nearest shrink would drop pixels)
AUTO_MAX = 1.5


def auto_scale(w, h):
    """character.json's "scale": "auto" for a w x h head: enough to fill the face area's 24-px height, to 0.1, between
    1 (never shrunk) and 1.5, and no wider than the 40-px area if 1x fits it. The hand-picked boards agree on most
    (Mega Man 19x17 1.4, Marine 19x18 1.3, Mephiles 25x21 and Emerl 19x22 1.1, Big 40x26, Ecco and Omega 40x24, Headdy
    32x24 1.0); the rest chose 0.1-0.3 more, trimming a crest or quills at the top (Chaos 1.3, Silver 1.3, Jet 1.2)."""
    s = min(AUTO_MAX, max(1.0, round(FACE_H / h, 1)))
    if w <= FACE_W < w * s:
        s = max(1.0, math.floor(FACE_W / w * 10) / 10)
    return s


def drawn_box(src, rect, background):
    """The drawn part of `rect` on the RGBA sheet `src` (pixels neither transparent nor a `background` (r, g, b)), in
    sheet coordinates [x, y, w, h], as sheet2ani's trim cuts it; None when it's empty or off the sheet."""
    x, y, w, h = rect
    if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > src.width or y + h > src.height:
        return None
    from PIL import Image
    img = src.crop((x, y, x + w, y + h))
    mask = Image.new("L", img.size, 0)
    px, mp = img.load(), mask.load()
    for yy in range(h):
        for xx in range(w):
            p = px[xx, yy]
            if p[3] and p[:3] not in background:
                mp[xx, yy] = 255
    box = mask.getbbox()
    return [x + box[0], y + box[1], box[2] - box[0], box[3] - box[1]] if box else None


def is_whole_sign(w, h):
    return w >= WHOLE_SIGN[0] and h >= WHOLE_SIGN[1]


def default_head(src, rect, background):
    """A head for a character with no sign_face: the top half of his standing frame's drawing (at most the face area's
    24 rows), trimmed to what's drawn there. None when the frame is empty."""
    box = drawn_box(src, rect, background)
    if not box:
        return None
    x, y, w, h = box
    return drawn_box(src, [x, y, w, min(h, FACE_H, max(1, round(h / 2)))], background)


def preview(src, background, el, colour=lambda rgb: rgb):
    """The board a board_face element builds (sheet2ani.build_ui's "base" paste), as an RGBA image for the editor: the
    head cut from the RGBA sheet `src`, each colour through `colour` (rgb -> the game's rgb), enlarged nearest by its
    scale, on the Items2 board (cleared and recoloured as the build does), in Items2's own colours."""
    from PIL import Image
    x, y, w, h = el["rect"]
    head = src.crop((x, y, x + w, y + h)).convert("RGBA")
    px = head.load()
    for yy in range(h):
        for xx in range(w):
            p = px[xx, yy]
            px[xx, yy] = (0, 0, 0, 0) if not p[3] or p[:3] in background else (*colour(p[:3]), 255)
    if el.get("flip"):
        head = head.transpose(Image.FLIP_LEFT_RIGHT)
    s = el.get("scale", 1.0)
    head = head.resize((max(1, round(w * s)), max(1, round(h * s))), Image.NEAREST)
    b = el["base"]
    bx, by, bw, bh = b["rect"]
    board = Image.open(b["file"]).crop((bx, by, bx + bw, by + bh))
    rc = {int(k): v for k, v in b.get("recolour", {}).items()}
    board = board.point(lambda i: rc.get(i, i))
    cx, cy, cw, ch, index = b["clear"]
    board.paste(index, (cx, cy, cx + cw, cy + ch))
    out = board.convert("RGBA")
    out.putdata([(0, 0, 0, 0) if i == 0 else p for i, p in zip(board.getdata(), out.getdata())])
    out.alpha_composite(head, tuple(el.get("at", (0, 0))))
    return out
