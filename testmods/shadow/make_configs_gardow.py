#!/usr/bin/env python3
"""NOT USED (kept for reference; build_art.py runs make_configs.py, the Megamix sheet). Writes Shadow's sheet2ani configs (shadow.json for Sonic 1, shadow_s2.json for Sonic 2).

Frames are boxes on 18229.png ("Shadow (Sonic 3-Style)", Gardow and others; see SOURCE.txt), numbered
as detected: connected components of everything that isn't the #09c2ff background (the section divider
lines ignored), rows left to right, top to bottom. A few boxes held two touching sprites and are split
by hand below (86, 114, 266, 283); the loose jet-flame specks 90 and 95 join the skate frames.

The sheet says "Do not edit any sprites that are on this sheet", so unlike Big's config nothing here
redraws a sprite: frames are only cut, laid side by side (the Chaos Control sparkle, the Chaos Spear
crescent) or, for the small continue icons, shrunk as Fang's and Big's are.

Output goes into the mod (mods/NoSwap), like the other extras.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import sonic_ball  # noqa: E402
from sign_face import board_face  # noqa: E402
B = {  # box number -> [x, y, w, h]
    2: [6, 49, 27, 39], 16: [507, 43, 26, 45], 17: [535, 47, 28, 41], 18: [6, 92, 27, 39], 19: [41, 92, 28, 39],
    20: [76, 92, 29, 39], 21: [113, 92, 29, 39], 22: [150, 92, 30, 39], 23: [187, 92, 29, 39], 26: [293, 93, 36, 38],
    32: [512, 91, 30, 40], 33: [547, 93, 25, 38], 34: [11, 138, 23, 39], 35: [38, 138, 26, 39], 44: [327, 138, 27, 39],
    45: [360, 138, 26, 39], 50: [542, 135, 29, 48], 51: [576, 135, 23, 48], 52: [14, 185, 28, 39], 57: [191, 185, 28, 39],
    58: [230, 185, 28, 39], 59: [264, 184, 36, 40], 60: [305, 185, 39, 39], 61: [348, 185, 35, 39], 62: [397, 184, 37, 40],
    63: [438, 183, 35, 41], 64: [477, 183, 33, 41], 70: [15, 237, 38, 32], 71: [58, 238, 39, 31], 72: [102, 232, 33, 41],
    74: [178, 234, 33, 39], 75: [215, 233, 36, 39], 76: [263, 230, 25, 44], 77: [302, 233, 53, 23], 78: [301, 258, 54, 23],
    83: [6, 296, 30, 38], 84: [38, 296, 28, 38], 85: [69, 296, 32, 38],
    86: [105, 296, 37, 38],  # 86 held two walk frames touching at a glove
    86.5: [142, 296, 29, 38], 87: [175, 296, 25, 38], 88: [206, 296, 31, 38], 89: [240, 296, 31, 38],
    91: [275, 296, 47, 39],  # with jet-flame speck 90
    92: [327, 296, 34, 39], 93: [364, 296, 44, 39], 94: [412, 296, 45, 41],
    96: [461, 296, 44, 38],  # with jet-flame speck 95
    97: [511, 296, 30, 38], 98: [546, 296, 43, 38], 99: [593, 296, 41, 39], 100: [15, 348, 33, 27], 101: [56, 341, 36, 34],
    102: [95, 339, 32, 37], 103: [139, 349, 30, 27], 104: [173, 349, 29, 27], 105: [207, 349, 29, 27], 106: [240, 349, 29, 27],
    107: [272, 349, 29, 27], 108: [304, 349, 29, 27],
    114: [518, 340, 32, 38],  # 114 held two run frames
    114.5: [552, 340, 35, 38], 115: [590, 341, 34, 36], 116: [627, 343, 32, 34], 118: [56, 388, 45, 59], 126: [379, 412, 29, 32],
    127: [412, 412, 26, 32], 128: [443, 403, 28, 43], 129: [476, 405, 32, 39], 130: [511, 408, 23, 36], 131: [538, 411, 30, 33],
    132: [572, 412, 29, 32], 135: [10, 459, 24, 37], 136: [39, 459, 28, 37], 137: [72, 459, 24, 37], 138: [101, 459, 28, 37],
    139: [159, 460, 40, 36], 140: [207, 462, 39, 36], 141: [253, 462, 37, 36], 142: [302, 463, 40, 36], 179: [295, 716, 28, 41],
    180: [326, 716, 28, 41], 181: [357, 716, 28, 41], 182: [388, 722, 38, 34], 183: [428, 722, 38, 34], 184: [467, 722, 38, 34],
    190: [41, 767, 30, 39], 191: [74, 767, 43, 39], 192: [121, 769, 36, 37], 193: [155, 781, 14, 18], 194: [172, 769, 35, 37],
    197: [227, 769, 30, 37], 265: [452, 1078, 48, 48],
    266: [503, 1086, 32, 32],  # the medium sparkle (the box also held a small one)
    272: [470, 1169, 25, 20], 281: [543, 1165, 84, 60],
    283: [471, 1193, 23, 21],  # the upper of two front-on heads
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "18229.png"

WALK = f(83, 84, 85, 86, 86.5, 87, 88, 89)
SKATE = f(91, 92, 93, 94, 96, 97, 98, 99)  # hover-skating on his jet shoes
PEEL = f(139, 140, 141, 142)  # figure-eight legs
BALL = f(103, 104, 105, 106, 107, 108)
TUMBLE = f(126, 127, 128, 129, 130, 131, 132)

ANIMS = {
    "Stopped": {"frames": f(2)},
    "Waiting": {"frames": f(18, 19, 20, 21, 22, 23), "loop": 4},  # checks his wrist, then taps his foot
    "Looking Up": {"frames": f(16), "loop": 0},
    "Looking Down": {"frames": f(100), "loop": 0},
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": SKATE, "rot": 2, "align": True},  # the flame trail widens some frames: keep him put
    "Skidding": {"frames": f(101)},
    "Super Peel Out": {"frames": PEEL, "rot": 2},
    "Spin Dash": {"frames": BALL},
    "Jumping": {"frames": BALL, "anchor": "center"},  # replaced in config() by Sonic's recoloured curl
    "Bouncing": {"frames": f(76), "anchor": "center"},
    "Hurt": {"frames": f(70), "anchor": "center"},
    "Dying": {"frames": f(72), "anchor": "center"},
    "Drowning": {"frames": f(74), "anchor": "center"},
    "Fan Rotate": {"frames": TUMBLE, "anchor": "center"},
    "Breathing": {"frames": f(75), "anchor": "center"},
    "Pushing": {"frames": f(135, 136, 137, 138)},
    "Flailing 1": {"frames": f(59, 60, 61)},
    "Flailing 2": {"frames": f(62, 63, 64)},
    "Hanging": {"frames": f(50, 51), "anchor": "center"},
    "Clinging On": {"frames": f(77, 78), "anchor": "center"},
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": f(71), "anchor": "center"},
    "Continue": {"frames": f(77, 78)},
    "Continue Up": {"frames": f(16), "loop": 0},
    "Super Transform": {"frames": f(2), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": f(59, 60, 61)},
    "Grabbed": {"frames": f(70), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(52, 57, 58, 57), "loop": 1},  # arms crossed, tapping his foot
}


def flash(body, sparkle):
    """A sparkle over Shadow's chest, positioned by his body (the sparkle is the front layer)."""
    bx, by, bw, bh = B[body]
    sx, sy, sw, sh = B[sparkle]
    return {"layers": [{"rect": B[body], "at": [0, 0]},
                       {"rect": B[sparkle], "at": [bw // 2 - sw // 2, bh // 3 - sh // 2]}], "anchor_layer": 0}


# Chaos Control (jump ability, slot 41): a flash, then the blue warp dash from the sheet
# (179-184: he turns blue, lunges forward as a blue after-image and comes out of it). 3 game frames each.
CHAOS_CONTROL = [flash(181, 265), flash(181, 266), B[182], B[182], B[183], B[183], B[184]]


def spear(anchor):
    """Chaos Spear: wind up, swing, the crescent (193) flies out 12 px a frame, recover.
    The crescent's reach per frame goes in tools/abilities.py (see the report)."""
    cx, cy = B[193][0] - B[192][0], B[193][1] - B[192][1]  # where the sheet has it after the swing
    frames = [B[190], B[191]]
    for k, body in enumerate((192, 192, 194, 194)):  # 194 is the same pose, arm lowering
        frames.append({"layers": [{"rect": B[body], "at": [0, 0]}, {"rect": B[193], "at": [cx + 12 * k, cy]}],
                       "anchor_layer": 0})
    frames.append(B[197])
    return {"frames": frames, "anchor": anchor, "speed": 80}


APPENDED = {
    "41": {"name": "Chaos Control", "frames": CHAOS_CONTROL, "anchor": "center", "speed": 80, "loop": 6},
    "43": dict(spear("feet"), name="Chaos Spear"),
    "44": dict(spear("center"), name="Chaos Spear Air"),
}


def tag(word, font):
    """Hand-drawn name tag in the game's HUD style: 2 px strokes, shadow right and below."""
    rows = [""] * 6
    for ch in word:
        glyph = font[ch]
        w = max(map(len, glyph))
        for r in range(6):
            rows[r] += glyph[r].ljust(w, ".") + ".."
    rows = [r.rstrip(".") for r in rows] + [""]
    w = max(map(len, rows)) + 1
    grid = [list(r.ljust(w, ".")) for r in rows]
    for y in range(6):
        for x in range(w):
            if grid[y][x] == "f":
                for dx, dy in ((1, 0), (0, 1)):
                    if grid[y + dy][x + dx] == ".":
                        grid[y + dy][x + dx] = "1"
    return ["".join(r).rstrip(".") for r in grid]


FONT = {
    "S": [".ffff", "ff...", ".fff.", "...ff", "...ff", "ffff."],
    "H": ["ff.ff", "ff.ff", "fffff", "ff.ff", "ff.ff", "ff.ff"],
    "A": [".fff.", "ff.ff", "ff.ff", "fffff", "ff.ff", "ff.ff"],
    "D": ["ffff.", "ff.ff", "ff.ff", "ff.ff", "ff.ff", "ffff."],
    "O": [".fff.", "ff.ff", "ff.ff", "ff.ff", "ff.ff", ".fff."],
    "W": ["ff...ff", "ff...ff", "ff.f.ff", "ff.f.ff", "fffffff", ".ff.ff."],
}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
ELEMENTS = {
    "life_icon": {"rect": [474, 1170, 16, 16], "trim": False},  # side-on head 272, its back quills cut off
    "life_name": {"pixel_colours": HUD_FONT, "pixels": tag("SHADOW", FONT)},
    "monitor_1up": {"rect": [474, 1171, 16, 14], "trim": False},
    # Shadow's front-on head on the game's own signpost board (its yellow interior is 40x24 at 4,5), enlarged 1.3x
    # nearest-neighbour to fill it (the user's signpost exception; tools/sign_face.py: the top quill's tip is trimmed)
    "sign_face": board_face(B[283], 1.3),
    "mini_1": {"rect": B[57], "remap": PLUS_128},  # full size: the sheet asks not to edit its sprites
    "mini_2": {"rect": B[58], "remap": PLUS_128},  # foot out
}
ENDING = {
    "end_idle": {"rect": B[2], "remap": PLUS_128},
    "end_pose_1": {"rect": B[26], "remap": PLUS_128},  # pointing
    "end_pose_2": {"rect": B[118], "remap": PLUS_128},  # on his snowboard
    "end_pose_3": {"rect": B[281], "remap": PLUS_128},  # the portrait
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((44, 45, 34, 35, 17, 33), 1)},
}

# Faithful colours (the sheet asks not to edit its sprites): colours Sonic's slots hold exactly stay
# there; all others get Shadow's own slots, which extras share (only one plays at a time)
PALETTE = {
    "74": "#212021", "75": "#414141", "76": "#e84a4b", "77": "#e80000", "78": "#840000",
    "79": "#c0c0e0", "80": "#a0a0c0", "81": "#606080", "82": "#efa263", "83": "#a56121",
    "84": "#2040e0", "85": "#4080e0", "86": "#80c0e0", "87": "#213080", "88": "#ffdb9c", "89": "#ffffff",
}
KEY_COLOURS = {
    "#000000": 1, "#e0e0e0": 6, "#800000": 13, "#e0e000": 15,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet in the slot of its nearest key colour
    (the sheet has many one-off shades, e.g. #636384 beside #636184)."""
    from PIL import Image
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in Image.open(HERE / SHEET).convert("RGB").getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c != "#09c2ff":
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


COLOURS = all_colours()


# The sheet's ball frames (103-108) are smooth ovals, like Sonic's Spin Dash, with no curled-up jump frames.
# He keeps them for the Spin Dash and jumps with Sonic's own curl, recoloured to his black fur, skin and
# (like Sonic's) red and white shoes; see tools/sonic_ball.py.
BALL_COLOURS = {2: "#000000", 3: "#212021", 4: "#414141", 5: "#606080", 10: "#efa263", 11: "#a56121"}


def config(game):
    ex = REPO / "extracted" / game
    ball = sonic_ball.source_with_ball(HERE / SHEET, game, BALL_COLOURS, "#09c2ff",
                                       HERE / "build" / f"source_{game}.png")
    jump = {"frames": ball["Jumping"], "anchor": "center"}
    cfg = {"name": "Extra4",
           "credit": "Shadow (Sonic 3-Style) by Gardow; bases by Rathe, Deekman, Fox Omega, Nate; sheeted by Cylent Nite, The Sprite Lord, Karahni Popus, Cyclone TE, Charity - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/18229/",
           "source": f"build/source_{game}.png", "feet_y": 20, "background": ["#09c2ff"], "colours": COLOURS, "palette": PALETTE,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, Jumping=jump, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra4SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": jump}}]
        cfg["ui"] = [{"name": "Extra4_UI", "manifest": "Extra4_ui.json", "elements": ELEMENTS, "out": "build/Extra4_UI.gif"},
                     {"name": "Extra4_Ending", "manifest": "Extra4_ending.json", "elements": ENDING,
                      "out": "build/Extra4_Ending.gif"}]
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "shadow.json"), ("Sonic2", "shadow_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
