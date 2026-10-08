#!/usr/bin/env python3
"""Writes Trip's sheet2ani configs (trip.json for Sonic 1, trip_s2.json for Sonic 2).

Frames are the boxes on Trip.png ("S1 Trip" by miniluv73 & Tarkan809; see SOURCE.txt), numbered as detected:
connected components of everything that isn't the #25661a sheet background (8-connected, sorted by top edge,
then left edge). The sheet labels its rows (Idle, Waiting, Look Up...), and the mapping follows them. Box
backgrounds are colour-coded: dark green (#0d4807) for the base set, dark blue (#11307a) "2013 exclusive",
blue (#0068dd) "S1F exclusive", purple (#680093) "New sprites"; lime (#b5e61d) bars mark the ground or a
wall in a few boxes. All of them are background (transparent).

Template: Sonic's .ani (base character Sonic). The sheet is laid out like Sonic's own art: "Walking" and
"Running" are upright frames (40x40 boxes) followed by pre-drawn 45-degree ones (48x48 boxes), exactly the
halves Sonic's static-frame rotation (rot 3) expects, so they're used as-is.

Placement: the artist placed every frame in equal-size boxes (the body stays put, the head bobs as in Sonic 1),
so each row is positioned by its boxes (box(): one anchor for the whole animation), not by each trimmed
frame. That keeps the artist's own alignment and bob with no sideways jitter.

Abilities (appended slots; the moves are wired elsewhere):
  41 "Double Jump": "Double Jump", her spinning shell (four frames, the ring's hole is transparent)
  47 "Wall Cling": "Clinging", two frames. In the art she lies level, feet planted on the lime wall bar at
      the RIGHT of the box, head and hands pointing LEFT, belly down. (The same frames are also Sonic's
      "Clinging On", the Labyrinth current pose, which has exactly this shape.) Turned a quarter clockwise and
      mirrored (together: flipped over the top-left to bottom-right diagonal), she's upright on a wall to her
      RIGHT: belly and shoes against it, hands reaching up, head tilted back to look up it. Unmirrored (facing
      right) is a wall on the right, so the move just faces her toward the wall.

Not used: the "unused" grey dying frame (17), the "ALT." roll (small 32x32 set, 58-62), "AS P2" (132-133),
the title-screen emblem pieces (blue 60x28 boxes and "OVERLAY"), the S2-style picture boxes (109-111 are used:
109 is the signpost board; 110-111 its dithered turn frames are not needed, the game spins Sonic's), the
"TRIP" logo texts, "TRIP THE SUNGAZER IN" (the ending title, not an ani/ui element), the S1F shoe icon (85),
palette strips and swaps, the cameo line-up and the big menu portrait.
"Dragon Trip" (her super form) is not built; it's the purple boxes from y=602 down: 167-169, 176-181,
182-185 (the dragon flying), 186-187 (dragon with the lime wall bar), 161-162 and 170-171 (the fireball /
flare), 188-190 (small flames), with its palette swaps at 163-166 / 172-175.
Nothing is redrawn or resized: frames are cut, the HUD art is cropped from the sheet's own, and the signpost
board sits under the game's own two-row pole cap (Items2), like other extras.
"""
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SHEET = "Trip.png"
BACKGROUND = ["#25661a", "#0d4807", "#11307a", "#0068dd", "#680093", "#b5e61d"]

