#!/usr/bin/env python3
"""Writes Rouge's sheet2ani configs (rouge.json for Sonic 1, rouge_s2.json for Sonic 2).

Rouge plays like Knuckles (glide and wall climb), so her .ani follows KNUCKLES' animation list
(extracted/<game>/Data/Animations/Knuckles.ani is the template), not Sonic's:
  - Walking and Running use rotation style 3 (pre-drawn angled frames): the upright frames, then the
    same frames drawn at 45 degrees. Her sheet has exactly that ("WALK" + "WALK (ANGLED)", "RUN" + "RUN (ANGLED)").
  - Gliding, Gliding Drop, Gliding Stop, Climbing and Ledge Pull Up (slots 28-32) and Dropping (Sonic 1)
    are Knuckles' own; the frames that sit against a wall or the floor are pinned to Knuckles' pivots.

Frames are the light-green boxes on 565796.png ("Rouge the Bat, custom sprites (Sonic 1 style)" by
DeltaConduit; see SOURCE.txt), numbered as detected: connected components of everything that isn't the
#24b448 sheet background, rows left to right, top to bottom. The mapping follows the sheet's row labels.
The sheet says "Do not edit effortlessly": nothing is redrawn or resized, frames are only cut or cropped.

"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import sheet2ani  # noqa: E402

B = {  # box number -> [x, y, w, h]
    42: [2, 65, 26, 41], 43: [38, 65, 28, 41], 44: [67, 65, 28, 41], 45: [96, 65, 28, 41], 46: [134, 65, 30, 41],
    47: [218, 67, 23, 39], 48: [242, 65, 32, 38], 49: [275, 66, 29, 40], 50: [305, 67, 27, 39], 51: [333, 65, 36, 37],
    52: [370, 66, 29, 40], 53: [409, 67, 39, 37], 54: [449, 66, 41, 40], 55: [491, 66, 43, 38], 56: [535, 71, 41, 35],
    57: [577, 69, 43, 37], 58: [621, 70, 44, 31], 59: [174, 76, 34, 30], 61: [675, 83, 16, 23], 62: [692, 83, 16, 23],
    67: [2, 133, 35, 38], 68: [38, 133, 37, 38], 69: [76, 133, 35, 38], 70: [112, 133, 37, 38], 71: [159, 127, 36, 41],
    72: [196, 129, 32, 42], 73: [229, 127, 33, 44], 74: [263, 129, 33, 42], 76: [306, 134, 34, 37], 77: [341, 134, 33, 37],
    80: [554, 141, 30, 30], 81: [585, 141, 30, 30], 82: [616, 141, 30, 30], 83: [647, 141, 30, 30], 84: [678, 141, 30, 30],
    85: [384, 144, 32, 27], 86: [417, 144, 31, 27], 87: [449, 144, 31, 27], 88: [481, 144, 31, 27], 89: [513, 144, 31, 27],
    92: [197, 186, 26, 49], 94: [334, 192, 37, 43], 95: [372, 192, 40, 43], 96: [413, 192, 40, 43], 97: [454, 192, 40, 43],
    99: [2, 197, 27, 38], 100: [30, 196, 24, 39], 101: [55, 197, 28, 38], 102: [84, 196, 24, 39], 103: [118, 195, 34, 40],
    104: [153, 195, 34, 40], 105: [233, 197, 37, 38], 106: [280, 198, 44, 37], 107: [504, 197, 39, 38], 108: [544, 198, 42, 37],
    109: [587, 198, 42, 37], 110: [630, 198, 42, 37], 111: [604, 251, 48, 48], 113: [2, 265, 47, 32], 114: [50, 264, 48, 35],
    115: [358, 263, 37, 36], 116: [405, 266, 37, 33], 119: [108, 274, 42, 24], 120: [151, 274, 43, 24], 121: [195, 274, 42, 25],
    123: [298, 274, 50, 25], 124: [452, 267, 48, 32], 125: [501, 267, 44, 32], 126: [546, 267, 48, 32], 127: [247, 275, 50, 23],
    128: [662, 283, 48, 16], 130: [2, 320, 23, 41], 131: [26, 320, 26, 41], 132: [87, 320, 27, 41], 133: [115, 320, 27, 41],
    134: [180, 320, 52, 80], 135: [233, 320, 167, 161], 136: [53, 324, 33, 37], 137: [143, 323, 36, 38],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "565796.png"
BACKGROUND = ["#24b448", "#6cfc90", "#48d86c"]  # the sheet, the boxes, and a darker panel in a few boxes

WALK = f(47, 48, 49, 50, 51, 52)  # "WALK"
WALK_ANGLED = f(53, 54, 55, 56, 57, 58)  # "WALK (ANGLED)", the same steps at 45 degrees
RUN = f(67, 68, 69, 70)  # "RUN"
RUN_ANGLED = f(71, 72, 73, 74)  # "RUN (ANGLED)"
SPIN = f(81, 82, 83, 84, 80)  # "SPIN": curled frames, then the ball
BALANCE = f(103, 104)


def trimmed(rect):
    """Where the art sits inside a box: (dx, dy, w, h) relative to the box's top-left."""
    x, y, w, h = rect
    img = Image.open(HERE / SHEET).convert("RGB").crop((x, y, x + w, y + h))
    bg = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in BACKGROUND}
    mask = Image.new("L", img.size, 0)
    mask.putdata([0 if p in bg else 255 for p in img.getdata()])
    return mask.getbbox()[:2] + (mask.getbbox()[2] - mask.getbbox()[0], mask.getbbox()[3] - mask.getbbox()[1])


