#!/usr/bin/env python3
"""Writes Ray's sheet2ani configs (ray.json for Sonic 1, ray_s2.json for Sonic 2).

Frames are the dark boxes on Ray.png ("Ray, The Flying Squirrel In Sonic 1" by Akimaca; see SOURCE.txt),
numbered as detected: connected components of everything that isn't the #76d1d1 sheet background, rows left
to right, top to bottom. The sheet labels its rows (Idle, Waiting, Walking...), and the mapping follows them.

The sheet has his own spin (curled frames plus a ball) and Spindash, so tools/sonic_ball.py isn't needed.
Nothing is redrawn or resized: frames are cut, and the life icon, name tag and signpost are crops of the
sheet's own HUD art. His own colours go in the extras' shared palette slots 74-85.

"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
B = {  # box number -> [x, y, w, h]
    8: [289, 52, 21, 44], 10: [9, 59, 33, 37], 11: [139, 59, 22, 37], 12: [167, 61, 24, 35], 13: [196, 61, 25, 35],
    14: [226, 60, 22, 36], 15: [253, 65, 31, 31], 16: [54, 68, 20, 19], 17: [77, 69, 23, 18], 18: [103, 71, 24, 16],
    25: [44, 120, 42, 38], 26: [178, 120, 42, 38], 27: [328, 120, 46, 38], 28: [381, 113, 31, 45], 29: [4, 122, 33, 36],
    30: [92, 122, 37, 36], 31: [136, 122, 35, 36], 32: [228, 122, 42, 36], 33: [277, 121, 46, 37], 37: [4, 177, 47, 33],
    38: [57, 176, 48, 34], 39: [112, 177, 47, 33], 40: [166, 176, 48, 34], 41: [222, 176, 42, 34], 42: [269, 173, 36, 37],
    43: [314, 177, 47, 33], 44: [366, 178, 46, 32], 46: [481, 186, 36, 35], 47: [522, 186, 36, 35], 48: [566, 191, 30, 30],
    54: [175, 226, 31, 33], 55: [211, 225, 31, 34], 56: [247, 226, 31, 33], 57: [282, 225, 31, 34], 60: [4, 229, 30, 30],
    61: [37, 229, 30, 30], 62: [70, 229, 30, 30], 63: [103, 229, 30, 30], 64: [136, 229, 30, 30], 65: [322, 235, 49, 24],
    66: [376, 235, 49, 24], 67: [498, 239, 28, 27], 68: [536, 239, 28, 27], 69: [576, 239, 28, 27], 70: [614, 239, 28, 27],
    71: [657, 239, 28, 27], 72: [698, 239, 29, 27], 77: [106, 281, 31, 55], 78: [145, 281, 31, 55], 79: [184, 281, 31, 55],
    80: [4, 290, 42, 46], 81: [50, 295, 42, 41], 82: [376, 302, 40, 34], 83: [421, 308, 42, 28], 84: [469, 301, 31, 35],
    86: [228, 310, 45, 26], 87: [283, 310, 30, 26], 88: [319, 310, 42, 26], 92: [347, 351, 48, 48], 93: [13, 361, 21, 37],
    94: [42, 364, 37, 34], 95: [98, 361, 29, 37], 96: [131, 361, 31, 37], 97: [169, 361, 34, 37], 98: [209, 361, 34, 37],
    99: [249, 361, 34, 37], 100: [291, 364, 37, 34], 101: [443, 377, 20, 22], 102: [465, 377, 20, 22], 104: [403, 383, 35, 16],
    110: [113, 430, 102, 141], 114: [13, 470, 59, 73],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "Ray.png"

WALK = f(29, 25, 30, 31, 26, 32)  # "Walking"
RUN = f(37, 38, 39, 40)  # "Running"
SPIN = f(60, 61, 62, 63, 64)  # "Spin": curled frames, then a ball (Sonic 1's jump pattern)
SPINDASH = f(67, 68, 69, 70, 71, 72)  # "Spindash"
BALANCE = f(41, 42)
HURT_SLIDE = f(43, 44)

ANIMS = {
    "Stopped": {"frames": f(10)},  # "Idle", tail down
    "Waiting": {"frames": f(12, 13), "loop": 0},
    "Looking Up": {"frames": f(14), "loop": 0},
    "Looking Down": {"frames": f(15), "loop": 0},  # "Crouch"
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2},
    "Skidding": {"frames": f(33, 27)},
    "Super Peel Out": {"frames": RUN, "rot": 2},  # no peel-out art
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": {"frames": SPIN, "anchor": "center"},
    "Bouncing": {"frames": f(8), "anchor": "center"},  # "Spring"
    "Hurt": {"frames": f(43), "anchor": "center"},  # "Hurt/Slide"
    "Dying": {"frames": f(80), "anchor": "center"},  # "Death"
    "Drowning": {"frames": f(81), "anchor": "center"},  # "Drown"
    "Fan Rotate": {"frames": f(86, 87, 88), "anchor": "center"},  # "Labyrinth spin"
    "Breathing": {"frames": f(28), "anchor": "center"},  # "Bubble"
    "Pushing": {"frames": f(54, 55, 56, 57)},
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(8), "anchor": "center"},  # no hanging art: the spring pose (arms up)
    "Clinging On": {"frames": f(65, 66), "anchor": "center"},  # "Cling"
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": HURT_SLIDE, "anchor": "center"},
    "Continue": {"frames": f(77, 78, 79)},
    "Continue Up": {"frames": f(8), "loop": 0},
    "Super Transform": {"frames": f(10), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": f(43), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(46, 47), "loop": 0},  # "Victory": thumbs up
}

APPENDED = {
    # The flying-squirrel glide (hold jump in mid-air): "Glide", one pose per direction of the swoop
    "42": {"name": "Glide", "frames": f(83), "anchor": "center"},  # level
    # slots 47 / 48, not 45 / 46: those count as attacks (Blaze's dash), and the glide isn't one
    "47": {"name": "Glide Up", "frames": f(82), "anchor": "center"},  # pulling up, arms forward
    "48": {"name": "Glide Down", "frames": f(84), "anchor": "center"},  # diving
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": [403, 383, 16, 16], "trim": False},  # "Life counter": his head
    "life_name": {"rect": [420, 384, 18, 7]},  # ...and "RAY"
    "monitor_1up": {"rect": [403, 384, 16, 14], "trim": False},  # no separate 1-up: the icon's middle rows
    "sign_face": {"rect": [347, 351, 48, 32], "trim": False},  # "Signpost": the board, without its pole
    "mini_1": {"rect": B[101], "remap": PLUS_128},  # "Continue icon" (20x22)
    "mini_2": {"rect": B[102], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[93], "remap": PLUS_128},  # "Normal ending"
    "end_pose_1": {"rect": B[94], "remap": PLUS_128},
    "end_pose_2": {"rect": B[46], "remap": PLUS_128},  # "Victory", thumbs up
    # "End sprite": the smaller of the two (59x73). The large one (110, 102x141) would take a lot of the
    # shared ending sheet's height; swap it in if there's room.
    "end_pose_3": {"rect": B[114], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((95, 96, 97, 98, 99, 100), 1)},
}

PALETTE = {  # Ray's own colours, in the extras' shared global palette slots 74+
    "74": "#6c2400", "75": "#b44800", "76": "#b46c00", "77": "#d86c00", "78": "#d89000",  # fur, dark to light
    "79": "#fcb400", "80": "#fcd800", "81": "#d86c24",  # fur highlights, muzzle
    "82": "#fc0000",  # shoes (and the signpost's red background)
    "83": "#fcfcfc", "84": "#b4b4b4",  # white and light grey (gloves, shoe straps)
    "85": "#fcfc00",  # the "RAY" name tag
}
KEY_COLOURS = {  # near-exact matches go in Sonic's slots; the rest are Ray's own
    "#000000": 1, "#010101": 1, "#909090": 8, "#484848": 9, "#900000": 13, "#480000": 14,
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


BACKGROUND = ["#76d1d1", "#4ca1b2"]  # the sheet, and the boxes the frames sit in
COLOURS = all_colours()


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the sheet's "Victory": the thumbs up
S3K_VICTORY = {"frames": f(46, 47)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra8",
           "credit": "Ray (The Flying Squirrel In Sonic 1) by Akimaca; original sprites by SEGA / Sonic Team - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/227243/",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra8SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": SPIN, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra8_UI", "manifest": "Extra8_ui.json", "elements": ELEMENTS, "out": "build/Extra8_UI.gif"},
                     {"name": "Extra8_Ending", "manifest": "Extra8_ending.json", "elements": ENDING,
                      "out": "build/Extra8_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "ray.json"), ("Sonic2", "ray_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
