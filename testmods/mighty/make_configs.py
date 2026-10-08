#!/usr/bin/env python3
"""Writes Mighty's sheet2ani configs (mighty.json for Sonic 1, mighty_s2.json for Sonic 2).

Frames are the dark boxes on Mighty.png ("Mighty, The Armadillo In Sonic 1" by Akimaca; see SOURCE.txt),
numbered as detected: connected components of everything that isn't the #7acab9 sheet background, rows left
to right, top to bottom. The sheet labels its rows (Idle, Waiting, Walking...), and the mapping follows them.

The sheet has his own spin (curled frames plus a ball) and Spindash, so tools/sonic_ball.py isn't needed.
Nothing is redrawn or resized: frames are cut, and the life icon, name tag and signpost are crops of the
sheet's own HUD art. His own colours go in the extras' shared palette slots 74-84.

"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
B = {  # box number -> [x, y, w, h]
    9: [174, 56, 21, 51], 10: [8, 66, 25, 41], 11: [39, 66, 25, 41], 12: [68, 66, 25, 41], 13: [98, 65, 26, 42],
    19: [130, 83, 36, 24], 21: [7, 126, 31, 37], 22: [43, 124, 38, 39], 23: [88, 126, 35, 37],
    24: [129, 126, 31, 37], 25: [166, 124, 43, 39], 26: [216, 126, 35, 37], 27: [263, 126, 39, 37],
    28: [312, 123, 39, 40], 29: [362, 124, 39, 39],
    32: [8, 183, 42, 35], 33: [55, 182, 42, 36], 34: [101, 183, 41, 35], 35: [148, 182, 42, 36],
    36: [200, 180, 30, 38], 37: [239, 181, 40, 37], 38: [288, 181, 47, 37], 39: [341, 180, 46, 38],
    45: [316, 233, 37, 50], 48: [207, 243, 22, 40], 49: [237, 243, 22, 40], 50: [14, 253, 30, 30],
    51: [51, 253, 30, 30], 52: [88, 253, 30, 30], 53: [127, 253, 30, 30], 54: [164, 253, 30, 30],
    55: [364, 252, 26, 31], 56: [266, 261, 40, 22],
    60: [531, 285, 28, 27], 61: [569, 285, 28, 27], 62: [609, 285, 28, 27], 63: [647, 285, 28, 27],
    64: [690, 285, 28, 27], 65: [731, 285, 29, 27],
    66: [10, 300, 32, 36], 67: [50, 299, 30, 37], 68: [87, 300, 31, 36], 69: [126, 299, 30, 37],
    70: [167, 309, 54, 27], 71: [224, 309, 54, 27], 72: [293, 312, 45, 24], 73: [343, 312, 36, 24],
    74: [383, 312, 36, 24],
    79: [6, 353, 42, 43], 80: [54, 352, 42, 44], 81: [258, 348, 48, 48],
    83: [106, 357, 43, 39], 84: [153, 357, 43, 39], 85: [200, 357, 43, 39],
    87: [376, 370, 17, 26], 88: [397, 370, 17, 26], 94: [312, 380, 57, 16],
    97: [12, 413, 25, 41], 98: [79, 413, 23, 41], 99: [105, 413, 25, 41], 100: [134, 412, 30, 42],
    101: [168, 413, 35, 41], 102: [207, 413, 35, 41], 105: [42, 421, 28, 33], 106: [247, 421, 28, 33],
    118: [135, 487, 129, 191], 129: [32, 545, 71, 88],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "Mighty.png"

WALK = f(21, 22, 23, 24, 25, 26)  # "Walking"
RUN = f(32, 33, 34, 35)  # "Running"
SPIN = f(50, 51, 52, 53, 54)  # "Spin": curled frames, then his shell as a ball (Sonic 1's jump pattern)
SPINDASH = f(60, 61, 62, 63, 64, 65)  # "Spindash"
BALANCE = f(36, 37)
HURT_SLIDE = f(38, 39)

ANIMS = {
    "Stopped": {"frames": f(10)},  # "Idle"
    "Waiting": {"frames": f(11, 12), "loop": 0},
    "Looking Up": {"frames": f(13), "loop": 0},
    "Looking Down": {"frames": f(19), "loop": 0},  # "Crouch"
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2},
    "Skidding": {"frames": f(28, 29)},
    "Super Peel Out": {"frames": RUN, "rot": 2},  # no peel-out art
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": {"frames": SPIN, "anchor": "center"},
    "Bouncing": {"frames": f(9), "anchor": "center"},  # "Spring"
    "Hurt": {"frames": f(38), "anchor": "center"},  # "Hurt/Slide"
    "Dying": {"frames": f(79), "anchor": "center"},  # "Death"
    "Drowning": {"frames": f(80), "anchor": "center"},  # "Drown"
    "Fan Rotate": {"frames": f(72, 73, 74), "anchor": "center"},  # "Labyrinth spin"
    "Breathing": {"frames": f(27), "anchor": "center"},  # "Bubble"
    "Pushing": {"frames": f(66, 67, 68, 69)},
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(9), "anchor": "center"},  # no hanging art: the spring pose (arms up)
    "Clinging On": {"frames": f(70, 71), "anchor": "center"},  # "Cling"
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": HURT_SLIDE, "anchor": "center"},
    "Continue": {"frames": f(83, 84, 85)},
    "Continue Up": {"frames": f(9), "loop": 0},
    "Super Transform": {"frames": f(10), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": f(38), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(11, 12), "loop": 0},
}

APPENDED = {
    # Hammer Drop (jump in mid-air, attack slot 41): "Hammer drop", his shell stretched as he plunges
    "41": {"name": "Hammer Drop", "frames": f(48, 49), "anchor": "center", "speed": 120},
    # the landing (slot 45): the shell squashed flat on impact, then "Uncurl" as he bounces back up
    "45": {"name": "Hammer Drop Land", "frames": f(56, 56, 45), "anchor": "feet", "speed": 60},
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": [312, 380, 16, 16], "trim": False},  # "Life counter": his head
    "life_name": {"rect": [329, 381, 40, 7]},  # ...and "MIGHTY"
    "monitor_1up": {"rect": [312, 381, 16, 14], "trim": False},  # no separate 1-up: the icon's middle rows
    "sign_face": {"rect": [258, 348, 48, 32], "trim": False},  # "Signpost": the board, without its pole
    "mini_1": {"rect": B[87], "remap": PLUS_128},  # "Continue icon" (17x26)
    "mini_2": {"rect": B[88], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[97], "remap": PLUS_128},  # "Normal ending"
    "end_pose_1": {"rect": B[105], "remap": PLUS_128},
    "end_pose_2": {"rect": B[45], "remap": PLUS_128},  # "Uncurl", arms flung out
    # "End sprite": the smaller of the two (71x88). The large one (118, 129x191) would take a lot of the
    # shared ending sheet's height; swap it in if there's room.
    "end_pose_3": {"rect": B[129], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((98, 99, 100, 101, 102, 106), 1)},
}

PALETTE = {  # Mighty's own colours, in the extras' shared global palette slots 74+
    "74": "#b42400", "75": "#d84800", "76": "#fc6c00", "77": "#6c0000",  # his shell, dark to light, and its shadow
    "78": "#fc0000",  # shoes
    "79": "#b46c24", "80": "#fcb46c",  # muzzle and arms
    "81": "#fcfcfc", "82": "#b4b4b4",  # white and light grey (gloves, shoe straps)
    "83": "#48fcb4",  # the signpost's mint background
    "84": "#fcfc00",  # the "MIGHTY" name tag
}
KEY_COLOURS = {  # near-exact matches go in Sonic's slots; the rest are Mighty's own
    "#000000": 1, "#080000": 1, "#909090": 8, "#484848": 9, "#900000": 13, "#480000": 14,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (palette swaps, sketches, text) in the slot of its
    nearest key colour, so nothing is left to sheet2ani's guess."""
    from PIL import Image
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in Image.open(HERE / SHEET).convert("RGB").getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


BACKGROUND = ["#7acab9", "#246d5e"]  # the sheet, and the boxes the frames sit in
COLOURS = all_colours()


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the ending poses: into "Uncurl", arms flung out
S3K_VICTORY = {"frames": f(105, 45)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra7",
           "credit": "Mighty (The Armadillo In Sonic 1) by Akimaca; original sprites by SEGA / Sonic Team - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/239838/",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra7SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": SPIN, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra7_UI", "manifest": "Extra7_ui.json", "elements": ELEMENTS, "out": "build/Extra7_UI.gif"},
                     {"name": "Extra7_Ending", "manifest": "Extra7_ending.json", "elements": ENDING,
                      "out": "build/Extra7_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "mighty.json"), ("Sonic2", "mighty_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
