#!/usr/bin/env python3
"""Writes E-123 Omega's sheet2ani configs (omega.json for Sonic 1, omega_s2.json for Sonic 2; CD's and S3&K's come from
the Sonic 2 one).

E-123 Omega, extra 32 (file "Extra32", build ID 38), base character Sonic. Public (credit in mods/NoSwap/README.md).
Sheet: testmods/Omega.png (530x8662), Sonic Battle style, custom sprited by Gussprint (see SOURCE.txt). Its terms,
printed on the sheet: "Give credit to Gussprint, and do not, I repeat, DO NOT steal and/or claim as own."

The sheet: a white page (#ffffff, the background), rows labelled in red. Every move is drawn twice, a "Right Ver." row
and a "Left Ver." row (mirror images); only the right-facing rows are used. Rows used (y, sheet coordinates):
     4  IDLE - Right Ver. (6 frames: I1-I6)
   109  TURNING (5: T1-T5, a turn through the front)
   162  RUN START / RUN - Right Ver. (RS, then R1-R9)
   796  BRAKING - Right Ver. (B1-B6)
  1013  JUMPING/MIDAIR FALL - Right Ver. (J1-J9, and J10-J11 in the next row at 1073: rising, arms up, then the fall
        with his legs dangling)
  1131  LANDING - Right Ver. (L1-L6)
  1366  MIDAIR ACTION SFX (his jets' flames: F1 / F2, the two vertical ones, are used for the hover)
  3798  SHOT ATTACK "FLAME SHOT" - Right Ver. (S0 the arm, S1-S5 the gun coming out, S6-S8 firing, recoiling)
  4111  AIR SHOT ATTACK "AIR FLAME SHOT" - Right Ver. (A1-A7; A7 the gun level)
  3757  AIM ATTACK SFX (the first frame, a small flame burst: the small flame, abilities.py 38 "shot")
  4473  SHOT ATTACK SFX (the flame shot's fireball, then its explosion: FB3 / FB4, the two compact fireballs of its first
        row, are the charged Flame Blast: abilities.py 38 "shot2")
  6445  HURT - Right Ver. (H1-H5)
  6548  KNOCKED BACKWARDS - Right Ver. (K1-K10, a tumble)
  6813  KNOCKED UPWARDS - Right Ver. (U1-U5)
  7929  the small head beside the "E-123 OMEGA" logo (the HUD icon)
  7993  EXTRA POSES MISC (CHEER: arms raised; FRONT: facing us)
Not used: the dash, the dash attack, the attack combos, guard / heal, the other attacks and their effects, the knock
downs, the story art, the overworld sprites and the credits.

Size: he stands 45 px tall (IDLE), about Big's size (Sonic is about 40). Not scaled.

Frames are whole drawings: build/source.png is a working copy holding each used frame's pixels (the blobs of the
sheet inside its box, copied exactly) in a cell of its own, so a rect crop never catches a neighbour. The hover's jet
flames are the sheet's own flame drawings (F1 / F2) placed under his feet (layered, as Tails Doll's tails are).

Abilities (tools/abilities.py 38; wired there, in build_soniccd.py and the DLL):
  - Y: Flame Shot, real projectiles (abilities.py "shot" / "shot2", motion "straight"): tap Y, a small flame (the
    AIM ATTACK SFX's first frame, a 20x20 burst); hold Y to charge (a red-orange flash, CHARGE_PALETTES) and let go for the big fireball,
    which pierces. Slots 43 / 44 (CD 46) are only the pose: the gun out, then firing (S6), or the air pose (A7).
  - Jump ability: Jet Hover (Gamma's hover, abilities.py "umbrella" with float_frames): slot 42, the fall pose with his
    jets burning under his feet.
  - Heavy physics, breaks walls, never drowns.
  - He never curls into a ball (extras.py "no_roll", as Gamma): his jump is the fall pose (J10); no Spin Dash.

Colours: his frames use 15 colours (the sheet's in-game palette), each exact in its own slot; the fireball's own colours
take 7 more slots (exact); the few left (the fireball's rare shades, the jet flames' four) go to their nearest slot
(the faithful-art rule's colour exception: MERGED, printed with pixel counts).
The "OMEGA" HUD tag isn't on the sheet (the sheet's logo is too big): our lettering in the HUD font the other extras use.
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

SHEET = HERE.parent / "Omega.png"
SOURCE = "build/source.png"  # working copy: each used frame's blobs in a cell of its own (source_sheet)
BACKGROUND = ["#ffffff"]
BG = (255, 255, 255)
SRC = Image.open(SHEET).convert("RGB")

# ---------------------------------------------------------------- frames (right-facing rows): name -> [x, y, w, h]
B = {
    **{f"I{k + 1}": r for k, r in enumerate([[3, 4, 56, 45], [65, 5, 57, 44], [126, 6, 59, 43], [187, 6, 61, 43],
                                             [251, 5, 60, 44], [317, 4, 57, 45]])},
    **{f"T{k + 1}": r for k, r in enumerate([[5, 110, 56, 45], [67, 110, 57, 45], [129, 109, 61, 46], [195, 110, 57, 45],
                                             [259, 110, 56, 45]])},
    "RS": [8, 162, 47, 45],
    **{f"R{k + 1}": r for k, r in enumerate([[60, 163, 31, 44], [97, 163, 31, 44], [132, 162, 34, 45], [170, 162, 38, 45],
                                             [213, 164, 34, 43], [253, 163, 31, 44], [289, 162, 30, 45],
                                             [322, 162, 33, 45], [360, 164, 30, 43]])},
    **{f"B{k + 1}": r for k, r in enumerate([[9, 796, 35, 48], [51, 797, 38, 47], [94, 797, 42, 47], [139, 797, 44, 47],
                                             [188, 798, 48, 46], [242, 799, 53, 46]])},
    **{f"J{k + 1}": r for k, r in enumerate([[6, 1016, 55, 49], [66, 1016, 56, 48], [126, 1015, 53, 50],
                                             [183, 1014, 52, 50], [240, 1013, 49, 50], [294, 1013, 51, 50],
                                             [350, 1013, 51, 52], [404, 1013, 55, 52], [463, 1013, 54, 52],
                                             [6, 1073, 51, 53], [61, 1073, 52, 52]])},
    **{f"L{k + 1}": r for k, r in enumerate([[6, 1131, 52, 50], [61, 1132, 52, 48], [117, 1132, 52, 45],
                                             [173, 1133, 52, 44], [228, 1133, 52, 44], [284, 1132, 52, 45]])},
    "F1": [11, 1368, 10, 13], "F2": [41, 1368, 10, 12],  # MIDAIR ACTION SFX: the jets' vertical flames
    **{f"S{k}": r for k, r in enumerate([[7, 3799, 52, 43], [62, 3800, 51, 42], [116, 3800, 49, 42], [168, 3800, 52, 42],
                                         [223, 3800, 54, 42], [280, 3800, 56, 42], [339, 3798, 49, 44],
                                         [391, 3798, 49, 44], [443, 3798, 49, 44]])},
    **{f"A{k + 1}": r for k, r in enumerate([[4, 4111, 51, 49], [58, 4111, 52, 52], [113, 4111, 53, 51],
                                             [169, 4111, 57, 50], [229, 4111, 59, 51], [291, 4111, 60, 50],
                                             [354, 4111, 58, 47]])},
    **{f"H{k + 1}": r for k, r in enumerate([[7, 6445, 59, 45], [69, 6445, 60, 45], [132, 6446, 58, 44],
                                             [193, 6446, 57, 44], [253, 6445, 56, 45]])},
    **{f"K{k + 1}": r for k, r in enumerate([[7, 6558, 37, 44], [47, 6555, 48, 46], [98, 6548, 50, 59],
                                             [152, 6560, 63, 36], [219, 6553, 59, 50], [283, 6544, 36, 63],
                                             [322, 6547, 50, 59], [376, 6561, 63, 36], [443, 6558, 59, 50],
                                             [7, 6611, 36, 63]])},
    **{f"U{k + 1}": r for k, r in enumerate([[7, 6817, 33, 49], [43, 6817, 34, 49], [80, 6815, 43, 51],
                                             [126, 6814, 51, 52], [180, 6813, 51, 53]])},
    "CHEER": [217, 7993, 44, 51], "FRONT": [324, 8054, 40, 45],
    "HEAD": [489, 7929, 17, 15],  # the small head by the logo
}
FIREBALLS = [[151, 4482, 64, 45], [232, 4482, 64, 46]]  # the Flame Blast's art (abilities.py 38 "shot2"; FB3, FB4's ball)
# the small flame's art (abilities.py 38 "shot": AIM ATTACK SFX's first frame, the small flame burst, 20x20, whole)
PUFFS = [[13, 3764, 20, 20]]

# The Flame Blast's charge flash (abilities.py 38 "shot2", a runtime palette effect: the art files keep his own): his
# metal greys (75-77) and pink highlight (82) glow in his own reds, oranges and the flame's yellows; black, white, his
# reds, oranges and greens (which the flames share) stay. charge1: a dim red glow; charge2a / charge2b: full, orange
# then white-hot
CHARGE_PALETTES = {
    "charge1": {"75": "#700000", "76": "#a81000", "77": "#f86868", "82": "#f8a018"},
    "charge2a": {"75": "#a81000", "76": "#f82000", "77": "#f8a018", "82": "#f8d500"},
    "charge2b": {"75": "#e07820", "76": "#f8b820", "77": "#f8f898", "82": "#f8f8f8"},
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
        raise SystemExit(f"omega: {rect} isn't the tight box of whole drawings")
    return [(x + a, y + b) for a, b in zip(xs, ys)]


def source_sheet():
    """Each frame's pixels, copied exactly, in a cell of its own (shelves 256 wide). Returns {name: rect in the copy}."""
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


