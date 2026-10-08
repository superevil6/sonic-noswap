#!/usr/bin/env python3
"""Writes Sally Acorn's sheet2ani configs (sally.json for Sonic 1, sally_s2.json for Sonic 2; CD's and S3&K's come from
the Sonic 2 one).

Sally Acorn, extra 33 (file "Extra33", build ID 39), base character Sonic. Public (credit in mods/NoSwap/README.md).
Sheet: testmods/Sally.png (854x2540), Genesis style, by E-122-Psi (see SOURCE.txt). Its terms, printed on the sheet:
"Sprites made by E-122-Psi. Permission not needed but please don't steal credit."

The sheet: a mint page (#60e0c0, the background), nothing labelled. Sprites face right. Its blocks and rows (y, sheet
coordinates; T = the top block, B = the second one, K = the kick rows; the names are the ones used below):
  T  25  standing (T1), idle: looking round, tapping her foot, Nicole (T2-T7); a walk (not used: B's is longer); the
         run, her legs a blur (TR1-TR4)
  T  77  curling up (TC1-TC3, her limbs showing) and her ball (TBALL); kicks and a step (not used)
  T 128  looking up at something (not used), crouching (TCROUCH), a spring leap, arms up (TSPRING), leaning back
         (TSKID), leaning in, arms out (not used), knocked back, feet up (THURT1-2); crawling / lying (not used)
  T 177  sliding on her front (TSLIDE), looking up (TUP), pushing (TPUSH1-4), arms flung up (TDIE), the same greyed
         (TDROWN), a bubble breath (TBREATH), wobbling on a ledge (TBAL1-2), sitting on the ground with Nicole (TBORED1-3)
  T 255  front-on poses, a grown-up portrait (not used)
  B 402  the walk (BW1-BW8), the Spin Dash (BSD1-BSD6: the egg-shaped dash ball)
  B 453  high-stepping runs (BR1-BR8) and a flying dash, arm out (BD1-BD4) (not used: the top block's run reads better)
  B 503  turning away (not used), a forward tumble (BT1-BT9), sitting (not used)
  B 552  more poses (not used); the special stage from behind (611: not used); her HUD art at the right: the continue
         icons (700, 534), the signpost board (751, 521), the life icon (743, 588), the "SALLY" name tags (760, 579 / 589)
  1553-1768  Nicole, pointing, crawl, walk variants (not used)
  K 1559 a flying kick, the leg out diagonally down (KFLY: the Flying Kick Dive)
  K 1832 a standing spin kick with the blue swirl (not used)
  K 1897 the somersault spin kick with the blue swirl: crouched wind-up (KWIND), the leap (not used), the flip with the
         swirl (KS1-KS5: the Spin-Kick High Jump), coming upright (KREC: its recovery), landing (not used)
  K 1958 a spinning kick with a horizontal swirl ring (not used)
  Below that: more poses, portraits, the palette swatches and the credit (not used).

Size: she stands 42 px tall (T1); Sonic is about 40. Not scaled. The top block and B are the same drawing size.

Frames are whole drawings: build/source.png is a working copy holding each used frame's pixels (the blobs inside its box,
copied exactly) in a cell of its own, so a rect crop never catches a neighbour.

Abilities (tools/abilities.py 39; wired there, in build_soniccd.py and the DLL):
  - Y: Spin-Kick High Jump (abilities.py high_kick, new): a wind-up (slot 42 frame 0: KWIND, not an attack), then she
    flips straight up in the swirl (slot 43: KS1-KS5, an attack) higher than her jump, then comes upright (slot 42 frame
    1: KREC, not an attack) before falling as from a jump. CD: 47 / 46.
  - Jump ability: Flying Kick Dive: Mecha Sonic's Spike Ball (abilities.py screw_kick with kick_jump), in KFLY (slot 41).
  - Ball: her own (TC1-TC3 between plain TBALL frames), and her own Spin Dash (BSD1-BSD6).

Nothing is redrawn, recoloured or resized. Colours: the sheet's in-game palette (15 colours) and the HUD tag's, exact in
her own slots; any other (a stray pixel) goes to its nearest slot (MERGED, printed with pixel counts).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

SHEET = HERE.parent / "Sally.png"
SOURCE = "build/source.png"  # working copy: each used frame's blobs in a cell of its own (source_sheet)
BACKGROUND = ["#60e0c0"]
BG = (0x60, 0xE0, 0xC0)
SRC = Image.open(SHEET).convert("RGB")

B = {  # name -> [x, y, w, h] on the sheet: the tight box of the drawing's blobs
    **{f"T{k + 1}": r for k, r in enumerate([[18, 25, 22, 42], [47, 27, 23, 40], [77, 28, 23, 39], [112, 26, 23, 41],
                                             [147, 26, 23, 41], [181, 25, 22, 42], [212, 25, 21, 42]])},
    "TR1": [470, 32, 35, 35], "TR2": [512, 31, 32, 37], "TR3": [549, 32, 34, 35], "TR4": [593, 31, 32, 37],
    "TC1": [48, 87, 32, 23], "TC2": [91, 82, 23, 32], "TC3": [121, 86, 32, 23], "TBALL": [162, 83, 30, 30],
    "TCROUCH": [58, 139, 30, 29], "TSPRING": [104, 128, 29, 40], "TSKID": [145, 130, 29, 38],
    "THURT1": [512, 138, 37, 30], "THURT2": [560, 138, 35, 30],
    "TSLIDE": [17, 188, 47, 25], "TUP": [141, 177, 21, 47],
    "TPUSH1": [175, 184, 30, 37], "TPUSH2": [216, 183, 24, 38], "TPUSH3": [249, 184, 29, 37], "TPUSH4": [288, 183, 25, 38],
    "TDIE": [321, 178, 32, 46], "TDROWN": [357, 178, 32, 46], "TBREATH": [392, 179, 32, 45],
    "TBAL1": [438, 178, 26, 42], "TBAL2": [472, 180, 27, 40],
    "TBORED1": [522, 183, 23, 37], "TBORED2": [559, 183, 23, 37], "TBORED3": [596, 183, 24, 37],
    **{f"BW{k + 1}": r for k, r in enumerate([[51, 402, 23, 42], [83, 402, 27, 41], [121, 403, 25, 41], [158, 403, 23, 41],
                                              [191, 402, 22, 42], [222, 402, 27, 42], [259, 403, 26, 41],
                                              [300, 403, 23, 41]])},
    **{f"BSD{k + 1}": [x, 411, w, 27] for k, (x, w) in enumerate([(335, 30), (372, 29), (406, 29), (440, 29), (475, 29),
                                                                  (510, 29)])},
    **{f"BT{k + 1}": r for k, r in enumerate([[116, 516, 23, 24], [149, 512, 23, 30], [180, 513, 25, 29],
                                              [212, 508, 27, 36], [248, 508, 26, 38], [281, 508, 24, 39],
                                              [313, 514, 28, 33], [352, 513, 26, 29], [389, 512, 23, 31]])},
    "MINI1": [700, 534, 16, 24], "MINI2": [721, 534, 16, 24], "SIGN": [751, 521, 48, 48],
    "ICON": [743, 588, 16, 16], "TAG": [760, 589, 29, 7],
    "KFLY": [436, 1559, 39, 32],
    "KWIND": [52, 1903, 25, 37],
    "KS1": [137, 1902, 43, 34], "KS2": [190, 1899, 53, 37], "KS3": [249, 1892, 45, 44], "KS4": [305, 1897, 37, 37],
    "KS5": [363, 1898, 39, 31],
    "KREC": [417, 1902, 34, 35],
    # the row at 1553: crouching (VJ1), then a jump with a fist in the air (VJ3): the S3&K act clear celebration
    "VJ1": [141, 1554, 23, 40], "VJ3": [207, 1554, 31, 44],
}

# ---------------------------------------------------------------- the working copy
LABELS, _ = ndimage.label(np.any(np.array(SRC) != BG, axis=2), structure=np.ones((3, 3)))
OBJECTS = ndimage.find_objects(LABELS)


def frame_pixels(rect):
    """The pixels of the blobs lying wholly inside the rect (a neighbour reaching into it is left out)."""
    x, y, w, h = rect
    inside = set()
    for lab in np.unique(LABELS[y:y + h, x:x + w]):
        if lab == 0:
            continue
        sl = OBJECTS[lab - 1]
        if sl[0].start >= y and sl[0].stop <= y + h and sl[1].start >= x and sl[1].stop <= x + w:
            inside.add(lab)
    ys, xs = np.nonzero(np.isin(LABELS[y:y + h, x:x + w], list(inside)))
    if not len(xs) or xs.min() != 0 or ys.min() != 0 or xs.max() != w - 1 or ys.max() != h - 1:
        raise SystemExit(f"sally: {rect} isn't the tight box of whole drawings")
    return [(x + a, y + b) for a, b in zip(xs, ys)]


def source_sheet():
    """Each frame's pixels, copied exactly, in a cell of its own (shelves 512 wide). Returns {name: rect in the copy}."""
    cells, x, y, shelf = {}, 2, 2, 0
    for name, rect in B.items():
        w, h = rect[2], rect[3]
        if x + w + 2 > 512:
            x, y, shelf = 2, y + shelf + 3, 0
        cells[name] = (frame_pixels(rect), rect, [x, y, w, h])
        x += w + 3
        shelf = max(shelf, h)
    out = Image.new("RGB", (512, y + shelf + 2), BG)
    for pts, (sx, sy, _, _), (cx, cy, _, _) in cells.values():
        for a, b in pts:
            out.putpixel((cx + a - sx, cy + b - sy), SRC.getpixel((a, b)))
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return {name: c[2] for name, c in cells.items()}


