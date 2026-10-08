#!/usr/bin/env python3
"""Writes Mephiles the Dark's sheet2ani configs (mephiles.json for Sonic 1, mephiles_s2.json for Sonic 2; CD's and
S3&K's come from the Sonic 2 one).

PREPARED 2026-09-28, NOT YET INTEGRATED: no extras.py / abilities.py entry yet, never built. NAME below is a guess
(extra 35 if Sally, Marine and Omega take 32-34 first): set it to the extras.py position ("Extra<n>") when integrating.
Base character Sonic. Public once integrated (credit in mods/NoSwap/README.md).

Sheet: testmods/Mephiles.png (675x652), "Mephiles the Dark" by Gardow (see SOURCE.txt; the sheet credits "Gardow,
Xeric, Fox Omega, Charity, Domenico"). Sky-blue page (#09c2ff), the only background. Every sprite faces right.
Sections (the sheet's own labels) and the frame names used here:
  "Mephiles - Ground"   G1_0 standing; G1_1-G1_4 idle (weight shifts, a hand raised); G1_5-G1_12 walking (8);
                        G2_0-G2_6 gestures (G2_1 hand drawn back to his chest, G2_3 open palm thrust out, G2_4 pointing,
                        G2_5 / G2_6 arms across); G2_7-G2_12 the red crystal (held out, turned, tossed up, caught)
  "Floating"            F1_0-F1_7 floating idle (8, the lower body a wisp); F1_8 head bowed; F1_9 arms spread; F1_10
                        diving forward; F1_11 flying flat; F2_0-F2_12 the same gestures and crystal frames floating
  "Both"                CROUCH (hunched); RECOIL, REEL (hit); KNOCKED (thrown back); RISE1-RISE3 standing in a dark
                        pool; MELT1-MELT7 sinking into it (the last ones loose specks, cut together)
  "Mephiles - Alternative"  FLOAT_ALT; HEAD1-HEAD4 (loose heads, 24x21, and their repeats at 286-343); UP (standing,
                        looking up), DOWN (looking down), FLOAT_UP / FLOAT_DOWN; the Shadow form (unused: 21 colours of
                        its own), WHITE1 / WHITE2 (white silhouettes), CRYSTAL (back in his crystal form)
  "SFX"                 dark aura puffs, streaks, the dark orb (ORB1-ORB6), bubbles, dark crystal spikes, big spheres

Size: standing 40-42 px (G1_0 is 40), floating 44-46 (the wisp adds a few px); Sonic is about 40. Not scaled.

Abilities (PLANNED, the user's design in memory last-five.md; wire them in abilities.py when integrating):
  - jump ability: a very SHORT float: slot 42 "Float" (hover-type, not an attack; CD 47, S3&K hover offset 1): his
    full-speed run's frame F1_11 (flying flat), the user's pick 2026-09-29 (the Floating idle F1_4-F1_7 looked awkward).
  - Y: a PARABOLIC dark crystal shot, a pair, one each way (goes down, then arcs up once, then disappears; cooldown about 2 s): throw pose
    slots 43 / 44 (CD 46): F2_1 (hand drawn back) then F2_3 (palm thrust out), floating (G2_1 / G2_3 before the rework).
    Projectile art: SHOT_DRAWINGS below (the SFX dark orb; see the notes there for the other candidates).
  - THE REWORK (the user, 2026-09-29, built): he floats everywhere: F1_4-F1_7 (FLOAT_FEET) are his Stopped, Walking,
    Running and Super Peel Out (S3&K's Idle, Walk / Jog / Run / Dash / Peelout and their angled ones come from those),
    F1_0-F1_3 + F2_7-F2_12 his Waiting, FLOAT_UP / FLOAT_DOWN his look up / down, F2_2 / F2_3 his push, and the throw
    pose is F2_1 / F2_3 on the ground too; the walk / run lean forward with his speed at runtime (abilities.py
    float_lean). The Crystal Shot is the orb 2x (abilities.py "scale" 2) through terrain. Down + Y: the Shadow Sink,
    slot 47 (SINK: RISE1-3, MELT1-7; abilities.py sink).
  - ball: the sheet has none: the generic spin ball (tools/generic_ball.py: Sonic Mania's plain spin ball, SEGA's art), dark with his blues
    (BALL_COLOURS), as Chaos / Heavy / Bomb.

Nothing is redrawn, recoloured or resized: frames are cut as drawn. The name tag is our own lettering in the HUD font
the other extras use (the sheet has none); the life icon / 1-UP are crops of HEAD2; the signpost is HEAD2 on the game's
own board (the signpost exception). Colours: 22 on the frames, UI crops and the shot; black is Sonic's slot 1, the other 21 keep their
exact values in slots 74-94: nothing merged. (Unused and left to their nearest slot: the Shadow form's 21 colours,
#006aaa and #ffffff.)
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
import generic_ball  # noqa: E402
from sign_face import board_face  # noqa: E402

NAME = "Extra35"  # (its extras.py position)
SHEET = "../Mephiles.png"
BACKGROUND = ["#09c2ff"]
SRC = Image.open(HERE / SHEET).convert("RGB")


def row(prefix, rects):
    return {f"{prefix}_{k}": list(r) for k, r in enumerate(rects)}


B = {  # frame -> [x, y, w, h] (its bounding box on the sheet; loose bits such as the crystal and sparkles included)
    **row("G1", [(5, 57, 30, 40), (44, 55, 27, 42), (79, 55, 27, 42), (113, 55, 27, 42), (149, 55, 31, 42),
                 (193, 56, 24, 41), (225, 56, 27, 42), (257, 56, 30, 42), (289, 56, 24, 42), (321, 56, 23, 42),
                 (353, 56, 26, 42), (386, 56, 27, 42), (418, 56, 23, 42)]),
    **row("G2", [(8, 107, 28, 42), (39, 107, 28, 42), (70, 107, 31, 42), (104, 107, 30, 42), (138, 107, 32, 42),
                 (177, 107, 27, 42), (214, 107, 27, 42), (253, 107, 34, 42), (299, 107, 34, 42), (345, 107, 35, 42),
                 (391, 107, 42, 42), (437, 107, 38, 42), (483, 107, 35, 42)]),
    **row("F1", [(11, 177, 31, 46), (52, 176, 31, 46), (91, 176, 31, 46), (130, 176, 31, 46), (171, 176, 27, 46),
                 (208, 176, 27, 46), (242, 176, 27, 46), (276, 176, 31, 46), (313, 178, 30, 44), (354, 180, 37, 43),
                 (404, 179, 37, 39), (446, 189, 49, 26)]),
    **row("F2", [(12, 233, 28, 46), (43, 233, 28, 46), (74, 233, 31, 46), (108, 233, 30, 46), (142, 233, 32, 46),
                 (181, 233, 27, 46), (218, 233, 27, 46), (264, 235, 34, 46), (310, 235, 34, 46), (356, 235, 35, 46),
                 (402, 235, 42, 46), (448, 235, 38, 46), (494, 235, 35, 46)]),
    # Both
    "CROUCH": [14, 318, 24, 31], "RECOIL": [43, 304, 28, 44], "REEL": [73, 304, 36, 43], "KNOCKED": [123, 307, 41, 36],
    "RISE1": [174, 297, 27, 46], "RISE2": [205, 297, 27, 46], "RISE3": [239, 297, 27, 46],
    **{f"MELT{k + 1}": list(r) for k, r in enumerate([(273, 305, 27, 38), (308, 313, 30, 30), (347, 319, 30, 24),
                                                      (385, 327, 30, 16), (419, 330, 24, 13), (451, 330, 22, 13),
                                                      (485, 330, 14, 13)])},
    # Alternative
    "FLOAT_ALT": [18, 386, 31, 46],
    "HEAD1": [65, 382, 24, 21], "HEAD2": [90, 382, 25, 21], "HEAD3": [65, 408, 22, 21], "HEAD4": [90, 407, 25, 21],
    "UP": [156, 390, 27, 40], "DOWN": [188, 388, 24, 42], "FLOAT_UP": [218, 386, 27, 44], "FLOAT_DOWN": [252, 384, 24, 46],
    "WHITE1": [469, 393, 29, 40], "WHITE2": [504, 391, 29, 42], "CRYSTAL": [539, 391, 30, 42],
}


def f(*names):
    return [B[n] for n in names]


def run(prefix, first, last):
    return f(*[f"{prefix}_{k}" for k in range(first, last + 1)])


C = lambda frames: {"frames": frames, "anchor": "center"}


def _trim(rect):
    """The sheet bbox (x, y, w, h) of a rect's non-background pixels."""
    x, y, w, h = rect
    bg = tuple(int(BACKGROUND[0][i:i + 2], 16) for i in (1, 3, 5))
    crop = SRC.crop((x, y, x + w, y + h))
    pts = [(i, j) for j in range(h) for i in range(w) if crop.getpixel((i, j)) != bg]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return x + min(xs), y + min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


