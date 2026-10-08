#!/usr/bin/env python3
"""Writes Silver's sheet2ani configs (silver.json for Sonic 1, silver_s2.json for Sonic 2).

Frames are boxes on 111917.png ("Silver", sheet by Gardow and others; see SOURCE.txt), numbered as detected:
connected components of everything that isn't the #bfffbf background, rows left to right, top to bottom.
Boxes 67 and 68 each held several touching frames and are split below (67 -> 67.0-67.6, 68 -> 68.0-68.1).

The sheet is mostly standing and psychic poses: it has no spin ball, spin dash, push, skid, balance, spring
or hurt frames, so those animations borrow the nearest poses (see the comments). Nothing is resized or
redrawn: frames are cut, the life icon and signpost head are crops, and the "SILVER" name tag is drawn
from scratch in the HUD style. Silver's own colours go in the extras' shared palette slots 74-91.

"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
import sonic_ball  # noqa: E402
from sign_face import board_face  # noqa: E402
B = {  # box number -> [x, y, w, h]
    7: [2, 35, 27, 44], 24: [637, 45, 35, 49], 27: [4, 116, 23, 44],
    28: [32, 116, 26, 44], 29: [64, 116, 27, 44], 34: [252, 117, 25, 43], 35: [285, 116, 25, 44],
    36: [319, 116, 27, 44], 37: [352, 116, 26, 44],
    38: [392, 115, 24, 43], 39: [423, 113, 24, 45], 40: [452, 113, 39, 45], 41: [496, 115, 37, 43],
    42: [542, 115, 26, 43], 43: [571, 113, 28, 45], 44: [604, 113, 37, 45], 45: [647, 115, 37, 43],
    46: [6, 168, 28, 44], 47: [45, 168, 32, 44], 48: [81, 168, 28, 44], 49: [116, 168, 28, 44],
    52: [223, 168, 35, 44], 53: [264, 168, 29, 44], 54: [305, 168, 29, 44], 55: [346, 168, 28, 44],
    58: [464, 172, 32, 40], 59: [504, 171, 33, 41],
    60: [546, 168, 31, 44], 61: [587, 168, 31, 44], 62: [621, 168, 32, 44], 63: [655, 168, 33, 44],
    64: [689, 168, 33, 44], 65: [723, 168, 31, 44],
    # 67: Silver inside a psychic sphere, seven frames in a row (cyan rim, teal, cyan, cyan, teal, white, cyan)
    **{67 + k / 10: [54 + 56 * k, 225, 55, 47] for k in range(7)},
    68.0: [450, 222, 57, 50], 68.1: [509, 222, 57, 50],  # floating inside rings of light
    69: [571, 222, 34, 50], 73: [15, 291, 34, 49], 74: [55, 294, 34, 46], 75: [104, 291, 34, 49],
    76: [144, 294, 34, 46], 77: [184, 290, 35, 49], 78: [228, 293, 35, 46],
    83: [434, 303, 34, 37], 84: [476, 298, 33, 42], 86: [567, 302, 30, 38], 87: [607, 294, 40, 46],
    89: [705, 295, 35, 40], 107: [313, 437, 28, 44], 110: [427, 437, 31, 44],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "111917.png"

WALK = f(38, 39, 40, 41, 42, 43, 44, 45)  # an 8-frame walk into long strides
RUN = f(40, 41, 44, 45)  # the long strides (Super Peel Out)
RUN_FULL = f(40, 41, 42, 43, 44, 45, 38, 39)  # "Running": the whole walk cycle from a stride (the strides and
# their landings alone looked like the same foot forward every step)
SPHERE = f(67.0, 67.2, 67.3, 67.6)  # the four cyan-rimmed spheres (the teal and white ones flash too hard)
FLOAT = f(73, 74, 75, 76, 77, 78)  # levitating, legs dangling

ANIMS = {
    "Stopped": {"frames": f(7)},
    "Waiting": {"frames": f(46, 47, 48), "loop": 1},  # talking with his hands
    "Looking Up": {"frames": f(84), "loop": 0},
    "Looking Down": {"frames": f(86), "loop": 0},  # crouched
    "Walking": {"frames": WALK, "rot": 2, "align": True},  # frames lined up: no sideways jitter
    "Running": {"frames": RUN_FULL, "rot": 2, "align": True},  # frames lined up: no sideways jitter
    "Skidding": {"frames": f(83)},  # no skid art: leaning back low
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},  # no peel-out art
    "Spin Dash": {"frames": SPHERE},  # replaced in config() by Sonic's recoloured ball
    "Jumping": {"frames": SPHERE, "anchor": "center"},  # (same)
    "Bouncing": {"frames": f(24), "anchor": "center"},  # leaping, arm raised
    "Hurt": {"frames": f(87), "anchor": "center"},  # thrown back
    "Dying": {"frames": f(107), "anchor": "center"},  # shocked
    "Drowning": {"frames": f(55), "anchor": "center"},  # mouth open
    "Fan Rotate": {"frames": FLOAT, "anchor": "center"},
    "Breathing": {"frames": f(55), "anchor": "center"},
    "Pushing": {"frames": f(58, 59)},  # no push art: leaning forward, hands out
    "Flailing 1": {"frames": f(89)},  # no balance art: arms out, a leg up
    "Flailing 2": {"frames": f(89)},
    "Hanging": {"frames": f(84), "anchor": "center"},  # one arm up
    "Clinging On": {"frames": f(87), "anchor": "center"},
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": f(87), "anchor": "center"},
    "Continue": {"frames": f(86)},
    "Continue Up": {"frames": f(84), "loop": 0},
    "Super Transform": {"frames": f(7), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": f(89)},
    "Grabbed": {"frames": f(87), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(52, 53, 54), "loop": 0},  # toying with psychic energy in his hands
}

# Psychic Wave (Y, slots 43/44): his hand goes out (60), then the sheet's psychic sphere swells around
# him (67.0-67.6: cyan rim, teal, cyan, cyan, teal, white, cyan), which shows the attack's range: the
# hit area is the sphere, all around him (melee_radial in tools/abilities.py). Centred on him, since
# the sphere reaches below his feet.
WAVE = f(60, *[67 + k / 10 for k in range(7)])
APPENDED = {
    # Psychokinesis (jump ability, slot 42): he floats inside rings of light while jump is held
    "42": {"name": "Psychokinesis", "frames": f(68.0, 68.1), "anchor": "center", "speed": 40},
    "43": {"name": "Psychic Wave", "frames": WAVE, "anchor": "center", "speed": 80},
    "44": {"name": "Psychic Wave Air", "frames": WAVE, "anchor": "center", "speed": 80},
    # Psychokinesis (Y with a badnik in reach, abilities.py psycho_grab): his hand goes out and the orb forms in it (60-64)
    # while he holds the caught badnik, then he throws it. The DLL picks the frame (the hold's timer)
    "45": {"name": "Psychic Hold", "frames": f(60, 61, 62, 63, 64), "anchor": "center", "speed": 0},
    # the same pose for Sonic CD (cd_config.py maps no 45; 47 becomes CD's 48: tools/psycho_grab.py CD_POSE, as Heavy's
    # Shine Spark does)
    "47": {"name": "Psychic Hold", "frames": f(60, 61, 62, 63, 64), "anchor": "center", "speed": 0},
}


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
ELEMENTS = {
    "life_icon": {"rect": [10, 44, 16, 16], "trim": False},  # his face, cropped from the standing frame 7
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("SILVER")},
    "monitor_1up": {"rect": [10, 45, 16, 14], "trim": False},
    # his front-on head (the top of frame 110, 23x22) on the game's own signpost board, enlarged 1.3x
    # nearest-neighbour to fill its 40x24 face area (the user's signpost exception; tools/sign_face.py: the quill tips
    # are trimmed)
    "sign_face": board_face([428, 437, 23, 22], 1.3),
    # no small continue icons on the sheet, and nothing is shrunk: two full-size standing frames
    "mini_1": {"rect": B[7], "remap": PLUS_128},
    "mini_2": {"rect": B[49], "remap": PLUS_128},
}
ENDING = {  # the sheet has no ending art; its most dramatic poses stand in
    "end_idle": {"rect": B[7], "remap": PLUS_128},
    "end_pose_1": {"rect": B[24], "remap": PLUS_128},  # leaping
    "end_pose_2": {"rect": B[69], "remap": PLUS_128},  # levitating
    "end_pose_3": {"rect": B[68.1], "remap": PLUS_128},  # floating in rings of light (57x50, not large)
    # good ending: he conjures a ring of psychic energy
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((60, 61, 62, 63, 64, 65), 1)},
}

PALETTE = {  # Silver's own colours, in the extras' shared global palette slots 74+
    "74": "#202020",  # near-black (shoes, outlines)
    "75": "#404060", "76": "#606080", "77": "#8080a0", "78": "#b5b2d6", "79": "#d6d7ff", "80": "#fffbff",
    "81": "#a5a2c6", "82": "#c6c3e7", "83": "#e7e3e7",  # his lavender-grey fur and gloves, dark to light
    "84": "#006b6b", "85": "#009494", "86": "#00b5b5", "87": "#00ffff", "88": "#b5ffff",  # teal shoes, cyan glow
    "89": "#a56121", "90": "#e8a364", "91": "#f9dfaa",  # muzzle and arms
}
KEY_COLOURS = {  # exact matches go in Sonic's slots; the rest are Silver's own
    "#000000": 1, "#e00000": 12, "#e80000": 12, "#800000": 13, "#fcfc00": 15,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (near-duplicate shades, other characters,
    text) in the slot of its nearest key colour, so nothing is left to sheet2ani's guess."""
    from PIL import Image
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in Image.open(HERE / SHEET).convert("RGB").getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c != "#bfffbf":
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


