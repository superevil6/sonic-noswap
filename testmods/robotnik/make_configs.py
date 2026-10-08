#!/usr/bin/env python3
"""Writes Dr. Robotnik's sheet2ani configs (robotnik.json for Sonic 1, robotnik_s2.json for Sonic 2).

Frames are the light-green (#91f257) boxes on Robotnik.png (sheet by Dr. Cheesecrumbz; see SOURCE.txt), numbered
as detected: connected components of everything that isn't the #246c00 sheet background or the #054601 section
panels (8-connected, numbered in scan order). The sheet is a compilation in sections: GENESIS, SMS / GG, SONIC'S
GAMEWORLD, KNUX CHAOTIX, CD, SEGASONIC and EXTRAS. The player set is mostly EXTRAS (run cycle, figure-eight
"peel out", skid, dive / tumble, parachute), SEGASONIC (the run) and GENESIS (standing, laughing, hopping).

Template: Sonic's .ani. He's on foot here: the sheet's Egg Mobile art is only busts, a few small pods and CD's
claw-arm pod, nowhere near Tails' flying / tired / swimming set.
He never curls up, and the sheet has no ball: Jumping, rolling, the Spin Dash and the special stages use the generic
spin ball (tools/generic_ball.py: Sonic Mania's plain spin ball, SEGA's art) in his own reds
(BALL_COLOURS), drawn in a strip under a working copy of the sheet (build/source_<game>.png; the sheet file itself is
untouched). The sheet says "NO EDITS / NO RECOLORS", so nothing of his is redrawn, resized or recoloured: frames are
only cut, mirrored or turned by whole quarter turns, which moves pixels without changing any.
Moves (tools/abilities.py extra 20): the Rocket Ride (slot 41: KNUX CHAOTIX's rocket pack, then the Chaotix blasts),
the parachute (slot 42), and the Egg Claw throw pose (slots 43 / 44). The claw and the bomb themselves are shots,
cut from this sheet by tools/build_s3k_shot.py (abilities.py "shot" / "shot2" art).
The sheet has no HUD name tag: "ROBOTNIK" is hand-drawn in the game's HUD letter style (NAME below).
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
import generic_ball  # noqa: E402
B = {  # box number -> [x, y, w, h]
    # GENESIS: standing (22, 23), smiling (2, 3), laughing (4, 5), hop (12), squat (13), waving (14-16),
    # arms-up hop (35), knocked back (36), signposts (19, 20), HUD icons (25-27)
    22: [6, 14, 32, 51], 23: [40, 14, 32, 51], 2: [76, 13, 32, 52], 3: [110, 13, 32, 52], 4: [146, 13, 32, 52],
    5: [180, 13, 32, 52], 12: [541, 13, 44, 62], 13: [587, 13, 48, 42], 14: [637, 13, 58, 51],
    15: [698, 13, 60, 51], 16: [760, 13, 58, 51], 35: [284, 70, 80, 80], 36: [366, 70, 80, 80],
    19: [878, 13, 48, 48], 20: [928, 13, 48, 48], 25: [822, 38, 16, 16], 26: [840, 38, 16, 16], 27: [858, 38, 16, 16],
    # SMS / GG: arms-up panic, sweat flying (42-44)
    42: [632, 90, 49, 62], 43: [683, 90, 46, 68], 44: [731, 90, 49, 64],
    # SONIC'S GAMEWORLD: small sprites
    100: [6, 239, 17, 27], 101: [25, 239, 17, 27],
    # KNUX CHAOTIX: the rocket pack (123 riding it, facing right; 124 from behind)
    123: [611, 305, 61, 64], 124: [674, 305, 61, 64],
    # SEGASONIC: run
    190: [2, 534, 44, 53], 196: [48, 538, 53, 44], 194: [103, 536, 33, 51], 191: [138, 535, 45, 52],
    192: [185, 535, 55, 49], 197: [242, 538, 53, 44], 195: [297, 537, 33, 50], 193: [332, 535, 38, 52],
    # EXTRAS, row 1: run cycle, figure-eight run, skid, dive (214, 215), tumble (201, 213), face-plant (216)
    202: [2, 603, 32, 50], 203: [36, 603, 34, 50], 207: [72, 605, 39, 48], 205: [113, 604, 39, 49],
    204: [154, 603, 44, 50], 199: [200, 602, 41, 51], 208: [243, 606, 46, 47], 206: [291, 604, 37, 49],
    211: [332, 607, 39, 46], 209: [373, 606, 40, 47], 212: [415, 607, 39, 46], 210: [456, 606, 40, 47],
    200: [500, 602, 49, 51], 214: [551, 621, 66, 32], 215: [619, 621, 66, 32], 201: [687, 602, 51, 51],
    213: [740, 616, 66, 37], 216: [808, 624, 64, 29],
    # EXTRAS, row 2: finger up, 16t weight, arms out, leap, hand-rubbing, parachute, laughing, pointing
    223: [11, 730, 47, 51], 218: [60, 717, 52, 64], 224: [114, 730, 68, 51], 220: [184, 721, 59, 61],
    225: [260, 730, 42, 51], 217: [306, 668, 68, 124], 222: [376, 725, 70, 56], 226: [448, 730, 51, 51],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "Robotnik.png"
BACKGROUND = ["#246c00", "#054601", "#91f257"]  # the sheet, the section panels, and the boxes the frames sit in

WALK = f(202, 203, 207, 205, 204, 199, 208, 206)  # EXTRAS run cycle, the steadier of his two runs
RUN = f(190, 196, 194, 191, 192, 197, 195, 193)  # SEGASONIC: arms pumping
WHIRR = f(211, 209, 212, 210)  # EXTRAS: legs in a figure-eight blur
HOP = f(35)  # GENESIS: arms-up hop (he never curls up)
BALANCE = f(42, 44)  # SMS / GG: arms up, sweat flying
TUMBLE = f(214, 201, 213)  # EXTRAS: dive, upside down, tipping over
PARACHUTE = {"rect": B[217], "anchor_box": [317, 730, 50, 62]}  # placed by his body, the canopy above

ANIMS = {
    "Stopped": {"frames": f(22)},  # GENESIS standing
    "Waiting": {"frames": f(4, 5), "loop": 0},  # GENESIS: ho ho ho
    "Looking Up": {"frames": f(223), "loop": 0},  # finger to the sky
    "Looking Down": {"frames": f(13), "loop": 0},  # GENESIS squat
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2, "align": True},  # his body lurched between the run's frames
    "Skidding": {"frames": f(200)},  # EXTRAS: leaning back on one heel
    "Super Peel Out": {"frames": WHIRR, "rot": 2},
    "Spin Dash": {"frames": WHIRR},  # revving in place (no ball)
    "Jumping": {"frames": HOP, "anchor": "center"},
    "Bouncing": {"frames": f(12), "anchor": "center"},  # GENESIS: stretched hop
    "Hurt": {"frames": f(36), "anchor": "center"},  # GENESIS: knocked back
    "Dying": {"frames": f(201), "anchor": "center"},  # EXTRAS: upside down
    "Drowning": {"frames": f(43), "anchor": "center"},  # SMS / GG: panicking, drops flying
    "Fan Rotate": {"frames": TUMBLE, "anchor": "center"},
    "Breathing": {"frames": f(5), "anchor": "center"},  # GENESIS: mouth wide open
    "Pushing": {"frames": f(202, 203, 207, 205)},  # no pushing art: the first four run-cycle steps, marching into it
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(12), "anchor": "center"},  # no hanging art: the stretched hop, hands up
    "Clinging On": {"frames": f(214, 215), "anchor": "center"},  # EXTRAS: flat out, legs trailing
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": f(216, 213), "anchor": "center"},  # EXTRAS: on his face, sliding
    "Continue": {"frames": f(225, 226)},  # EXTRAS: rubbing his hands, pointing
    "Continue Up": {"frames": f(12), "loop": 0},
    "Super Transform": {"frames": f(22), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": f(36), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(14, 15, 16, 15), "loop": 0},  # GENESIS: waving
}

ROCKET = f(123)  # KNUX CHAOTIX: riding his rocket pack, facing the way he flies
# KNUX CHAOTIX fireballs, big to small: (box, left edge under the hop pose's 64 px trimmed width, overlap with his feet)
BLASTS = [([805, 303, 33, 32], 16, 10), ([795, 337, 22, 22], 21, 8), ([819, 337, 16, 16], 24, 6)]
# The launch: the arms-up hop (35, 64x51 trimmed) with the blast behind and below him. Layers only place the
# sheet's own sprites side by side (first at the back), so nothing is redrawn. The code picks the frame
# (abilities.py rocket_ride): the rocket for the ride, then the three blasts as the explosion fades.
LAUNCH = [{"layers": [{"rect": r, "at": [x, 51 - overlap]}, {"rect": B[35], "at": [0, 0]}], "anchor_layer": 1}
          for r, x, overlap in BLASTS]

# The Egg Claw's throw (slots 43 / 44; the pose is the last frame): finger up, then pointing ahead (226 points left
# as drawn: mirrored)
THROW = [B[223], {"rect": B[226], "flip": True}]

APPENDED = {
    # Rocket Ride (rocket_ride, jump in mid-air): he rides the rocket pack, it blows up, and the blast pops him up
    "41": {"name": "Rocket Ride", "frames": ROCKET + LAUNCH, "anchor": "center"},
    # ...then the parachute (hover: keep holding jump once he's falling), drifting down
    "42": {"name": "Parachute", "frames": [PARACHUTE], "anchor": "center"},
    # Egg Claw throw (the shot's pose), standing and in the air
    "43": {"name": "Egg Claw", "frames": THROW, "speed": 60},
    "44": {"name": "Egg Claw Air", "frames": THROW, "speed": 60, "anchor": "center"},
}


NAME = "ROBOTNIK"  # 56 px wide in Rayan C.'s letters (tools/hud_font.py); "EGGMAN" would be 46
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
ELEMENTS = {
    "life_icon": {"rect": B[26], "trim": False},  # GENESIS: his head, 16x16
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag(NAME)},
    "monitor_1up": {"rect": [B[26][0], B[26][1] + 1, 16, 14], "trim": False},  # the icon's middle rows
    # GENESIS signpost: the 30-row board and the 2-row pole stub above it, without the pole below
    "sign_face": {"rect": [B[19][0], B[19][1], 48, 32], "trim": False},
    "mini_1": {"rect": B[100], "remap": PLUS_128},  # SONIC'S GAMEWORLD small sprites (17x27)
    "mini_2": {"rect": B[101], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[2], "remap": PLUS_128},  # GENESIS: smiling
    "end_pose_1": {"rect": B[224], "remap": PLUS_128},  # arms out
    "end_pose_2": {"rect": B[222], "remap": PLUS_128},  # laughing, pointing
    "end_pose_3": {"rect": B[220], "remap": PLUS_128},  # the leap, finger up
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((3, 4, 5, 14, 15, 16), 1)},
}

PALETTE = {  # Robotnik's own colours, in the extras' shared global palette slots 74+
    "74": "#fc0000",  # red coat
    "75": "#fcb400", "76": "#fc9000",  # yellow-orange coat trim; orange (signpost, HUD icon)
    "77": "#fcfcfc", "78": "#b4b4b4",  # white and light grey (gloves, goggles)
    "79": "#fcb490", "80": "#b46c48",  # skin, light and shaded
    "81": "#1f46d9", "82": "#1f1fb6", "83": "#4646fc", "84": "#6c6cfc",  # the jetpack's blues
    "85": "#fcfc00",  # the "ROBOTNIK" name tag
    # colours Sonic's slots would hold, kept in their own slots so no game shifts them to its nearest shade
    # (the sheet says "NO RECOLORS"): greys, skin, dark reds
    "86": "#909090", "87": "#808080", "88": "#484848", "89": "#404040",
    "90": "#e0a080", "91": "#a06040", "92": "#900000", "93": "#480000",
    "94": "#202020",  # 9 pixels in a run frame: halfway between black and #404040, so its own slot
}
KEY_COLOURS = {  # black shares Sonic's slot 1; everything else is Robotnik's own, exact
    "#000000": 1, "#080000": 1,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (near-duplicates like #464646, other games' shades,
    text) in the slot of its nearest key colour, so nothing is left to sheet2ani's guess."""
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