def _head_shift(name, ref, rows=14, reach=8):
    """(dx, dy) that best lays `ref`'s head (its top rows, exact colours) over `name`'s, in sheet px between their
    trimmed boxes: where the head sits in `name` relative to `ref`."""
    rx, ry, rw, _ = _trim(B[ref])
    nx, ny, _, _ = _trim(B[name])
    bg = tuple(int(BACKGROUND[0][i:i + 2], 16) for i in (1, 3, 5))
    head = [(i, j, SRC.getpixel((rx + i, ry + j))) for j in range(rows) for i in range(rw)
            if SRC.getpixel((rx + i, ry + j)) != bg]
    fx, fy, fw, fh = B[name]
    def score(dx, dy):
        n = 0
        for i, j, c in head:
            X, Y = nx + i + dx, ny + j + dy
            if fx <= X < fx + fw and fy <= Y < fy + fh and SRC.getpixel((X, Y)) == c:
                n += 1
        return n
    return max(((dx, dy) for dy in range(-reach, reach + 1) for dx in range(-reach, reach + 1)),
               key=lambda d: (score(*d), -abs(d[0]) - abs(d[1])))


def pinned(names, ref, feet=True):
    """Frames positioned by his head (and so his torso) instead of their bounding boxes, which an outstretched arm,
    the crystal or the sparkles widen: the reference frame's own box, moved with the head (sheet2ani anchor_box).
    feet: the bottom still each frame's own (feet on the ground line); otherwise (floating, centred) the box moves
    down with the head too, so only the drawn motion shows."""
    rx, ry, rw, rh = _trim(B[ref])
    out = []
    for n in names:
        dx, dy = _head_shift(n, ref)
        nx, ny, nw, nh = _trim(B[n])
        box = [nx + dx, ny, rw, nh] if feet else [nx + dx, ny + dy, rw, rh]
        out.append({"rect": B[n], "anchor_box": box})
    return out


