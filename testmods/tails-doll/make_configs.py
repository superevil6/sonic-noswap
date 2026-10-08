#!/usr/bin/env python3
"""Writes Tails Doll's sheet2ani configs (tailsdoll.json for Sonic 1, tailsdoll_s2.json for Sonic 2; CD's and S3&K's
come from the Sonic 2 one: cd_animations, s3k_animations).

Tails Doll, extra 26 (file "Extra26", build ID 32), base character Sonic (the user's rework, 2026-09-28: he was built on
Tails, with Tails' flight; now his own moves), so his .ani follows Sonic's animation list. Public (credit in
mods/NoSwap/README.md). Sheet: testmods/TailsDoll.png (947x972), "Tails Doll (Sonic 1 / CD-Style)": sprite artist and
creator Nikog266; sprite corrections and edits by Danthebol, Lmeichi, Spooky and Selphy Geumja (see SOURCE.txt). Not
used: the pumpkin doodle, the big "TAILS DOLL" logo, the "MILES DOLL" tag, the P / F posts, the shield, the palette
swaps, BOREDALT and DRIP.

The sheet's sprites sit in labelled cells (53x51, 52x51 from the SPRING row down) on a dark green sheet. A cell's colour
marks what the variant is for (the sheet's legend): green S1 (and CD), pink SCD (the Super Peel-Out and its tails),
peach SCUSTOMNIK, yellow SCUSTOMDAN, purple SCUSTOMSPO (the custom sets of Nikog266, Danthebol and Spooky). All the cell
colours are background. The green cells are used wherever the sheet has them; the custom sets only for what it has
nothing else for (FLY2, FALL2, HAPPY, SIT). Every sprite faces right, except the HANG ROLL pair (they
face left: mirrored here).

His tails are separate pieces, as real Tails' are (TAIL: 4 standing frames; TAIL WALK: 3; TAIL RUN: 4; TAIL SUPER
PEEL-OUT: 4). The extras draw no tails object (the Tails Object is their shot's host), so each body frame that has none
drawn in (standing, bored, looking up, crouching, walking, running, the Peel-Out, skidding, pushing) is a layered frame:
the sheet's own tail piece behind the sheet's own body (sheet2ani cut_layered; placed by the body, so the tails don't move
him). The sheet draws each tail piece in its cell exactly where it joins a body in its own cell (its root at his lower
back), so a tail goes at the same place in the body's cell as in its own: one rule for every frame, consistent per
animation. Animations cycle the tail frames under the body frames: standing, looking up and crouching get the 4-frame
wag (one body frame, speed 30); walking pairs its 6 frames with the 3 walk tails; running and the Peel-Out repeat their 6
frames twice (12) so the 4 tails line up (for S3&K, which fits frames to its base's count, 6-frame versions). Everything
else has its tails drawn in (spring, fly, fall, hurt, death, continue, hang, spin, balance, the endings).

Size: he stands 35 px tall with his antenna (the gem at its tip), about 31 without; Sonic is about 40. Not enlarged.

Abilities (tools/abilities.py 32; the moves are wired there, in build_soniccd.py and the DLL):
  - jump ability: "Phase Warp" (abilities.py phase_warp): he flickers out and back in up to 96 px away, the flicker in the
    SPIN row turning round (slot 41, CD 45); FALL2 (a head-first drop) is S3&K's Fall and CD's Dropping.
  - Y: "Screen Nuke" (slots 43 / 44, CD 46; abilities.py melee_nuke): ENDING(SMALL)'s arms-out pose (ES6), then the
    dark CONTINUE form, his head open on the pulsing red core (CONT1-6: the sheet's most dramatic frames; the nuke goes
    off on CONT3, the core at its brightest), and back out through CONT2 to the arms-out pose.
  - ball: his own ROLL (3 frames).

Nothing is redrawn, recoloured or resized: frames are cut as drawn, mirrored (HANG ROLL, the spin's last side view), and
the tail pieces placed. Palette: black in Sonic's slot 1; 22 colours exactly in the extras' slots 74-95. Merged (the
colour exception: the sheet has more shades than the 22 slots): #080000 (a near-black, 716 px of his outlines, the tag's
shadow) into black, #902400 (3 px, in ROLL1 and HURT2) into #880000, and near-duplicate shades (1-3 levels off, only on the signpost's board and 6 px of the minis) into
their exact twins. See check_colours.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

SHEET = "../TailsDoll.png"
# the dark green sheet, its borders and the five cell colours (S1 green, SCD pink, Nik peach, Dan yellow, Spooky purple)
BACKGROUND = ["#25661a", "#0d4807", "#439931", "#f584ff", "#ffc184", "#f0e744", "#bb3afc"]
SRC = Image.open(HERE / SHEET).convert("RGB")

# frame -> (x, y, w, h: its sprite's bounding box, cell x, cell y: its cell's top left)
B = {
    "IDLE": (27, 32, 21, 35, 13, 20), "UP": (81, 30, 21, 37, 67, 20), "CROUCH": (137, 40, 20, 27, 121, 20),
    "T1": (175, 55, 22, 11, 175, 20), "T2": (229, 55, 23, 11, 229, 20), "T3": (283, 55, 23, 10, 283, 20),
    "T4": (337, 54, 22, 11, 337, 20),
    "BORED1": (27, 93, 22, 35, 13, 81), "BORED2": (81, 94, 22, 34, 67, 81), "BORED3": (135, 96, 22, 32, 121, 81),
    "BORED4": (189, 96, 22, 32, 175, 81),
    "WALK1": (28, 152, 20, 37, 13, 142), "WALK2": (77, 151, 32, 38, 67, 142), "WALK3": (132, 151, 26, 38, 121, 142),
    "WALK4": (190, 152, 23, 37, 175, 142), "WALK5": (239, 151, 36, 38, 229, 142), "WALK6": (298, 151, 27, 38, 283, 142),
    "TW1": (338, 174, 23, 11, 337, 142), "TW2": (392, 173, 23, 11, 391, 142), "TW3": (446, 173, 23, 11, 445, 142),
    "RUN1": (29, 212, 27, 38, 13, 203), "RUN2": (84, 213, 26, 37, 67, 203), "RUN3": (129, 212, 35, 39, 121, 203),
    "RUN4": (182, 213, 36, 37, 175, 203), "RUN5": (237, 212, 35, 38, 229, 203), "RUN6": (291, 213, 35, 37, 283, 203),
    "SPO1": (351, 217, 37, 31, 337, 203), "SPO2": (407, 216, 35, 34, 391, 203), "SPO3": (455, 217, 41, 32, 445, 203),
    "SPO4": (510, 216, 40, 34, 499, 203), "SPO5": (563, 217, 41, 31, 553, 203), "SPO6": (616, 216, 42, 34, 607, 203),
    "ROLL1": (25, 283, 28, 28, 13, 264), "ROLL2": (79, 283, 28, 28, 67, 264), "ROLL3": (133, 283, 28, 28, 121, 264),
    "TR1": (183, 299, 22, 13, 175, 264), "TR2": (236, 298, 23, 11, 229, 264), "TR3": (291, 297, 23, 11, 283, 264),
    "TR4": (345, 298, 22, 12, 337, 264),
    "TP1": (401, 297, 22, 13, 391, 264), "TP2": (456, 297, 23, 11, 445, 264), "TP3": (509, 297, 23, 11, 499, 264),
    "TP4": (562, 297, 22, 12, 553, 264),
    "HURT1": (21, 339, 37, 33, 13, 325), "HURT2": (73, 339, 39, 33, 67, 325), "DEATH": (127, 334, 39, 36, 121, 325),
    **{f"CONT{k + 1}": (184 + 54 * k, 347, 35, 27 if k < 3 else 26, 175 + 54 * k, 325) for k in range(6)},
    "HANG1": (14, 400, 40, 27, 13, 386), "HANG2": (67, 401, 42, 24, 66, 386),
    "SPIN1": (129, 397, 32, 24, 119, 386), "SPIN2": (176, 399, 43, 22, 173, 386), "SPIN3": (237, 398, 33, 23, 227, 386),
    "SPRING1": (27, 453, 23, 41, 13, 447), "SPRING2": (78, 451, 26, 43, 66, 447),
    "FLY1A": (130, 467, 38, 27, 119, 447), "FLY1B": (184, 467, 36, 27, 172, 447),
    "FLY2A": (239, 449, 28, 45, 225, 447), "FLY2B": (290, 448, 31, 46, 278, 447), "FLY2C": (345, 449, 29, 45, 331, 447),
    "FLY2D": (396, 448, 31, 46, 384, 447),
    "FALL1A": (446, 456, 38, 27, 437, 447), "FALL1B": (500, 457, 36, 26, 490, 447),
    "FALL2A": (559, 456, 29, 33, 543, 447), "FALL2B": (612, 455, 29, 34, 596, 447),
    "SKID1": (21, 521, 35, 34, 13, 508), "SKID2": (74, 522, 35, 33, 66, 508),
    "BAL1": (127, 518, 31, 37, 119, 508), "BAL2": (183, 518, 33, 37, 173, 508),
    "PUSH1": (28, 583, 25, 33, 13, 569), "PUSH2": (85, 582, 21, 34, 66, 569), "PUSH3": (134, 583, 25, 33, 119, 569),
    "PUSH4": (189, 582, 23, 34, 172, 569),
    "ES1": (25, 642, 34, 35, 13, 630), "ES2": (75, 642, 37, 35, 66, 630), "ES3": (128, 640, 37, 37, 119, 630),
    "ES4": (178, 642, 39, 35, 172, 630), "ES5": (231, 642, 39, 35, 225, 630), "ES6": (283, 641, 42, 37, 278, 630),
    "HAPPY": (188, 859, 22, 35, 174, 847), "SIT": (127, 923, 36, 33, 120, 908),
    # ENDING(BIG): the small and the big drawing (the big one fills its 126x124 cell)
    "EB_SMALL": (32, 730, 68, 69, 13, 691), "EB_BIG": (140, 691, 126, 124, 140, 691),
    # the two small dolls by the signpost (the continue minis)
    "MINI1": (316, 790, 16, 25, 316, 790), "MINI2": (333, 790, 16, 25, 333, 790),
}


def r(name):
    return list(B[name][:4])


def f(*names):
    return [r(n) for n in names]


def flip(name):
    return {"rect": r(name), "flip": True}


def tailed(body, tail):
    """The body frame with the sheet's tail piece behind it, where the tail's cell puts it relative to the body's cell."""
    bx, by, _, _, bcx, bcy = B[body]
    tx, ty, _, _, tcx, tcy = B[tail]
    at = [(tx - tcx) - (bx - bcx), (ty - tcy) - (by - bcy)]
    return {"layers": [{"rect": r(tail), "at": at}, {"rect": r(body), "at": [0, 0]}]}