# The generic ball (tools/generic_ball.py) in his own reds (Sonic Mania's plain spin ball, SEGA's art, not his
# sprites): his coat's dark red, shade and red, a white shine; the outline its darkest red (outline_for: no darker red)
BALL_COLOURS = generic_ball.colours(dark="#480000", mid="#900000", light="#fc0000", shine="#fcfcfc",
                                    palette=list(PALETTE.values()))


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): GENESIS: laughing, then the arms-up hop
S3K_VICTORY = {"frames": f(4, 35)}


def config(game):
    ex = REPO / "extracted" / game
    (HERE / "build").mkdir(parents=True, exist_ok=True)
    source = HERE / "build" / f"source_{game}.png"  # (the sheet as drawn, with the ball's strip under it)
    ball = generic_ball.source_with_ball(Image.open(HERE / SHEET).convert("RGBA"), BALL_COLOURS, BACKGROUND[0], source)
    jump = {"frames": ball, "anchor": "center"}
    cfg = {"name": "Extra14",
           "credit": "Dr. Robotnik sheet by Dr. Cheesecrumbz - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/272390/",
           "source": f"build/source_{game}.png", "feet_y": 20, "background": BACKGROUND, "palette": PALETTE,
           "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, Jumping=jump, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra14SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": jump}}]
        cfg["ui"] = [{"name": "Extra14_UI", "manifest": "Extra14_ui.json", "elements": ELEMENTS, "out": "build/Extra14_UI.gif"},
                     {"name": "Extra14_Ending", "manifest": "Extra14_ending.json", "elements": ENDING,
                      "out": "build/Extra14_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return generic_ball.apply(cfg, ball, game)  # jump, Spin Dash, special stages, CD's and S3&K's


if __name__ == "__main__":
    for game, out in (("Sonic1", "robotnik.json"), ("Sonic2", "robotnik_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
