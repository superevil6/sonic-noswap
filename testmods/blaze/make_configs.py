#!/usr/bin/env python3
"""Writes Blaze's sheet2ani configs (blaze.json for Sonic 1, blaze_s2.json for Sonic 2).

Frames are the light-green boxes on 216879.png ("Blaze (Sonic 1-Style)" by Madz and Selphy Geumja; see
SOURCE.txt), numbered as detected: connected components of everything that isn't the dark #485617 sheet
background, rows left to right, top to bottom. The sheet labels its rows (IDLE, WAITING, WALKING...), and
the mapping below follows those labels.

Nothing is redrawn or resized: frames are only cut (the signpost face is cropped to the 48x32 board).
Blaze's own colours go in global palette slots 74-85, which all extras share, so she keeps her exact colours.

Output goes into the mod (mods/NoSwap), like the other extras.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import fire_dash  # noqa: E402
B = {  # box number -> [x, y, w, h]
    5: [7, 59, 33, 45], 6: [48, 59, 32, 45], 7: [84, 59, 32, 45], 8: [120, 59, 33, 45], 9: [157, 59, 33, 45],
    10: [288, 56, 29, 48], 11: [198, 64, 35, 40], 12: [241, 70, 39, 34],
    21: [7, 141, 29, 44], 22: [40, 139, 34, 44], 23: [78, 140, 31, 45], 24: [113, 141, 36, 44],
    25: [153, 139, 43, 44], 26: [200, 140, 39, 45], 27: [247, 144, 36, 41], 28: [287, 146, 37, 39],
    29: [328, 144, 43, 41], 30: [375, 146, 40, 39], 31: [423, 147, 40, 38], 32: [464, 147, 39, 38],
    33: [517, 163, 30, 27], 34: [548, 163, 30, 27], 35: [579, 163, 30, 27], 36: [610, 163, 30, 27],
    37: [641, 163, 30, 27], 38: [672, 163, 30, 27],
    43: [7, 222, 40, 46], 44: [51, 223, 39, 45], 45: [98, 228, 42, 38], 46: [144, 228, 40, 40],
    47: [360, 226, 31, 42], 48: [395, 225, 29, 43], 49: [428, 226, 31, 42], 50: [463, 225, 29, 43],
    51: [611, 226, 36, 42], 52: [651, 228, 36, 40], 53: [517, 230, 39, 38], 54: [560, 232, 43, 36],
    55: [192, 238, 30, 30], 56: [226, 238, 27, 30], 57: [257, 240, 30, 27], 58: [291, 238, 27, 30],
    59: [322, 239, 30, 27],
    66: [318, 298, 32, 50], 67: [354, 298, 32, 50], 68: [394, 294, 37, 54], 69: [268, 302, 42, 46],
    70: [439, 302, 37, 46], 71: [517, 311, 25, 44], 72: [546, 311, 23, 44], 73: [573, 311, 25, 44],
    74: [606, 310, 33, 45], 75: [643, 310, 33, 45], 76: [680, 310, 33, 45],
    77: [7, 320, 44, 28], 78: [55, 320, 47, 28], 79: [106, 321, 39, 27], 80: [153, 321, 51, 27],
    81: [208, 322, 52, 25],
    86: [364, 375, 48, 55], 87: [7, 385, 33, 45], 88: [44, 385, 35, 45], 89: [83, 385, 33, 45],
    90: [120, 389, 37, 41], 91: [161, 385, 37, 45], 92: [202, 385, 37, 45], 93: [243, 391, 32, 39],
    94: [517, 391, 42, 35], 95: [563, 393, 40, 33], 97: [420, 402, 19, 28], 98: [443, 402, 19, 28],
    99: [283, 414, 49, 16], 100: [340, 414, 16, 16], 103: [183, 464, 198, 199], 104: [43, 511, 80, 100],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "216879.png"

WALK = f(21, 22, 23, 24, 25, 26)  # "WALKING"
RUN = f(27, 28, 29, 30)  # "RUNNING": legs in a streak of flame colours
ROLL = f(55, 56, 57, 58, 59)  # "ROLL": the ball, then curled frames with streaks
SPIN = f(33, 34, 35, 36, 37, 38)  # "SPINDASH"
BALANCE = f(43, 44)

ANIMS = {
    "Stopped": {"frames": f(5)},  # "IDLE"
    "Waiting": {"frames": f(6, 7, 8, 9), "loop": 2},  # "WAITING": wags her finger
    "Looking Up": {"frames": f(11), "loop": 0},
    "Looking Down": {"frames": f(12), "loop": 0},  # "CROUCH"
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2},
    "Skidding": {"frames": f(31, 32)},
    "Super Peel Out": {"frames": f(94, 95), "rot": 2},  # "MAX SPEED"
    "Spin Dash": {"frames": SPIN},
    "Jumping": {"frames": ROLL, "anchor": "center"},
    "Bouncing": {"frames": f(10), "anchor": "center"},  # "SPRING"
    "Hurt": {"frames": f(45), "anchor": "center"},  # "HURT/SLIDE"
    "Dying": {"frames": f(68), "anchor": "center"},
    "Drowning": {"frames": f(70), "anchor": "center"},
    "Fan Rotate": {"frames": f(77, 78, 79), "anchor": "center"},  # "LABYRINTH SPIN"
    "Breathing": {"frames": f(69), "anchor": "center"},  # "BUBBLE"
    "Pushing": {"frames": f(47, 48, 49, 50)},
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(10), "anchor": "center"},  # no hanging art: the spring pose (arms up)
    "Clinging On": {"frames": f(80, 81), "anchor": "center"},  # "CLING"
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": f(45, 46), "anchor": "center"},  # "HURT/SLIDE"
    "Continue": {"frames": f(66, 67)},
    "Continue Up": {"frames": f(10), "loop": 0},
    "Super Transform": {"frames": f(5), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": f(45), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(74, 75, 76, 75), "loop": 0},  # "BLINK"
}

APPENDED = {
    # Burst Dash, an aimable jet_dash: the direction held when it starts picks one of three animations.
    # Straight ahead (slot 41): "MAX SPEED", a flat-out lunge trailing streaks.
    "41": {"name": "Burst Dash", "frames": f(94, 95), "anchor": "center", "speed": 120},
    # Optional follow-up hover (slot 42): the curled roll frames, spinning like a small tornado.
    "42": {"name": "Axel Tornado", "frames": f(56, 57, 58, 59), "anchor": "center", "speed": 120},
    # Up-diagonal (slot 45): "BURST-DASH", rising with her legs trailing behind and below.
    "45": {"name": "Burst Dash Up", "frames": f(51, 52), "anchor": "center", "speed": 120},
    # Down-diagonal (slot 46): the sheet has no dive pose, so it's the straight lunge with full rotation
    # (rot 1). The script tilts it 45 degrees nose-down by setting player.rotation during the dash.
    "46": {"name": "Burst Dash Down", "frames": f(94, 95), "anchor": "center", "speed": 120, "rot": 1},
}


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {
    "life_icon": {"rect": [283, 414, 16, 16], "trim": False},  # "LIFE COUNTER": her head
    "life_name": {"rect": [300, 414, 32, 7]},  # ...and her name tag
    "monitor_1up": {"rect": [340, 415, 16, 14], "trim": False},  # "1-UP"
    # "SIGNPOST": the 48x32 board with her face (ear tips above it cropped; the pole isn't needed)
    "sign_face": {"rect": [364, 382, 48, 32], "trim": False},
    "mini_1": {"rect": B[97], "remap": PLUS_128},  # "CONTINUE ICON", unscaled (19x28)
    "mini_2": {"rect": B[98], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[87], "remap": PLUS_128},
    "end_pose_1": {"rect": B[9], "remap": PLUS_128},  # finger up
    "end_pose_2": {"rect": B[68], "remap": PLUS_128},  # arms up
    # "ENDING POSE": the smaller of the two. The large one (103, 198x199) can't share a 256x256 sheet
    # with the rest of the ending art, so it's unused.
    "end_pose_3": {"rect": B[104], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((88, 89, 90, 91, 92, 93), 1)},
}

PALETTE = {  # Blaze's own colours, in the extras' shared global palette slots 74+
    "74": "#4b0070", "75": "#8808c8", "76": "#c838e8", "77": "#f878f8",  # purples, lilac highlight
    "78": "#fd0078", "79": "#800042", "80": "#400021",  # pink (gem, shoes), dark magentas
    "81": "#fcfcfc", "82": "#b4b4b4",  # white fur and gloves, light grey
    "83": "#fcfc00",  # gold (her collar and gem setting)
    "84": "#fcb490", "85": "#b46c48",  # tan streaks of her running flame
    "86": "#fc9000",  # orange: the Burst Dash flame (tools/fire_dash.py; its yellow is the gold above)
}
KEY_COLOURS = {  # near-exact matches go in Sonic's slots; the rest are Blaze's own
    "#000000": 1, "#909090": 8, "#484848": 9, "#e00000": 12,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (other characters, text) in the slot of its
    nearest key colour, so nothing is left to sheet2ani's guess."""
    from PIL import Image
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in Image.open(HERE / SHEET).convert("RGB").getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in ("#485617", "#c8e33e"):
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


