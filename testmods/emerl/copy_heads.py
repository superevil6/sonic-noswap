#!/usr/bin/env python3
"""Emerl's copy heads (the user's request, 2026-09-29): a different head for each Copycat move (abilities.py
"ability_cycle" / "copy_heads"), and his double jump's tilted leap. Used by make_configs.py; run on its own it writes
a preview (copy_heads_preview.png in the session's scratchpad, or the path given).

The heads are the sheet's own loose heads, pasted as drawn (no pixel changed, only placed): on each frame the default
head is found by exact pixel match against the sheet's loose default heads (every body frame's head is one of them: R5_1
is head 0 pixel for pixel, the stance head 5, the leap and the dive head 1, FRONT head 6), its matching pixels are
lifted off, and the move's head goes in its place, aligned on the default head it was drawn from (the four variants are
head 0 with another crest / eyes: placed where they overlap head 0 best, then on the frame's own head as head 0 overlaps
it best). Pixels left over from the old head (a shade or two off its loose drawing: the stance's crest tip) go too when
they're cut off from the body; anything joined to the body stays, under the new head.

The double jump's pose is the flying leap (R5_10, the user's pick), with its move's head, turned 45 degrees to point up
and forward by a pixel-art rotation (tilt(): RotSprite's method, Scale2x three times, then turned by nearest-neighbour
sampling at the original size): only the sheet's own colours, hard pixels, nothing smoothed (the user's exception to
the faithful-art rule, as Fang's cork diagonals).
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SHEET = HERE.parent / "Emerl.png"
BACKGROUND = [(0x95, 0xb1, 0xc8), (0x54, 0x6d, 0x8e), (0xa8, 0xe6, 0x1d)]

# the sheet's loose heads (the row at y 107-131, left to right; boxes of their own pixels)
DEFAULT_HEADS = [(18, 109, 19, 22), (43, 109, 20, 22), (68, 109, 18, 22), (90, 109, 19, 22), (113, 108, 19, 22),
                 (133, 108, 19, 23), (153, 107, 19, 24)]
# the four heads the user picked (the right end of the row): each move's, in abilities.py's ability_cycle order
MOVE_HEADS = {
    "double_jump": (222, 109, 23, 22),  # the crest swept up and forward: the spring of a second jump
    "screw_kick": (296, 109, 20, 22),   # red eyes narrowed, the crest bent: the angry dive kick
    "jet_dash": (246, 110, 25, 21),     # the crest folded back into wide fins: the air dash
    "umbrella": (273, 113, 20, 18),     # the crest folded down flat: the calm float
}


def _rgba(img):
    return np.array(img.convert("RGBA")).astype(np.int32)


def _mask(a):
    m = a[..., 3] > 0
    for b in BACKGROUND:
        m &= ~(a[..., :3] == b).all(-1)
    return m


_SRC = _rgba(Image.open(SHEET))


def _crop(rect):
    x, y, w, h = rect
    a = _SRC[y:y + h, x:x + w].copy()
    m = _mask(a)
    a[~m] = 0
    return a, m


def _best(a, am, b, bm, reach=None):
    """(count, dx, dy): b's top left at (dx, dy) in a's coordinates where the most pixels are exactly equal."""
    H, W = am.shape
    h, w = bm.shape
    best = (-1, 0, 0)
    ys = range(-h + 1, H) if reach is None else range(-reach, reach + 1)
    xs = range(-w + 1, W) if reach is None else range(-reach, reach + 1)
    for dy in ys:
        for dx in xs:
            y0, y1, x0, x1 = max(0, dy), min(H, dy + h), max(0, dx), min(W, dx + w)
            if y0 >= y1 or x0 >= x1:
                continue
            sa, sm = a[y0:y1, x0:x1], am[y0:y1, x0:x1]
            sb, sbm = b[y0 - dy:y1 - dy, x0 - dx:x1 - dx], bm[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
            n = int(((sa == sb).all(-1) & sm & sbm).sum())
            if n > best[0]:
                best = (n, dx, dy)
    return best


# where each move's head sits on head 0 (the one it was drawn from), and head 0 on each default head
_H0 = _crop(DEFAULT_HEADS[0])
_ON_H0 = {m: _best(*_H0, *_crop(r), reach=8)[1:] for m, r in MOVE_HEADS.items()}
_H0_ON = [(0, 0)] + [_best(*_crop(r), *_H0, reach=8)[1:] for r in DEFAULT_HEADS[1:]]


def find_head(a, m):
    """The default head on a frame (RGBA array, mask): (head index, x, y, matched pixels)."""
    best = None
    for k, r in enumerate(DEFAULT_HEADS):
        n, dx, dy = _best(a, m, *_crop(r))
        if best is None or n > best[3]:
            best = (k, dx, dy, n)
    return best


def swap_head(img, move):
    """`img` (RGBA, a frame as cut) with `move`'s head in place of its default one. Returns (image, (ox, oy)): the new
    image and where the old image's top left is in it (the new head can reach past the old edges)."""
    a = _rgba(img)
    m = _mask(a)
    k, hx, hy, n = find_head(a, m)
    ha, hm = _crop(DEFAULT_HEADS[k])
    if n < hm.sum() * 0.8:
        sys.exit(f"copy_heads: no default head found on a frame ({n} of {hm.sum()} pixels)")
    va, vm = _crop(MOVE_HEADS[move])
    # the move's head: on head 0 where it was drawn from it, head 0 on this frame's head
    vx = hx + _H0_ON[k][0] + _ON_H0[move][0]
    vy = hy + _H0_ON[k][1] + _ON_H0[move][1]
    H, W = m.shape
    h, w = hm.shape
    vh, vw = vm.shape
    x0, y0 = min(0, vx), min(0, vy)
    x1, y1 = max(W, vx + vw), max(H, vy + vh)
    out = np.zeros((y1 - y0, x1 - x0, 4), np.int32)
    om = np.zeros(out.shape[:2], bool)
    out[-y0:H - y0, -x0:W - x0] = a
    om[-y0:H - y0, -x0:W - x0] = m
    # lift off the old head's own pixels; the frame's other pixels in its box (drawn over it) come back on top
    front = np.zeros_like(om)
    for yy in range(h):
        for xx in range(w):
            if not hm[yy, xx]:
                continue
            fy, fx = hy + yy - y0, hx + xx - x0
            if 0 <= hy + yy < H and 0 <= hx + xx < W and om[fy, fx]:
                if (out[fy, fx] == ha[yy, xx]).all():
                    om[fy, fx] = False
                    out[fy, fx] = 0
                else:
                    front[fy, fx] = True
    # the old head's pixels that don't match its loose drawing exactly (a shade or two differ: the stance's crest tip)
    # go with it when they're cut off from the body once the head is lifted; the rest (joined to the body) stay, under
    # the new head
    from scipy import ndimage
    lab, _ = ndimage.label(om, structure=np.ones((3, 3)))
    # (the body: what reaches below the old head's box; the stance's crest tip runs a pixel or two past the loose drawing)
    body = set(np.unique(lab[hy + h - y0:])) - {0}
    loose = om & ~np.isin(lab, list(body))
    om[loose] = False
    out[loose] = 0
    sy, sx = vy - y0, vx - x0
    region = out[sy:sy + vh, sx:sx + vw]
    region[vm] = va[vm]
    om[sy:sy + vh, sx:sx + vw] |= vm
    out[~om] = 0
    return Image.fromarray(out.astype(np.uint8), "RGBA"), (-x0, -y0)


