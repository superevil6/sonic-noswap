#!/usr/bin/env python3
"""Writes Charmy's sheet2ani configs (charmy.json for Sonic 1, charmy_s2.json for Sonic 2).

Charmy flies like Tails (the games' own Tails flight code), so his .ani follows TAILS' animation list
(extracted/<game>/Data/Animations/Tails.ani is the template), not Sonic's: Flying, Flying Tired, Swimming and
Swimming Tired (slots 24-27), and the carrying/lift animations after Sonic's list (39 Fly Lift Down,
40 Fly Lift Up, 41 Fly Lift Tired, 42 Swim Lift). Tails' two tails are NOT in the .ani: the Tails Object
player type draws them from its own sprite frames, so Charmy (a plain Player Object) never shows them.
Charmy's wings are drawn into every frame, so the flight poses are his "RUN/FLYING" frames.

Tails' Walking, Running and Super Peel Out use rotation style 3 (pre-drawn angled frames); Charmy has no
angled frames, so those use Sonic's free rotation (rot 2) instead.

Frames are the boxes on 278731.png ("Charmy in Sonic 1" by Casteor573; see SOURCE.txt), numbered as
detected: connected components of everything that isn't the #b4d890 sheet background, rows left to right,
top to bottom. The mapping follows the sheet's row labels. Nothing is redrawn or resized.

"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
B = {  # box number -> [x, y, w, h]
    10: [9, 72, 16, 24], 12: [37, 72, 16, 24], 13: [54, 72, 16, 24], 14: [79, 70, 16, 26], 15: [133, 72, 17, 24], 16: [151, 71, 17, 25],
    17: [170, 72, 17, 24], 18: [188, 72, 15, 24], 19: [204, 71, 16, 25], 20: [221, 72, 14, 24], 22: [248, 72, 19, 24], 23: [268, 71, 19, 25],
    25: [103, 79, 19, 17], 27: [298, 81, 27, 15], 28: [326, 81, 27, 15], 29: [367, 77, 20, 19], 30: [388, 76, 20, 20], 33: [129, 117, 19, 24],
    34: [149, 118, 19, 23], 36: [193, 117, 16, 24], 37: [210, 117, 17, 24], 38: [228, 117, 16, 24], 39: [245, 117, 17, 24], 40: [274, 114, 16, 27],
    42: [308, 117, 17, 24], 43: [326, 115, 15, 26], 44: [355, 117, 18, 24], 45: [383, 117, 18, 24], 46: [10, 124, 16, 17], 47: [27, 121, 16, 20],
    48: [44, 125, 20, 16], 49: [65, 121, 16, 20], 50: [82, 125, 20, 16], 52: [10, 167, 16, 18], 53: [27, 167, 23, 18], 54: [51, 167, 19, 18],
    55: [81, 161, 18, 24], 56: [112, 161, 20, 24], 57: [139, 166, 22, 19], 58: [246, 161, 16, 24], 59: [263, 161, 16, 24], 60: [280, 161, 16, 24],
    61: [297, 161, 16, 24], 62: [314, 161, 16, 24], 63: [331, 163, 18, 22], 64: [351, 160, 25, 41], 65: [377, 160, 76, 100], 66: [182, 168, 24, 17],
    67: [207, 168, 26, 17], 77: [206, 268, 48, 31], 81: [255, 283, 16, 16],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "278731.png"
BACKGROUND = ["#b4d890", "#6c9024"]  # the sheet, and the boxes the frames sit in

WALK = f(15, 16, 17, 18, 19, 20)  # "WALKIN'"
FLY = f(22, 23)  # "RUN/FLYING": wings buzzing
DASH = f(27, 28)  # "DASH": flat out, with a speed trail
ROLL = f(47, 48, 49, 50, 46)  # "ROLL": curled frames, then the ball
BALANCE = f(42, 43)
TIRED = f(55, 22)  # no tired-flight art: "FALLING" (arms up) alternating with a flap

ANIMS = {
    "Stopped": {"frames": f(10)},  # "IDLE"
    "Waiting": {"frames": f(12, 13), "loop": 0},  # "BORED"
    "Bored!": {"frames": f(12, 13), "loop": 0},
    "Looking Up": {"frames": f(14), "loop": 0},  # "UP"
    "Looking Down": {"frames": f(25), "loop": 0},  # "DOWN"
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": FLY, "rot": 2},  # "RUN/FLYING": he runs by flying low
    "Skidding": {"frames": f(56)},  # "SKID"
    "Super Peel Out": {"frames": DASH, "rot": 2},  # "DASH" (Tails keeps this as his fastest run)
    "Spin Dash": {"frames": f(29, 30)},  # "CHARGE"
    "Jumping": {"frames": ROLL, "anchor": "center"},
    "Bouncing": {"frames": f(40), "anchor": "center"},  # "SPRING"
    "Hurt": {"frames": f(33), "anchor": "center"},  # "HURT/WATERSLIDE"
    "Dying": {"frames": f(44), "anchor": "center"},  # "DEATH"
    "Drowning": {"frames": f(45), "anchor": "center"},  # "DROWN"
    "Fan Rotate": {"frames": f(52, 53, 54), "anchor": "center"},  # "FAN ROTATE"
    "Breathing": {"frames": f(45), "anchor": "center"},  # no bubble art: the drown pose (mouth open)
    "Pushing": {"frames": f(36, 37, 38, 39)},  # "PUSHIN"
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(40), "anchor": "center"},  # Tails has none; the spring pose, arms up, just in case
    "Clinging On": {"frames": f(66, 67), "anchor": "center"},  # "CLINGING"
    "Corkscrew H": {"frames": WALK},  # Sonic 1 (Tails has none)
    "Twirl H": {"frames": WALK, "rot": 2},  # Sonic 2
    "Water Slide": {"frames": f(33, 34), "anchor": "center"},  # "HURT/WATERSLIDE"
    "Continue": {"frames": f(57)},
    "Continue Up": {"frames": f(14), "loop": 0},
    "Super Transform": {"frames": f(10), "loop": 0},
    # Tails' flight set
    "Flying": {"frames": FLY, "anchor": "center"},
    "Flying Tired": {"frames": TIRED, "anchor": "center"},
    "Swimming": {"frames": FLY, "anchor": "center"},  # no swimming art: he flies through the water
    "Swimming Tired": {"frames": TIRED, "anchor": "center"},
    "Fly Lift Down": {"frames": FLY, "anchor": "center"},  # carrying a partner (never happens: extras play alone)
    "Fly Lift Up": {"frames": FLY, "anchor": "center"},
    "Fly Lift Tired": {"frames": TIRED, "anchor": "center"},  # S1/S2's slot 41: the Stinger replaces it (APPENDED)
    "Swim Lift": {"frames": FLY, "anchor": "center"},
}
# Sonic 3 & Knuckles, by its (Mania's) names (build_s3k_art.py "s3k_animations"): Tails' Fly / Fly Lift poses are 1
# frame (his flapping is his separate tails object), which froze Charmy's wings; his own 2 buzzing frames ("own_count")
S3K_ANIMS = {n: dict(ANIMS["Flying"], own_count=True) for n in ("Fly", "Fly Lift", "Fly Lift Down")}
S2_ONLY = {
    # Sonic 2's slot 20 is Tails' (empty) "Sliding" but Sonic's "Flailing 3": fill it with his balance
    # frames so Sonic's balance code can't show an empty animation
    "Sliding": {"frames": BALANCE},
    "Grabbed": {"frames": f(33), "anchor": "center"},
}

# Stinger (Y in mid-air; abilities.py aim_dash with aim_dash_y): the "DASH" frames, flat out with speed lines,
# for all three directions. Slot 41 is Tails' Fly Lift Tired in S1/S2, which a solo player never shows.
APPENDED = {
    "41": {"name": "Stinger", "frames": DASH, "anchor": "center", "speed": 120},
    "45": {"name": "Stinger Up", "frames": DASH, "anchor": "center", "speed": 120},
    "46": {"name": "Stinger Down", "frames": DASH, "anchor": "center", "speed": 120},
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
ELEMENTS = {
    "life_icon": {"rect": B[81], "trim": False},  # "EXTRAS": his head
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("CHARMY")},  # the sheet has no name tag
    "monitor_1up": {"rect": [B[81][0], B[81][1] + 1, 16, 14], "trim": False},  # the icon's middle rows
    "sign_face": {"rect": [B[77][0], B[77][1], 48, 32], "trim": False},  # "EXTRAS": his signpost board
    "mini_1": {"rect": B[10], "remap": PLUS_128},  # no continue icons: his idle frames (16x24, already mini-sized)
    "mini_2": {"rect": B[12], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[58], "remap": PLUS_128},
    "end_pose_1": {"rect": B[63], "remap": PLUS_128},  # arms out
    "end_pose_2": {"rect": B[64], "remap": PLUS_128},  # the medium ending pose (25x41)
    "end_pose_3": {"rect": B[65], "remap": PLUS_128},  # the large one (76x100)
    # "ENDING": the six small frames in the sheet's order
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((58, 59, 60, 61, 62, 63), 1)},
}

PALETTE = {  # Charmy's own colours, in the extras' shared global palette slots 74+
    "74": "#ffffff", "75": "#b4b4b4",  # white, light grey (gloves, goggles)
    "76": "#ffb490", "77": "#b46c48",  # muzzle
    "78": "#ffff00", "79": "#909000",  # yellow stripes and antennae; the signpost's olive
    "80": "#ff0000",  # red (goggles, shoes)
    "81": "#d86c00", "82": "#904800",  # orange-brown helmet
    "83": "#4848b4",  # wings (lighter blue; the darker #242490 is Sonic's slot 2)
}
KEY_COLOURS = {  # near-exact matches go in Sonic's slots; the rest are Charmy's own
    "#000000": 1, "#242490": 2, "#fcfc00": 15, "#909090": 8, "#484848": 9, "#900000": 13, "#480000": 14,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (palette swaps, sketches, text) in the slot of its
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
# the last frame, the pose held or looped): the ending: into arms out
S3K_VICTORY = {"frames": f(62, 63)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra10",
           "credit": "Charmy in Sonic 1 by Casteor573 - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/278731/",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Tails.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra10SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": ROLL, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra10_UI", "manifest": "Extra10_ui.json", "elements": ELEMENTS, "out": "build/Extra10_UI.gif"},
                     {"name": "Extra10_Ending", "manifest": "Extra10_ending.json", "elements": ENDING,
                      "out": "build/Extra10_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
        cfg["s3k_animations"] = S3K_ANIMS
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "charmy.json"), ("Sonic2", "charmy_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