IDLE = run("G1", 1, 4)
# floating idle: the short float. The sheet's Floating row holds two versions of his idle: F1_0-F1_3 (arms spread:
# spread, palm out, hand to face, head turned) and F1_4-F1_7 (arms in: chest, hand to face, head turned, palm out,
# the floating twin of the ground idle G1_1-G1_4). One cycle only, F1_4-F1_7, pinned on his head (their boxes differ
# by the arm, so centring them jumped the body 2 px)
FLOAT = pinned([f"F1_{k}" for k in range(4, 8)], "F1_4", feet=False)
FLY = f("F1_11")  # flying flat
# The rework (the user, 2026-09-29): he floats everywhere. His floating idle's arms-in cycle (F1_4-F1_7, the floating twin
# of the ground idle) is his stand, walk, run and top speed, feet (the wisp's tip) on the ground line, pinned on his head
# as FLOAT is. The walk / run lean forward with his speed at runtime (abilities.py float_lean), not in the art
# (the user, 2026-09-29: cycling F1_4-F1_7 had him "waving his arms around like an unbalanced individual": one calm
# pose, arms folded at his chest; the speed lean gives it the motion)
FLOAT_FEET = pinned(["F1_4"], "F1_4")
# the arms-spread floating idle (F1_0-F1_3) and the floating crystal toss (F2_7-F2_12), pinned on the same head
FLOAT_IDLE = pinned([f"F1_{k}" for k in range(0, 4)], "F1_4")
FLOAT_TOSS = pinned([f"F2_{k}" for k in range(7, 13)], "F1_4")
# Shadow Sink (abilities.py sink, down + Y): the sheet's own sinking row as drawn, in order: RISE1-RISE3 (the dark pool
# opening under him) then MELT1-MELT7 (sinking into it, down to the last purple specks). Frames 0-9 of slot 47; the
# code shows them forward to sink, 8 / 9 (the smoke specks) while he's under, and backward to rise
SINK = f("RISE1", "RISE2", "RISE3", *[f"MELT{k}" for k in range(1, 8)])
MELT = f(*[f"MELT{k}" for k in range(1, 8)])
THROW = f("F2_1", "F2_3")  # hand drawn back, then the palm thrust out (the crystal leaves it): floating, as he stands now
THROW_AIR = f("F2_1", "F2_3")
CRYSTAL_TOSS = run("G2", 7, 12)  # the red crystal: held, turned, tossed, caught (ending / idle flavour)
# the standing sequences pinned on his head (the palm out and the crystal widen the boxes: centred, he slid 2-8 px)
IDLE_PINNED = pinned([f"G1_{k}" for k in range(1, 5)], "G1_1")
TOSS_PINNED = pinned([f"G2_{k}" for k in range(7, 13)], "G1_1")

