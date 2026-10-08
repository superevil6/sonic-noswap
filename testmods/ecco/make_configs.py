#!/usr/bin/env python3
"""Writes Ecco the Dolphin's sheet2ani configs (ecco.json for Sonic 1, ecco_s2.json for Sonic 2; CD's and S3&K's come
from the Sonic 2 one).

Ecco the Dolphin (Ecco: The Tides of Time, Sega Genesis; Sega / Novotrade). A separate download (extras.py "crossover":
never in the all-in-one; memory crossover-characters.md). Not in the Mania build. Base character Sonic. His number
(file "Extra<n>") is his place in tools/extras.py, looked up.

Sheet (see SOURCE.txt): Ecco_TidesOfTime.png, "Ecco & Dolphins", ripped by arkonviox (The Spriters Resource, genesis
eccothetidesoftime asset 141831). Genesis art at 1x: he's 73 x 26 px swimming sideways. The cyan page is background.
(Ecco.png, the PC version's sheet, is unused: twice the size, too big for the player sheets.) Frames are found on the
sheet itself (each drawing's box, with the blur streaks' loose dither pixels), named "r<row>.<k>": row r of the
sheet from the top (as SOURCE.txt lists them), k-th drawing from the left. Used as drawn: cut, positioned, and
(Dying) turned half round; nothing redrawn, recoloured or resized.

The sheet's 8 swim rows (6 frames each) by the way he heads on screen, in the sheet's order (clockwise from right):
  r0 right, r1 down-right, r2 down, r3 down-left, r4 left, r5 up-left, r6 up, r7 up-right.
Four of them are the sheet's own mirror copies of the others (checked pixel for pixel): r4 = r0 mirrored left-right,
r3 = r1 mirrored left-right, r5 = r7 mirrored left-right, r6 = r2 mirrored top-bottom. The charge rows r17-r24 (8 frames
each: straight, bend, coil, uncoil, straight, then the blur streak) are in the same direction order.

Land (the user's design, 2026-09-30: "painful but beatable"): he lies on his side and flops along on his swim cycle's
tail slaps (r0), belly on the ground line; a small hop with his tail up; no ball (extras.py "no_roll"); never drowns
(abilities.py no_breathing); slow physics (abilities.py, his entry).

Appended ability slots for the free swim (abilities.py "free_swim", the lead's; the code picks the frame: speed 0, all
anchored on his body's centre, "center"):
  41 "Swim":   8 directions x 6 frames = 48, direction-major: frame 6 * d + k is direction d's cycle frame k.
               d = 0 right, then counterclockwise in 45-degree steps: 1 up-right, 2 up, 3 up-left, 4 left,
               5 down-left, 6 down, 7 down-right (sheet rows r0, r7, r6, r5, r4, r3, r2, r1).
  42 "Charge": 8 directions x 8 frames = 64, the same direction order (rows r17, r24, r23, r22, r21, r20, r19, r18).
  43 "Leap":   the 8-frame somersault (r25), a full turn, for the leap out of the water.
Built: Sonic 1/2 slots 41-43; Sonic CD 45 / 47 / 46 (cd_config.py); S3&K the base's count + 0 / 1 / 2 (build_s3k_art.py
ABILITY_SLOTS).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
from sign_face import board_face  # noqa: E402
from extras import EXTRAS  # noqa: E402

# "Extra<n>", its extras.py position (before its entry exists, the next one)
NAME = next((e["file"] for e in EXTRAS if e["art"].name == HERE.name), f"Extra{len(EXTRAS) + 1}")
SHEET = HERE / "Ecco_TidesOfTime.png"
SOURCE = SHEET.name  # (read in place: the frames are found on it)
BG = (0, 255, 255)
BACKGROUND = ["#00ffff"]
CREDIT_TEXT_Y = 2240  # the ripper's credit line (bottom right): not a frame
A = np.array(Image.open(SHEET).convert("RGB")).astype(int)
FG = ~np.all(A == BG, axis=2)


# ---------------------------------------------------------------- the frames, found on the sheet
def find_frames():
    """{"r<row>.<k>": [x, y, w, h]}: each drawing's box (its biggest piece plus the loose pixels within 6 px of it: the
    blur streaks' dither), rows by overlapping height, left to right."""
    lab, n = ndimage.label(FG, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel())
    boxes, loose = [], []
    for i, s in enumerate(ndimage.find_objects(lab), 1):
        b = [s[1].start, s[0].start, s[1].stop, s[0].stop]
        if b[1] >= CREDIT_TEXT_Y:
            continue
        (boxes if sizes[i] >= 15 else loose).append(b)
    while loose:  # (a box grows as it takes them in, so dither further out joins on the next pass)
        left = []
        for p in loose:
            near = [b for b in boxes if b[0] - 6 <= p[0] and p[2] <= b[2] + 6 and b[1] - 6 <= p[1] and p[3] <= b[3] + 6]
            # (between two drawings: the nearer one's)
            near.sort(key=lambda b: max(b[0] - p[0], p[2] - b[2], 0) + max(b[1] - p[1], p[3] - b[3], 0))
            if not near:
                left.append(p)
                continue
            b = near[0]
            b[:] = [min(b[0], p[0]), min(b[1], p[1]), max(b[2], p[2]), max(b[3], p[3])]
        if len(left) == len(loose):
            raise SystemExit(f"ecco: loose pixels at {left[0][:2]} near no drawing")
        loose = left
    rows = []
    for b in sorted(boxes, key=lambda b: b[1]):
        for r in rows:
            if b[1] < max(x[3] for x in r) - 2 and b[3] > min(x[1] for x in r) + 2:
                r.append(b)
                break
        else:
            rows.append([b])
    out = {}
    for ri, r in enumerate(rows):
        for k, b in enumerate(sorted(r)):
            out[f"r{ri}.{k}"] = [b[0], b[1], b[2] - b[0], b[3] - b[1]]
    names = list(out)
    for i, a in enumerate(names):  # (no box may take in another drawing's pixels)
        for b in names[i + 1:]:
            p, q = out[a], out[b]
            if p[0] < q[0] + q[2] and q[0] < p[0] + p[2] and p[1] < q[1] + q[3] and q[1] < p[1] + p[3]:
                raise SystemExit(f"ecco: frames {a} and {b} overlap")
    return out


