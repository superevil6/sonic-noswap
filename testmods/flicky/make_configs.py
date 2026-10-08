#!/usr/bin/env python3
"""Writes Flicky's sheet2ani configs (flicky.json for Sonic 1, flicky_s2.json for Sonic 2; CD's and S3&K's come from the
Sonic 2 one: cd_animations, s3k_animations).

Flicky, extra 25 (file "Extra25", build ID 31), base character TAILS (extras.py "base": Tails' own flight in all four
games, as Cream and Charmy), so his .ani follows Tails' animation list (Flying, Flying Tired, Swimming, Swimming Tired,
the carrying animations). Public (credit in mods/NoSwap/README.md).
Sheet: testmods/Flicky.png (600x500), "Flicky (Sonic 1/CD-Style)" by TheOrangePlumber (see SOURCE.txt). The sheet asks
for credit and "Do Not Make This .exe Related": nothing Sonic.exe-themed (the "?" death frame and the gun gag at the
bottom right are not used).

The sheet's sprites sit in green boxes (#4bb98d, some #177e55) on a mint background (#9dffd8): all three are background.
Frames are named "<row>.<column>": rows of boxes top to bottom, boxes left to right (row 2 is the one small box under 1.31,
rows 6-10 are the special-stage rows, which aren't used). Every sprite faces right. Only the "Normal" palette is used:
the special stage rows (7-10: Introduction, Acquire TimeStone, Walk / Turn / Hard Turn / Spinball, Run, Booster, Fan,
Slip, Rotation) are drawn in Sonic CD's special stage blues, and the pipeline's special stages show the extra's own
spin ball (build_soniccd.special_ball), so they're left out, with the other palettes, the arcade sprites and the
"Unused Shenanigans".

Labels (the sheet's own):
  row 0   0.0 idle, 0.1-0.2 bored (a peck, then lying down), 0.3 up, 0.4 down, 0.5 spring; 0.6-0.11 Walking;
          0.12-0.15 Running; 0.16-0.17 Skid; 0.18-0.22 Spinball (0.18 the plain ball, 0.19-0.22 turning); 0.23-0.26
          Pushing; 0.27-0.28 Balance; 0.29-0.30 Hurt; 0.31 death, 0.32 drown, 0.33 gasp (0.34 burnt, 0.35 "?": unused)
  row 1   1.0-1.2 Continue; 1.3-1.7 Mid-Air Rotation; 1.8-1.9 Grab Bar; 1.10-1.12 Fly; 1.13-1.15 Up; 1.16-1.18 Down;
          1.19-1.24 Tired; 1.25-1.30 Ending; 1.31 and 2.0 Mini Flicky
  row 3   3.0-3.5 Rotation; 3.6-3.9 Bye-Bye; 3.10-3.14 Fly Away; 3.15-3.19 Spring Twirl; 3.20-3.23 Falling; 3.24-3.27
          Skid (CD); 3.28-3.31 Peelout; 3.32-3.35 Speen
  row 4   4.0-4.3 Balance 1; 4.4-4.7 Balance 2; 4.8-4.31 3D Ramp 1-6 (4 frames each)
  row 5   5.0-5.6 3D Ramp 7; 5.7-5.8 Ride; 5.9-5.11 Ceiling Bar; 5.12-5.15 Dash n Dive; 5.16-5.23 Swim
  and 11.1 the signpost (S1), 13.4 / 11.3 the Big Ending, and loose art: the "FLICKY" HUD tag, the life icon (his head,
  outlined in white) and the 1-UP monitor picture.

Size: he's drawn about 22 px tall (Sonic is about 40). Not enlarged: that needs the user's approval (the faithful art
rule's exceptions are per character).

Abilities (tools/abilities.py 31; the moves are wired there, in build_soniccd.py and the DLL):
  - jump ability: Tails' own flight (the base), with his Fly / Up / Down / Tired / Swim rows.
  - Y: Animal Drop (2026-09-27, replacing Dash n Dive): a real projectile (abilities.py "shot", motion "drop"), one of the
    critters of the sheet's "Boredom Bonus" row (the chicken, squirrel, penguin, pig, rabbit and seal: loose drawings cut
    as drawn, each exactly in his own colours) falling from under him onto enemies, a different one each throw. Its art
    is made from the shot's "drawings" boxes (build_s3k_shot.py): S3&K's Shot.bin, S1/S2's reserved strip of his player
    sheet (the first four: shots_v4.FRAMES), CD's shot animation (shots_v3.place_art). No ability animations of his own.

Nothing is redrawn, recoloured or resized: frames are cut as drawn. The HUD name tag, life icon, 1-UP picture, signpost,
continue minis and ending poses are the sheet's own. The frames use 15 colours: black in Sonic's slot 1 (the same black),
the other 14 exactly in the extras' own slots 74-87; nothing merged.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

SHEET = "../Flicky.png"
BACKGROUND = ["#9dffd8", "#4bb98d", "#177e55"]  # the mint sheet and its two box greens
SRC = Image.open(HERE / SHEET).convert("RGB")

B = {  # frame -> [x, y, w, h] (its sprite's bounding box inside its box)
    # row 0
    "0.0": [5, 24, 12, 22], "0.1": [20, 27, 13, 19], "0.2": [35, 34, 15, 12], "0.3": [52, 25, 13, 21],
    "0.4": [67, 34, 15, 12], "0.5": [84, 24, 13, 21], "0.6": [102, 24, 12, 22], "0.7": [117, 23, 12, 22],
    "0.8": [132, 25, 12, 21], "0.9": [147, 24, 12, 22], "0.10": [162, 23, 12, 22], "0.11": [177, 25, 12, 21],
    "0.12": [195, 24, 14, 22], "0.13": [211, 23, 14, 23], "0.14": [227, 24, 14, 22], "0.15": [243, 23, 14, 23],
    "0.16": [262, 24, 16, 22], "0.17": [279, 23, 15, 23], "0.18": [299, 27, 14, 14], "0.19": [315, 27, 14, 14],
    "0.20": [331, 27, 14, 14], "0.21": [347, 27, 14, 14], "0.22": [363, 27, 14, 14], "0.23": [383, 24, 14, 22],
    "0.24": [400, 23, 13, 23], "0.25": [415, 24, 14, 22], "0.26": [432, 23, 13, 23], "0.27": [451, 25, 12, 21],
    "0.28": [466, 26, 14, 20], "0.29": [483, 26, 17, 16], "0.30": [501, 26, 17, 16], "0.31": [522, 23, 13, 22],
    "0.32": [538, 25, 12, 20], "0.33": [554, 24, 13, 21],
    # row 1
    "1.0": [5, 76, 11, 20], "1.1": [19, 75, 11, 21], "1.2": [33, 73, 11, 23], "1.3": [50, 77, 19, 16],
    "1.4": [70, 77, 17, 16], "1.5": [88, 77, 19, 16], "1.6": [108, 77, 18, 16], "1.7": [129, 77, 18, 16],
    "1.8": [150, 79, 21, 12], "1.9": [173, 79, 22, 12], "1.10": [199, 75, 17, 18], "1.11": [218, 75, 17, 18],
    "1.12": [237, 75, 17, 18], "1.13": [258, 76, 17, 17], "1.14": [277, 76, 17, 17], "1.15": [296, 76, 17, 17],
    "1.16": [316, 78, 17, 15], "1.17": [335, 78, 17, 15], "1.18": [354, 78, 17, 15], "1.19": [374, 75, 17, 18],
    "1.20": [393, 75, 17, 18], "1.21": [412, 75, 17, 18], "1.22": [432, 76, 17, 17], "1.23": [451, 76, 17, 17],
    "1.24": [470, 76, 17, 17], "1.25": [494, 75, 12, 22], "1.26": [509, 75, 12, 22], "1.27": [523, 76, 14, 21],
    "1.28": [538, 75, 13, 22], "1.29": [553, 75, 13, 22], "1.30": [570, 77, 11, 20], "1.31": [587, 74, 8, 11],
    "2.0": [587, 89, 9, 8],
    # row 3
    "3.0": [5, 110, 12, 22], "3.1": [19, 110, 13, 22], "3.2": [33, 110, 11, 22], "3.3": [45, 110, 13, 22],
    "3.4": [60, 110, 12, 22], "3.5": [75, 110, 11, 22], "3.6": [93, 110, 12, 22], "3.7": [107, 110, 12, 22],
    "3.8": [120, 110, 14, 22], "3.9": [135, 110, 14, 22], "3.10": [151, 113, 13, 19], "3.11": [165, 120, 15, 12],
    "3.12": [181, 116, 17, 15], "3.13": [200, 116, 17, 15], "3.14": [219, 116, 17, 15], "3.15": [242, 110, 13, 21],
    "3.16": [258, 110, 13, 21], "3.17": [273, 110, 13, 21], "3.18": [288, 110, 13, 21], "3.19": [304, 110, 13, 21],
    "3.20": [322, 110, 14, 22], "3.21": [337, 110, 14, 22], "3.22": [352, 110, 13, 22], "3.23": [366, 110, 14, 22],
    "3.24": [385, 109, 15, 23], "3.25": [401, 110, 16, 22], "3.26": [418, 110, 15, 22], "3.27": [434, 110, 16, 22],
    "3.28": [455, 111, 20, 21], "3.29": [476, 111, 20, 21], "3.30": [497, 111, 20, 21], "3.31": [518, 111, 19, 21],
    "3.32": [540, 110, 13, 22], "3.33": [555, 110, 13, 22], "3.34": [569, 110, 14, 22], "3.35": [584, 110, 13, 22],
    # row 4
    "4.0": [5, 149, 12, 21], "4.1": [19, 149, 13, 21], "4.2": [35, 150, 14, 20], "4.3": [51, 150, 13, 20],
    "4.4": [70, 151, 18, 19], "4.5": [89, 151, 18, 19], "4.6": [110, 152, 16, 18], "4.7": [129, 152, 16, 18],
    "4.8": [150, 152, 18, 17], "4.9": [170, 152, 17, 17], "4.10": [189, 152, 17, 18], "4.11": [208, 152, 17, 17],
    "4.12": [232, 152, 18, 18], "4.13": [251, 152, 18, 18], "4.14": [270, 152, 18, 18], "4.15": [289, 152, 18, 18],
    "4.16": [312, 148, 16, 21], "4.17": [329, 148, 14, 21], "4.18": [344, 148, 14, 21], "4.19": [359, 148, 14, 21],
    "4.20": [378, 148, 15, 22], "4.21": [394, 148, 15, 22], "4.22": [410, 148, 13, 22], "4.23": [424, 148, 15, 22],
    "4.24": [446, 154, 16, 16], "4.25": [465, 154, 16, 16], "4.26": [484, 154, 16, 16], "4.27": [503, 154, 16, 16],
    "4.28": [524, 152, 17, 18], "4.29": [542, 152, 17, 18], "4.30": [560, 152, 16, 18], "4.31": [577, 152, 17, 18],
    # row 5
    "5.0": [4, 193, 14, 14], "5.1": [19, 193, 14, 14], "5.2": [34, 193, 14, 14], "5.3": [49, 193, 14, 14],
    "5.4": [64, 193, 14, 14], "5.5": [79, 193, 14, 14], "5.6": [94, 193, 14, 14], "5.7": [113, 188, 16, 20],
    "5.8": [130, 187, 16, 21], "5.9": [152, 189, 13, 19], "5.10": [167, 189, 12, 19], "5.11": [181, 189, 12, 19],
    "5.12": [200, 192, 19, 16], "5.13": [220, 191, 19, 17], "5.14": [240, 192, 18, 16], "5.15": [259, 192, 18, 16],
    "5.16": [282, 189, 18, 19], "5.17": [301, 189, 18, 17], "5.18": [320, 189, 18, 17], "5.19": [339, 189, 18, 17],
    "5.20": [358, 189, 18, 19], "5.21": [377, 189, 18, 17], "5.22": [396, 189, 18, 17], "5.23": [415, 189, 18, 17],
    # the Big Ending
    "13.4": [519, 328, 32, 60], "11.3": [552, 299, 47, 89],
}


def f(*names):
    return [B[n] for n in names]


def run(first, last, row):
    return f(*[f"{row}.{k}" for k in range(first, last + 1)])


IDLE = f("0.0")
BORED = f("0.1", "0.2")  # a peck at the ground, then lying down
WALK = run(6, 11, 0)
RUN = run(12, 15, 0)
PEEL = run(28, 31, 3)  # the Peelout's figure-of-eight legs
# the Spinball: the plain ball between the four turning frames, as Sonic 1's jump alternates its plain ball
BALL = f("0.19", "0.18", "0.20", "0.18", "0.21", "0.18", "0.22", "0.18")
TURNING = f("0.19", "0.20", "0.21", "0.22")
FLY = run(10, 12, 1)
FLY_UP = run(13, 15, 1)
FLY_DOWN = run(16, 18, 1)
TIRED = run(19, 24, 1)
SWIM = run(16, 23, 5)
ROTATION = run(0, 5, 3)  # turning round where he stands
SPRING_TWIRL = run(15, 19, 3)
FALLING = run(20, 23, 3)
BALANCE = f("0.27", "0.28")
BALANCE_1 = run(0, 3, 4)
BALANCE_2 = run(4, 7, 4)
CEILING_BAR = run(9, 11, 5)  # hanging by his wings, seen from behind
GRAB_BAR = f("1.8", "1.9")  # stretched out level, holding a bar
C = lambda frames: {"frames": frames, "anchor": "center"}

ANIMS = {
    "Stopped": {"frames": IDLE},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": BORED, "loop": 1},
    "Looking Up": {"frames": f("0.3")},
    "Looking Down": {"frames": f("0.4")},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("0.16", "0.17"), "align": True},
    "Super Peel Out": {"frames": PEEL, "rot": 2, "align": True},  # (Tails' fastest run)
    "Spin Dash": {"frames": TURNING},
    "Jumping": C(BALL),
    "Bouncing": C(f("0.5")),  # the spring pose
    "Hurt": C(f("0.29", "0.30")),
    "Dying": C(f("0.31")),
    "Drowning": C(f("0.32")),
    "Breathing": C(f("0.33")),  # the gasp
    "Fan Rotate": C(run(3, 7, 1)),  # the Mid-Air Rotation (5 frames, as Tails')
    "Pushing": {"frames": run(23, 26, 0), "align": True},
    "Flailing 1": {"frames": BALANCE, "align": True},
    "Flailing 2": {"frames": BALANCE_2, "align": True},
    "Hanging": C(CEILING_BAR),
    "Clinging On": C(GRAB_BAR),
    "Corkscrew H": C(SPRING_TWIRL),  # Sonic 1 (Tails has none)
    "Water Slide": {"frames": f("5.7", "5.8")},  # the Ride pose, leaning back
    "Continue": {"frames": run(0, 2, 1)},
    "Continue Up": {"frames": f("3.10", "3.11")},  # Fly Away's start: turning, crouching to take off
    "Super Transform": C(ROTATION),
    # Tails' flight set
    "Flying": C(FLY),
    "Flying Tired": C(TIRED),
    "Swimming": C(SWIM),
    "Swimming Tired": C(TIRED),
    "Fly Lift Down": C(FLY_DOWN),  # carrying a partner (never happens: extras play alone)
    "Fly Lift Up": C(FLY_UP),
    "Fly Lift Tired": C(TIRED),
    "Swim Lift": C(SWIM),
}
S2_ONLY = {
    "Bored!": {"frames": BORED, "loop": 1},
    # Sonic 2's slot 20 is Tails' (empty) "Sliding" but Sonic's "Flailing 3": his other balance
    "Sliding": {"frames": BALANCE_1, "align": True},
    "Grabbed": C(GRAB_BAR),
    "Twirl H": {"frames": SPRING_TWIRL, "rot": 2, "anchor": "center"},
}
# Sonic CD's own animations, by CD's names (tools/cd_config.py "cd_animations")
CD_ANIMS = {
    "Skidding": {"frames": run(24, 27, 3), "align": True},  # Skid (CD)
    "Spinning Top": {"frames": run(32, 35, 3), "align": True},  # "Speen"
    "Dropping": {"frames": FALLING, "align": True},
    **{f"3D Ramp {n}": {"frames": run(8 + 4 * (n - 1), 11 + 4 * (n - 1), 4), "align": True} for n in range(1, 7)},
    "3D Ramp 7": C(run(0, 6, 5)),
}
# Sonic 3 & Knuckles, by its (Mania's) names (build_s3k_art.py "s3k_animations"); the rest from the ones above
S3K_ANIMS = {
    "Jump": C(TURNING),  # (Tails' S3&K jump has 3 frames: the game's code counts them)
    "Fall": {"frames": FALLING, "align": True},
    "Dash": {"frames": PEEL, "align": True},
    "Balance 1": {"frames": BALANCE_1, "align": True},
    "Balance 2": {"frames": BALANCE_2, "align": True},
    "Transform": C(ROTATION),
    # Tails' S3&K flight poses have 1-2 frames (his flapping is his separate tails object): Flicky's own flaps in full
    # ("own_count", build_s3k_art.py; his flight state sets only the animation speed, so the game plays them). Fly: the
    # Fly row there and back (wings up, level, down, level)
    "Fly": dict(C(f("1.10", "1.11", "1.12", "1.11")), own_count=True),
    "Fly Tired": dict(C(TIRED), own_count=True),
    "Fly Lift": dict(C(FLY_UP), own_count=True),
    "Fly Lift Down": dict(C(FLY_DOWN), own_count=True),
    "Fly Lift Tired": dict(C(TIRED), own_count=True),
    **{n: {"frames": CEILING_BAR} for n in ("Hang Move", "HangGimmick", "Pulley Hold", "HorizontalBarHang")},
}

# (No ability animations: his Y, the Animal Drop, is a projectile with its own art, abilities.py 31 "shot". The sheet's
# Dash n Dive row, 5.12-5.15, was the old Y move's.)
APPENDED = {}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
BLANK = HERE / "build" / "blank16.png"  # an empty 16x16 board, to centre the life icon on (sheet2ani "base")
ELEMENTS = {
    # his head, outlined in white (12x14, loose on the sheet between the P and F posts), centred in the HUD's 16x16
    "life_icon": {"rect": [530, 298, 12, 14], "base": {"file": str(BLANK), "rect": [0, 0, 16, 16]}, "at": [2, 1]},
    "life_name": {"rect": [560, 286, 35, 7]},  # the sheet's own yellow "FLICKY" tag
    "monitor_1up": {"rect": [506, 304, 16, 14], "trim": False},  # the sheet's 1-UP picture (inside its black lines)
    "sign_face": {"rect": [408, 303, 48, 32], "trim": False},  # the Signpost (S1): the bolt and the board
    "mini_1": {"rect": B["1.31"], "remap": PLUS_128},  # Mini Flicky
    "mini_2": {"rect": B["2.0"], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B["0.0"], "remap": PLUS_128},
    "end_pose_1": {"rect": B["3.8"], "remap": PLUS_128},  # Bye-Bye, waving
    "end_pose_2": {"rect": B["13.4"], "remap": PLUS_128},  # the Big Ending, small
    "end_pose_3": {"rect": B["11.3"], "remap": PLUS_128},  # the Big Ending, large
    **{f"good_{n}": {"rect": B[f"1.{24 + n}"], "remap": PLUS_128} for n in range(1, 7)},  # the Ending row
}

# The "Normal" palette: 15 colours. Black is Sonic's own slot 1; the rest keep their exact values in slots 74-87.
PALETTE = {
    "74": "#242490", "75": "#4848b4", "76": "#6c6cd8", "77": "#9090fc",  # his blues, dark to light
    "78": "#fcfc00", "79": "#fcfcfc", "80": "#fcb490", "81": "#b46c48",  # beak and feet, white, face, brown
    "82": "#b4b4b4", "83": "#909090", "84": "#484848",  # greys (his belly, the signpost's frame)
    "85": "#fc0000", "86": "#900000", "87": "#480000",  # reds (cheeks, the signpost's board)
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (the other palettes, the special stage rows) in the slot of its
    nearest key colour, so nothing is left to sheet2ani's guess. (No built frame uses one: check_colours.)"""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


