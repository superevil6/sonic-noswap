#!/usr/bin/env python3
"""Writes Tikal's sheet2ani configs (tikal.json for Sonic 1, tikal_s2.json for Sonic 2).

Frames are the sprites on Tikal.png ("Tikal the Echidna" by SunnyVies; see SOURCE.txt), numbered as detected:
connected components of everything that isn't the #ffffff sheet background (8-connected, numbered in scan
order). The sheet has no boxes; each sprite is one component, and the mapping follows the sheet's row labels
(Rotation, Look up, Crouch, Sonic 1 idle, Edge, Pushing...).

Template: Sonic's .ani (Sonic's moveset). Her moves, in the appended ability slots:
  41 "Spirit Flight": the sheet's "Spirit Transform" row: she becomes an orange silhouette that shrinks into a
      glowing orb, which then flies trailing sparks (SPIRIT_TRANSFORM / SPIRIT_ORB below)
  43 / 44 "Spirit Orb" / "Spirit Orb Air": the Spirit Orb's throw pose, the "Punching" row's first three frames
      (THROW; the orb is the shot in abilities.py, cut from the "Spirit Transform" row's glowing orbs)

Not used: the "Praying", "Sit", "Adventure walk" (both), "6-frame walk cycle", "Runners run", "Transform",
"Glide", "Landing"'s first frame, "Climbing", "Floating" (both), "Double Jump", "Summoning", "Falling",
"Bonus Emotes" rows, the two fading frames of "Spirit Transform" (they're blended half-transparent, dozens of
in-between colours with no palette slots to hold them exactly), the big artwork, the title-screen heads and
the ring (24x24) and 18x27 icons. Nothing is redrawn, recoloured or resized: frames are cut, the HUD art is
cropped from the sheet's own "Life icons and goalpost", and only the "TIKAL" name tag (not on the sheet) is our
own lettering in the HUD font the other extras use.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402

B = {  # sprite number -> [x, y, w, h] (its bounding box)
    # Rotation, Look up, Crouch
    93: [26, 141, 24, 37], 94: [56, 141, 24, 37], 91: [85, 140, 24, 38], 92: [113, 140, 23, 38],
    95: [142, 141, 22, 37], 96: [174, 141, 21, 37], 97: [340, 141, 25, 37], 98: [368, 141, 25, 37],
    99: [428, 141, 25, 36], 102: [458, 146, 27, 31],
    # Sonic 1 idle, Sonic 2 idle, Alternative idle
    145: [26, 204, 24, 37], 146: [56, 204, 24, 37], 147: [85, 204, 35, 37], 148: [123, 204, 35, 37],
    151: [190, 206, 24, 37], 152: [222, 206, 24, 37], 153: [255, 206, 35, 37], 154: [293, 206, 35, 37],
    149: [391, 204, 27, 39], 157: [423, 207, 24, 37], 156: [453, 206, 24, 38], 150: [486, 205, 24, 39],
    158: [519, 207, 24, 38], 159: [548, 208, 24, 37],
    # Edge, Pushing, Continue
    196: [26, 278, 36, 40], 197: [67, 278, 36, 39], 198: [107, 278, 36, 39], 199: [147, 278, 35, 39],
    200: [246, 280, 30, 38], 201: [282, 280, 26, 39], 202: [313, 281, 29, 38],
    203: [425, 288, 32, 30], 204: [464, 288, 32, 30], 205: [504, 288, 32, 30], 206: [544, 288, 32, 30],
    # Victory Animation, Rolling / Jumping
    243: [26, 360, 27, 38], 241: [56, 355, 28, 42], 242: [88, 356, 29, 41],
    249: [336, 369, 25, 29], 248: [365, 368, 30, 30], 250: [400, 369, 25, 29], 252: [430, 373, 29, 25],
    251: [464, 369, 25, 29], 253: [494, 373, 29, 25],
    # 8-frame walk cycle
    292: [308, 425, 23, 37], 293: [337, 425, 24, 37], 286: [364, 424, 36, 38], 294: [404, 425, 35, 37],
    295: [442, 425, 23, 37], 287: [472, 424, 26, 38], 288: [501, 424, 35, 38], 289: [540, 424, 36, 38],
    # SA2B run, Classic run
    360: [26, 553, 27, 37], 366: [65, 554, 30, 36], 368: [104, 555, 36, 35], 369: [148, 555, 31, 35],
    361: [191, 553, 28, 37], 367: [225, 554, 32, 36], 370: [262, 555, 37, 35], 371: [306, 555, 30, 35],
    362: [425, 553, 31, 37], 363: [462, 553, 32, 37], 364: [501, 553, 31, 37], 365: [537, 553, 31, 37],
    # Skid/ turn around, Hurt, Breathing, Spring jump
    400: [335, 618, 40, 37], 401: [378, 618, 40, 37], 405: [420, 619, 37, 36], 402: [463, 618, 34, 37],
    448: [26, 690, 39, 30], 440: [73, 681, 34, 39], 446: [116, 684, 34, 36],
    447: [346, 686, 34, 36], 442: [384, 681, 30, 41],
    445: [478, 682, 25, 38], 443: [508, 681, 32, 40], 444: [545, 681, 32, 40],
    # Landing (lying flat), Holding bar, Rotating fan, Vine grab
    485: [224, 766, 48, 21], 486: [279, 766, 48, 21], 516: [26, 813, 46, 23], 517: [83, 814, 46, 22],
    513: [209, 811, 34, 24], 511: [252, 810, 42, 25], 512: [304, 810, 46, 25], 510: [357, 809, 45, 24],
    514: [411, 811, 43, 25], 515: [461, 811, 29, 25], 562: [301, 862, 25, 43], 563: [335, 862, 25, 45],
    # Punching, Mid-air punch
    597: [26, 942, 24, 37], 598: [57, 942, 27, 37], 600: [90, 943, 32, 36], 601: [126, 943, 30, 36],
    599: [162, 942, 27, 37],
    595: [245, 938, 25, 41], 593: [276, 937, 27, 42], 591: [309, 933, 23, 46], 594: [339, 937, 24, 42],
    592: [371, 936, 34, 43], 596: [412, 940, 32, 40],
    # Spirit Transform: normal, (fading x2, faded: not used), silhouette x6, orbs; the last four orbs with the
    # sparks they trail (loose pixels below each, x 488-493 / 506-514 / 528-533 / 548-556, y to 1102)
    647: [26, 1068, 34, 37], 650: [174, 1068, 34, 37], 651: [213, 1068, 34, 37], 652: [255, 1068, 34, 37],
    653: [294, 1068, 37, 37], 654: [340, 1068, 33, 32], 655: [380, 1068, 27, 26],
    656: [416, 1068, 16, 16], 657: [438, 1068, 16, 16], 658: [460, 1068, 16, 16],
    659: [483, 1068, 16, 16], 660: [503, 1068, 16, 16], 661: [523, 1068, 16, 16], 662: [544, 1068, 16, 16],
    # Sonic 1 Ending (and the medium-sized leap next to it), Life icons and goalpost
    725: [26, 1231, 24, 37], 724: [57, 1230, 28, 37], 726: [87, 1231, 24, 37], 727: [120, 1231, 31, 37],
    728: [153, 1234, 28, 34], 709: [185, 1200, 57, 68],
    786: [384, 1374, 17, 16], 784: [426, 1367, 15, 22], 785: [447, 1368, 15, 22], 772: [467, 1342, 48, 48],
}
SHEET = "Tikal.png"
BACKGROUND = ["#ffffff"]
SRC = Image.open(HERE / SHEET).convert("RGB")


def trim_origin(rect):
    """Where sheet2ani's trim starts inside `rect`: its first column and row that aren't background."""
    x, y, w, h = rect
    pts = [(i, j) for j in range(h) for i in range(w) if "#%02x%02x%02x" % SRC.getpixel((x + i, y + j)) not in BACKGROUND]
    return min(i for i, _ in pts), min(j for _, j in pts)


def without_corner(n, side):
    """Sprite n, leaving out one pixel of the sheet's "LOOP" bracket that pokes into a bottom corner of its box
    (left or right). The edge column is cut 1 row short and joined back on as a second layer."""
    x, y, w, h = B[n]
    body = [x + 1, y, w - 1, h] if side == "left" else [x, y, w - 1, h]
    edge = [x, y, 1, h - 1] if side == "left" else [x + w - 1, y, 1, h - 1]
    (bx, by), (ex, ey) = trim_origin(body), trim_origin(edge)
    at = [edge[0] + ex - body[0] - bx, edge[1] + ey - body[1] - by]
    return {"layers": [{"rect": body, "at": [0, 0]}, {"rect": edge, "at": at}], "anchor_layer": 0}


def f(*nums):
    return [CLEAN.get(n, B[n]) for n in nums]


CLEAN = {147: without_corner(147, "left"), 148: without_corner(148, "right"), 157: without_corner(157, "left")}


def orb(n):
    """An orb with its trailing sparks, placed by the orb (so the sparks hang below it)."""
    x, y, w, h = B[n]
    return {"rect": [x, y, w, 35], "anchor_box": B[n]}


WALK = f(292, 293, 286, 294, 295, 287, 288, 289)  # "8-frame walk cycle"
RUN = f(362, 363, 364, 365)  # "Classic run"
SA2B_RUN = f(360, 366, 368, 369, 361, 367, 370, 371)  # "SA2B run"
BALL = f(248)[0]  # "Rolling / Jumping": the plain ball
ROLL = f(250, 252, 251, 253)  # ...and the four rolled-up frames
JUMP = [ROLL[0], BALL, ROLL[1], BALL, ROLL[2], BALL, ROLL[3], BALL]
EDGE = f(196, 197, 198, 199)  # "Edge"
# "Rotation": side (92), three-quarter (93, 94), front (91), back three-quarter (95), back (96); the other
# half of the turn is the same frames mirrored
TURN = [B[92], B[93], B[94], B[91], {"rect": B[94], "flip": True}, {"rect": B[93], "flip": True},
        {"rect": B[92], "flip": True}, {"rect": B[95], "flip": True}, B[96], B[95]]

ANIMS = {
    "Stopped": {"frames": f(145)},  # "Sonic 1 idle" frame 1 (also the Origins select card)
    "Looking Up": {"frames": f(97, 98), "loop": 1},  # "Look up"
    "Looking Down": {"frames": f(99, 102), "loop": 1, "align": True},  # "Crouch"
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f(400, 401), "align": True},  # "Skid/ turn around"
    "Super Peel Out": {"frames": SA2B_RUN, "rot": 2, "align": True},  # "SA2B run": her fastest-looking run
    "Spin Dash": {"frames": ROLL, "anchor": "center"},
    "Jumping": {"frames": JUMP, "anchor": "center"},
    "Bouncing": {"frames": f(443), "anchor": "center"},  # "Spring jump", arms up
    "Hurt": {"frames": f(448), "anchor": "center"},  # "Hurt": thrown back
    "Dying": {"frames": f(446), "anchor": "center"},  # "Hurt": front-on, mouth open
    "Drowning": {"frames": f(442), "anchor": "center"},  # "Breathing": the second (choking) frame
    "Fan Rotate": {"frames": f(513, 511, 512, 510, 514, 515), "anchor": "center"},  # "Rotating fan"
    "Breathing": {"frames": f(447), "anchor": "center"},  # "Breathing": the gasp
    "Pushing": {"frames": f(200, 201, 202, 201), "align": True},
    "Flailing 1": {"frames": f(196, 197), "align": True},  # "Edge"
    "Flailing 2": {"frames": f(198, 199), "align": True},
    "Hanging": {"frames": f(562, 563), "anchor": "center"},  # "Vine grab": arms up, holding on
    "Clinging On": {"frames": f(516, 517), "anchor": "center"},  # "Holding bar" (flat out in the current)
    "Corkscrew H": {"frames": TURN},  # "Rotation"
    "Water Slide": {"frames": f(485, 486), "anchor": "center"},  # "Landing": lying flat, sliding
    "Continue": {"frames": f(203, 204, 205, 206)},  # "Continue"
    "Continue Up": {"frames": f(444), "loop": 0},  # "Spring jump"
    "Super Transform": {"frames": f(145), "loop": 0},
}
S1_ONLY = {
    "Waiting": {"frames": f(145, 146, 147, 148), "loop": 2},  # "Sonic 1 idle" (the sheet's LOOP: the last two)
}
S2_ONLY = {
    "Waiting": {"frames": f(151, 152, 153, 154), "loop": 2},  # "Sonic 2 idle" (LOOP: the last two)
    "Bored!": {"frames": f(149, 157, 156, 150, 158, 159), "loop": 1},  # "Alternative idle" (LOOP: from 157)
    "Flailing 1": {"frames": EDGE, "align": True},
    "Flailing 3": {"frames": EDGE, "align": True},
    "Grabbed": {"frames": f(448), "anchor": "center"},
    "Twirl H": {"frames": TURN, "rot": 2},
    "Skidding": {"frames": f(400, 401, 405), "loop": 2, "align": True},
}

# Spirit Flight (slot 41). Frames 0-9 are the transform (her, then the silhouette shrinking to the first orb):
# 647, 650, 651, 652, 653, 654, 655, 656, 657, 658. Frames 10-13 are the orb loop (659-662, glowing, sparks
# trailing below): "loop": 10. Centred, so the orb sits where her middle was.
SPIRIT_TRANSFORM = f(647, 650, 651, 652, 653, 654, 655, 656, 657, 658)
SPIRIT_ORB = [orb(n) for n in (659, 660, 661, 662)]
SPIRIT_LOOP = len(SPIRIT_TRANSFORM)

# Spirit Orb throw pose (slots 43 / 44; the orb itself is the shot, abilities.py): the "Punching" row's wind-up, jab
# and full reach, her arm thrust out ahead; the pose is the last frame (600). The same frames in the air, centred
THROW = f(597, 598, 600)
THROW_REACH = [12, 15, 21]  # how far ahead of her centre each reaches, px (the old punch's)
PUNCH = f(597, 598, 600, 601, 599)  # "Punching": wind up, jab out, full reach, back, recovered
# "Mid-air punch": side, uppercut, back, then (drawn facing left) turning and punching, and front-on. The two
# left-facing frames are mirrored so the spin ends with the punch forwards, where the hitbox is
PUNCH_AIR = [B[595], B[593], B[591], {"rect": B[594], "flip": True}, {"rect": B[592], "flip": True}, B[596]]
# How far ahead of her centre (the pivot) the art reaches per frame, px, as built (for the move's hitbox):
# ground: wind-up (body only), fist half out, full reach, coming back, back at the chest; air: the fist is
# forward in frames 0 and 4 (13, 17 px); frame 1 is the uppercut (fist 21 px above centre, 14 ahead); 2-3 are
# the spin (12 px, no fist forward); 5 is front-on, both fists out 16 px each side
PUNCH_REACH = [12, 15, 21, 18, 15]
PUNCH_AIR_REACH = [13, 14, 12, 12, 17, 16]
APPENDED = {
    "41": {"name": "Spirit Flight", "frames": SPIRIT_TRANSFORM + SPIRIT_ORB, "anchor": "center", "speed": 60,
           "loop": SPIRIT_LOOP},
    "43": {"name": "Spirit Orb", "frames": THROW, "speed": 80, "align": True},
    "44": {"name": "Spirit Orb Air", "frames": THROW, "anchor": "center", "speed": 80},
}


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
LIFE = B[786]  # "Life icons and goalpost": her head, 17x16 with black rows top and bottom
SIGN = B[772]  # the goalpost: pole stub (2 rows), the 30-row board, then the pole
ELEMENTS = {
    # the head without its rightmost column (a plain light-grey edge), to keep Sonic's 16x16
    "life_icon": {"rect": [LIFE[0], LIFE[1], 16, 16], "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("TIKAL")},
    "monitor_1up": {"rect": [LIFE[0], LIFE[1] + 1, 16, 14], "trim": False},  # the icon's middle rows
    "sign_face": {"rect": [SIGN[0], SIGN[1], 48, 32], "trim": False},  # stub and board, without the pole
    "mini_1": {"rect": B[784], "remap": PLUS_128},  # the two small standing sprites (15x22)
    "mini_2": {"rect": B[785], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[725], "remap": PLUS_128},  # "Sonic 1 Ending"
    "end_pose_1": {"rect": B[727], "remap": PLUS_128},  # ...arms out
    "end_pose_2": {"rect": B[242], "remap": PLUS_128},  # "Victory Animation": the leap
    # the medium leap next to "Sonic 1 Ending" (57x68); the big artwork (126x142) is too big for the shared sheet
    "end_pose_3": {"rect": B[709], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((725, 724, 726, 727, 728, 243), 1)},
}

PALETTE = {  # Tikal's own colours, in the extras' shared global palette slots 74+
    "74": "#ef8741", "75": "#d24b1e", "76": "#f2be84",  # orange fur and hair: mid, dark, light
    "77": "#a0a0c0", "78": "#606080", "79": "#fcfcfc",  # lavender-grey gloves and shoes, shading; white
    "80": "#e7b39a", "81": "#edc598",  # skin, cream
    "82": "#0363d2",  # blue (jewel, cuffs)
    "83": "#1b6d24", "84": "#359f47",  # green skirt, dark and light
    "85": "#c00020",  # red
    "86": "#f3bb10",  # gold headband; the signpost's board
    "87": "#fcfc00",  # the "TIKAL" name tag
    # one-off shades on a few frames that are too far from their neighbours above to merge
    "88": "#c46a09",  # brownish orange ("Landing")
    "89": "#22b14c",  # bright green
    "90": "#c3c3c3",  # light grey
    "91": "#ff7f27",  # bright orange ("Holding bar")
    "92": "#ffc90e",  # gold (the small standing sprites)
}
KEY_COLOURS = {  # exact matches go in Sonic's slots; black shares Sonic's (#080000) like the other extras'
    "#000000": 1, "#e0e0e0": 6, "#a06040": 11,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (a few one-off shades, the blended fade frames, the
    artwork) in the slot of its nearest key colour, so nothing is left to sheet2ani's guess."""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


COLOURS = all_colours()


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the sheet's "Victory Animation": the hop looping
S3K_VICTORY = {"frames": f(243, 241, 242), "pose": 1}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra16",
           "credit": "Tikal the Echidna - sprites by SunnyVies; thanks to Skylights1, E-122-Psi, CreamTheRabbit, "
                     "Cylent Nite, Mod. Gen Project Team, Deebs and NinjaRaccoon - "
                     "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/268711/",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else S1_ONLY)),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra16SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": JUMP, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra16_UI", "manifest": "Extra16_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra16_UI.gif"},
                     {"name": "Extra16_Ending", "manifest": "Extra16_ending.json", "elements": ENDING,
                      "out": "build/Extra16_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "tikal.json"), ("Sonic2", "tikal_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("throw reach:", THROW_REACH)