def hover(flame_a, flame_b):
    """The fall pose (J10, legs dangling) with a jet flame under each foot: the sheet's own flame drawings, their top
    rows at the soles. J10's soles (px from its box's top left): the back foot 13-20 wide, bottom 53; the front foot
    (bent forward) 29-36 wide, bottom 47."""
    return {"layers": [{"rect": R["J10"], "at": [0, 0]},
                       {"rect": R[flame_a], "at": [12, 53]}, {"rect": R[flame_b], "at": [28, 47]}],
            "anchor_layer": 0}


# ---------------------------------------------------------------- animations
IDLE = f("I1", "I2", "I3", "I4", "I5", "I6")
TURN = f("T1", "T2", "T3", "T4", "T5")
RUN = f(*[f"R{k}" for k in range(1, 10)])
JUMP = f("J10")  # no ball: the fall pose, legs dangling (as Gamma's)
FLAIL = f("U1", "U2")
KNOCK = f(*[f"K{k}" for k in range(1, 11)])

ANIMS = {
    "Stopped": {"frames": f("I1")},  # (also the S3&K save screen picture; the Origins card is extras.py "card")
    "Waiting": {"frames": IDLE, "loop": 0, "align": True},
    "Looking Up": {"frames": f("FRONT")},  # no look-up art: facing us
    "Looking Down": {"frames": f("L3")},  # the landing crouch
    "Walking": {"frames": RUN, "rot": 2, "align": True},  # no walk: the run
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("B1", "B2"), "align": True},  # braking, sparks at his feet
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Spin Dash": {"frames": f("L3")},  # PLACEHOLDER: he never curls up (no Spin Dash)
    "Jumping": C(JUMP),
    "Bouncing": C(f("J3")),  # springs: rising, arms up
    "Hurt": C(f("H1")),
    "Dying": C(KNOCK),  # the tumble
    "Drowning": C(f("H3")),  # (he never drowns: no_breathing)
    "Fan Rotate": C(TURN),
    "Breathing": C(f("J3")),
    "Pushing": {"frames": f("RS")},  # leaning in (the run's start)
    "Flailing 1": {"frames": FLAIL, "align": True},
    "Flailing 2": {"frames": FLAIL, "align": True},
    "Hanging": C(f("J3")),
    "Clinging On": C(f("J3")),
    "Corkscrew H": {"frames": TURN},
    "Water Slide": C(f("K4")),  # knocked flat
    "Continue": {"frames": IDLE, "align": True},
    "Continue Up": {"frames": f("CHEER")},
    "Super Transform": {"frames": f("CHEER")},
}
S2_ONLY = {
    "Bored!": {"frames": f("CHEER", "I1"), "loop": 0},
    "Flailing 3": {"frames": FLAIL, "align": True},
    "Grabbed": C(f("H1", "H2")),
    "Twirl H": {"frames": TURN, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# The Flame Shot's pose (slots 43 / 44: the shot shows their last frame; abilities.py 38's melee_reach has as many
# entries): the gun out (S3), then firing (S6), level ahead; in the air the gun out (A6), then level (A7)
APPENDED = {
    "42": {"name": "Jet Hover", "frames": [hover("F1", "F2"), hover("F2", "F1")], "anchor": "center", "speed": 60},
    "43": {"name": "Flame Shot", "frames": f("S3", "S6"), "speed": 0},
    "44": {"name": "Flame Shot Air", "frames": f("A6", "A7"), "anchor": "center", "speed": 0},
}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
I1 = R["I1"]
# the HUD head: 16x16 of the 17x15 head (its leftmost outline column left out, a blank row above it)
HEAD = [R["HEAD"][0] + 1, R["HEAD"][1] - 1, 16, 16]
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("OMEGA")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1] + 1, 16, 14], "trim": False},
    # his head and chest (the top 24 rows of the standing frame, its middle 40 columns) on the game's own board, as
    # Gamma's and Big's: they fill the 40x24 face area at 1x
    "sign_face": board_face([I1[0] + 8, I1[1], 40, 24]),
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the HUD head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": R["FRONT"], "remap": PLUS_128},  # (his idle, 56 wide, is wider than the shared 46 px box)
    "end_pose_1": {"rect": R["CHEER"], "remap": PLUS_128},  # arms raised
    "end_pose_2": {"rect": R["FRONT"], "remap": PLUS_128},  # facing us
    "end_pose_3": {"rect": R["S6"], "remap": PLUS_128},  # the Flame Shot
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("FRONT", "CHEER", "FRONT", "J3", "L3", "I1"), 1)},
}