B = find_frames()
ROW_COUNTS = {r: sum(1 for k in B if k.startswith(f"r{r}.")) for r in range(27)}
for _r, _n in [*((r, 6) for r in range(8)), (12, 32), (13, 32), *((r, 8) for r in range(16, 27))]:
    if ROW_COUNTS[_r] != _n:
        raise SystemExit(f"ecco: sheet row {_r} has {ROW_COUNTS[_r]} drawings, expected {_n}")


def pixels(name):
    x, y, w, h = B[name]
    return FG[y:y + h, x:x + w]


def best_offset(ref, name, reach=12):
    """(dx, dy) on the sheet that carries `ref`'s drawing onto `name`'s where their shapes overlap most (the body
    held still while the tail and fins move): frame `name`'s place for ref's anchor box."""
    a, (ax, ay, _, _) = pixels(ref), B[ref]
    b, (bx, by, bw, bh) = pixels(name), B[name]
    pa = np.argwhere(a)
    best = None
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            # ref pixel (i, j) at sheet (ax + j, ay + i) lands on frame `name`'s (bx + j + ... ): its box-relative spot
            # is (j + ox, i + oy), with ox = ax - bx + (bx - ax) + dx: aligned box corners plus a nudge
            ys, xs = pa[:, 0] + dy, pa[:, 1] + dx
            ok = (ys >= 0) & (ys < bh) & (xs >= 0) & (xs < bw)
            hit = int(b[ys[ok], xs[ok]].sum())
            key = (hit, -(abs(dx) + abs(dy)))
            if best is None or key > best[0]:
                best = (key, dx, dy)
    return bx - ax + best[1], by - ay + best[2]


def centroid(name):
    ys, xs = np.nonzero(pixels(name))
    x, y = B[name][:2]
    return int(round(x + xs.mean())), int(round(y + ys.mean()))


def belly_row(name, min_px=15):
    """The lowest row of a sideways frame that is body (at least min_px pixels across), not just the hanging flipper."""
    counts = pixels(name).sum(axis=1)
    return B[name][1] + max(i for i, c in enumerate(counts) if c >= min_px)


def spec(name, box):
    return {"rect": B[name], "anchor_box": [int(v) for v in box]}


