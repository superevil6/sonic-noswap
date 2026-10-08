#!/usr/bin/env python3
"""Writes Espio's sheet2ani configs (espio.json for Sonic 1, espio_s2.json for Sonic 2).

Frames are the dark boxes on Espio.png ("Espio, The Chameleon In Sonic 1" by Akimaca; see SOURCE.txt), numbered
as detected: connected components of everything that isn't the #9fca7a sheet background, rows left to right,
top to bottom. The sheet labels its rows (Idle, Waiting, Walking...), and the mapping follows them.

Template: Sonic's .ani. The sheet has no glide, climb or flight art, so neither Knuckles' nor Tails' animation
set would be filled; his moves (below) are NoSwap ability slots.
The sheet has his own spin (curled frames plus a ball) and Spindash, so tools/sonic_ball.py isn't needed.
Nothing is redrawn or resized: frames are cut, and the HUD art is cropped from the sheet's own.

"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
B = {  # box number -> [x, y, w, h]
    10: [17, 56, 28, 41], 11: [303, 51, 28, 46], 13: [227, 59, 28, 38], 14: [265, 65, 31, 32], 15: [54, 68, 43, 29], 16: [100, 67, 39, 30],
    17: [142, 68, 35, 29], 18: [182, 67, 39, 30], 24: [12, 119, 39, 36], 25: [55, 117, 44, 38], 26: [104, 118, 41, 37], 27: [151, 119, 41, 36],
    28: [198, 117, 46, 38], 29: [250, 118, 43, 37], 30: [304, 119, 44, 36], 31: [359, 117, 37, 38], 32: [397, 117, 35, 38], 36: [508, 161, 35, 48],
    37: [12, 181, 47, 31], 38: [65, 181, 51, 31], 39: [123, 181, 53, 31], 40: [180, 181, 53, 31], 41: [242, 177, 43, 35], 42: [287, 175, 37, 37],
    43: [334, 182, 42, 30], 44: [379, 182, 42, 30], 45: [557, 179, 30, 30], 46: [596, 179, 30, 30], 47: [632, 179, 30, 30], 48: [668, 179, 30, 30],
    49: [706, 179, 30, 30], 54: [507, 224, 28, 27], 55: [545, 224, 28, 27], 56: [585, 224, 28, 27], 57: [623, 224, 28, 27], 58: [666, 224, 28, 27],
    59: [707, 224, 29, 27], 60: [21, 232, 28, 49], 61: [55, 232, 31, 49], 62: [95, 232, 27, 49], 63: [129, 232, 31, 49], 64: [163, 232, 28, 49],
    65: [197, 232, 27, 49], 66: [240, 247, 34, 33], 67: [279, 246, 33, 34], 68: [316, 247, 35, 33], 69: [358, 246, 33, 34], 71: [502, 272, 38, 39],
    72: [542, 268, 41, 43], 73: [585, 272, 36, 39], 74: [624, 268, 38, 43], 75: [664, 269, 35, 42], 76: [703, 272, 36, 39], 79: [306, 299, 24, 45],
    80: [339, 299, 24, 45], 81: [372, 299, 24, 45], 82: [409, 296, 35, 48], 83: [449, 295, 35, 49], 84: [21, 319, 60, 25], 85: [87, 319, 61, 25],
    86: [163, 316, 45, 28], 87: [215, 316, 36, 28], 88: [255, 316, 41, 28], 99: [28, 373, 25, 41], 100: [113, 373, 24, 41], 101: [141, 373, 25, 41],
    102: [209, 373, 30, 41], 103: [245, 373, 30, 41], 104: [350, 366, 48, 48], 105: [58, 379, 38, 35], 106: [170, 375, 30, 39], 107: [281, 379, 38, 35],
    108: [459, 390, 18, 24], 109: [481, 390, 16, 24], 115: [405, 398, 48, 16], 120: [145, 456, 162, 145], 122: [53, 482, 50, 89],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "Espio.png"
BACKGROUND = ["#9fca7a", "#609b2e"]  # the sheet, and the boxes the frames sit in

WALK = f(24, 25, 26, 27, 28, 29)  # "Walking"
RUN = f(37, 38, 39, 40)  # "Running"
SPIN = f(45, 46, 47, 48, 49)  # "Normal spin": curled frames, then the ball
SPINDASH = f(54, 55, 56, 57, 58, 59)  # "Spindash"
BALANCE = f(41, 42)
HURT_SLIDE = f(43, 44)
TORNADO = f(60, 61, 62, 63, 64, 65)  # "Tornado spin": whirling front-on, with the drill-like whirlwind between

ANIMS = {
    "Stopped": {"frames": f(10)},  # "Idle"
    "Waiting": {"frames": f(15, 16, 17, 18), "loop": 2},  # "Waiting": crouched, tapping
    "Looking Up": {"frames": f(13), "loop": 0},
    "Looking Down": {"frames": f(14), "loop": 0},  # "Crouch"
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2},
    "Skidding": {"frames": f(31, 32)},
    "Super Peel Out": {"frames": RUN, "rot": 2},  # no peel-out art
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": {"frames": SPIN, "anchor": "center"},
    "Bouncing": {"frames": f(11), "anchor": "center"},  # "Spring"
    "Hurt": {"frames": f(43), "anchor": "center"},  # "Hurt/Slide"
    "Dying": {"frames": f(82), "anchor": "center"},  # "Death"
    "Drowning": {"frames": f(83), "anchor": "center"},  # "Drown"
    "Fan Rotate": {"frames": f(86, 87, 88), "anchor": "center"},  # "Labyrinth spin"
    "Breathing": {"frames": f(30), "anchor": "center"},  # "Bubble"
    "Pushing": {"frames": f(66, 67, 68, 69)},
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(11), "anchor": "center"},  # no hanging art: the spring pose (arms up)
    "Clinging On": {"frames": f(84, 85), "anchor": "center"},  # "Cling"
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": HURT_SLIDE, "anchor": "center"},
    "Continue": {"frames": f(79, 80, 81)},
    "Continue Up": {"frames": f(11), "loop": 0},
    "Super Transform": {"frames": f(10), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": f(43), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(15, 16, 17, 18), "loop": 2},
}

APPENDED = {
    # Whirlwind (jump in mid-air, attack slot 41): the "Tornado spin", whirling in place as he floats down
    "41": {"name": "Whirlwind", "frames": TORNADO, "anchor": "center", "speed": 120},
    # Leaf Swirl (Y, slot 43): the same whirl on the ground, before he turns invisible
    "43": {"name": "Leaf Swirl", "frames": TORNADO, "anchor": "feet", "speed": 120},
    "44": {"name": "Leaf Swirl Air", "frames": TORNADO, "anchor": "center", "speed": 120},  # Y in mid-air
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": [B[115][0], B[115][1], 16, 16], "trim": False},  # "Life counter": his head
    "life_name": {"rect": [B[115][0] + 17, B[115][1] + 1, 31, 7]},  # ...and "ESPIO"
    "monitor_1up": {"rect": [B[115][0], B[115][1] + 1, 16, 14], "trim": False},  # the icon's middle rows
    "sign_face": {"rect": [B[104][0], B[104][1], 48, 32], "trim": False},  # "Signpost": the board, without its pole
    "mini_1": {"rect": B[108], "remap": PLUS_128},  # "Continue icon"
    "mini_2": {"rect": B[109], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[99], "remap": PLUS_128},  # "Normal ending"
    "end_pose_1": {"rect": B[105], "remap": PLUS_128},
    "end_pose_2": {"rect": B[11], "remap": PLUS_128},  # "Spring", arms up
    # "End sprite": the smaller of the two (50x89). The large one (120, 162x145) would take a lot of the
    # shared ending sheet's height; swap it in if there's room.
    "end_pose_3": {"rect": B[122], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((100, 101, 106, 102, 103, 107), 1)},
}

PALETTE = {  # Espio's own colours, in the extras' shared global palette slots 74+
    "74": "#6c0090", "75": "#9024b4", "76": "#b448d8", "77": "#d86cfc",  # purple scales, dark to light
    "78": "#6c2400", "79": "#b46c24", "80": "#fcb46c",  # muzzle and chest, dark to light
    "81": "#fcfcfc", "82": "#b4b4b4",  # white and light grey (gloves)
    "83": "#006c00", "84": "#48d800",  # green shoes and tail stripe
    "85": "#fcd800",  # gold horn and wrist bands
    "86": "#fcfc00",  # the "ESPIO" name tag
}
KEY_COLOURS = {  # near-exact matches go in Sonic's slots; the rest are Espio's own
    "#000000": 1, "#010101": 1, "#080000": 1, "#909090": 8, "#484848": 9,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (palette swaps, cameos, text) in the slot of its
    nearest key colour, so nothing is left to sheet2ani's guess."""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in Image.open(HERE / SHEET).convert("RGB").getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


COLOURS = all_colours()


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the ending poses: into "Spring", arms up
S3K_VICTORY = {"frames": f(105, 11)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra11",
           "credit": "Espio (The Chameleon In Sonic 1) by Akimaca; original sprites by SEGA / Sonic Team",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra11SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": SPIN, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra11_UI", "manifest": "Extra11_ui.json", "elements": ELEMENTS, "out": "build/Extra11_UI.gif"},
                     {"name": "Extra11_Ending", "manifest": "Extra11_ending.json", "elements": ENDING,
                      "out": "build/Extra11_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "espio.json"), ("Sonic2", "espio_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