COLOURS = all_colours()


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the ending poses: a finger up, then arms up
S3K_VICTORY = {"frames": f(9, 68)}


def config(game):
    ex = REPO / "extracted" / game
    # The Burst Dash is wrapped in S3&K's fire dash flame (the user's idea): straight, and turned 45
    # degrees for the up / down dashes
    fire = fire_dash.source_with_fire(HERE / SHEET, "#c8e33e", HERE / "build" / "source.png", {
        "41": ([B[94], B[95]], 0), "45": ([B[51], B[52]], 45), "46": ([B[94], B[95]], -45)})
    appended = {slot: dict(APPENDED[slot], frames=frames) for slot, frames in fire.items()}
    cfg = {"name": "Extra5",
           "credit": "Blaze (Sonic 1-Style) by Madz (ManiaMadnez) and Selphy Geumja, original sprites by SEGA/Sonic Team - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/216879/",
           "source": "build/source.png", "feet_y": 20, "background": ["#c8e33e", "#485617"], "palette": PALETTE,
           "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": dict(APPENDED, **appended)}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra5SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": ROLL, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra5_UI", "manifest": "Extra5_ui.json", "elements": ELEMENTS, "out": "build/Extra5_UI.gif"},
                     {"name": "Extra5_Ending", "manifest": "Extra5_ending.json", "elements": ENDING,
                      "out": "build/Extra5_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "blaze.json"), ("Sonic2", "blaze_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