# Each frame is ONE spec wherever it's used (one copy on the sheets), positioned by its anchor box:
#   swim rows: frame 0's box carried onto each frame where their shapes overlap most (sideways, r0: the box from his
#     top down to his belly line, so "feet" puts his belly on the ground line and "center" his body's middle);
#   charge, leap and the other single poses: a 1 px box at the drawing's centroid (his centre of mass stays put
#     through the coil and the somersault).
F = {}
for _r in range(8):
    ref = f"r{_r}.0"
    x0, y0, w0, h0 = B[ref]
    h = belly_row(ref) - y0 + 1 if _r == 0 else h0
    for _k in range(6):
        name = f"r{_r}.{_k}"
        ox, oy = best_offset(ref, name) if _k else (0, 0)
        F[name] = spec(name, (x0 + ox, y0 + oy, w0, h))
for name in B:
    if name not in F:
        cx, cy = centroid(name)
        F[name] = spec(name, (cx, cy, 1, 1))


# Single poses on the ground ("feet"): the same drawing with its own box's bottom on the ground line (the centroid box
# would sink it halfway), centred on its centroid across
def feet(name):
    x, y, w, h = B[name]
    return spec(name, (centroid(name)[0], y, 1, h))


def f(*names):
    return [F[n] for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)

# ---------------------------------------------------------------- animations
SWIM_R = [f"r0.{k}" for k in range(6)]
FLOP = f(*SWIM_R)  # his sideways swim cycle (tail slaps) along the ground
LIE = f("r0.0")  # lying on his side, belly on the ground line
TILT_UP, TILT_DOWN = "r12.30", "r12.1"  # the rotation row's nearly-flat angles: head a little up / down
ARCH = "r17.3"  # the charge's arched frame (head and tail down): his spring / leap pose
CURL = "r26.0"  # the curl row's first (full-size) curl: his flinch
DEAD = {"rect": B["r0.0"], "rotate": 180}  # belly up (turned half round)
SOMERSAULT = [f"r25.{k}" for k in range(8)]

ANIMS = {
    "Stopped": {"frames": LIE},  # (also the S3&K save screen picture)
    "Waiting": {"frames": LIE},  # (lying still; no idle on the sheet)
    "Looking Up": {"frames": [feet(TILT_UP)]},  # head raised a little
    "Looking Down": {"frames": [feet(TILT_DOWN)]},  # head dipped a little
    "Walking": {"frames": FLOP},  # the flop: his swim cycle's tail slaps, sideways (aligned: the body stays put)
    "Running": {"frames": FLOP},
    "Skidding": {"frames": [feet("r17.1")]},  # the charge's first bend (braking with a flex)
    "Super Peel Out": {"frames": FLOP},
    "Spin Dash": {"frames": [feet(TILT_DOWN)]},  # PLACEHOLDER: he never curls up (extras.py "no_roll")
    "Jumping": C(f(TILT_DOWN)),  # the hop: no ball, his body tipped head-down, tail up (sheet2ani puts it on the ground)
    "Bouncing": C(f(ARCH)),  # springs: the arched leap
    "Hurt": C(f(CURL)),  # curled up
    "Dying": C([DEAD]),  # belly up
    "Drowning": C([DEAD]),  # (never: no_breathing)
    "Fan Rotate": C(f(*SOMERSAULT)),  # tumbling in the fan's updraft: the somersault
    "Breathing": C(f("r7.0")),  # (never needed) heading up-right
    "Pushing": {"frames": FLOP},  # nosing at it, still flopping
    "Flailing 1": {"frames": [feet(TILT_DOWN), F["r0.0"]]},  # teetering at a ledge: rocking head down and back
    "Flailing 2": {"frames": [feet(TILT_DOWN), F["r0.0"]]},
    "Hanging": C(f("r6.0")),  # (S1 poles) upright, head up
    "Clinging On": C(f("r6.0")),
    "Corkscrew H": {"frames": FLOP},
    "Water Slide": C(LIE),
    "Continue": {"frames": LIE},
    "Continue Up": C(f("r6.0")),  # off he goes, head up
    "Super Transform": C(f("r6.0")),  # (he has no Super form)
}
S2_ONLY = {
    "Bored!": {"frames": LIE},
    "Flailing 3": {"frames": [feet(TILT_DOWN), F["r0.0"]]},
    "Grabbed": C(f(CURL)),
    "Twirl H": {"frames": FLOP},
}
CD_ONLY = {name: {"frames": FLOP} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# The free swim's slots (see the docstring): direction d = 0 right, counterclockwise in 45-degree steps
SWIM_ROWS = [0, 7, 6, 5, 4, 3, 2, 1]  # right, up-right, up, up-left, left, down-left, down, down-right
CHARGE_ROWS = [17, 24, 23, 22, 21, 20, 19, 18]
SWIM = [F[f"r{r}.{k}"] for r in SWIM_ROWS for k in range(6)]
CHARGE = [F[f"r{r}.{k}"] for r in CHARGE_ROWS for k in range(8)]
APPENDED = {
    "41": {"name": "Swim", "frames": SWIM, "anchor": "center", "speed": 0},
    "42": {"name": "Charge", "frames": CHARGE, "anchor": "center", "speed": 0},
    "43": {"name": "Leap", "frames": f(*SOMERSAULT), "anchor": "center", "speed": 0},
}

HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
_S = B["r0.0"]
HEAD = [_S[0] + 57, _S[1] + 4, 16, 16]  # his head and beak, from the sideways frame (the life icon)
FACE = [_S[0] + 33, _S[1], 40, 24]  # his front half, dorsal fin to beak (the signpost)
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("ECCO")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1] + 1, 16, 14], "trim": False},
    "sign_face": board_face(FACE),  # on the game's own board, 1x
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": B["r0.0"], "remap": PLUS_128},
    "end_pose_1": {"rect": B[ARCH], "remap": PLUS_128},
    "end_pose_2": {"rect": B["r7.1"], "remap": PLUS_128},
    "end_pose_3": {"rect": B["r25.2"], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128}
       for n, k in enumerate(("r0.0", "r0.2", "r0.4", ARCH, "r7.0", "r7.1"), 1)},
}

