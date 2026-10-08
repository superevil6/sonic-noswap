#!/usr/bin/env python3
"""Writes Shadow's sheet2ani configs (shadow.json for Sonic 1, shadow_s2.json for Sonic 2), from the Sonic Megamix sheet.

Sheet: testmods/ShadowMegamix.png, "Shadow the Hedgehog - Sonic Megamix (Versions 3.0 to 5.0A)", ripped and improved
by AsuharaMoon; credits Chimpo, GrandMasterGalvatron, Team Megamix (see SOURCE.txt). The sheet has no terms against
edits. The earlier sheet (Gardow's "Shadow (Sonic 3-Style)", 18229.png) is kept, unused, in make_configs_gardow.py.

build/megamix_source.png, the working copy sheet2ani reads (the sheet file is untouched):
- Colours: the sheet's sprites are drawn in its "Custom" palette; the game's own "Original" palette (the strip under
  the "Original" standing preview) holds the same colours in the same places except four darks, so each sprite colour
  becomes the Original colour in its place: #151515 -> #000000, #202420 -> #212121, #4b4545 -> #424242,
  #736a6a -> #636363 (Original has black twice, and #424242 twice). Nothing else changes.
- Frames: each sprite is cut out by its pixels (a connected shape plus the loose flame and spark specks within 7 px
  of it; the sheet's white asterisks and captions are left out) and set, unchanged, in a strip under the sheet, so no
  frame's box catches a neighbour's flames. A frame is named by its top-left corner on the sheet (x, y).
- The sheet itself stays above, recoloured, for the UI elements cut straight from it (life icon, sign face).

Ignored, as briefed: the "Version 3.0 Only" box, the early concept sprites, the big portraits, the palette strips.
Output goes into the mod (mods/NoSwap), like the other extras.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402

SHEET = REPO / "testmods" / "ShadowMegamix.png"
BG = (0, 128, 128)
BG_HEX = "#008080"
SOURCE = "build/megamix_source.png"
# the sheet's "Custom" palette colours -> the "Original" palette's colour in the same place (the other 11 are the same)
ORIGINAL = {(0x15, 0x15, 0x15): (0, 0, 0), (0x20, 0x24, 0x20): (0x21, 0x21, 0x21),
            (0x4b, 0x45, 0x45): (0x42, 0x42, 0x42), (0x73, 0x6a, 0x6a): (0x63, 0x63, 0x63),
            (0x40, 0, 0): (0x42, 0, 0)}  # (7 stray pixels of #400000, one shade off the Original's #420000: merged)
TEXT_WHITE = (0xe7, 0xe7, 0xe7)  # the asterisks ("improved") and captions

# frames by their top-left corner on the sheet
STAND = (9, 10)
IDLE = [(42, 10), (76, 10), (107, 10)]  # the glow in his hand (107 is the improved one, tapping his foot)
LOOK_UP, CROUCH = (141, 11), (174, 18)
PUSH = [(214, 12), (251, 12), (276, 12), (311, 12)]
SKID = [(339, 16), (387, 15)]  # with sparks
BALANCE = [(425, 9), (464, 10)]  # leaning back at the edge, arms out / one arm up
WALK = [(12, 57), (43, 56), (85, 57), (124, 59), (154, 57), (199, 58)]
RUN = [(236, 54), (320, 54), (361, 56), (442, 56)]  # the fast run (unused: too few frames at top speed)
SKATE = [(8, 102), (53, 102), (95, 102), (150, 102), (200, 102), (261, 102), (306, 102), (345, 102), (393, 102),
         (440, 102), (492, 102), (540, 102)]  # hover-skating on his jet shoes, flames trailing
CLING = [(293, 201), (337, 201)]  # holding on, blown sideways (hands blurred)
FRONT_FALL = (456, 203)  # face down, arms spread
FLUNG = (501, 203)  # flung through the air, arm out
HANG = [(110, 197), (149, 198)]  # hanging by one hand
SPRING = (191, 201)  # stretched upward
SHOCK = (220, 201)  # arms up, mouth open
GASP_FIST = (254, 200)  # fist raised, gasping
LIE = [(8, 256), (57, 255)]  # lying flat, arms out front
GULP = (105, 251)  # mouth open, arm out: the air bubble
CURL = [(142, 255), (172, 257), (205, 255), (235, 257)]  # curling up (his own ball, quills and shoes showing)
BALL = (269, 255)  # the plain ball
DASH_BALLS = [(301, 259), (332, 259), (362, 259), (392, 259), (422, 259), (452, 259)]  # Spin Dash (the black ovals)
GREY = (82, 293)  # the grey, drained pose: the Chaos Control flash
ARMS_CROSSED = [(116, 293), (150, 293)]
AIR_DASH = [(11, 443), (51, 448)]  # flying forward, arms back: the Chaos Control lunge
FRONT = (16, 542)  # front-on, standing (improved)
THUMBS_UP = (74, 542)
ARMS_OUT = (13, 591)
FRONT_2 = (46, 595)
BIG_POSE = (116, 556)  # the tall pose (not one of the big portraits)
FLAME = (345, 121)  # a loose jet-flame streak from the skate row (the old melee bolt; unused)

USED = ([FLAME, STAND, LOOK_UP, CROUCH, FLUNG, FRONT_FALL, SPRING, SHOCK, GASP_FIST, GULP, BALL, GREY, FRONT, THUMBS_UP,
         ARMS_OUT, FRONT_2, BIG_POSE] + IDLE + PUSH + SKID + BALANCE + WALK + RUN + SKATE + CLING + HANG + LIE + CURL
        + DASH_BALLS + ARMS_CROSSED + AIR_DASH)
STRIP_Y, STRIP_W = 662, 644
SKATE_ROWS = (95, 142)  # the ground skate row's y range


def shapes():
    """{top-left (x, y): boolean mask of its pixels over the whole sheet} for every sprite on the sheet: connected
    shapes of 120+ px, each with the small loose specks (flames, sparks) within 7 px of it, nearest first; white-only
    specks (asterisks, captions) are left out. The flame streak FLAME is also a shape of its own."""
    rgb = np.array(Image.open(SHEET).convert("RGB"))
    fg = ~np.all(rgb == BG, axis=2)
    lab, n = ndimage.label(fg, structure=np.ones((3, 3)))
    boxes = ndimage.find_objects(lab)
    count = ndimage.sum(fg, lab, range(1, n + 1))
    white = np.all(rgb == TEXT_WHITE, axis=2)
    big = [i for i in range(n) if count[i] >= 120]
    groups = {i: [i] for i in big}

    def gap(a, b):
        (ya, xa), (yb, xb) = boxes[a], boxes[b]
        return max(max(xa.start, xb.start) - min(xa.stop, xb.stop), max(ya.start, yb.start) - min(ya.stop, yb.stop), 0)
    for i in range(n):
        if i in groups:
            continue
        if white[boxes[i]][lab[boxes[i]] == i + 1].all():
            continue
        near = min(big, key=lambda b: gap(i, b))
        (ys, xs) = boxes[i]
        if SKATE_ROWS[0] <= ys.start < SKATE_ROWS[1]:  # skate row: flames trail behind, so a speck between two
            row = [b for b in big if SKATE_ROWS[0] <= boxes[b][0].start < SKATE_ROWS[1]]  # frames is the next one's
            inside = [b for b in row if boxes[b][1].start <= xs.start < boxes[b][1].stop]
            ahead = [b for b in row if boxes[b][1].start > xs.start]
            near = (inside or sorted(ahead, key=lambda b: boxes[b][1].start) or [near])[0]
        if gap(i, near) <= 7:
            groups[near].append(i)
    out = {}
    for i, members in groups.items():
        out[(boxes[i][1].start, boxes[i][0].start)] = np.isin(lab, [m + 1 for m in members])
    for i in range(n):  # (also a speck of its skate frame)
        if (boxes[i][1].start, boxes[i][0].start) == FLAME:
            out[FLAME] = lab == i + 1
    return out


# The sign face: Megamix's own goal sign ("Goal Signs - Sonic Megamix", testmods/MegamixObjects.png, ripped by
# AsuharaMoon; credits Yuski, Shadowsoft Games, Chimpo, Team Megamix & Sonic Team): the "Versions 4.0-5.0A" group,
# Shadow's board (bottom row), 48x32 as the game's boards (its frame is 46 wide: a clear column each side; the top
# 2 rows are his quills over the frame). Cut exactly, without its pole: the pole's cap behind his quills (the 6 and 4
# pole pixels in those top 2 rows) is left out. Colours as his sprites' (ORIGINAL: #4b4545 -> #424242, #202420 -> #212121).
SIGN_SHEET = REPO / "testmods" / "MegamixObjects.png"
SIGN_RECT = (391, 122, 48, 32)
SIGN_POLE = [(413, 122, 6), (415, 123, 4)]  # (x, y, width) of the pole's pixels inside the rect
SIGN = "sign"


def sign_board():
    """Shadow's Megamix goal-sign board, recoloured as his sprites, pole pixels cleared to the background."""
    x, y, w, h = SIGN_RECT
    rgb = np.array(Image.open(SIGN_SHEET).convert("RGB"))
    board = rgb[y:y + h, x:x + w].copy()
    for px, py, pw in SIGN_POLE:
        board[py - y, px - x:px - x + pw] = BG
    for a, b in ORIGINAL.items():
        board[np.all(board == a, axis=2)] = b
    return board