def with_tails(bodies, tails, count=None):
    """Body frames k with tail frames k (both cycling) for `count` frames (default: the longer of the two)."""
    n = count or max(len(bodies), len(tails))
    return [tailed(bodies[k % len(bodies)], tails[k % len(tails)]) for k in range(n)]


STAND_TAILS = ["T1", "T2", "T3", "T4"]
WALK_TAILS = ["TW1", "TW2", "TW3"]
RUN_TAILS = ["TR1", "TR2", "TR3", "TR4"]
PEEL_TAILS = ["TP1", "TP2", "TP3", "TP4"]
RUN_BODY = [f"RUN{k}" for k in range(1, 7)]
PEEL_BODY = [f"SPO{k}" for k in range(1, 7)]

IDLE = with_tails(["IDLE"], STAND_TAILS)  # the 4-frame wag
BORED = with_tails([f"BORED{k}" for k in range(1, 5)], STAND_TAILS)
LOOK_UP = with_tails(["UP"], STAND_TAILS)
CROUCH = with_tails(["CROUCH"], STAND_TAILS)
WALK = with_tails([f"WALK{k}" for k in range(1, 7)], WALK_TAILS)
RUN = with_tails(RUN_BODY, RUN_TAILS, 12)
PEEL = with_tails(PEEL_BODY, PEEL_TAILS, 12)
RUN_6 = with_tails(RUN_BODY, RUN_TAILS)  # (S3&K: fitted to its base's frame count)
PEEL_6 = with_tails(PEEL_BODY, PEEL_TAILS)
SKID = with_tails(["SKID1", "SKID2"], STAND_TAILS, 2)
PUSH = with_tails([f"PUSH{k}" for k in range(1, 5)], STAND_TAILS)
BALL = f("ROLL1", "ROLL2", "ROLL3")
SPIN = f("SPIN1", "SPIN2", "SPIN3") + [flip("SPIN2")]  # front, side, back, the other side: turning round
HANG = [flip("HANG1"), flip("HANG2")]  # (drawn facing left)
FLY = f("FLY2A", "FLY2B", "FLY2C", "FLY2D")
DROP = f("FALL2A", "FALL2B")
BALANCE = f("BAL1", "BAL2")
C = lambda frames: {"frames": frames, "anchor": "center"}