R = source_sheet()


def f(*names):
    return [R[n] for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)

# ---------------------------------------------------------------- animations
IDLE = f(*[f"T{k}" for k in range(2, 8)])
WALK = f(*[f"BW{k}" for k in range(1, 9)])
RUN = f("TR1", "TR2", "TR3", "TR4")  # the top block's run: legs a blur
BALL = f("TC1", "TBALL", "TC2", "TBALL", "TC3", "TBALL")  # her curled frames between the plain ball
SPINDASH = f(*[f"BSD{k}" for k in range(1, 7)])
TUMBLE = f(*[f"BT{k}" for k in range(1, 10)])
PUSH = f("TPUSH1", "TPUSH2", "TPUSH3", "TPUSH4")
BAL = f("TBAL1", "TBAL2")

ANIMS = {
    "Stopped": {"frames": f("T1")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": IDLE, "loop": 0, "align": True},
    "Looking Up": {"frames": f("TUP")},
    "Looking Down": {"frames": f("TCROUCH")},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("TSKID")},
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": C(BALL),
    "Bouncing": C(f("TSPRING")),
    "Hurt": C(f("THURT1")),
    "Dying": C(f("TDIE")),
    "Drowning": C(f("TDROWN")),
    "Fan Rotate": C(TUMBLE),
    "Breathing": C(f("TBREATH")),
    "Pushing": {"frames": PUSH, "align": True},
    "Flailing 1": {"frames": BAL, "align": True},
    "Flailing 2": {"frames": BAL, "align": True},
    "Hanging": C(f("TSPRING")),
    "Clinging On": C(f("TSPRING")),
    "Corkscrew H": {"frames": TUMBLE},
    "Water Slide": C(f("TSLIDE")),
    "Continue": {"frames": IDLE, "align": True},
    "Continue Up": {"frames": f("TSPRING")},
    "Super Transform": {"frames": f("TSPRING")},
}
S2_ONLY = {
    "Bored!": {"frames": f("TBORED1", "TBORED2", "TBORED3"), "loop": 0},
    "Flailing 3": {"frames": BAL, "align": True},
    "Grabbed": C(f("THURT1", "THURT2")),
    "Twirl H": {"frames": TUMBLE, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    # the Flying Kick Dive (the jump ability: abilities.py kick_jump), an attack
    "41": C(f("KFLY"), name="Flying Kick", speed=0),
    # the Spin-Kick High Jump's poses that aren't attacks (abilities.py high_kick picks the frame): the wind-up, then
    # the recovery
    "42": C(f("KWIND", "KREC"), name="Spin Kick Pose", speed=0),
    # the kick itself, an attack: the somersault in the swirl (the code steps through it)
    "43": C(f("KS1", "KS2", "KS3", "KS4", "KS5"), name="Spin Kick", speed=0),
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ICON = R["ICON"]
SIGN = R["SIGN"]
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": ICON, "trim": False},
    "life_name": {"rect": R["TAG"]},  # "SALLY" (yellow, dark shadow)
    "monitor_1up": {"rect": [ICON[0], ICON[1] + 1, 16, 14], "trim": False},
    "sign_face": {"rect": [SIGN[0], SIGN[1], 48, 32], "trim": False},  # the board, without its pole
    "mini_1": {"rect": R["MINI1"], "remap": PLUS_128},
    "mini_2": {"rect": R["MINI2"], "remap": PLUS_128},
}
ENDING = {  # no ending art: her poses stand in
    "end_idle": {"rect": R["T1"], "remap": PLUS_128},
    "end_pose_1": {"rect": R["TSPRING"], "remap": PLUS_128},  # arms up
    "end_pose_2": {"rect": R["T7"], "remap": PLUS_128},
    "end_pose_3": {"rect": R["KREC"], "remap": PLUS_128},
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("T1", "T2", "T3", "TSPRING", "T5", "T6"), 1)},
}