def build_source():
    """Write build/megamix_source.png (the recoloured sheet with the used frames in a strip below). Returns
    {top-left: [x, y, w, h] of that frame in the strip}."""
    sheet = Image.open(SHEET).convert("RGB")
    rgb = np.array(sheet)
    for a, b in ORIGINAL.items():
        rgb[np.all(rgb == a, axis=2)] = b
    shapes_ = shapes()
    tops = {}  # each shape by the top-left of all its pixels (flames and sparks included)
    for key, m in shapes_.items():
        ys, xs = np.nonzero(m)
        tops[(int(xs.min()), int(ys.min()))] = m
    found = {}
    for key in USED:  # the shape whose top-left is nearest (within 8 px) the name's
        near = min(tops, key=lambda t: abs(t[0] - key[0]) + abs(t[1] - key[1]))
        if abs(near[0] - key[0]) + abs(near[1] - key[1]) > 8:
            sys.exit(f"no sprite at {key}")
        found[key] = tops[near]
    if len({id(m) for m in found.values()}) != len(set(USED)):
        sys.exit("two frame names picked the same sprite")
    cells, x, y, row_h = {}, 1, STRIP_Y, 0
    placed = []
    for key in dict.fromkeys(USED):
        m = found[key]
        ys, xs = np.nonzero(m)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        w, h = x1 - x0, y1 - y0
        if x + w + 1 > STRIP_W:
            x, y, row_h = 1, y + row_h + 2, 0
        placed.append((key, m[y0:y1, x0:x1], rgb[y0:y1, x0:x1], x, y))
        cells[key] = [int(x), int(y), int(w), int(h)]
        x, row_h = x + w + 2, max(row_h, h)
    if x + SIGN_RECT[2] + 1 > STRIP_W:  # the sign board (sign_board) after the frames
        x, y, row_h = 1, y + row_h + 2, 0
    sign_at = (x, y)
    cells[SIGN] = [int(x), int(y), SIGN_RECT[2], SIGN_RECT[3]]
    row_h = max(row_h, SIGN_RECT[3])
    out = np.zeros((y + row_h + 1, STRIP_W, 3), np.uint8)
    out[:] = BG
    out[:rgb.shape[0], :rgb.shape[1]] = rgb
    for key, m, px, x, y in placed:
        region = out[y:y + m.shape[0], x:x + m.shape[1]]
        region[m] = px[m]
    board = sign_board()
    out[sign_at[1]:sign_at[1] + board.shape[0], sign_at[0]:sign_at[0] + board.shape[1]] = board
    (HERE / "build").mkdir(exist_ok=True)
    Image.fromarray(out).save(HERE / SOURCE)
    return cells