ANIMS = {
    # floating (the rework): the arms-in cycle, slowly (also the Origins select card and the S3&K save screen picture:
    # frame 0, F1_4)
    "Stopped": {"frames": FLOAT_FEET, "speed": 24},
    "Waiting": {"frames": FLOAT_IDLE + FLOAT_TOSS, "loop": 4},  # arms spread, then toying with the crystal, floating
    "Looking Up": {"frames": f("FLOAT_UP")},
    "Looking Down": {"frames": f("FLOAT_DOWN")},
    # the walk, run and top speed: the same float, full rotation ("rot" 1) so the runtime lean shows (abilities.py
    # float_lean: no slope rotation, only the lean). "hold" 2: each frame twice, so the script's walk speed doesn't whirl
    # his arms (Sonic 1/2; CD drops it)
    "Walking": {"frames": FLOAT_FEET, "rot": 1, "hold": 2},
    "Running": {"frames": FLOAT_FEET, "rot": 1, "hold": 2},
    "Skidding": {"frames": f("F1_8")},  # head bowed, pulling up
    "Super Peel Out": {"frames": FLOAT_FEET, "rot": 1, "hold": 2},
    "Bouncing": C(f("F1_9")),  # arms spread
    "Hurt": C(f("REEL")),
    "Dying": C(f("KNOCKED")),
    "Drowning": C(f("KNOCKED")),
    "Fan Rotate": C(FLOAT),
    "Breathing": C(f("F1_9")),
    "Pushing": {"frames": f("F2_2", "F2_3"), "align": True},  # palm out, floating
    "Flailing 1": {"frames": FLOAT_FEET},  # at a ledge he just floats (the user, 2026-09-29: the teeter looked weird)
    "Flailing 2": {"frames": FLOAT_FEET},  # at a ledge he just floats (the user, 2026-09-29: the teeter looked weird)
    "Hanging": C(f("F1_9")),
    "Clinging On": C(f("F1_9")),
    "Corkscrew H": {"frames": FLOAT},
    "Water Slide": C(FLY),
    "Continue": {"frames": IDLE_PINNED},
    "Continue Up": {"frames": f("F1_9")},
    # rising out of the dark pool, then the flash of his crystal form (not the Shadow form: too many colours)
    "Super Transform": {"frames": f("RISE1", "RISE2", "RISE3", "WHITE1", "WHITE2", "CRYSTAL"), "loop": 5},
}
S2_ONLY = {
    "Bored!": {"frames": FLOAT_TOSS, "loop": 0},
    "Flailing 3": {"frames": FLOAT_FEET},  # at a ledge he just floats (the user, 2026-09-29: the teeter looked weird)
    "Grabbed": C(f("RECOIL", "REEL")),
    "Twirl H": {"frames": FLOAT, "rot": 2},
}
CD_ONLY = {name: {"frames": FLY} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    # the short float (CD 47): his full-speed run's frame (Running: F1_11, flying flat; the user's pick 2026-09-29, the
    # floating idle looked awkward there). One frame, so its speed shows nothing
    "42": {"name": "Float", "frames": FLY, "anchor": "center", "speed": 60},
    "43": {"name": "Crystal Shot", "frames": THROW, "speed": 0},  # the code picks the frame (CD 46)
    "44": {"name": "Crystal Shot Air", "frames": THROW_AIR, "anchor": "center", "speed": 0},
    # Shadow Sink (abilities.py sink; CD 48, S3&K extra 5): the code picks the frame. In S3&K in the standing boxes, so
    # the game keeps him on the same ground line
    "47": {"name": "Shadow Sink", "frames": SINK, "speed": 0, "s3k_boxes": "idle"},
}