B = {  # box number -> [x, y, w, h]
    # Idle, Waiting, Look Up (9: 2013), Crouching (11: 2013)
    4: [3, 12, 40, 40], 5: [48, 12, 40, 40], 6: [89, 12, 40, 40], 7: [130, 12, 40, 40], 8: [171, 12, 40, 40],
    9: [216, 12, 40, 40], 10: [257, 12, 40, 40], 11: [302, 12, 40, 40], 12: [343, 12, 40, 40],
    # Spring (the box's bottom rows are the lime ground bar), Dying (17 "unused"), Inhaling, Spin Dash (2013)
    15: [3, 63, 40, 43], 16: [48, 63, 40, 40], 18: [130, 63, 40, 40], 19: [175, 63, 40, 40],
    20: [220, 63, 40, 40], 21: [261, 63, 40, 40], 22: [302, 63, 40, 40], 23: [343, 63, 40, 40],
    24: [384, 63, 40, 40], 25: [425, 63, 40, 40],
    # Walking: upright, then 45 degrees
    33: [3, 117, 40, 40], 34: [44, 117, 40, 40], 35: [85, 117, 40, 40], 36: [126, 117, 40, 40],
    37: [167, 117, 40, 40], 38: [208, 117, 40, 40],
    27: [253, 113, 48, 48], 28: [302, 113, 48, 48], 29: [351, 113, 48, 48], 30: [400, 113, 48, 48],
    31: [449, 113, 48, 48], 32: [498, 113, 48, 48],
    # Running: upright, then 45 degrees
    45: [3, 168, 40, 40], 46: [44, 168, 40, 40], 47: [85, 168, 40, 40], 48: [126, 168, 40, 40],
    40: [171, 163, 48, 48], 41: [220, 163, 48, 48], 42: [269, 163, 48, 48], 43: [318, 163, 48, 48],
    # Jump / Roll (49: the plain shell), Double Jump
    49: [3, 219, 40, 40], 50: [44, 219, 40, 40], 51: [85, 219, 40, 40], 52: [126, 219, 40, 40],
    53: [167, 219, 40, 40],
    54: [381, 219, 40, 39], 55: [422, 219, 40, 39], 56: [463, 219, 40, 39], 57: [504, 219, 40, 39],
    # Rotation, Clinging (each box ends in the lime wall bar)
    75: [3, 270, 40, 40], 76: [44, 270, 40, 40], 77: [85, 270, 40, 40], 78: [126, 270, 40, 40],
    79: [167, 270, 40, 40], 80: [208, 270, 40, 40], 81: [253, 270, 47, 40], 82: [301, 270, 46, 40],
    # Hurt, Balancing, Skidding, Pushing
    93: [3, 321, 40, 40], 94: [44, 321, 40, 40], 95: [89, 321, 40, 40], 96: [130, 321, 40, 40],
    97: [175, 321, 40, 40], 98: [216, 321, 40, 40],
    99: [261, 321, 40, 40], 100: [302, 321, 40, 40], 101: [343, 321, 40, 40], 102: [384, 321, 40, 40],
    # Ungrounded Rotation, Continue?
    113: [3, 372, 48, 24], 114: [52, 372, 48, 24], 115: [101, 372, 48, 24], 116: [150, 372, 48, 24],
    117: [199, 372, 48, 24], 118: [248, 372, 48, 24],
    119: [3, 407, 40, 40], 120: [44, 407, 40, 40], 121: [85, 407, 40, 40],
    # Ending: normal (124-125), good (126-131), the medium and large poses (122, 112)
    124: [3, 458, 40, 40], 125: [44, 458, 40, 40], 126: [89, 458, 40, 40], 127: [130, 458, 40, 40],
    128: [171, 458, 40, 40], 129: [212, 458, 40, 40], 130: [253, 458, 40, 40], 131: [294, 458, 40, 40],
    122: [335, 418, 56, 80], 112: [392, 362, 160, 136],
    # Max Speed, Spring Twirl (S1F), Use Emeralds (2013), Hanging (2013; 134 ends in the lime ground bar)
    136: [3, 509, 40, 40], 137: [44, 509, 40, 40], 138: [85, 509, 40, 40], 139: [126, 509, 40, 40],
    140: [171, 509, 40, 40], 141: [212, 509, 40, 40], 142: [253, 509, 40, 40], 143: [294, 509, 40, 40],
    144: [335, 509, 40, 40],
    145: [380, 509, 40, 40], 146: [421, 509, 40, 40], 147: [462, 509, 40, 40],
    134: [507, 508, 40, 42], 135: [548, 508, 40, 40],
    # Golf (S1F)
    149: [3, 559, 40, 40], 150: [44, 559, 40, 40], 151: [85, 559, 40, 40], 152: [126, 559, 40, 40],
    153: [167, 559, 40, 40], 154: [208, 559, 40, 40], 155: [249, 559, 40, 40],
    # HUD: continue minis (73, 74), life icons (83; 84 starts with a second face, then "TRIP"), signpost board
    73: [405, 264, 16, 24], 74: [422, 264, 16, 24], 83: [417, 289, 16, 16], 84: [434, 289, 48, 16],
    109: [568, 360, 48, 30],
}
SRC = Image.open(HERE / SHEET).convert("RGB")
_BG = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in BACKGROUND}


def content(n):
    """The drawn pixels' bounding box inside box n: (left, top, right, bottom), box-relative, inclusive."""
    x, y, w, h = B[n]
    pts = [(i, j) for j in range(h) for i in range(w) if SRC.getpixel((x + i, y + j)) not in _BG]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def box(*nums, mode="feet"):
    """Frames of one animation, all placed by the same point of their (equal-size) boxes, so the artist's own
    alignment is kept. "feet": the lowest drawn row of the set on the ground (sheet2ani's feet anchor);
    "center": the set's average drawn centre at the player's centre (use with "anchor": "center").
    Horizontally, the set's average drawn centre goes to x=0."""
    bbs = [content(n) for n in nums]
    cx = round(sum((l + r + 1) / 2 for l, _, r, _ in bbs) / len(bbs))
    frames = []
    if mode == "feet":
        bottom = max(b for *_, b in bbs) + 1
        for n in nums:
            x, y, _, _ = B[n]
            frames.append({"rect": B[n], "anchor_box": [x + cx - 8, y, 16, bottom]})
    else:
        cy = round(sum((t + b + 1) / 2 for _, t, _, b in bbs) / len(bbs))
        for n in nums:
            x, y, _, _ = B[n]
            frames.append({"rect": B[n], "anchor_box": [x + cx - 8, y + cy - 8, 16, 16]})
    return frames