C = build_source()
f = lambda *keys: [C[k] for k in keys]
flip = lambda key: {"rect": C[key], "flip": True}


def spear(anchor):
    """Chaos Spear's throw pose: the wind-up (arm back), then the throw (arm out). The spear itself is a real projectile
    (tools/abilities.py "shot": a jet-flame streak from the sheet); the game shows this animation's last frame, the
    throw, while he fires."""
    return {"frames": [C[BALANCE[1]], C[BALANCE[0]]], "anchor": anchor, "speed": 80}


ANIMS = {
    "Stopped": {"frames": f(STAND)},
    "Waiting": {"frames": f(IDLE[0], IDLE[1], IDLE[0], IDLE[1], IDLE[2], IDLE[1]), "loop": 4},
    "Looking Up": {"frames": f(LOOK_UP), "loop": 0},
    "Looking Down": {"frames": f(CROUCH), "loop": 0},
    "Walking": {"frames": f(*WALK), "rot": 2},
    "Running": {"frames": f(*SKATE), "rot": 2, "align": True},  # the flame trail widens some frames: keep him put
    "Skidding": {"frames": f(*SKID)},
    # top speed: the whole 12-frame hover-skate cycle, as "Running" (the 4 fast-run frames flickered at that speed)
    "Super Peel Out": {"frames": f(*SKATE), "rot": 2, "align": True},
    "Spin Dash": {"frames": f(*DASH_BALLS)},
    "Jumping": {"frames": f(*CURL, BALL), "anchor": "center"},  # his own curl, then the plain ball (Sonic 1's pattern)
    "Bouncing": {"frames": f(SPRING), "anchor": "center"},
    "Hurt": {"frames": f(FLUNG), "anchor": "center"},
    "Dying": {"frames": f(SHOCK), "anchor": "center"},
    "Drowning": {"frames": f(GASP_FIST), "anchor": "center"},
    "Fan Rotate": {"frames": f(LIE[0], FRONT_FALL, LIE[1], FRONT_FALL), "anchor": "center"},
    "Breathing": {"frames": f(GULP), "anchor": "center"},
    "Pushing": {"frames": f(*PUSH)},
    "Flailing 1": {"frames": f(*BALANCE)},
    "Flailing 2": {"frames": f(*BALANCE)},
    "Hanging": {"frames": f(*HANG), "anchor": "center"},
    "Clinging On": {"frames": f(*LIE), "anchor": "center"},
    "Corkscrew H": {"frames": f(*WALK)},
    "Water Slide": {"frames": f(*CLING), "anchor": "center"},
    "Continue": {"frames": f(*LIE)},
    "Continue Up": {"frames": f(LOOK_UP), "loop": 0},
    "Super Transform": {"frames": f(STAND), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": f(*BALANCE)},
    "Grabbed": {"frames": f(FLUNG), "anchor": "center"},
    "Twirl H": {"frames": f(*WALK), "rot": 2},
    "Bored!": {"frames": f(*ARMS_CROSSED), "loop": 0},  # arms crossed, tapping his foot
}

# Sonic 3 & Knuckles (build_s3k_art.py "s3k_animations"): Run, Dash and Peelout get the whole 12-frame skate cycle
# ("own_count": the game only sets their speed; Sonic's have 4 frames, which took every third skate frame and flickered)
SKATE_FULL = {"frames": f(*SKATE), "align": True, "own_count": True}
S3K_ANIMS = {"Run": SKATE_FULL, "Dash": SKATE_FULL, "Peelout": SKATE_FULL}

# Chaos Control (jump ability, slot 41): the grey, drained flash, then the forward lunge. 3 game frames each.
CHAOS_CONTROL = f(GREY, GREY, AIR_DASH[0], AIR_DASH[0], AIR_DASH[1], AIR_DASH[1], AIR_DASH[1])
APPENDED = {
    "41": {"name": "Chaos Control", "frames": CHAOS_CONTROL, "anchor": "center", "speed": 80, "loop": 6},
    "43": dict(spear("feet"), name="Chaos Spear"),
    "44": dict(spear("center"), name="Chaos Spear Air"),
}


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
LIFE_ICON = [111, 500, 16, 16]  # the sheet's "5.0A" life icon (his head on white, framed)
ELEMENTS = {
    "life_icon": {"rect": LIFE_ICON, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("SHADOW")},
    "monitor_1up": {"rect": [LIFE_ICON[0], LIFE_ICON[1] + 1, 16, 14], "trim": False},  # the same, 14 rows
    "sign_face": {"rect": C[SIGN], "trim": False},  # Megamix's own goal sign (sign_board), the board without its pole
    "mini_1": {"rect": C[ARMS_CROSSED[0]], "remap": PLUS_128},  # full size, as the other extras' (nothing shrunk)
    "mini_2": {"rect": C[ARMS_CROSSED[1]], "remap": PLUS_128},
}
ENDING = {
    "end_idle": {"rect": C[STAND], "remap": PLUS_128},
    "end_pose_1": {"rect": C[THUMBS_UP], "remap": PLUS_128},
    "end_pose_2": {"rect": C[ARMS_OUT], "remap": PLUS_128},
    "end_pose_3": {"rect": C[BIG_POSE], "remap": PLUS_128},  # the tall pose
    **{f"good_{n}": {"rect": C[k], "remap": PLUS_128}
       for n, k in enumerate((STAND, FRONT, ARMS_OUT, THUMBS_UP, FRONT_2, GASP_FIST), 1)},
}

# The Original palette (13 colours): black is Sonic's own slot 1; the rest keep their exact values in slots 74-85
PALETTE = {
    "74": "#212121", "75": "#424242", "76": "#636363",  # fur, darkest to lightest
    "77": "#420000", "78": "#840000", "79": "#e70000",  # red stripes
    "80": "#848484", "81": "#a5a5a5", "82": "#e7e7e7",  # gloves and shoes
    "83": "#e78442", "84": "#e7a542", "85": "#e7e700",  # skin, the gold rings
}
COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): arms out, then the thumbs up (the ending poses)
S3K_VICTORY = {"frames": f(ARMS_OUT, THUMBS_UP)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra4",
           "credit": "Shadow the Hedgehog, from Sonic Megamix (Versions 3.0 to 5.0A): ripped and improved by AsuharaMoon; "
                     "credits: Chimpo, GrandMasterGalvatron, Team Megamix. Shadow the Hedgehog (c) SEGA - "
                     "https://www.spriters-resource.com/sega_genesis/sonicthehedgehogmegamixhack/asset/97116/. Signpost: Goal Signs - "
                     "Sonic Megamix. Ripped by AsuharaMoon. Credits: Yuski, Shadowsoft Games, Chimpo, Team Megamix & Sonic "
                     "Team - https://www.spriters-resource.com/sega_genesis/sonicthehedgehogmegamixhack/asset/97514/",
           "source": SOURCE, "feet_y": 20, "background": [BG_HEX], "colours": COLOURS, "palette": PALETTE,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic2":
        cfg["s3k_animations"] = S3K_ANIMS
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra4SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": ANIMS["Jumping"]}}]
        cfg["ui"] = [{"name": "Extra4_UI", "manifest": "Extra4_ui.json", "elements": ELEMENTS, "out": "build/Extra4_UI.gif"},
                     {"name": "Extra4_Ending", "manifest": "Extra4_ending.json", "elements": ENDING,
                      "out": "build/Extra4_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "shadow.json"), ("Sonic2", "shadow_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