ANIMS = {
    "Stopped": {"frames": IDLE, "speed": 30},  # (the first frame: also the Origins select card and S3&K's save screen)
    "Waiting": {"frames": BORED, "loop": 1},
    "Looking Up": {"frames": LOOK_UP, "speed": 30},
    "Looking Down": {"frames": CROUCH, "speed": 30},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": SKID, "align": True},
    "Super Peel Out": {"frames": PEEL, "rot": 2, "align": True},  # (Tails' fastest run)
    "Spin Dash": {"frames": BALL},
    "Jumping": C(BALL),
    "Bouncing": C(f("SPRING1", "SPRING2")),
    "Hurt": C(f("HURT1", "HURT2")),
    "Dying": C(f("DEATH")),
    "Drowning": C(f("DEATH")),
    "Breathing": C(f("HAPPY")),  # (no gasp on the sheet: his happy pose)
    "Fan Rotate": C(SPIN),
    "Pushing": {"frames": PUSH, "align": True},
    "Flailing 1": {"frames": BALANCE, "align": True},
    "Flailing 2": {"frames": BALANCE, "align": True},
    "Hanging": C(HANG),
    "Clinging On": C(HANG),
    "Corkscrew H": C(SPIN),  # Sonic 1 (Tails has none)
    "Water Slide": {"frames": f("SIT")},  # sitting
    "Continue": {"frames": f(*[f"CONT{k}" for k in range(1, 7)])},
    "Continue Up": C(FLY),
    "Super Transform": C(SPIN),
}
S2_ONLY = {
    "Bored!": {"frames": BORED, "loop": 1},
    "Flailing 3": {"frames": BALANCE, "align": True},
    "Grabbed": C(HANG),
    "Twirl H": {"frames": SPIN, "rot": 2, "anchor": "center"},
}
# Sonic CD's own animations, by CD's names (tools/cd_config.py "cd_animations")
CD_ANIMS = {
    "Dropping": C(DROP),
    "Spinning Top": {"frames": SPIN, "align": True},
}
# Sonic 3 & Knuckles, by its (Mania's) names (build_s3k_art.py "s3k_animations"); the rest from the ones above
S3K_ANIMS = {
    "Jump": C(BALL),  # (Tails' S3&K jump has 3 frames: the game's code counts them)
    "Fall": C(DROP),
    "Run": {"frames": RUN_6, "align": True},
    "Dash": {"frames": PEEL_6, "align": True},
    "Balance 1": {"frames": BALANCE, "align": True},
    "Balance 2": {"frames": BALANCE, "align": True},
    "Transform": C(SPIN),
}