def diagonal(*nums):
    """45-degree frames (the second half of a rot 3 walk/run): centred on the player, like Sonic's."""
    bbs = [content(n) for n in nums]
    cx = round(sum((l + r + 1) / 2 for l, _, r, _ in bbs) / len(bbs))
    cy = round(sum((t + b + 1) / 2 for _, t, _, b in bbs) / len(bbs))
    # in "feet" mode the anchor box's bottom goes to y=+20: a box ending 20 px below the centre puts it at 0
    return [{"rect": B[n], "anchor_box": [B[n][0] + cx - 8, B[n][1], 16, cy + 20]} for n in nums]


f = lambda *nums: [B[n] for n in nums]

WALK = box(33, 34, 35, 36, 37, 38) + diagonal(27, 28, 29, 30, 31, 32)  # "Walking": upright, then 45 degrees
RUN = box(45, 46, 47, 48) + diagonal(40, 41, 42, 43)  # "Running": upright, then 45 degrees
MAX_SPEED = box(136, 137, 138, 139)  # "Max Speed" (S1F): legs a figure-eight blur
JUMP = box(50, 51, 52, 53, 49, mode="center")  # "Jump / Roll": curled spins, then the plain shell
SPINDASH = box(20, 21, 22, 23, 24, 25)  # "Spin Dash" (2013): the spiked shell ring
BALANCE = box(95, 96)  # "Balancing"
HURT = box(93, 94, mode="center")  # "Hurt"
ROTATION = box(75, 76, 77, 78, 79, 80)  # "Rotation" (new sprites): a full turn, side to front to back
SPRING_TWIRL = box(140, 141, 142, 143, 144)  # "Spring Twirl" (S1F)
UNGROUNDED = box(113, 114, 115, 116, 117, 118, mode="center")  # "Ungrounded Rotation": lying flat, turning
CLINGING = box(81, 82, mode="center")  # "Clinging"
# "Clinging" turned upright against a wall on the right (see the docstring); the anchor boxes turn with the frames
WALL_CLING = [dict(fr, rotate=90, flip=True) for fr in CLINGING]
DOUBLE_JUMP = box(54, 55, 56, 57, mode="center")  # "Double Jump": the spinning shell

ANIMS = {
    "Stopped": {"frames": f(4)},  # "Idle" (also the Origins character-select card picture)
    "Waiting": {"frames": box(5, 6, 7, 8), "loop": 0},  # "Waiting": hand to her chin, blinking
    "Looking Up": {"frames": box(9, 10), "loop": 1},  # "Look Up": 2013's in-between, then the pose
    "Looking Down": {"frames": box(11, 12), "loop": 1},  # "Crouching": 2013's in-between, then curled up
    "Walking": {"frames": WALK},  # rot 3 (the template's): the 45-degree half is drawn
    "Running": {"frames": RUN},
    "Skidding": {"frames": box(97, 98)},
    "Super Peel Out": {"frames": MAX_SPEED, "rot": 2},  # upright only: rotated by the engine
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": {"frames": JUMP, "anchor": "center"},
    "Bouncing": {"frames": f(15), "anchor": "center"},  # "Spring"
    "Hurt": {"frames": HURT[:1], "anchor": "center"},
    "Dying": {"frames": f(16), "anchor": "center"},  # "Dying"
    "Drowning": {"frames": f(18), "anchor": "center"},  # "Dying": the red-faced one
    "Fan Rotate": {"frames": UNGROUNDED, "anchor": "center"},  # "Ungrounded Rotation"
    "Breathing": {"frames": f(19), "anchor": "center"},  # "Inhaling"
    "Pushing": {"frames": box(99, 100, 101, 102)},
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": box(134, 135, mode="center"), "anchor": "center"},  # "Hanging" (2013)
    "Clinging On": {"frames": CLINGING, "anchor": "center"},  # "Clinging": the Labyrinth current pose
    "Corkscrew H": {"frames": SPRING_TWIRL},  # "Spring Twirl" (S1F exclusive: Sonic 1's twirl)
    "Water Slide": {"frames": HURT, "anchor": "center"},  # no slide art: "Hurt", arms up
    "Continue": {"frames": box(119, 120, 121)},  # "Continue?": lying down, tapping
    "Continue Up": {"frames": box(9, 10), "loop": 1},  # getting up: the look-up frames
    "Super Transform": {"frames": box(145, 146, 147), "loop": 1},  # "Use Emeralds" (2013): flashes at the end
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": HURT, "anchor": "center"},
    "Twirl H": {"frames": ROTATION, "rot": 2},  # "Rotation" (new sprites): Sonic 2's corkscrew / spring flip
    "Bored!": {"frames": box(149, 150, 151, 152, 153, 154, 155), "loop": 1},  # "Golf" (S1F)
}