def pinned(rect, kframe, align):
    """A frame positioned like one of Knuckles' (same bottom edge; same centre, or same right edge for
    frames pressed against a wall). Use with "anchor": "center"."""
    dx, dy, w, h = trimmed(rect)
    kx, ky, kw, kh = kframe["px"], kframe["py"], kframe["w"], kframe["h"]
    px = kx + kw - w if align == "right" else kx + kw // 2 - w // 2
    py = ky + kh - h
    return {"rect": rect, "anchor_box": [rect[0] + dx - px, rect[1] + dy - py, 0, 0]}


def knuckles_only(game):
    """Knuckles' own animations, with Rouge's nearest art."""
    tpl = sheet2ani.read_ani(REPO / "extracted" / game / "Data" / "Animations" / "Knuckles.ani")
    k = {a["name"]: a["frames"] for a in tpl["anims"]}
    out = {
        # three turning frames (facing the camera, three-quarter, side-on), picked by the glide code
        "Gliding": {"frames": f(94, 107, 106), "anchor": "center"},  # "FLY (STATIONARY)", "FLY (MOVING)", "GLIDE"
        "Gliding Drop": {"frames": f(95, 96), "anchor": "center"},  # let go of the glide: wings flapping as she falls
        # landing from a glide: sliding flat ("PIPE CLING"), then getting up ("CROUCH")
        # (the pipe-cling pose faces left: mirrored to slide forwards, as Knuckles does)
        "Gliding Stop": {"frames": [dict(pinned(B[123], k["Gliding Stop"][0], "centre"), flip=True),
                                    pinned(B[59], k["Gliding Stop"][1], "centre")], "anchor": "center"},
        # no climbing art: "PUSH" (hands flat against the wall), pressed against the wall like Knuckles
        "Climbing": {"frames": [pinned(B[n], k["Climbing"][i], "right")
                                for i, n in enumerate((99, 100, 101, 102, 101, 100))], "anchor": "center"},
        # no pull-up art: stretched up ("SPRING"), knee up ("CROUCH"), standing
        "Ledge Pull Up": {"frames": [pinned(B[n], k["Ledge Pull Up"][i], "right")
                                     for i, n in enumerate((92, 59, 42))], "anchor": "center"},
    }
    if game == "Sonic1":
        out["Dropping"] = {"frames": f(105), "anchor": "center"}  # "AIR GASP"
    else:
        # Sonic 2's slot 20 is Knuckles' (empty) "Sliding" but Sonic's "Flailing 3": fill it with her
        # balance frames so Sonic's balance code can't show an empty animation
        out["Sliding"] = {"frames": BALANCE}
        out["Grabbing"] = {"frames": f(113), "anchor": "center"}
    return out