# Phase Warp (the jump ability, slot 41: the flicker as he goes and comes back): the SPIN row turning round, fast
# Screen Nuke (Y, slots 43 / 44; abilities.py 32 melee_nuke, "at" 4: CONT3): arms spread, the dark form opening on its
# red core, the core pulsing, and back (the move's timer picks the frame: 10 frames of 4 game frames)
NUKE = f("ES6", "ES6", "CONT1", "CONT2", "CONT3", "CONT4", "CONT5", "CONT6", "CONT2", "ES6")
APPENDED = {
    "41": {"name": "Phase Warp", "frames": SPIN, "anchor": "center", "speed": 120},
    "43": {"name": "Screen Nuke", "frames": NUKE, "speed": 0},
    "44": {"name": "Screen Nuke Air", "frames": NUKE, "anchor": "center", "speed": 0},
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {
    # the S1 HUD tag's own icon (his head in a white box between black lines) and its yellow "TAILS DOLL"
    "life_icon": {"rect": [267, 691, 16, 16], "trim": False},
    "life_name": {"rect": [284, 691, 57, 7]},
    "monitor_1up": {"rect": [267, 692, 16, 14], "trim": False},  # that icon inside its black lines
    "sign_face": {"rect": [267, 767, 48, 32], "trim": False},  # the Signpost's board (his antenna above it cropped)
    "mini_1": {"rect": r("MINI1"), "remap": PLUS_128},
    "mini_2": {"rect": r("MINI2"), "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": r("ES1"), "remap": PLUS_128},  # ENDING(SMALL)'s first: standing, his tails drawn in
    "end_pose_1": {"rect": r("ES6"), "remap": PLUS_128},  # its arms-out pose
    "end_pose_2": {"rect": r("EB_SMALL"), "remap": PLUS_128},  # ENDING(BIG), small
    "end_pose_3": {"rect": r("EB_BIG"), "remap": PLUS_128},  # ENDING(BIG), big
    **{f"good_{n}": {"rect": r(f"ES{n}"), "remap": PLUS_128} for n in range(1, 7)},  # the ENDING(SMALL) row
}

# 22 colours in slots 74-95, exact; black is Sonic's own slot 1
PALETTE = {
    "74": "#d86c00", "75": "#fc9000", "76": "#e08000", "77": "#f67300",  # his oranges
    "78": "#b46c48", "79": "#e0a080",  # brown, the gem's highlight
    "80": "#480000", "81": "#800000", "82": "#880000", "83": "#e060e0", "84": "#e00000", "85": "#fc0000",  # reds
    "86": "#404040", "87": "#484848", "88": "#808080", "89": "#909090", "90": "#a0a0a0", "91": "#b4b4b4",  # greys
    "92": "#e0e0e0", "93": "#fcfcfc", "94": "#ffffff",  # whites
    "95": "#e0e000",  # the name tag's yellow (83: the signpost board's pink)
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}
# Merged (the colour exception): a near-black into black, and a dark brownish red (3 px: ROLL1, HURT2) into #880000; the
# signpost's shades 1-3 levels off their twins and the minis' 6 blue-grey px go to the nearest key colour (all_colours)
MERGED = {"#080000": 1, "#902400": 82}


def all_colours():
    """KEY_COLOURS and MERGED, plus every other colour on the sheet in the slot of its nearest key colour, so nothing is
    left to sheet2ani's guess."""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS, **MERGED)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


