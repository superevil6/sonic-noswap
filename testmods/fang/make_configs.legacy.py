#!/usr/bin/env python3
"""Writes Fang's sheet2ani configs (fang.json for Sonic 1, fang_s2.json for Sonic 2).

Frames are Akimaca's boxes on 224261.png, numbered as detected (see the labels on the sheet)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
B = {  # box number -> [x, y, w, h]
    10: [413, 53, 27, 53], 11: [10, 65, 30, 41], 12: [51, 70, 34, 36], 13: [89, 70, 34, 36],
    14: [133, 69, 39, 37], 15: [181, 68, 39, 38], 16: [227, 68, 39, 38], 17: [272, 68, 39, 38],
    18: [317, 65, 31, 41], 29: [358, 82, 40, 24],
    38: [14, 130, 34, 35], 39: [54, 128, 38, 37], 40: [98, 130, 33, 35], 41: [138, 130, 34, 35],
    42: [177, 128, 40, 37], 43: [226, 130, 33, 35], 44: [268, 125, 47, 40], 45: [323, 125, 45, 40],
    46: [375, 125, 48, 40], 47: [431, 125, 44, 40],
    57: [14, 190, 29, 30], 58: [48, 190, 30, 30], 59: [83, 190, 29, 30], 60: [115, 190, 30, 30],
    61: [148, 190, 30, 30], 62: [189, 181, 45, 39], 63: [239, 182, 45, 38], 64: [295, 183, 37, 37],
    65: [337, 185, 38, 35], 66: [385, 184, 28, 36], 67: [417, 183, 28, 37], 68: [449, 184, 28, 36],
    69: [482, 183, 28, 37], 70: [111, 258, 38, 38], 71: [160, 248, 34, 48], 72: [200, 245, 34, 51],
    73: [15, 260, 40, 36], 74: [61, 260, 41, 36], 75: [244, 269, 67, 27], 76: [317, 269, 67, 27],
    77: [392, 267, 45, 29], 78: [446, 267, 24, 29], 79: [483, 267, 35, 29],
    85: [16, 318, 43, 43], 86: [64, 319, 39, 42],
    95: [28, 391, 34, 36], 96: [68, 392, 25, 35], 97: [109, 386, 28, 41], 98: [143, 386, 28, 41],
    99: [179, 385, 31, 42], 100: [219, 386, 30, 41], 101: [258, 386, 30, 41], 102: [296, 392, 25, 35],
    106: [161, 453, 171, 177], 118: [50, 503, 63, 80],
    109: [592, 499, 28, 27], 110: [630, 499, 28, 27], 111: [673, 499, 28, 27], 112: [714, 499, 29, 27],
    116: [1015, 486, 42, 41], 117: [1068, 486, 37, 41], 133: [694, 612, 41, 54],
    134: [1122, 617, 31, 49], 146: [1082, 632, 32, 34],
}
CORK = [[990, 444, 7, 7], [999, 444, 7, 7], [1008, 444, 7, 7]]  # the sheet's loose "Cork": three spin frames (the shot's art)
f = lambda *nums: [B[n] for n in nums]

WALK = f(38, 39, 40, 41, 42, 43)
ANIMS = {
    "Stopped": {"frames": f(11)},
    "Waiting": {"frames": f(12, 13, 14, 15, 16, 17), "loop": 2},
    "Looking Up": {"frames": f(18), "loop": 0},
    "Looking Down": {"frames": f(29), "loop": 0},
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": f(44, 45, 46, 47), "rot": 2},
    "Skidding": {"frames": f(62, 63)},
    "Super Peel Out": {"frames": f(44, 45, 46, 47), "rot": 2},
    "Spin Dash": {"frames": f(109, 110, 111, 112)},
    "Jumping": {"frames": f(57, 58, 59, 60, 61), "anchor": "center"},
    "Bouncing": {"frames": f(10), "anchor": "center"},
    "Hurt": {"frames": f(73), "anchor": "center"},
    "Dying": {"frames": f(71), "anchor": "center"},
    "Drowning": {"frames": f(72), "anchor": "center"},
    "Fan Rotate": {"frames": f(77, 78, 79, 78), "anchor": "center"},
    "Breathing": {"frames": f(70), "anchor": "center"},
    "Pushing": {"frames": f(66, 67, 68, 69)},
    "Flailing 1": {"frames": f(64, 65)},
    "Flailing 2": {"frames": f(64, 65)},
    "Hanging": {"frames": f(75, 76), "anchor": "center"},
    "Clinging On": {"frames": f(75, 76), "anchor": "center"},
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": f(74), "anchor": "center"},
    "Continue": {"frames": f(85, 86)},
    "Continue Up": {"frames": f(18), "loop": 0},
    "Super Transform": {"frames": f(11), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": f(64, 65)},
    "Grabbed": {"frames": f(73), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(12, 13), "loop": 0},
}


def shot(frames, anchor):
    """The cork gun's throw pose: aim, then fired (the gun kicked up). The cork itself is a real projectile
    (tools/abilities.py "shot": the sheet's loose "Cork" drawings, CORK); the game shows this animation's last frame,
    the fired gun, while he shoots. None of these frames has a cork drawn in it."""
    return {"frames": f(*frames), "anchor": anchor, "speed": 80}


APPENDED = {
    "41": {"name": "Pogo", "frames": f(146, 146, 134), "loop": 2, "speed": 60},
    "43": dict(shot((116, 117), "feet"), name="Popgun"),  # "Holding gun + Shoot": aim, fired
    "44": dict(shot((133, 133), "center"), name="Popgun Air"),  # "Jump w. gun" (the sheet has no air shoot frame)
}

ELEMENTS = {  # HUD, monitor, signpost and continue art
    "life_icon": {"rect": [119, 328, 16, 16], "trim": False},
    "life_name": {"rect": [136, 328, 27, 9]},
    "monitor_1up": {"rect": [119, 329, 16, 14], "trim": False, "remap": {str(i): 128 + i for i in range(2, 6)}},
    "sign_face": {"rect": [173, 312, 48, 32], "trim": False, "remap": {str(i): 128 + i for i in range(2, 6)}},
    "mini_1": {"rect": [233, 336, 24, 25], "remap": {str(i): 128 + i for i in range(1, 16)}},
    "mini_2": {"rect": [261, 336, 24, 25], "remap": {str(i): 128 + i for i in range(1, 16)}},
}
ALL_128 = {str(i): 128 + i for i in range(1, 16)}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[95], "remap": ALL_128},
    "end_pose_1": {"rect": B[96], "remap": ALL_128},
    "end_pose_2": {"rect": B[118], "remap": ALL_128},
    "end_pose_3": {"rect": B[106], "remap": ALL_128},
    **{f"good_{n}": {"rect": B[96 + n], "remap": ALL_128} for n in range(1, 7)},
}

COMMON = {
    "credit": "Fang (Sonic 1-Style) by Akimaca - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/224261/",
    "source": "224261.png",
    "feet_y": 20,
    "background": ["#a2c86e", "#598818"],
    "palette": {"74": "#6c0090", "75": "#9024b4", "76": "#b448d8", "77": "#d86cfc",
                "78": "#6c2400", "79": "#b44800", "80": "#fc6c00"},
}
COLOURS = {  # neutrals share Sonic's slots; Fang's own colours use slots 74-80
    "#000000": 1, "#010101": 1, "#242490": 2, "#fcfcfc": 6, "#b4b4b4": 7, "#909090": 8, "#484848": 9,
    "#fc0000": 12, "#fcfc00": 15,
    "#6c0090": 74, "#9024b4": 75, "#b448d8": 76, "#d86cfc": 77, "#6c2400": 78, "#b44800": 79, "#fc6c00": 80,
}


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the good ending: standing, then arms out
S3K_VICTORY = {"frames": f(97, 101)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = dict(COMMON, name="Extra2", colours=COLOURS,
               template_ani=str(ex / "Data/Animations/Sonic.ani"),
               template_sheet=str(ex / "Data/Sprites/Players/Sonic1.gif"),
               out_dir=str(REPO / "mods/NoSwap" / (game + "u")),
               animations=dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
               appended_animations=APPENDED)
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra2SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": f(57, 58, 59, 60), "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra2_UI", "manifest": "Extra2_ui.json", "elements": ELEMENTS, "out": "build/Extra2_UI.gif"},
                     {"name": "Extra2_Ending", "manifest": "Extra2_ending.json", "elements": ENDING,
                      "out": "build/Extra2_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "fang.json"), ("Sonic2", "fang_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
