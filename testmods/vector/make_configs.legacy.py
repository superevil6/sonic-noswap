#!/usr/bin/env python3
"""Writes Vector's sheet2ani configs (vector.json for Sonic 1, vector_s2.json for Sonic 2).

Frames are the dark boxes on Vector.png ("Vector, The Crocodile In Sonic 1" by Akimaca; see SOURCE.txt),
numbered as detected: connected components of everything that isn't the #db70d2 sheet background (8-connected,
numbered in scan order). The sheet labels its rows (Idle, Waiting, Walking...), and the mapping follows them.

Template: Sonic's .ani. Vector doesn't glide or fly, so Knuckles' and Tails' sets don't fit; his Chaotix air dash
is the aim_dash module, drawn with the sheet's "Shoulder dash" (slots 41 level, 45 straight up, 46 down).

Vector is big (57 px tall standing; Sonic is 39), so his frames take 3 player sheets. Not used: "Running w. thumbs up",
"Climbing", "Ledge", "Wall bounce" and the 45-degree-up shoulder dash (their boxes stay in B).
The sheet has his own spin (curled frames plus a ball) and Spindash, so tools/sonic_ball.py isn't needed.
Nothing is redrawn or resized: frames are cut, and the HUD art is cropped from the sheet's own.
"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

B = {  # box number -> [x, y, w, h]
    # Idle, Waiting, Look up, Crouch, Spring
    52: [9, 60, 42, 57], 51: [56, 59, 43, 58], 53: [103, 61, 38, 56], 58: [148, 75, 37, 42], 50: [194, 56, 39, 61],
    49: [239, 54, 42, 63], 59: [290, 82, 52, 35], 48: [352, 47, 28, 70],
    # Walking, Skidding, Bubble
    101: [8, 136, 44, 56], 96: [56, 134, 45, 58], 97: [105, 134, 45, 58], 102: [156, 136, 43, 56],
    98: [207, 134, 50, 58], 99: [265, 134, 48, 58], 103: [327, 150, 57, 42], 104: [391, 150, 55, 42],
    100: [455, 134, 49, 58],
    # Running, Running w. thumbs up
    150: [9, 215, 66, 37], 151: [82, 215, 65, 37], 152: [154, 215, 66, 37], 153: [227, 215, 65, 37],
    145: [303, 211, 68, 41], 146: [376, 211, 67, 41], 147: [448, 211, 68, 41], 148: [521, 211, 67, 41],
    # Balance, Hurt/Slide, Spin, Pushing short obj./wall
    196: [11, 271, 52, 60], 194: [72, 268, 51, 63], 197: [138, 271, 41, 60], 195: [193, 268, 49, 63],
    199: [256, 291, 40, 40], 200: [299, 291, 40, 40], 201: [342, 291, 40, 40], 202: [385, 291, 40, 40],
    203: [430, 291, 40, 40],
    206: [489, 295, 60, 36], 204: [555, 294, 60, 37], 207: [621, 295, 60, 36], 205: [687, 294, 60, 37],
    # Pushing tall obj./wall, Cling, Labyrinth spin, Continue
    262: [5, 349, 49, 51], 260: [59, 348, 49, 52], 263: [114, 349, 49, 51], 261: [169, 348, 49, 52],
    269: [233, 370, 82, 30], 270: [320, 372, 83, 28],
    267: [415, 366, 77, 34], 268: [502, 367, 54, 33], 266: [561, 365, 68, 35],
    264: [641, 351, 56, 49], 265: [698, 351, 56, 49],
    # Death, Drown, Shoulder dash, Climbing, Ledge
    370: [10, 439, 55, 52], 331: [69, 433, 55, 58],
    431: [139, 462, 62, 29], 373: [206, 441, 51, 50], 328: [265, 429, 29, 62], 372: [305, 440, 50, 51],
    332: [370, 433, 29, 58], 329: [405, 431, 32, 60], 333: [445, 433, 33, 58], 330: [487, 431, 32, 60],
    327: [539, 421, 28, 70], 348: [577, 436, 44, 55], 399: [631, 451, 47, 40],
    # Normal ending, Good ending, Signpost, Continue icon, Life counter
    478: [17, 511, 42, 60], 486: [66, 527, 40, 44],
    481: [144, 515, 38, 56], 482: [185, 515, 38, 56], 479: [231, 514, 42, 57], 483: [278, 515, 47, 56],
    484: [328, 515, 47, 56], 487: [384, 527, 40, 44],
    485: [449, 518, 48, 53], 488: [506, 536, 22, 35], 489: [533, 536, 22, 35], 490: [566, 538, 57, 33],
    # End sprite (large, small)
    587: [160, 605, 269, 147], 594: [51, 654, 68, 70],
    # Extras: Dig it, Wall bounce, Notes, Burnt, Fall, Alt. spindash, Spindash
    491: [812, 547, 34, 50], 493: [848, 548, 34, 49], 492: [886, 547, 34, 50], 494: [932, 550, 53, 47],
    589: [760, 621, 55, 52], 590: [828, 634, 52, 39],
    591: [890, 637, 47, 36], 592: [940, 638, 48, 35], 593: [994, 638, 51, 35],
    621: [772, 704, 38, 37], 622: [815, 704, 38, 37], 623: [858, 704, 38, 37], 624: [901, 704, 38, 37],
    625: [944, 704, 38, 37], 620: [988, 703, 39, 38],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "Vector.png"
BACKGROUND = ["#db70d2", "#9f1394"]  # the sheet, and the boxes the frames sit in

WALK = f(101, 96, 97, 102, 98, 99)  # "Walking"
RUN = f(150, 151, 152, 153)  # "Running"
SPIN = f(199, 200, 201, 202, 203)  # "Spin": curled frames, then the ball (Sonic 1's jump pattern)
SPINDASH = f(621, 622, 623, 624, 625, 620)  # "Spindash" (Extras)
BALANCE = f(196, 194)
HURT_SLIDE = f(197, 195)
DIG_IT = f(491, 493, 492)  # "Dig it" (Extras): grooving, hands on his headphones


ANIMS = {
    "Stopped": {"frames": f(52)},  # "Idle"
    "Waiting": {"frames": f(51, 53, 58, 50), "loop": 0},  # "Waiting": head-banging to his headphones
    "Looking Up": {"frames": f(49), "loop": 0},  # "Look up"
    "Looking Down": {"frames": f(59), "loop": 0},  # "Crouch"
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2},
    "Skidding": {"frames": f(103, 104)},
    "Super Peel Out": {"frames": RUN, "rot": 2},  # no peel-out art ("Running w. thumbs up" doesn't fit)
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": {"frames": SPIN, "anchor": "center"},
    "Bouncing": {"frames": f(48), "anchor": "center"},  # "Spring"
    "Hurt": {"frames": f(197), "anchor": "center"},  # "Hurt/Slide"
    "Dying": {"frames": f(370), "anchor": "center"},  # "Death"
    "Drowning": {"frames": f(331), "anchor": "center"},  # "Drown"
    "Fan Rotate": {"frames": f(267, 268, 266), "anchor": "center"},  # "Labyrinth spin"
    "Breathing": {"frames": f(100), "anchor": "center"},  # "Bubble"
    "Pushing": {"frames": f(206, 204, 207, 205)},  # "Pushing short obj./wall" (blocks are short to him)
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(48), "anchor": "center"},  # no hanging art: the spring pose (stretched up)
    "Clinging On": {"frames": f(269, 270), "anchor": "center"},  # "Cling"
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": HURT_SLIDE, "anchor": "center"},  # "Hurt/Slide"
    "Continue": {"frames": f(264, 265)},
    "Continue Up": {"frames": f(48), "loop": 0},
    "Super Transform": {"frames": f(52), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": f(197), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": DIG_IT, "loop": 0},  # "Dig it"
}

APPENDED = {
    # Air Dash (jump in mid-air; aim_dash): the "Shoulder dash", level / straight up / 45 degrees down
    "41": {"name": "Shoulder Dash", "frames": f(431), "anchor": "center"},
    "45": {"name": "Shoulder Dash Up", "frames": f(328), "anchor": "center"},  # the vertical one
    "46": {"name": "Shoulder Dash Down", "frames": f(372), "anchor": "center"},
}

LIFE = B[490]  # "Life counter": two versions stacked, "VECTOR" on top and "V-T-C" below
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": [LIFE[0], LIFE[1], 16, 16], "trim": False},  # his head
    "life_name": {"rect": [LIFE[0] + 17, LIFE[1] + 1, 39, 7]},  # ...and "VECTOR"
    "monitor_1up": {"rect": [LIFE[0], LIFE[1] + 1, 16, 14], "trim": False},  # the icon's middle rows
    # "Signpost": the board (30 rows) and the 2 rows above it, without the pole. His hand and headphones
    # stick up 7 rows above the board; the top 5 of those are cut to keep Sonic's 48x32 board size
    "sign_face": {"rect": [B[485][0], B[485][1] + 5, 48, 32], "trim": False},
    "mini_1": {"rect": B[488], "remap": PLUS_128},  # "Continue icon" (22x35)
    "mini_2": {"rect": B[489], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[478], "remap": PLUS_128},  # "Normal ending"
    "end_pose_1": {"rect": B[486], "remap": PLUS_128},
    "end_pose_2": {"rect": B[50], "remap": PLUS_128},  # "Waiting": head back, finger in the air
    # "End sprite": the smaller of the two (68x70). The large one (587, 269x147) would take most of the
    # shared ending sheet; swap it in if there's room.
    "end_pose_3": {"rect": B[594], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((481, 482, 479, 483, 484, 487), 1)},
}

PALETTE = {  # Vector's own colours, in the extras' shared global palette slots 74+
    "74": "#004800", "75": "#009000", "76": "#24b400", "77": "#48d800",  # green scales, dark to light
    "78": "#6c2400", "79": "#b49000", "80": "#fcd800",  # belly and jaw, dark to light
    "81": "#fcfcfc", "82": "#b4b4b4",  # white and light grey (gloves, eyes)
    "83": "#4848b4",  # lighter blue (shoes, headphones; the darker #242490 is Sonic's slot 2)
    "84": "#fc0000",  # red spines
    "85": "#fcfc00",  # the "VECTOR" name tag
}
KEY_COLOURS = {  # near-exact matches go in Sonic's slots; the rest are Vector's own
    "#000000": 1, "#010101": 1, "#242490": 2, "#909090": 8, "#484848": 9, "#900000": 13, "#480000": 14,
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
# the last frame, the pose held or looped): the ending poses: into "Waiting"'s head back, finger in the air
S3K_VICTORY = {"frames": f(486, 50)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra12",
           "credit": "Vector (The Crocodile In Sonic 1) by Akimaca; original sprites by SEGA / Sonic Team",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra12SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": SPIN, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra12_UI", "manifest": "Extra12_ui.json", "elements": ELEMENTS, "out": "build/Extra12_UI.gif"},
                     {"name": "Extra12_Ending", "manifest": "Extra12_ending.json", "elements": ENDING,
                      "out": "build/Extra12_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "vector.json"), ("Sonic2", "vector_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
