#!/usr/bin/env python3
"""Writes Max's sheet2ani configs (max.json for Sonic 1, max_s2.json for Sonic 2).

Frames are the dark boxes on Max.png ("Max, The Rabbit Or Whatever You Wanna Call Him In Sonic 1" by Akimaca; see
SOURCE.txt), numbered as detected: connected components of everything that isn't the #7aca7f sheet background
(8-connected, numbered in scan order). The sheet labels its rows (Idle, Waiting, Walking...), and the mapping
follows them.

Template: Sonic's .ani. The sheet has no glide or climb art (so not Knuckles'), and though it has a "Flying"
pose (helicopter ears), it's two frames with no tired or swimming art; Max's signature move is the sheet's
"Grab" (his ear shoots out, the "Example" shows it), which fits NoSwap ability slots on Sonic's set better
than Tails' flight would. His moves:
  ear_grapple (slot 41) "Ear Grapple": his ear shoots out 45 degrees up and forward ("Grab air" plus the sheet's
      diagonal "Grab" ear piece, placed as in the sheet's "Example"), growing a crop at a time; latched, he's
      reeled in with the ear shortening (the code picks the frame; tip per frame in GRAPPLE_TIP below)
  hover (slot 42): keep holding jump to whirl his ears like a helicopter ("Flying")
  melee (slots 43/44) "Ear Boomerang": only the throw pose ("Grab idle" / "Grab air" with the ear flicked out,
      then without it); the boomerang is the shot in tools/abilities.py: the diagonal "Grab" ear piece, spun
      (the old "Ear Jab" frames, ear_jab below, are unused)

Not used: "Jump" and "Fall" (Sonic's set has no uncurled air poses), "Burnt", "Laugh", the second "Victory"
frame, the vertical "Grab" ear piece and the "Grab spin" balls, the two small face pieces next to "Golf forever", the unboxed "Example", cameo and "Scraped/Test" sprites, the
"Palette's & ALTS" boxes, the alternative name tags ("ALTS"), and the large "End Sprite" (116x176).
Nothing is redrawn or resized: frames are cut (the ear lengths are crops of the sheet's ear), composites are
the sheet's own pieces, and the HUD art is cropped from the sheet's own.
"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

B = {  # box number -> [x, y, w, h]
    # Idle, Waiting, Look Up, Crouch, Spring
    86: [9, 80, 30, 38], 80: [49, 75, 26, 43], 81: [84, 75, 26, 43], 84: [119, 77, 24, 41], 82: [152, 75, 26, 43],
    90: [186, 83, 29, 35], 91: [223, 94, 23, 24], 83: [254, 75, 26, 43],
    # Walking, Skidding, Bubble
    139: [17, 140, 27, 37], 131: [53, 139, 32, 38], 132: [94, 139, 28, 38], 140: [130, 140, 28, 37],
    133: [164, 139, 33, 38], 134: [205, 139, 34, 38], 146: [249, 142, 28, 35], 145: [279, 141, 29, 36],
    147: [318, 142, 31, 35],
    # Running, Balance, Hurt/Slide
    231: [19, 196, 32, 36], 232: [58, 196, 32, 36], 233: [97, 196, 32, 36], 234: [136, 196, 32, 36],
    235: [185, 199, 37, 33], 236: [229, 199, 36, 33], 239: [275, 203, 39, 29], 238: [317, 202, 41, 30],
    # Spin, Pushing, Cling
    286: [18, 263, 30, 30], 287: [51, 263, 30, 30], 288: [83, 263, 30, 30], 289: [117, 263, 31, 30],
    290: [151, 263, 30, 30],
    281: [193, 260, 24, 33], 279: [225, 259, 21, 34], 282: [253, 260, 23, 33], 280: [283, 259, 21, 34],
    292: [318, 275, 65, 18], 293: [387, 275, 63, 18],
    # Death, Drown, Continue, Labyrinth spin
    326: [22, 316, 31, 38], 327: [61, 316, 31, 38],
    328: [108, 326, 36, 28], 329: [151, 326, 36, 28], 330: [192, 326, 36, 28],
    331: [238, 331, 41, 23], 332: [284, 331, 38, 23], 333: [327, 331, 37, 23],
    # Normal ending, Good ending
    400: [20, 383, 26, 43], 406: [50, 392, 29, 34],
    403: [97, 384, 28, 42], 404: [129, 384, 28, 42], 405: [162, 390, 31, 36], 401: [199, 383, 32, 43],
    402: [236, 383, 32, 43], 407: [273, 392, 29, 34],
    # End Sprite (small, large), Signpost, Continue Icon (both minis in one box), Life Counter
    562: [21, 520, 60, 96], 470: [111, 451, 116, 176],
    461: [276, 448, 48, 59], 479: [335, 460, 43, 24], 563: [276, 521, 38, 16],
    # Extras: Laugh, Victory
    324: [603, 302, 28, 39], 321: [641, 301, 28, 40], 299: [682, 296, 30, 45], 319: [716, 299, 42, 42],
    320: [762, 299, 42, 42],
    # Extras: Golf forever (389 holds two small face pieces), Flying, Spindash
    385: [592, 362, 22, 38], 389: [617, 365, 12, 18], 380: [632, 360, 33, 40], 381: [669, 360, 33, 40],
    383: [706, 361, 32, 39], 382: [742, 360, 33, 40], 384: [779, 361, 32, 39],
    408: [500, 392, 32, 52], 409: [538, 392, 32, 52],
    425: [583, 417, 28, 27], 426: [621, 417, 28, 27], 427: [661, 417, 28, 27], 428: [699, 417, 28, 27],
    429: [742, 417, 28, 27], 430: [783, 417, 29, 27],
    # Extras: Spring twirl, Grab idle, Grab spin (level, diagonal, vertical), Jump, Fall, Burnt
    480: [473, 465, 23, 41], 481: [501, 465, 23, 41], 482: [530, 465, 23, 41], 490: [574, 478, 23, 28],
    491: [616, 484, 36, 22], 487: [656, 474, 27, 32], 485: [688, 470, 22, 36],
    483: [718, 465, 26, 42], 486: [748, 472, 28, 35], 484: [783, 469, 31, 38],
    # Extras: Mach run, Grab air, Grab (the ear: level, diagonal, vertical)
    565: [454, 525, 41, 33], 566: [500, 525, 41, 33], 567: [546, 525, 41, 33], 568: [592, 525, 41, 33],
    569: [659, 528, 26, 30], 605: [658, 592, 77, 7], 582: [742, 546, 54, 53], 564: [804, 524, 9, 75],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "Max.png"
BACKGROUND = ["#7aca7f", "#1e8818"]  # the sheet, and the boxes the frames sit in

WALK = f(139, 131, 132, 140, 133, 134)  # "Walking"
RUN = f(231, 232, 233, 234)  # "Running"
MACH_RUN = f(565, 566, 567, 568)  # "Mach run" (Extras): the run with a white speed ring round his feet
SPIN = f(286, 287, 288, 289, 290)  # "Spin": curled frames, then the ball (Sonic 1's jump pattern)
SPINDASH = f(425, 426, 427, 428, 429, 430)  # "Spindash" (Extras)
BALANCE = f(235, 236)
HURT_SLIDE = f(239, 238)
SPRING_TWIRL = f(480, 481, 482)  # "Spring twirl" (Extras): side, front, back
# "Flying": the same body under a different rotor blur. Placed by his body, not the blur: 409 is 408 with
# the body drawn 5 px further left in an equal box (a pixel-perfect match), so its anchor moves 5 px left
FLYING = [{"rect": B[408], "anchor_box": B[408]},
          {"rect": B[409], "anchor_box": [B[409][0] - 5, B[409][1], B[409][2], B[409][3]]}]
GOLF = f(385, 380, 381, 383, 382, 384)  # "Golf forever" (Extras): club out, address, swing, follow through, watch

# The "Grab" ear (605): its pixels are x 660-732, y 594-598, the rounded tip at the right. In the sheet's
# "Example" it sits 12 px right of and 1 px above the "Grab idle" box's top-left (its dark base overlapping his
# head); "Grab air" has the head in the same place in its box. A shorter ear is a crop of the tip end, so its
# base still sits on his head and the tip reaches out.
EAR_RIGHT, EAR_TOP, EAR_LEN, EAR_AT = 733, 594, 73, (12, -1)


def ear(body, length):
    """The body box with the ear sticking out `length` px (drawn over the head, as in the "Example")."""
    return {"layers": [{"rect": B[body], "at": [0, 0]},
                       {"rect": [EAR_RIGHT - length, EAR_TOP, length, 5], "at": list(EAR_AT)}],
            "anchor_layer": 0}


EAR_LENGTHS = [0, 25, 49, 73, 73, 37, 0]  # out, held, back
# the ear tip's reach from his centre per frame (for tools/abilities.py's melee_reach): the body is 23 px
# ("Grab idle") wide and centred, so the tip is at 12 + length - 11 (2 px less in the air: "Grab air" is 26 wide)
EAR_REACH = [10 if n == 0 else EAR_AT[0] + n - 11 for n in EAR_LENGTHS]


# The diagonal "Grab" ear (582): its pixels fill the box (54 x 53), from the base at the bottom left to the rounded
# tip at the top right. In the "Example" (the middle figure) its top-left sits 11 px right of and 51 px above the
# "Grab idle" box's top-left; "Grab air" has the head 1 px further right in its box, so 12. A shorter ear is a
# crop of the tip end, moved down and back along the diagonal so its base stays on his head.
DIAG, DIAG_AT = B[582], (12, -51)
SRC = Image.open(HERE / SHEET).convert("RGB")


def trim_origin(rect):
    """Where sheet2ani's trim starts inside `rect`: its first column and row that aren't background."""
    x, y, w, h = rect
    pts = [(i, j) for j in range(h) for i in range(w) if "#%02x%02x%02x" % SRC.getpixel((x + i, y + j)) not in BACKGROUND]
    return min(i for i, _ in pts), min(j for _, j in pts)


def diag_ear(length):
    """The "Grab air" body with the diagonal ear `length` px out (1-53): its tip end, `length` rows high."""
    x, y, w, h = DIAG
    rect = [x + w - 1 - length, y, length + 1, length]  # the top-right corner, where the tip is
    tx, ty = trim_origin(rect)
    back = h - length  # how far the crop moves down and back from where it sits in the full ear
    at = [DIAG_AT[0] + rect[0] - x + tx - back, DIAG_AT[1] + ty + back]
    return {"layers": [{"rect": B[569], "at": [0, 0]}, {"rect": rect, "at": at}], "anchor_layer": 0}


# Ear Grapple: the ear out in 8 frames. Its tip (the top-right pixel, 52 px right of the full ear's left edge) from
# his centre (the "center" anchor: 13, 15 into the 26 x 30 "Grab air" box) is (length - 2, -13 - length); for
# tools/abilities.py's grapple_tip
GRAPPLE_LENGTHS = [DIAG[3] * k // 8 for k in range(1, 9)]
GRAPPLE_TIP = [(n - 2, -13 - n) for n in GRAPPLE_LENGTHS]


THROW_EAR = 25  # the Ear Boomerang's throw: the ear out this far, then gone (thrown)
THROW_REACH = [EAR_AT[0] + THROW_EAR - 11, 10]  # (for tools/abilities.py's melee_reach: the throw pose's reach)


def ear_jab(body, anchor):  # (the old Ear Jab's frames; unused since the Ear Boomerang)
    return {"frames": [B[body] if n == 0 else ear(body, n) for n in EAR_LENGTHS], "anchor": anchor, "speed": 60}


ANIMS = {
    "Stopped": {"frames": f(86)},  # "Idle"
    "Waiting": {"frames": f(80, 81, 84, 82), "loop": 2},  # "Waiting": arms crossed, then tapping his foot
    "Looking Up": {"frames": f(90), "loop": 0},  # "Look Up"
    "Looking Down": {"frames": f(91), "loop": 0},  # "Crouch"
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2},
    "Skidding": {"frames": f(146, 145)},
    "Super Peel Out": {"frames": MACH_RUN, "rot": 2},  # "Mach run"
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": {"frames": SPIN, "anchor": "center"},
    "Bouncing": {"frames": f(83), "anchor": "center"},  # "Spring"
    "Hurt": {"frames": f(239), "anchor": "center"},  # "Hurt/Slide"
    "Dying": {"frames": f(326), "anchor": "center"},  # "Death"
    "Drowning": {"frames": f(327), "anchor": "center"},  # "Drown"
    "Fan Rotate": {"frames": f(331, 332, 333), "anchor": "center"},  # "Labyrinth spin"
    "Breathing": {"frames": f(147), "anchor": "center"},  # "Bubble"
    "Pushing": {"frames": f(281, 279, 282, 280)},
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(83), "anchor": "center"},  # no hanging art: the spring pose (stretched up)
    "Clinging On": {"frames": f(292, 293), "anchor": "center"},  # "Cling"
    "Corkscrew H": {"frames": SPRING_TWIRL},  # "Spring twirl"
    "Water Slide": {"frames": HURT_SLIDE, "anchor": "center"},  # "Hurt/Slide"
    "Continue": {"frames": f(328, 329, 330)},
    "Continue Up": {"frames": f(83), "loop": 0},
    "Super Transform": {"frames": f(86), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": f(239), "anchor": "center"},
    "Twirl H": {"frames": SPRING_TWIRL, "rot": 2},  # "Spring twirl"
    "Bored!": {"frames": GOLF, "loop": 1},  # "Golf forever"
}

APPENDED = {
    # Ear Grapple (ear_grapple): the ear growing, shortest to full length; the code picks the frame
    "41": {"name": "Ear Grapple", "frames": [diag_ear(n) for n in GRAPPLE_LENGTHS], "anchor": "center"},
    "42": {"name": "Ear Copter", "frames": FLYING, "anchor": "center", "speed": 120},  # hover: "Flying"
    # Ear Boomerang's throw pose (the ear itself is the shot, abilities.py: the sheet's diagonal "Grab" ear, spun): the
    # ear flicked out a little, then his body as it flies off, held ("Grab idle" on the ground, "Grab air" in the air)
    "43": {"frames": [ear(490, THROW_EAR), B[490]], "anchor": "feet", "speed": 60, "name": "Ear Boomerang"},
    "44": {"frames": [ear(569, THROW_EAR), B[569]], "anchor": "center", "speed": 60, "name": "Ear Boomerang Air"},
}

LIFE = B[563]  # "Life Counter": his head (16x16, black rows top and bottom), "MAX", and an "x" below
SIGN = B[461]  # "Signpost": board rows 13-42 of the box, his ears sticking up above, the pole below
MINIS = B[479]  # "Continue Icon": both minis in one box, split at column 21
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": [LIFE[0], LIFE[1], 16, 16], "trim": False},  # his head
    "life_name": {"rect": [LIFE[0] + 17, LIFE[1] + 1, 21, 7]},  # ...and "MAX"
    "monitor_1up": {"rect": [LIFE[0], LIFE[1] + 1, 16, 14], "trim": False},  # the icon's middle rows
    # the board (30 rows) and the 2 rows above it, without the pole: his ears stick up 13 rows above the
    # board; the top 11 are cut to keep Sonic's 48x32 board size
    "sign_face": {"rect": [SIGN[0], SIGN[1] + 11, 48, 32], "trim": False},
    "mini_1": {"rect": [MINIS[0], MINIS[1], 21, 24], "remap": PLUS_128},
    "mini_2": {"rect": [MINIS[0] + 21, MINIS[1], 22, 24], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[400], "remap": PLUS_128},  # "Normal ending"
    "end_pose_1": {"rect": B[406], "remap": PLUS_128},  # ...its arms-out frame
    "end_pose_2": {"rect": B[319], "remap": PLUS_128},  # "Victory" (Extras): a kick and a fist pump
    # "End Sprite": the smaller of the two (60x96). The large one (470, 116x176) is too big for the shared
    # ending sheet
    "end_pose_3": {"rect": B[562], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((403, 404, 405, 401, 402, 407), 1)},
}

PALETTE = {  # Max's own colours, in the extras' shared global palette slots 74+
    "74": "#4848b4", "75": "#6c6cd8", "76": "#9090fc", "77": "#b4b4fc",  # lavender-blue fur, dark to light
    "78": "#fcfcfc", "79": "#b4b4b4",  # white and light grey (face, gloves, shoes)
    "80": "#fc0000",  # red bow tie and shoe stripes
    "81": "#fcb490",  # the signpost's peach board
    "82": "#fcfc00",  # the "MAX" name tag
}
KEY_COLOURS = {  # near-exact matches go in Sonic's slots; the rest are Max's own
    "#000000": 1, "#010101": 1, "#080000": 1, "#242490": 2, "#909090": 8, "#484848": 9, "#900000": 13,
    "#480000": 14,
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
# the last frame, the pose held or looped): the sheet's "Victory" (Extras): the kick and fist pump, both frames looping
S3K_VICTORY = {"frames": f(319, 320), "pose": 0}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra15",
           "credit": "Max (The Rabbit Or Whatever You Wanna Call Him In Sonic 1) by Akimaca; "
                     "original sprites by SEGA / Sonic Team",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra15SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": SPIN, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra15_UI", "manifest": "Extra15_ui.json", "elements": ELEMENTS, "out": "build/Extra15_UI.gif"},
                     {"name": "Extra15_Ending", "manifest": "Extra15_ending.json", "elements": ENDING,
                      "out": "build/Extra15_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "max.json"), ("Sonic2", "max_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("melee_reach (the throw pose):", THROW_REACH)
    print("grapple_tip:", GRAPPLE_TIP)