def used_colours(rects):
    used = {}
    for x, y, w, h in rects:
        for n, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16):
            c = "#%02x%02x%02x" % rgb
            if c not in BACKGROUND:
                used[c] = used.get(c, 0) + n
    return used


def check_colours():
    """Every colour in a player frame has its own slot but the two merged ones (the faithful art rule and its
    colour exception); returns what the UI elements merge, for the notes."""
    frames = [v[:4] for k, v in B.items() if k not in ("EB_SMALL", "EB_BIG", "MINI1", "MINI2")]
    missing = set(used_colours(frames)) - set(KEY_COLOURS) - set(MERGED)
    if missing:
        sys.exit(f"tails-doll: frame colours without a slot of their own: {sorted(missing)}")
    ui = used_colours([el["rect"] for el in list(ELEMENTS.values()) + list(ENDING.values())])
    return {c: n for c, n in ui.items() if c not in KEY_COLOURS}


CREDIT = ("Tails Doll (Sonic 1 / CD-Style). Sprite Artist & Creator: Nikog266. Sprite Corrections & Edits: Danthebol, "
          "Lmeichi, Spooky & Selphy Geumja - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/259541/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): ENDING(SMALL): into the arms-out pose
S3K_VICTORY = {"frames": f("ES5", "ES6"), "align": True}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra26", "credit": CREDIT,
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic2":
        cfg["cd_animations"] = CD_ANIMS
        cfg["s3k_animations"] = S3K_ANIMS
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra26SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(BALL)}}]
        cfg["ui"] = [{"name": "Extra26_UI", "manifest": "Extra26_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra26_UI.gif"},
                     {"name": "Extra26_Ending", "manifest": "Extra26_ending.json", "elements": ENDING,
                      "out": "build/Extra26_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    if "--merged" in sys.argv:
        print(check_colours())
        sys.exit()
    for game, out in (("Sonic1", "tailsdoll.json"), ("Sonic2", "tailsdoll_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