def check_colours():
    """Every colour in a built frame or UI element has its own slot (the faithful art rule: nothing merged)."""
    rects = list(B.values()) + [el["rect"] for el in ELEMENTS.values()]
    used = set()
    for x, y, w, h in rects:
        used |= {rgb for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    missing = {"#%02x%02x%02x" % c for c in used} - set(KEY_COLOURS) - set(BACKGROUND)
    if missing:
        sys.exit(f"flicky: frame colours without a slot of their own: {sorted(missing)}")


def blank_board():
    BLANK.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("P", (16, 16), 0)
    img.putpalette([0] * 768)
    img.save(BLANK)


CREDIT = ("Flicky (Sonic 1/CD-Style) Made By TheOrangePlumber - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/546165/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): Bye-Bye: waving
S3K_VICTORY = {"frames": f("3.8", "3.9"), "align": True}


def config(game):
    check_colours()
    blank_board()
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra25", "credit": CREDIT,
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Tails.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic2":
        cfg["cd_animations"] = CD_ANIMS
        cfg["s3k_animations"] = S3K_ANIMS
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra25SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(BALL)}}]
        cfg["ui"] = [{"name": "Extra25_UI", "manifest": "Extra25_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra25_UI.gif"},
                     {"name": "Extra25_Ending", "manifest": "Extra25_ending.json", "elements": ENDING,
                      "out": "build/Extra25_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "flicky.json"), ("Sonic2", "flicky_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
