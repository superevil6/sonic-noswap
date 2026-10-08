#!/usr/bin/env python3
"""Writes Mecha Sonic's sheet2ani configs (mecha.json for Sonic 1, mecha_s2.json for Sonic 2).

Mecha Sonic (Mk II), extra 22 (file "Extra22", build ID 28), base character Sonic.
Sheet: testmods/MechaSonic.png (711x787), "Custome Mecha Sonic sprites made by Domenico" (see SOURCE.txt). Its top
rows ("In-game sprites") are the original Sonic & Knuckles Mecha Sonic sprites (SEGA); the rest ("Custom sprites")
are Domenico's.

Frames are the sprites on the sheet, numbered as detected: connected components of everything that isn't the
#ffffff sheet background (8-connected), sorted by top edge, then left edge.

Layout (y):
   49-112  in-game: standing 20, crouching down 22 / 24 / 30 / 31, the spike ball 28 / 26 / 27 (turning), curling
           29 / 23, turning to the front 17, front-on 18 / 19 / 21
  116-181  in-game: charging with the emerald's power 33 / 34, crouch 40, the afterburner dash 36 / 37 / 38 (flame
           behind him) and 39 (the flame gone, a few sparks trailing: 41-52), energy rings 43 / 47 / 48 / 50 / 57
  199-265  standing 69, wait (looking at his hand) 71 / 73 / 72, head down 74, looking up 63, kicks 64 / 66, arms
           up 65, pointing 70 / 67 / 68, a low lunge 75
  268-330  the arm cannon row (a projectile: not used, the user wants no new projectiles)
  334-399  standing with / without the orb 91 / 92, leap 90, stride 101, fist up 96, 97, 98, 93, a claw swipe 94,
           a dive 103, front-on 95 / 99 / 100, from behind 102
  404-474  standing without arms (bases) 108-111, rising 107 / 106, rockets firing 105, falling apart 112-119
  478-538  crouching 125 / 126 / 130 / 131, legs-only walk bases 120-129, lying flat 132
  543-606  the walk, 8 frames with arms (141, 136, 142, 137, 133, 138, 143, 139); glowing white 134 / 135 / 147
  610-672  spare heads (152 side, 154 front, 155 back, ...), bodies and limbs; the big portrait 146 (84x124)
Below that: the credits box (not used).

Template: Sonic's .ani (Sonic's moveset). He rolls into his spiky ball: "Jumping", "Spin Dash", the special stages
and the Spike Ball are the in-game spike ball frames. The sheet has no run: "Running" is his hovering dash (93 / 94, the user's pick),
"Super Peel Out" every other frame (as Jet's).

Abilities (appended slots; the moves are wired in tools/abilities.py, build_soniccd.py and the DLL):
  41 "Spike Ball": the spike ball, turning fast (his S&K boss attack: the jump ability slams him diagonally down).
  43 / 44 "Jet Boost" / "Jet Boost Air": the afterburner dash (36, 37, 38: the flame flickers), then 39 with its
      trailing sparks as the flame dies. Every frame is placed by his body (the right 40 px of each frame, where the
      four are the same pose), so the flame only grows behind him.

Nothing is redrawn, recoloured or resized: frames are cut (the "Fan Rotate" pair is his flat pose and its mirror
image; the turn uses a mirrored side pose); the HUD icons are crops of the sheet's front head; only the "MECHA" name
tag (not on the sheet) is our own lettering in the HUD font the other extras use. Every sheet colour used has its own
palette slot (19 of the 22 extra slots) or is exactly Sonic's (#808080): no colour is merged.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
from sign_face import board_face  # noqa: E402
SHEET = "../MechaSonic.png"
BACKGROUND = ["#ffffff"]
SRC = Image.open(HERE / SHEET).convert("RGB")

B = {  # sprite number -> [x, y, w, h] (its bounding box)
    93: [344, 337, 40, 62], 94: [389, 337, 40, 62],  # the hovering dash pose, and with its yellow energy trail
    # in-game row 1: stand, crouch, spike ball
    20: [5, 50, 41, 62], 22: [51, 56, 43, 56], 24: [99, 63, 43, 49], 30: [147, 73, 43, 39], 31: [195, 73, 43, 39],
    28: [289, 66, 48, 46], 26: [342, 64, 48, 48], 27: [395, 64, 48, 48],
    # in-game row 2: the emerald's power, the afterburner dash
    33: [5, 117, 37, 64], 34: [179, 118, 39, 63],
    36: [223, 127, 64, 54], 37: [292, 127, 63, 54], 38: [360, 127, 63, 54],
    39: [428, 128, 90, 54],  # 39 [468, 128, 50, 53] with the sparks trailing behind it (41-52, from x 428)
    # custom row 1
    69: [5, 203, 41, 62], 71: [51, 205, 42, 60], 73: [98, 206, 42, 59], 72: [144, 205, 44, 60],
    63: [233, 199, 38, 65], 65: [339, 200, 38, 64], 70: [382, 203, 57, 61], 67: [444, 202, 47, 62],
    68: [496, 202, 38, 62],
    # custom row 3
    90: [106, 334, 40, 65], 101: [151, 339, 46, 60], 96: [202, 338, 42, 61], 97: [249, 338, 44, 61],
    98: [298, 338, 41, 61], 95: [489, 337, 40, 62], 99: [534, 338, 28, 61], 100: [567, 338, 42, 61],
    102: [614, 339, 26, 60],
    # crouch, lying flat
    125: [482, 478, 40, 60], 132: [361, 511, 64, 27],
    # the walk; glowing white
    141: [5, 545, 38, 61], 136: [48, 544, 39, 61], 142: [92, 545, 48, 60], 137: [145, 544, 41, 61],
    133: [191, 543, 38, 62], 138: [234, 544, 39, 61], 143: [278, 545, 45, 60], 139: [328, 544, 39, 61],
    134: [372, 543, 41, 62], 135: [418, 543, 41, 62],
    # heads, the big portrait
    152: [5, 614, 36, 28], 153: [46, 614, 38, 28], 154: [121, 615, 26, 27], 146: [614, 548, 84, 124],
}


def f(*nums):
    return [B[n] for n in nums]


def flip(n):
    return {"rect": B[n], "flip": True}


def body(n):
    """An afterburner frame placed by his body: the right 40 px of the frame (all four are the same pose there), so
    the flame and sparks grow out behind him without moving him."""
    x, y, w, h = B[n]
    return {"rect": B[n], "anchor_box": [x + w - 40, y + h - 53, 40, 53]}


WALK = f(141, 136, 142, 137, 133, 138, 143, 139)  # the 8-frame walk (arms swinging)
RUN = f(141, 142, 133, 143)  # no run on the sheet: every other walk frame
FAST = f(93, 94)  # "Running": his hovering dash, alternating with the yellow energy trail (the user's pick)
BALL = f(28, 26, 27)  # the in-game spike ball, its spikes turning
TURN = [B[69], B[99], flip(69), B[102]]  # side, front, the other side, back
BOOST = [body(36), body(37), body(38), body(37), body(38), body(39)]

ANIMS = {
    "Stopped": {"frames": f(20)},  # the in-game standing frame (also the Origins select card)
    "Waiting": {"frames": f(69, 71, 73, 73, 72, 71), "loop": 1},  # looks at his hand
    "Looking Up": {"frames": f(20, 63), "loop": 1},
    "Looking Down": {"frames": f(22, 24, 30), "loop": 2},  # the in-game crouch
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": FAST, "rot": 2, "align": True},
    "Skidding": {"frames": f(98), "align": True},  # braced, legs apart
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Spin Dash": {"frames": BALL, "anchor": "center"},
    "Jumping": {"frames": BALL, "anchor": "center"},
    "Bouncing": {"frames": f(90), "anchor": "center"},  # the leap, arms down
    "Hurt": {"frames": f(65), "anchor": "center"},  # arms thrown up
    "Dying": {"frames": f(95), "anchor": "center"},  # front-on, arms out
    "Drowning": {"frames": f(100), "anchor": "center"},  # front-on, arms bent
    "Fan Rotate": {"frames": [B[132], flip(132)], "anchor": "center"},  # lying flat, spikes first
    "Breathing": {"frames": f(63), "anchor": "center"},  # looking up
    "Pushing": {"frames": f(101), "align": True},  # leaning into a stride
    "Flailing 1": {"frames": f(70, 67), "align": True},  # arm up, arm out
    "Flailing 2": {"frames": f(65, 72), "align": True},
    "Hanging": {"frames": f(65), "anchor": "center"},  # arms up
    "Clinging On": {"frames": f(132), "anchor": "center"},  # flat out
    "Corkscrew H": {"frames": TURN},
    "Water Slide": {"frames": f(132), "anchor": "center"},
    "Continue": {"frames": f(30, 31)},  # crouched, waiting (in-game)
    "Continue Up": {"frames": f(24, 22, 63), "loop": 2},  # getting up, looking up
    "Super Transform": {"frames": f(33, 34, 134, 135), "loop": 2},  # the emerald's power, glowing white
}
S1_ONLY = {}
S2_ONLY = {
    "Bored!": {"frames": f(67, 68, 67, 68, 69), "loop": 4},  # pointing: "come on"
    "Flailing 3": {"frames": f(70, 65), "align": True},
    "Grabbed": {"frames": f(65, 70), "anchor": "center"},
    "Twirl H": {"frames": TURN, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    "41": {"name": "Spike Ball", "frames": BALL, "speed": 240, "anchor": "center"},  # turning fast
    "43": {"name": "Jet Boost", "frames": BOOST, "speed": 60},
    "44": {"name": "Jet Boost Air", "frames": BOOST, "speed": 60},
}
BOOST_REACH = 20  # his body's front, px ahead of the frames' pivot (the middle of the 40 px body box)


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
HEAD = B[154]  # the front head (26x27): spikes, eyes and mouth grille at the bottom
ELEMENTS = {
    # the front head's eyes and grille (its middle 16 columns, the bottom 16 rows)
    "life_icon": {"rect": [HEAD[0] + 5, HEAD[1] + 11, 16, 16], "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("MECHA")},
    "monitor_1up": {"rect": [HEAD[0] + 5, HEAD[1] + 12, 16, 14], "trim": False},
    # no signpost art: the front head on the game's own board (Items2), enlarged 1.3x nearest-neighbour to fill its
    # 40x24 face area (the user's signpost exception; tools/sign_face.py: the top spike is trimmed, the grille stays)
    "sign_face": board_face(HEAD, 1.3),
    # continue icons: no small set on the sheet; his spare side heads, as Gamma's head crops, without the tips of
    # their back spikes (1 and 3 columns) so they fit the 35 px the other extras' boxes already have
    "mini_1": {"rect": [B[152][0] + 1, B[152][1], 35, 28], "remap": PLUS_128},
    "mini_2": {"rect": [B[153][0] + 3, B[153][1], 35, 28], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[20], "remap": PLUS_128},
    "end_pose_1": {"rect": B[96], "remap": PLUS_128},  # fist up
    "end_pose_2": {"rect": B[90], "remap": PLUS_128},  # the leap
    "end_pose_3": {"rect": B[146], "remap": PLUS_128},  # the sheet's big portrait (84x124)
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((20, 71, 73, 96, 97, 101), 1)},  # (101, the stride: 90 is 1 px taller than the box)
}

# The frames use 20 colours: #808080 is exactly Sonic's slot 8; the other 19 keep their exact values in the extras'
# own slots 74-92. Nothing is merged.
PALETTE = {
    "74": "#3d1a9f", "75": "#3d1a5b", "76": "#1a1a35", "77": "#3d3dc1", "78": "#001a00", "79": "#8585ee",
    "80": "#f7f7f7", "81": "#d3d3f7", "82": "#4040c0",  # his blues, outline and whites
    "83": "#f7a74d", "84": "#f7f74d", "85": "#f7f70f", "86": "#f73d0f",  # the flame, eyes and lights
    "87": "#3d0000", "88": "#a71a0f", "89": "#85000f",  # the red feet and eye rims
    "90": "#eaeaea", "91": "#85850f", "92": "#851a24",  # a few pixels each (the portrait, the eyes)
}
KEY_COLOURS = {"#808080": 8, **{c: int(s) for s, c in PALETTE.items()}}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (the title, labels and credits) in the slot of its nearest
    key colour, so nothing is left to sheet2ani's guess. (No frame uses one.)"""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


CREDIT = ("Custom Mecha Sonic sprites made by Domenico (\"Give credit if used.\"); the in-game sprites are Sonic & "
          "Knuckles' (SEGA). Mecha Sonic (c) SEGA - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/183703/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): into the fist up (the ending pose)
S3K_VICTORY = {"frames": f(97, 96)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra22", "credit": CREDIT,
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else S1_ONLY)),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra22SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": BALL, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra22_UI", "manifest": "Extra22_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra22_UI.gif"},
                     {"name": "Extra22_Ending", "manifest": "Extra22_ending.json", "elements": ENDING,
                      "out": "build/Extra22_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "mecha.json"), ("Sonic2", "mecha_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