def _scale2x(a):
    """Scale2x (EPX) on an RGBA array: every output pixel is one of the input's."""
    H, W = a.shape[:2]
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    B, D, F, Hh, E = p[:-2, 1:-1], p[1:-1, :-2], p[1:-1, 2:], p[2:, 1:-1], p[1:-1, 1:-1]
    eq = lambda u, v: (u == v).all(-1)
    out = np.zeros((2 * H, 2 * W, 4), a.dtype)
    e0 = np.where((eq(D, B) & ~eq(B, F) & ~eq(D, Hh))[..., None], D, E)
    e1 = np.where((eq(B, F) & ~eq(B, D) & ~eq(F, Hh))[..., None], F, E)
    e2 = np.where((eq(D, Hh) & ~eq(D, B) & ~eq(Hh, F))[..., None], D, E)
    e3 = np.where((eq(Hh, F) & ~eq(D, Hh) & ~eq(B, F))[..., None], F, E)
    out[0::2, 0::2], out[0::2, 1::2], out[1::2, 0::2], out[1::2, 1::2] = e0, e1, e2, e3
    return out


def tilt(img, degrees):
    """`img` (RGBA) turned `degrees` anticlockwise, pixel-art safe (RotSprite: Scale2x three times, then each output
    pixel sampled nearest from the 8x picture at its centre turned back): only the picture's own colours."""
    a = np.array(img.convert("RGBA"))
    a[a[..., 3] == 0] = 0
    big = a
    for _ in range(3):
        big = _scale2x(big)
    H, W = a.shape[:2]
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    R = int(math.ceil(math.hypot(W, H))) + 2
    out = np.zeros((R, R, 4), np.uint8)
    cx, cy = W / 2, H / 2
    for Y in range(R):
        for X in range(R):
            dx, dy = X + 0.5 - R / 2, Y + 0.5 - R / 2
            # screen y points down: anticlockwise on screen
            sx, sy = c * dx - s * dy + cx, s * dx + c * dy + cy
            bx, by = int(math.floor(sx * 8)), int(math.floor(sy * 8))
            if 0 <= bx < 8 * W and 0 <= by < 8 * H:
                out[Y, X] = big[by, bx]
    im = Image.fromarray(out, "RGBA")
    return im.crop(im.getbbox())