# ---------------------------------------------------------------- colours
# His frames: the sheet's 15-colour in-game palette, each exact (74-88). The fireball (FIREBALLS): 16 colours, 5 of them
# his; 7 more get slots of their own (89-95), exact; its rarest (under 60 px each) go to their nearest slot (MERGED).
PALETTE = {
    "74": "#181818", "75": "#363636", "76": "#656565", "77": "#a8a8a8", "78": "#f8f8f8",  # black to white (metal)
    "79": "#700000", "80": "#a81000", "81": "#f82000", "82": "#f86868",  # his reds
    "83": "#a04810", "84": "#e07820", "85": "#f8b820",  # his oranges (the head, the ring on his arms)
    "86": "#106020", "87": "#00a010", "88": "#70f800",  # his greens (the lights)
    "89": "#f83800", "90": "#d01800", "91": "#f8a018", "92": "#f8d500", "93": "#f8f800", "94": "#f8f898",  # the fireball
    "95": "#8c0800",
}
KEY_COLOURS = {"#000000": 1, "#fcfc00": 15, **{c: int(s) for s, c in PALETTE.items()}}


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def all_colours():
    """KEY_COLOURS, plus every other colour of the sheet in the slot of its nearest own colour. MERGED: those that the
    built art uses (the working copy, the fireballs, the head), with pixel counts."""
    keys = {hexrgb(c): int(s) for s, c in PALETTE.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            out[c] = keys[min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))]
    used = {}
    ims = [Image.open(HERE / SOURCE).convert("RGB")]
    ims += [SRC.crop((x, y, x + w, y + h)) for x, y, w, h in FIREBALLS + PUFFS]
    for im in ims:
        for n, rgb in im.getcolors(1 << 16):
            used["#%02x%02x%02x" % rgb] = used.get("#%02x%02x%02x" % rgb, 0) + n
    merged = {c: (out[c], n) for c, n in used.items()
              if c not in BACKGROUND and c not in PALETTE.values() and c != "#000000"}
    return out, merged


COLOURS, MERGED = all_colours()
CREDIT = ("E-123 Omega (Sonic Battle style) sprites custom sprited by Gussprint - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/18261/ "
          "(E-123 Omega (c) SEGA / Sonic Team)")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): EXTRA POSES MISC: facing us, then CHEER, arms raised
S3K_VICTORY = {"frames": f("FRONT", "CHEER")}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra32", "credit": CREDIT,
           "source": SOURCE, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "charge_palettes": CHARGE_PALETTES,  # (read by abilities.py: the Flame Blast's charge flash)
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        # no ball: the special stage turns his jump pose (as Gamma's)
        cfg["extra_anis"] = [{"name": "Extra32SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(JUMP)}}]
        cfg["ui"] = [{"name": "Extra32_UI", "manifest": "Extra32_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra32_UI.gif"},
                     {"name": "Extra32_Ending", "manifest": "Extra32_ending.json", "elements": ENDING,
                      "out": "build/Extra32_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "omega.json"), ("Sonic2", "omega_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("merged colours (colour: slot, pixels):",
          ", ".join(f"{c}: {s} x{n}" for c, (s, n) in sorted(MERGED.items(), key=lambda kv: -kv[1][1])))