# ---------------------------------------------------------------- colours
# The sheet's in-game palette (its first swatch): 15 colours, each exact in her own slots; the name tag's yellows too
PALETTE = {
    "74": "#60a0e0", "75": "#2060e0", "76": "#2040a0",  # blues (vest, boots)
    "77": "#a02000", "78": "#800000", "79": "#400000",  # hair reds
    "80": "#e0e0e0", "81": "#a0a0a0", "82": "#808080",  # whites / greys
    "83": "#e0c080", "84": "#a08040",  # tan (muzzle, belly)
    "85": "#e08000", "86": "#c06000", "87": "#404020",  # orange fur, its shade, the dark outline
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def all_colours():
    """KEY_COLOURS plus the working copy's other colours: the name tag's get slots of their own (up to 95), anything
    else its nearest own slot (MERGED, with pixel counts)."""
    counts = {"#%02x%02x%02x" % rgb: n for n, rgb in Image.open(HERE / SOURCE).getcolors(1 << 16)}
    pal, keys = dict(PALETTE), dict(KEY_COLOURS)
    tag = SRC.crop((760, 589, 789, 596)).getcolors(1 << 10)
    for _, rgb in sorted(tag, reverse=True):
        c = "#%02x%02x%02x" % rgb
        if c not in keys and c not in BACKGROUND and len(pal) < 22:
            slot = str(74 + len(pal))
            pal[slot] = c
            keys[c] = int(slot)
    out = dict(keys)
    near = {hexrgb(c): int(s) for s, c in pal.items()}
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            out[c] = near[min(near, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))]
    merged = {c: (out[c], n) for c, n in counts.items() if c not in BACKGROUND and c not in keys}
    return pal, out, merged


PALETTE, COLOURS, MERGED = all_colours()
CREDIT = ("Sally Acorn (Genesis style) sprites made by E-122-Psi - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogmediacustoms/asset/156080/ "
          "(Sally Acorn (c) SEGA / Archie Comics)")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): crouching, then the jump with a fist in the air
S3K_VICTORY = {"frames": f("VJ1", "VJ3")}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra33", "credit": CREDIT,
           "source": SOURCE, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra33SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(BALL)}}]
        cfg["ui"] = [{"name": "Extra33_UI", "manifest": "Extra33_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra33_UI.gif"},
                     {"name": "Extra33_Ending", "manifest": "Extra33_ending.json", "elements": ENDING,
                      "out": "build/Extra33_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "sally.json"), ("Sonic2", "sally_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("palette:", PALETTE)
    print("merged colours (colour: slot, pixels):",
          ", ".join(f"{c}: {s} x{n}" for c, (s, n) in sorted(MERGED.items(), key=lambda kv: -kv[1][1])))