def preview(path, frames):
    """The heads on the given frames (rows), the tilted double jump at the end, 4x."""
    from PIL import ImageDraw  # noqa: F401
    cells = []
    for rect in frames:
        x, y, w, h = rect
        base = Image.fromarray(_SRC[y:y + h, x:x + w].astype(np.uint8), "RGBA")
        base_a = _rgba(base)
        base_a[~_mask(base_a)] = 0
        base = Image.fromarray(base_a.astype(np.uint8), "RGBA")
        cells.append([base] + [swap_head(base, mv)[0] for mv in MOVE_HEADS])
    leap = (312, 194, 34, 42)
    x, y, w, h = leap
    la = _rgba(Image.fromarray(_SRC[y:y + h, x:x + w].astype(np.uint8), "RGBA"))
    la[~_mask(la)] = 0
    leap_img = Image.fromarray(la.astype(np.uint8), "RGBA")
    cells.append([leap_img, tilt(swap_head(leap_img, "double_jump")[0], 45)])
    cw = max(i.width for r in cells for i in r) + 6
    ch = max(i.height for r in cells for i in r) + 6
    cols = max(len(r) for r in cells)
    sheet = Image.new("RGBA", (cw * cols, ch * len(cells)), BACKGROUND[0] + (255,))
    for r, row in enumerate(cells):
        for c, im in enumerate(row):
            sheet.paste(im, (c * cw + (cw - im.width) // 2, r * ch + ch - 3 - im.height), im)
    sheet = sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST)
    sheet.save(path)
    return path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "build" / "copy_heads_preview.png")
    print(preview(out, [(46, 194, 20, 43), (100, 195, 22, 42), (312, 194, 34, 42), (270, 195, 33, 42),
                        (197, 302, 28, 50)]))