# The projectile's art (for abilities.py "shot": {"art": {...}}), loose drawings on the sheet, each in a 15x15 box centred
# on it (background only round it). The SFX section's DARK ORB: a violet crystal orb with a white-pink core, 4 colours
# (#400040, #800080, #e000e0, #e080e0), 9-15 px. Recommended: the upright three turning (narrow, round, round) and back,
# which reads the same moving down and then up (no direction to it). Other candidates, not used:
#   ORB4-ORB6 [17,523,15,9] [36,522,13,11] [53,522,11,11]: the same orb lying flat (a sideways spin)
#   dark crystal SPIKES [192,513,8,16] [208,505,15,24] [229,505,16,24] [253,513,15,16] [276,517,16,12]: his '06 shadow
#     crystals, but drawn growing out of the ground (pointing up, flat bottoms): they read badly flying down and up
#   the red crystal (Chaos Emerald) he tosses in G2_10-G2_12 [463,108,7,7] [510,113,8,9]: red, not dark, and tiny
#   the violet bubbles [76,518,12,14] [92,513,12,19] [109,513,12,19] (and their dithered ghosts 133-178): an orb
#     with a spark on top, a charging bubble; the streaks [316,471,47,16] [475,459,94,32]: horizontal, too long
SHOT_DRAWINGS = [[18, 503, 15, 15], [32, 503, 15, 15], [47, 503, 15, 15], [32, 503, 15, 15]]  # ORB1, ORB2, ORB3, ORB2
SHOT_ALT = [[17, 520, 15, 15], [35, 520, 15, 15], [51, 520, 15, 15]]  # ORB4-ORB6, the flat set
SHOT_ART = {"sheet": "../Mephiles.png", "background": BACKGROUND, "drawings": SHOT_DRAWINGS, "ticks": 4,
            "hitbox": [-8, -8, 8, 8]}  # (Sonic 1/2: 4 frames fit shots_v4.FRAMES)


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
HEAD = B["HEAD2"]  # 25x21, the front view: quills, both green eyes, the red mouth
ELEMENTS = {
    "life_icon": {"rect": [HEAD[0] + 5, HEAD[1] + 5, 16, 16], "trim": False},  # its middle: eyes and mouth
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("MEPHILES")},
    "monitor_1up": {"rect": [HEAD[0] + 5, HEAD[1] + 6, 16, 14], "trim": False},
    # no signpost art: HEAD2 on the game's own board (Items2), enlarged 1.1x nearest-neighbour to fill its face area
    # (the user's signpost exception; tools/sign_face.py)
    "sign_face": board_face(HEAD, 1.1),
    "mini_1": {"rect": B["HEAD1"], "remap": PLUS_128},  # continue icons: two of the sheet's loose heads
    "mini_2": {"rect": B["HEAD2"], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B["G1_0"], "remap": PLUS_128},
    "end_pose_1": {"rect": B["G2_4"], "remap": PLUS_128},  # pointing
    "end_pose_2": {"rect": B["F1_9"], "remap": PLUS_128},  # floating, arms spread
    "end_pose_3": {"rect": B["G2_11"], "remap": PLUS_128},  # the crystal tossed up (no big pose on the sheet)
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128}
       for n, k in enumerate(("G2_7", "G2_8", "G2_9", "G2_10", "G2_11", "G2_12"), 1)},  # the crystal toss
}