# ---------------------------------------------------------------- colours
# All his colours go exact in his own slots 74-95 (no black on his sheet; the credit line's navy isn't his).
KEY_COLOURS = {}


def own_colours():
    counts = {}
    for name in B:
        x, y, w, h = B[name]
        cell = A[y:y + h, x:x + w][FG[y:y + h, x:x + w]]
        for rgb, n in zip(*np.unique(cell, axis=0, return_counts=True)):
            c = "#%02x%02x%02x" % tuple(int(v) for v in rgb)
            counts[c] = counts.get(c, 0) + int(n)
    return sorted(counts.items(), key=lambda kv: -kv[1])


_OWN = own_colours()
if len(_OWN) > 22:
    raise SystemExit(f"ecco: {len(_OWN)} own colours, 22 slots")
PALETTE = {str(74 + k): c for k, (c, _) in enumerate(sorted(_OWN))}


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def all_colours():
    """PALETTE, plus every other colour of the sheet (the credit line's) in the slot of its nearest own colour."""
    keys = {hexrgb(c): int(s) for s, c in PALETTE.items()}
    out = dict(KEY_COLOURS, **{c: int(s) for s, c in PALETTE.items()})
    for rgb in np.unique(A.reshape(-1, 3), axis=0):
        rgb = tuple(int(v) for v in rgb)
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            out[c] = keys[min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))]
    return out


COLOURS = all_colours()
CREDIT = ("Ecco the Dolphin (Ecco: The Tides of Time): ripped by arkonviox, The Spriters Resource, asset 141831 "
          "(Ecco (c) Sega / Novotrade)")

# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose" the pose
# held): lying there, then the arched leap
S3K_VICTORY = {"frames": f("r0.0", "r17.2", ARCH), "pose": 2}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": NAME, "credit": CREDIT,
           "source": SOURCE, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": f"{NAME}SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(f(TILT_DOWN))}}]  # no ball: his hop pose (as Gamma's; one sheet: SS_SHEETS)
        cfg["ui"] = [{"name": f"{NAME}_UI", "manifest": f"{NAME}_ui.json", "elements": ELEMENTS,
                      "out": f"build/{NAME}_UI.gif"},
                     {"name": f"{NAME}_Ending", "manifest": f"{NAME}_ending.json", "elements": ENDING,
                      "out": f"build/{NAME}_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    (HERE / "build").mkdir(exist_ok=True)
    for game, out in (("Sonic1", "ecco.json"), ("Sonic2", "ecco_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("own colours:", ", ".join(f"{c} x{n}" for c, n in _OWN))
