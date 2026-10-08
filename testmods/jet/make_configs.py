#!/usr/bin/env python3
"""Writes Jet's sheet2ani configs (jet.json for Sonic 1, jet_s2.json for Sonic 2).

Jet the Hawk, extra 21 (file "Extra21", character ID 27), base character Sonic.
Sheet: Jet.png (a copy of testmods/Jet.png), "Jet the Hawk" by Gabriel Frag (Gabriel_aka_Frag); see SOURCE.txt.

Frames are the sprites on the sheet, numbered as detected: connected components of everything that isn't the
#ffffff sheet background (8-connected), sorted by top edge, then left edge. The sheet has no boxes or row labels.
White is background only: the artist's palette strip (sprite 866) has no pure white (his whites are #e0e0e0),
and the only enclosed #ffffff pixels are 1-3 px gaps between hair spikes / arms, which are background there too.

Layout (y): 70-420 head expressions (overlay heads for the body frames, 27x30 side / 21x27 front; used only
for the HUD icon and signpost), 500-1400 the body frames, from 1460 the SPARE PARTS (hands, legs, shoes, heads,
boards at every angle, props, wind swooshes, palette strips).

Template: Sonic's .ani (Sonic's moveset). Walk / run are upright frames only ("rot": 2, the engine turns them).
The sheet has no run cycle: "Running" uses the whole 8-frame walk (RUN_FULL), "Super Peel Out" every other frame (RUN).

Abilities (appended slots; the moves are wired elsewhere):
  41 "Extreme Gear": the board rows: he pulls his board out (473, 474), drops it level (480) and steps on (484),
      then rides it, balancing, side-on (476, 482, 483, 482). "loop": 4 (the ride), GEAR_LOOP below.
  43 / 44 "Tornado Trap" / "Tornado Trap Air": the throw pose (THROW: 525, 527, 530; the whirlwind is the shot in
      abilities.py, the SPARE PARTS swirls). The old Tornado swing (unused now): the sheet has no fan (Bashosen). His whirl-around swing is on it (525 fist
      out, 527 twisting, 530 / 535 spinning in a wind swoosh, 539 the finish); the SPARE PARTS swooshes (841 small
      streak, 856 long streak, 847 thin arc, 843 big crescent) are composed ahead of him as a whirlwind that
      grows frame by frame (TORNADO below). Reach per frame (px ahead of his centre) is printed when this runs.

Not used: the head expression grid (portrait overlays), the Wave the Swallow frames (507, 515), the Sonic Riders /
title logos and artist banner, the second (dark) board rows (501-509, 514), chair / TV / case props, the 2006 /
2011 comparison line-up, the "cracker" gag strip, loose limbs. Nothing is redrawn, recoloured or resized:
frames are cut (the Water Slide pair is mirrored); the HUD icons are crops of the sheet's front head; only the
"JET" name tag (not on the sheet) is our own lettering in the HUD font the other extras use.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
from sign_face import board_face  # noqa: E402
SHEET = "Jet.png"
BACKGROUND = ["#ffffff"]
SRC = Image.open(HERE / SHEET).convert("RGB")

B = {  # sprite number -> [x, y, w, h] (its bounding box)
    # heads (front), row 1: stand (329), walk (335-338), the snooty arms-crossed wait (339-342)
    11: [217, 73, 21, 27],
    329: [25, 501, 31, 48], 335: [62, 502, 26, 47], 324: [95, 500, 27, 49], 325: [130, 500, 39, 49],
    336: [175, 502, 38, 47], 337: [219, 502, 26, 47], 326: [255, 500, 29, 49], 327: [295, 500, 37, 49],
    338: [339, 502, 37, 47], 339: [430, 504, 33, 45], 340: [467, 504, 33, 45], 341: [506, 504, 33, 45],
    342: [545, 504, 35, 45],
    # row 2: hand on hip, blink, foot tap (347-355), look up (363), balancing (346, 356, 357 forward; 362, 360,
    # 361 back), crouch (364, 365)
    347: [25, 571, 31, 48], 348: [65, 571, 31, 48], 349: [104, 571, 31, 48], 350: [142, 571, 31, 48],
    351: [180, 571, 31, 48], 354: [299, 571, 31, 48], 363: [387, 574, 27, 45],
    346: [426, 570, 39, 49], 356: [470, 571, 38, 48], 357: [512, 571, 36, 48],
    362: [556, 573, 38, 46], 360: [600, 572, 36, 47], 361: [644, 572, 35, 47],
    364: [690, 581, 33, 38], 365: [729, 588, 35, 31],
    # row 3: the 12-frame turn (366 front ... 369 side ... 372 back ...), spin dash ovals, the ball and the
    # four rolled-up frames
    366: [26, 639, 22, 48], 367: [60, 639, 25, 48], 368: [94, 639, 31, 48], 369: [135, 639, 29, 48],
    370: [175, 639, 25, 48], 371: [214, 639, 23, 48], 372: [250, 639, 21, 48], 373: [282, 639, 23, 48],
    374: [319, 639, 25, 48], 375: [355, 639, 29, 48], 376: [394, 639, 31, 48], 377: [434, 639, 25, 48],
    383: [468, 660, 30, 27], 384: [503, 660, 30, 27], 385: [538, 660, 30, 27], 386: [573, 660, 30, 27],
    387: [608, 660, 30, 27], 388: [643, 660, 30, 27],
    380: [678, 657, 30, 30], 378: [718, 656, 29, 31], 381: [754, 657, 31, 29], 379: [795, 656, 29, 31],
    382: [836, 657, 31, 29],
    # row 4: lying flat (405-408), hurt (398, 399), front: arms out (390), mouth open (393), finger wag (392)
    406: [232, 732, 46, 21], 407: [283, 735, 46, 18], 408: [334, 736, 46, 17], 405: [386, 728, 55, 25],
    398: [457, 718, 39, 35], 399: [503, 719, 39, 34], 390: [553, 704, 33, 49], 393: [633, 714, 33, 39],
    392: [791, 705, 36, 48],
    # row 5: lying on his belly kicking (424-427), pushing (414-417), victory (409, 410, 413)
    424: [31, 790, 43, 33], 425: [81, 790, 43, 33], 426: [135, 790, 43, 33], 427: [185, 790, 43, 33],
    414: [450, 780, 24, 43], 415: [484, 780, 27, 43], 416: [523, 780, 23, 43], 417: [557, 780, 26, 43],
    409: [747, 775, 35, 48], 410: [791, 778, 36, 45], 413: [833, 779, 38, 44],
    # row 6: flying flat, arms forward (449, 450), skid (440, 441, 444, 445), spring (435), gasp (443)
    449: [122, 863, 53, 31], 450: [186, 865, 52, 29],
    440: [336, 848, 38, 46], 441: [377, 848, 37, 46], 444: [423, 850, 34, 44], 445: [544, 852, 37, 42],
    435: [469, 845, 29, 49], 443: [590, 849, 32, 45],
    # row 7: hanging from a bar (460, 461), sliding on his back (468, 469)
    460: [199, 914, 33, 48], 461: [244, 914, 32, 48], 468: [522, 927, 55, 27], 469: [585, 928, 55, 27],
    # rows 8-9: Extreme Gear (the green board)
    473: [28, 980, 37, 55], 474: [76, 980, 37, 55], 480: [193, 987, 55, 48], 476: [355, 985, 55, 51],
    482: [424, 988, 55, 48], 483: [492, 989, 55, 47], 477: [816, 985, 57, 50], 484: [16, 1056, 54, 57],
    # row 11: the whirl-around swing (530 and 535 with their swoosh's loose pixels, 1-3 rows above the bbox)
    525: [423, 1202, 31, 47], 527: [465, 1203, 30, 46], 530: [503, 1204, 43, 45], 535: [553, 1206, 44, 43],
    539: [602, 1216, 42, 33],
    # row 12: crouching front-on, powering up (564-567)
    564: [28, 1285, 23, 30], 565: [62, 1285, 23, 30], 566: [92, 1285, 37, 30], 567: [133, 1285, 37, 30],
    # SPARE PARTS wind swooshes (with their loose pixels)
    841: [29, 1740, 20, 10], 843: [56, 1740, 33, 39], 847: [121, 1741, 13, 35], 856: [97, 1766, 26, 13],
}


def f(*nums):
    return [B[n] for n in nums]


def trim_box(rect):
    """The sheet box of the non-background pixels inside `rect` (what sheet2ani's trim keeps)."""
    x, y, w, h = rect
    pts = [(i, j) for j in range(h) for i in range(w) if "#%02x%02x%02x" % SRC.getpixel((x + i, y + j)) not in BACKGROUND]
    x0, y0 = min(i for i, _ in pts), min(j for _, j in pts)
    x1, y1 = max(i for i, _ in pts), max(j for _, j in pts)
    return [x + x0, y + y0, x1 - x0 + 1, y1 - y0 + 1]


def feet_box(n):
    """The shoes: the bottom 8 rows of sprite n, trimmed. Its middle is the pivot of a composed frame."""
    x, y, w, h = B[n]
    return trim_box([x, y + h - 8, w, 8])


def compose(n, extras=()):
    """Sprite n with wind pieces around it. extras: (piece number, dx, dy): the piece's top-left, px from the
    pivot (the middle of his shoes, dx) and the ground (the shoes' bottom row + 1, dy). The shoes are added once
    more as the last (anchor) layer, the same pixels in the same place, so every frame is placed by its feet
    and the pieces don't shift him. Returns (frame, reach): reach = how far the art goes ahead of the pivot."""
    fx, fy, fw, fh = feet_box(n)
    px, ground = fx + fw // 2, fy + fh
    body = trim_box(B[n])
    layers, right = [], body[0] + body[2] - px
    for piece, dx, dy in extras:
        t = trim_box(B[piece])
        layers.append({"rect": B[piece], "at": [px + dx - fx, ground + dy - fy]})
        right = max(right, dx + t[2])
    layers.append({"rect": B[n], "at": [body[0] - fx, body[1] - fy]})
    layers.append({"rect": [fx, fy, fw, fh], "at": [0, 0]})
    return {"layers": layers, "anchor_layer": len(layers) - 1}, right


WALK = f(335, 324, 325, 336, 337, 326, 327, 338)  # 8-frame walk: legs together, stride, ... (both steps)
RUN_FULL = f(325, 336, 337, 326, 327, 338, 335, 324)  # "Running": all 8 walk frames from a stride (4 looked frantic)
RUN = f(325, 337, 327, 335)  # no run on the sheet: every other walk frame (stride, legs passing, stride, legs
# passing). The two strides and their landings (325, 336, 327, 338) looked like the same foot forward every step
BALL = B[380]
ROLL = f(378, 381, 379, 382)  # the rolled-up frames: body turning inside the ball
JUMP = [ROLL[0], BALL, ROLL[1], BALL, ROLL[2], BALL, ROLL[3], BALL]
SPINDASH = f(383, 384, 385, 386, 387, 388)  # the squashed ovals, highlight going round
TURN = f(369, 370, 371, 372, 373, 374, 375, 376, 377, 366, 367, 368)  # the turn, starting side-on

ANIMS = {
    "Stopped": {"frames": f(329)},  # standing (also the Origins select card)
    "Looking Up": {"frames": f(329, 363), "loop": 1},
    "Looking Down": {"frames": f(364, 365), "loop": 1, "align": True},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN_FULL, "rot": 2, "align": True},  # the whole walk cycle: half the leg speed of RUN
    "Skidding": {"frames": f(440, 441), "align": True},
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Spin Dash": {"frames": SPINDASH, "anchor": "center"},
    "Jumping": {"frames": JUMP, "anchor": "center"},
    "Bouncing": {"frames": f(435), "anchor": "center"},  # springing up, looking up
    "Hurt": {"frames": f(398), "anchor": "center"},  # thrown back
    "Dying": {"frames": f(390), "anchor": "center"},  # front-on, arms and legs out
    "Drowning": {"frames": f(393), "anchor": "center"},  # front-on, beak wide open
    "Fan Rotate": {"frames": f(406, 407, 408, 405), "anchor": "center"},  # lying flat, seen from round about
    "Breathing": {"frames": f(443), "anchor": "center"},  # the gasp
    "Pushing": {"frames": f(414, 415, 416, 417), "align": True},
    "Flailing 1": {"frames": f(346, 356), "align": True},  # teetering forward on one foot
    "Flailing 2": {"frames": f(362, 360), "align": True},  # leaning back
    "Hanging": {"frames": f(460, 461), "anchor": "center"},  # arms up, holding on
    "Clinging On": {"frames": f(449, 450), "anchor": "center"},  # flat out, arms forward (the current)
    "Corkscrew H": {"frames": TURN},
    "Water Slide": {"frames": [{"rect": B[468], "flip": True}, {"rect": B[469], "flip": True}],
                    "anchor": "center"},  # on his back, feet first (drawn facing left)
    "Continue": {"frames": f(424, 425, 426, 427)},  # lying on his belly, kicking his feet
    "Continue Up": {"frames": f(365, 364, 363), "loop": 2},  # getting up, looking up
    "Super Transform": {"frames": f(564, 565, 566, 567), "loop": 2},  # crouched front-on, powering up
}
S1_ONLY = {
    "Waiting": {"frames": f(347, 348, 349, 350, 351, 350), "loop": 4},  # hand on hip, blink, foot tap
}
S2_ONLY = {
    "Waiting": {"frames": f(347, 348, 347, 354, 349, 350, 351, 350), "loop": 4},
    "Bored!": {"frames": f(342, 339, 340, 341, 340), "loop": 1},  # finger wag, then arms crossed
    "Skidding": {"frames": f(440, 441, 444, 445), "loop": 2, "align": True},
    "Flailing 1": {"frames": f(346, 356, 357, 356), "align": True},
    "Flailing 3": {"frames": f(360, 361, 362, 361), "align": True},
    "Grabbed": {"frames": f(398, 399), "anchor": "center"},
    "Twirl H": {"frames": TURN, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# Extreme Gear (slot 41): pulls the board out (473, 474), drops it level (480), steps on (484), then rides it
# side-on, arms out balancing (476, 482, 483, 482): "loop": 4
GEAR_START = f(473, 474, 480, 484)
GEAR_RIDE = f(476, 482, 483, 482)
GEAR_LOOP = len(GEAR_START)

# Tornado (slots 43 / 44): the whirl-around swing with the whirlwind growing ahead of him. (piece, dx, dy):
# dx from his middle, dy from the ground (negative = up)
TORNADO_SPEC = [
    (525, []),  # fist out
    (527, []),  # twisting round, a swoosh behind his head
    (530, [(841, 20, -12)]),  # spinning in his swoosh; a puff of wind ahead
    (535, [(856, 20, -14), (841, 26, -26)]),  # the wind stretches and rises
    (539, [(856, 22, -14), (847, 44, -34), (841, 28, -30)]),  # it starts to turn
    (539, [(843, 24, -39), (847, 52, -36), (856, 30, -14)]),  # a whirlwind ahead of him
    (539, [(843, 30, -40), (847, 58, -37), (841, 36, -48), (856, 36, -14)]),  # full size, moving on
]
TORNADO, TORNADO_REACH = zip(*(compose(n, extras) for n, extras in TORNADO_SPEC))
TORNADO, TORNADO_REACH = list(TORNADO), list(TORNADO_REACH)
# Tornado Trap throw pose (slots 43 / 44; the whirlwind itself is the shot, abilities.py, cut from the SPARE PARTS
# swirls): fist out, twisting round, then spinning in his own swoosh (530), the pose held while the whirlwind goes out
THROW, THROW_REACH = zip(*(compose(n) for n in (525, 527, 530)))
THROW, THROW_REACH = list(THROW), list(THROW_REACH)

APPENDED = {
    "41": {"name": "Extreme Gear", "frames": GEAR_START + GEAR_RIDE, "speed": 60, "loop": GEAR_LOOP,
           "align": True},
    "43": {"name": "Tornado Trap", "frames": THROW, "speed": 60},
    "44": {"name": "Tornado Trap Air", "frames": THROW, "speed": 60},
}


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#f7cb00", "1": "#000000"}  # his own gold (the HUD's #fcfc00 has no slot to spare)
HEAD = B[11]  # the front head (21x27): crest, goggles, eyes, beak
ELEMENTS = {
    # the head's goggles, eyes and beak (its middle 16 columns, the 16 rows from the goggles down)
    "life_icon": {"rect": [HEAD[0] + 2, HEAD[1] + 10, 16, 16], "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("JET")},
    "monitor_1up": {"rect": [HEAD[0] + 2, HEAD[1] + 11, 16, 14], "trim": False},
    # no signpost art: the front head on the game's own board (Items2), enlarged 1.2x nearest-neighbour to fill its
    # 40x24 face area (the user's signpost exception; tools/sign_face.py: the crest's top is trimmed, the beak stays)
    "sign_face": board_face(HEAD, 1.2),
    "mini_1": {"rect": B[349], "remap": PLUS_128},  # full size (no small set on the sheet): foot tap
    "mini_2": {"rect": B[351], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[329], "remap": PLUS_128},
    "end_pose_1": {"rect": B[409], "remap": PLUS_128},  # victory: both hands up
    "end_pose_2": {"rect": B[413], "remap": PLUS_128},  # victory: V-signs, leaning in
    "end_pose_3": {"rect": B[477], "remap": PLUS_128},  # a trick on his board (57x50), the biggest pose
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((347, 392, 342, 409, 410, 413), 1)},
}

# The built frames use 40 colours. #e0e0e0, #e00000 and #800000 are exactly Sonic's slots 6, 12 and 13; the
# extras have 22 own slots (74-95), so the 22 most-used of the rest keep their exact values there, and the other
# 15 (4,300 px of about 115,000) share the slot of their nearest colour (MERGED; the distance is RGB distance).
PALETTE = {
    "74": "#069432", "75": "#0a6419", "76": "#043810", "77": "#0b5d39", "78": "#3fbe5d", "79": "#10a36b",  # greens
    "80": "#202020",  # outlines
    "81": "#606080", "82": "#a0a0c0", "83": "#c0c0e0",  # lavender greys (gloves, goggles, chest)
    "84": "#f7cb00", "85": "#db9e00", "86": "#a27912", "87": "#fff681",  # gold beak and goggle lenses
    "88": "#c93900",  # orange-red (eyes, beak line)
    "89": "#0171ab", "90": "#33a1ce", "91": "#003d5d",  # blue eyes
    "92": "#1dd312", "93": "#6df565", "94": "#03a710", "95": "#b3ffa4",  # the Extreme Gear's greens
}
MERGED = {  # colour: (slot, why)
    "#737478": (8, "board / sole grey -> Sonic's #808080 (distance 19)"),
    "#a2a5a2": (7, "board grey -> Sonic's #a0a0a0 (6)"),
    "#8c1606": (13, "dark red (eye) -> Sonic's #800000 (26)"),
    "#5e0100": (14, "darkest red -> Sonic's #400000 (30)"),
    "#0b100a": (1, "near-black, 7 px -> Sonic's #080000 (19)"),
    "#daffd4": (6, "the board's glow highlight -> Sonic's #e0e0e0 (34)"),
    "#fffbff": (6, "a near-white glint, 8 px -> #e0e0e0"),
    "#ffb9b9": (83, "1 px -> #c0c0e0"),
    "#191919": (80, "near-black, 35 px -> #202020 (12)"),
    "#9797b9": (82, "-> #a0a0c0 (15)"),
    "#b9b9dc": (83, "-> #c0c0e0 (11)"),
    "#b4ffa5": (95, "-> #b3ffa4 (1)"),
    "#86e78a": (93, "6 px -> #6df565"),
    "#54bde1": (90, "the eyes' lightest blue, 84 px -> #33a1ce (47)"),
    "#178617": (74, "a board green, 123 px -> #069432 (35)"),
}
KEY_COLOURS = {"#000000": 1, "#e0e0e0": 6, "#e00000": 12, "#800000": 13,
               **{c: s for c, (s, _) in MERGED.items()}, **{c: int(s) for s, c in PALETTE.items()}}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (logos, Wave, props, text) in the slot of its nearest
    key colour, so nothing is left to sheet2ani's guess."""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


CREDIT = ("Jet the Hawk sprites made by Gabriel Frag (Gabriel_aka_Frag) - \"Feel free to use this sheet in "
          "anyway. And if you use this in any manner i would appriciate if you credit me. Don't steal or claim as "
          "your own. And if you put this up on a website leave the tag and credits.\" Jet the Hawk (c) SEGA - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/96370/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the sheet's victory: hands up, then the V-signs swaying
S3K_VICTORY = {"frames": f(409, 410, 413), "pose": 1}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra21", "credit": CREDIT,
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else S1_ONLY)),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra21SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": JUMP, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra21_UI", "manifest": "Extra21_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra21_UI.gif"},
                     {"name": "Extra21_Ending", "manifest": "Extra21_ending.json", "elements": ENDING,
                      "out": "build/Extra21_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "jet.json"), ("Sonic2", "jet_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("tornado trap throw reach (px ahead of his middle, per frame):", THROW_REACH)