COLOURS = all_colours()


# The sheet has no spin ball: he jumps and Spin Dashes with Sonic's own ball, recoloured to his lavender fur,
# skin and teal shoes (tools/sonic_ball.py). His psychic sphere (67) is no longer used for them.
BALL_COLOURS = {1: "#202020", 2: "#404060", 3: "#8080a0", 4: "#b5b2d6", 5: "#d6d7ff", 10: "#e8a364",
                11: "#a56121", 12: "#00b5b5", 13: "#006b6b"}


# Sonic 3 & Knuckles (build_s3k_art.py "s3k_animations"): Run, Dash and Peelout get the whole 8-frame run cycle
# ("own_count": the game only sets their speed; Sonic's have 4 frames, which took every other stride and flickered
# between two poses at full speed, the user 2026-09-30; as Shadow's skate)
RUN_S3K = {"frames": RUN_FULL, "align": True, "own_count": True}
S3K_ANIMS = {"Run": RUN_S3K, "Dash": RUN_S3K, "Peelout": RUN_S3K}


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the ending poses: leaping, then levitating, arms spread
S3K_VICTORY = {"frames": f(24, 69)}


def config(game):
    ex = REPO / "extracted" / game
    ball = sonic_ball.source_with_ball(HERE / SHEET, game, BALL_COLOURS, "#bfffbf",
                                       HERE / "build" / f"source_{game}.png", anims=("Jumping", "Spin Dash"))
    jump = {"frames": ball["Jumping"], "anchor": "center"}
    cfg = {"name": "Extra6",
           "credit": "Silver - sheet by Gardow, additional credit to Xeric, Spyridon, Cyclone, Cylent Nite, DBurraki, Charity and Fox Omega - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/111917/",
           "source": f"build/source_{game}.png", "feet_y": 20, "background": ["#bfffbf"], "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, Jumping=jump, **{"Spin Dash": {"frames": ball["Spin Dash"]}},
                              **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra6SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": jump}}]
        cfg["ui"] = [{"name": "Extra6_UI", "manifest": "Extra6_ui.json", "elements": ELEMENTS, "out": "build/Extra6_UI.gif"},
                     {"name": "Extra6_Ending", "manifest": "Extra6_ending.json", "elements": ENDING,
                      "out": "build/Extra6_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
        cfg["s3k_animations"] = S3K_ANIMS
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "silver.json"), ("Sonic2", "silver_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