# CD-only animations that tools/cd_config.py would otherwise copy from "Running", whose second half is the 45-degree
# frames (these have no static-frame rotation): the upright run only. Sonic 2's template has none of these names,
# so its build ignores them; cd_config.py keeps them.
CD_ONLY = {name: {"frames": RUN[:4]} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    "41": {"name": "Double Jump", "frames": DOUBLE_JUMP, "anchor": "center", "speed": 120, "hitbox": 1},  # the jump ball's box
    "47": {"name": "Wall Cling", "frames": WALL_CLING, "anchor": "center", "speed": 20},  # on a wall to her right
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ICON = B[83]  # the life icon: her face on white, black rows top and bottom (S1F)
SIGN = B[109]  # the signpost board (48x30, grey frame, her face waving on yellow; its corners are background)
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": ICON, "trim": False},
    "life_name": {"rect": [450, 290, 32, 7]},  # "TRIP" (yellow, black shadow), above the "x"
    "monitor_1up": {"rect": [ICON[0], ICON[1] + 1, 16, 14], "trim": False},  # the icon's middle rows
    # the 30-row board under the game's own 2-row pole cap (Sonic's board is the same 30 rows plus that cap)
    "sign_face": {"rect": SIGN, "trim": False, "at": [0, 2],
                  "base": {"file": str(REPO / "extracted/Sonic1/Data/Sprites/Global/Items2.gif"),
                           "rect": [34, 182, 48, 32], "clear": [0, 2, 48, 30, 0]}},
    "mini_1": {"rect": B[73], "remap": PLUS_128},  # the two 16x24 continue minis
    "mini_2": {"rect": B[74], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending: idle, three poses (small, medium, large), six good-ending frames; the sheet has them all
    "end_idle": {"rect": B[124], "remap": PLUS_128},  # "Ending"
    "end_pose_1": {"rect": B[125], "remap": PLUS_128},  # ...facing front
    "end_pose_2": {"rect": B[122], "remap": PLUS_128},  # the medium pose (56x80)
    "end_pose_3": {"rect": B[112], "remap": PLUS_128},  # the large pose (160x136), like Sonic's big leap
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((126, 127, 128, 129, 130, 131), 1)},
}

PALETTE = {  # every colour of hers exact in a slot of its own (74+); only black shares Sonic's slot 1
    "74": "#d86c24", "75": "#b44824", "76": "#fc9000", "77": "#fc9e00", "78": "#fcb400",  # orange fur/shell
    "79": "#fcfc00",  # yellow (chest, shoes, crest; the "TRIP" name tag)
    "80": "#fcb490", "81": "#b46c48",  # skin, light and shaded
    "82": "#fcfcfc", "83": "#b4b4b4", "84": "#909090", "85": "#484848",  # white, greys (gloves, eyes)
    "86": "#fc0000", "87": "#900000", "88": "#480000",  # reds (shell, scarf)
    "89": "#e00000", "90": "#400000",  # the signpost board's red and darkest red
    # one-off greys in the large ending pose's glove (6 pixels), kept exact
    "91": "#5d5d5d", "92": "#5a5a5a", "93": "#868686", "94": "#939393",
}
KEY_COLOURS = {"#000000": 1, "#080000": 1, **{c: int(s) for s, c in PALETTE.items()}}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (Dragon Trip, palette swaps, cameos, text) in the slot
    of its nearest key colour, so nothing is left to sheet2ani's guess. None of those are in a built frame."""
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
CREDIT = ("S1 Trip by miniluv73 & Tarkan809; credit to karlemerald, ritz_blitz09, deltaconduit, _sumgaiondicord "
          "+ those who helped with Trip 3&K; Trip the Sungazer and original sprites by SEGA / Sonic Team / Arzest - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/227760/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the good ending: into arms out
S3K_VICTORY = {"frames": f(128, 130)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra18", "credit": CREDIT,
           "source": SHEET, "feet_y": 20, "angled_halves": True,  # walk/run: upright, then 45 degrees (S3&K splits them)
            "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra18SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": JUMP, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra18_UI", "manifest": "Extra18_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra18_UI.gif"},
                     {"name": "Extra18_Ending", "manifest": "Extra18_ending.json", "elements": ENDING,
                      "out": "build/Extra18_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "trip.json"), ("Sonic2", "trip_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