# black is Sonic's own slot 1; the other 21 keep their exact values in slots 74-94
PALETTE = {
    "74": "#202040", "75": "#2040c0", "76": "#4080e0", "77": "#80c0e0", "78": "#c0e0e0", "79": "#e0e0e0",  # body
    "80": "#404060", "81": "#4060a0", "82": "#424142", "83": "#0b060e",  # dark greys / blues, near-black
    "84": "#600020", "85": "#840000", "86": "#c00020", "87": "#e04060",  # eyes' reds and the red crystal
    "88": "#00a000", "89": "#00e020",  # his green pupils
    "90": "#400040", "91": "#800080", "92": "#e000e0", "93": "#e080e0",  # the dark pool and the orb
    "94": "#212084",  # 3 px of the flying frame F1_11 (#424142, 82: 4 px there, F1_10 and HEAD1)
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}
MERGED = set()  # nothing merged (the sheet's other colours, unused, go to their nearest slot: all_colours)

# the generic ball DARK with blue highlights, like his dark crystal look (the user, 2026-09-29: the all-blue one was too
# blue): his near-black body shade, his dark navy, then his blue and cyan accents as the highlight and shine; the
# outline Sonic's black (slot 1), a step darker than the near-black body. All his own colours: no new slots
BALL_COLOURS = generic_ball.colours(outline="#000000", dark="#0b060e", mid="#202040", light="#2040c0",
                                    shine="#80c0e0")


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet in the slot of its nearest key colour (MERGED among them)."""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


def used_rects():
    return (list(B.values()) + [el["rect"] for el in ELEMENTS.values() if "rect" in el and "base" not in el]
            + [ELEMENTS["sign_face"]["rect"]] + SHOT_DRAWINGS)


def check_colours():
    """Every colour in a built frame, UI element or the shot has a slot of its own, but the MERGED ones."""
    used = set()
    for x, y, w, h in used_rects():
        used |= {"#%02x%02x%02x" % rgb for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    used |= set(BALL_COLOURS.values())
    missing = used - set(KEY_COLOURS) - set(BACKGROUND) - MERGED
    if missing:
        sys.exit(f"mephiles: frame colours without a slot of their own: {sorted(missing)}")


CREDIT = ("Mephiles the Dark sprites by Gardow (sheet credits: Gardow, Xeric, Fox Omega, Charity, Domenico). "
          "Mephiles (c) SEGA - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/18326/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): pointing, then tossing the crystal (the good ending), looping
S3K_VICTORY = {"frames": pinned(["G2_4", "G2_9", "G2_10", "G2_11", "G2_12"], "G1_1"), "pose": 1}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    source = HERE / "build" / f"source_{game}.png"
    ball = generic_ball.source_with_ball(HERE / SHEET, BALL_COLOURS, BACKGROUND[0], source)
    cfg = {"name": NAME, "credit": CREDIT,
           "source": f"build/source_{game}.png", "feet_y": 20, "background": BACKGROUND, "palette": PALETTE,
           "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": f"{NAME}SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {}}}]  # (the ball: generic_ball.apply)
        cfg["ui"] = [{"name": f"{NAME}_UI", "manifest": f"{NAME}_ui.json", "elements": ELEMENTS,
                      "out": f"build/{NAME}_UI.gif"},
                     {"name": f"{NAME}_Ending", "manifest": f"{NAME}_ending.json", "elements": ENDING,
                      "out": f"build/{NAME}_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return generic_ball.apply(cfg, ball, game)  # jump, Spin Dash, special stages, CD's and S3&K's


if __name__ == "__main__":
    for game, out in (("Sonic1", "mephiles.json"), ("Sonic2", "mephiles_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