ANIMS = {
    "Stopped": {"frames": f(42)},  # "IDLE"
    "Waiting": {"frames": f(43, 44, 45), "loop": 1},
    "Bored!": {"frames": f(43, 44, 45), "loop": 1},
    "Looking Up": {"frames": f(46), "loop": 0},
    "Looking Down": {"frames": f(59), "loop": 0},  # "CROUCH"
    "Walking": {"frames": WALK + WALK_ANGLED},  # rotation style 3 from Knuckles' template
    "Running": {"frames": RUN + RUN_ANGLED},
    "Skidding": {"frames": f(76, 77)},
    "Super Peel Out": {"frames": RUN, "rot": 2},  # Knuckles has none; upright run, freely rotated like Sonic's
    "Spin Dash": {"frames": f(85, 86, 87, 88, 89)},
    "Jumping": {"frames": SPIN, "anchor": "center"},
    "Bouncing": {"frames": f(92), "anchor": "center"},  # "SPRING"
    "Hurt": {"frames": f(113), "anchor": "center"},  # "HURT/FLUME"
    "Dying": {"frames": f(115), "anchor": "center"},
    "Drowning": {"frames": f(116), "anchor": "center"},
    "Fan Rotate": {"frames": f(119, 120, 121), "anchor": "center"},  # "FAN"
    "Breathing": {"frames": f(105), "anchor": "center"},  # "AIR GASP"
    "Pushing": {"frames": f(99, 100, 101, 102)},
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(92), "anchor": "center"},  # no hanging art: the spring pose (arms up)
    "Clinging On": {"frames": f(123, 127), "anchor": "center"},  # "PIPE CLING"
    "Corkscrew H": {"frames": WALK},  # Sonic 1
    "Twirl H": {"frames": WALK, "rot": 2},  # Sonic 2
    "Water Slide": {"frames": f(114), "anchor": "center"},  # "HURT/FLUME"
    "Continue": {"frames": f(124, 125, 126)},
    "Continue Up": {"frames": f(92), "loop": 0},
    "Super Transform": {"frames": f(42), "loop": 0},
}

# Screw Kick (Y in mid-air; abilities.py screw_kick): the "SPIN" row's curled frames with a leg out, without the
# ball. Slot 41 is free after Knuckles' list (0-38) in S1/S2; cd_config.py moves it to CD's 45, build_s3k_art.py
# to Knux.bin's 78.
APPENDED = {
    "41": {"name": "Screw Kick", "frames": f(81, 82, 83, 84), "anchor": "center", "speed": 120},
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": [662, 283, 16, 16], "trim": False},  # "1-UP": her head
    "life_name": {"rect": [679, 284, 31, 7]},  # ...and "ROUGE"
    "monitor_1up": {"rect": [662, 284, 16, 14], "trim": False},  # the icon's middle rows
    "sign_face": {"rect": [604, 251, 48, 32], "trim": False},  # "GOAL SIGN": the board, without its pole
    "mini_1": {"rect": B[61], "remap": PLUS_128},  # "CONTINUE ICON" (16x23)
    "mini_2": {"rect": B[62], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[130], "remap": PLUS_128},
    "end_pose_1": {"rect": B[136], "remap": PLUS_128},  # waving
    "end_pose_2": {"rect": B[137], "remap": PLUS_128},  # wings out
    # the smaller of the two big ENDING poses (52x80). The large one (135, 167x161) would take a lot of the
    # shared ending sheet's height; swap it in if there's room.
    "end_pose_3": {"rect": B[134], "remap": PLUS_128},
    # "ENDING": the six small frames in the sheet's order
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((130, 131, 136, 132, 133, 137), 1)},
}

PALETTE = {  # Rouge's own colours, in the extras' shared global palette slots 74+
    "74": "#fcfcfc", "75": "#b4b4b4",  # white fur and boots, light grey
    "76": "#fc9048", "77": "#b44800", "78": "#6c0000",  # tan skin and ears, dark to darkest
    "79": "#fc00fc", "80": "#900090", "81": "#480048",  # pink heart and boots, purple wings
    "82": "#90d8fc", "83": "#6cb4d8", "84": "#246c90",  # blue eyeshadow
    "85": "#fcfc00",  # the "ROUGE" name tag
}
KEY_COLOURS = {  # near-exact matches go in Sonic's slots; the rest are Rouge's own
    "#000000": 1, "#909090": 8, "#484848": 9,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (title, text) in the slot of its nearest key
    colour, so nothing is left to sheet2ani's guess."""
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
# the last frame, the pose held or looped): the ending: waving (Knuckles' build-up frames), then wings out
S3K_VICTORY = {"frames": f(136, 136, 136, 137)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra9",
           "credit": "Rouge the Bat, custom sprites (Sonic 1 style) by DeltaConduit; original sprites by SEGA / Sonic Team - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/565796/",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Knuckles.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **knuckles_only(game)),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra9SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": SPIN, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra9_UI", "manifest": "Extra9_ui.json", "elements": ELEMENTS, "out": "build/Extra9_UI.gif"},
                     {"name": "Extra9_Ending", "manifest": "Extra9_ending.json", "elements": ENDING,
                      "out": "build/Extra9_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "rouge.json"), ("Sonic2", "rouge_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
