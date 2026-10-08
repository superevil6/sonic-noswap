#!/usr/bin/env python3
"""Writes Chaos (Chaos 0)'s sheet2ani configs (chaos.json for Sonic 1, chaos_s2.json for Sonic 2).

Chaos, extra 24 (file "Extra24", build ID 30), base character Sonic. Public (credit in mods/NoSwap/README.md).
Sheet: testmods/Chaos.png (602x458, white #ffffff background, 15 sprite colours: the sprites' own whites are #f8f8f8),
"Sonic Adventure Boss Chaos 0" by ssstGoldy20, signed "BY SSST_GOLDI20" (see SOURCE.txt).
Not used: the "PHOTO" at the top right (SEGA's art), the little signature portrait at the bottom left, the Chaos
Emerald icons, and the larger "PIXEL ART" Chaos on the right (the same artist's bigger drawing: his select card used
it at 4x until the user found it clashed with everyone else's).

Frames are cut by their bounding boxes (connected components of everything that isn't the #ffffff background). Every
sprite faces right. Rows (y):
   107-145  the rise from a puddle, 8 frames: R1-R3 flat puddles (R3 with his head's tip showing), R4 half risen, R5-R8
            standing (his legs settling)
   152-191  HIT: H1-H3 his body bubbling up, then the splash: H4-H6 droplets flying apart (several loose drops each,
            cut together)
   205-242  ATACK: A1 the wind-up, A2-A4 the stretching arm (the fist 53, 77, then 129 px ahead of his head;
            A4 lacks his brain, the pink core: not used)
   254-296  RUN: 14 frames (U1-U14)
   308-341  FALL (a dive)
   346-388  JUMP: J1 crouched, J2 arms up
He has no idle, skid, push, look up or crouch: stand-ins are chosen from these frames (below).

Template: Sonic's .ani (Sonic's moveset). His jump, Spin Dash and special stage ball is the generic spin ball
(tools/generic_ball.py: Sonic Mania's plain spin ball, SEGA's art; it replaced his wobbling puddle) in
his own blues (BALL_COLOURS), not enlarged (Sonic's ball size); its frames sit in a strip under the working sheet
(build/Chaos_ball.png). The Puddle Slide keeps his puddle frames.

Size: drawn 38-40 px, he reads as short, so every frame is enlarged 1.1x (SCALE), nearest-neighbour: the user's
exception to the faithful art rule, for him and Sticks only (2026-09-27). Each frame is enlarged on its own
(sheet2ani.scale_nearest) onto a working sheet, build/Chaos_scaled.png, that every build reads (S1 / S2 / CD / S3&K,
HUD, continue, ending, his Origins select card: his "Stopped" frame, 8x, like everyone's), so pivots, feet and anchors
follow from the enlarged frames; the punch's head columns and the melee reach (abilities.py) are 1.1x too.

Abilities (appended slots; the moves are in tools/abilities.py, build_soniccd.py and the DLL):
  41 "Puddle Drop": the dive (FALL), while he drops after jump in mid-air (an attack, like the Hammer Drop).
  42 "Puddle Slide": the rise, R1-R8, one frame each; the code picks the frame: melting (R5 down to R1), sliding on the
      flat puddle R1 (held: R2 shows his head's tip), rising (R2 up to R8). CD: 47.
  43 / 44 "Stretch Punch" / "Stretch Punch Air": A1, A2, A3, A3, A2, A1 (out and back; not A4, which lacks his brain),
      placed by his head (the arm's length doesn't move his body); the melee's reach follows the fist (abilities.py). CD: 46.
  47 "Swim": the water swim's stroke (underwater, jump in mid-air: abilities.py water_swim): U1, U3 ... U13 of his run,
      his limbs paddling, centred. CD: 48; S3&K: his extra animation 5.

Nothing is redrawn or recoloured (and only the 1.1x above resizes): frames are cut (and a run frame repeats); the HUD icons are crops of
his standing head (R8); only the "CHAOS" name tag (not on the sheet) is our own lettering in the HUD font the other
extras use. Every sheet colour used has its own palette slot (74-88): none merged.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import generic_ball  # noqa: E402
import hud_font  # noqa: E402
import sheet2ani  # noqa: E402
from sign_face import board_face  # noqa: E402

SHEET = "../Chaos.png"
BACKGROUND = ["#ffffff"]
SRC = Image.open(HERE / SHEET).convert("RGB")
SCALE = 1.1  # his frames enlarged (the user's exception for him: see the notes)
SCALED = HERE / "build" / "Chaos_scaled.png"

B = {  # frame -> [x, y, w, h] (its bounding box on the sheet)
    # the rise from a puddle
    "R1": [27, 126, 30, 19], "R2": [61, 126, 30, 19], "R3": [94, 125, 30, 20], "R4": [130, 113, 30, 32],
    "R5": [167, 107, 31, 38], "R6": [202, 107, 31, 38], "R7": [238, 108, 31, 37], "R8": [275, 108, 31, 37],
    # HIT: the body bubbling, then the splash (each splash frame is several loose drops)
    "H1": [19, 152, 31, 39], "H2": [58, 153, 31, 38], "H3": [97, 152, 31, 39],
    "H4": [139, 164, 24, 27], "H5": [182, 166, 23, 25], "H6": [218, 166, 16, 25],
    # ATACK
    "A1": [16, 205, 33, 37], "A2": [57, 205, 68, 37], "A3": [133, 205, 92, 37], "A4": [234, 205, 144, 37],
    # FALL, JUMP
    "FALL": [19, 308, 38, 33], "J1": [18, 355, 30, 33], "J2": [49, 346, 34, 39],
}
RUN_X = [(19, 255, 27, 38), (54, 254, 26, 39), (88, 254, 23, 40), (116, 255, 25, 39), (145, 257, 26, 38),
         (178, 256, 25, 39), (209, 255, 23, 39), (234, 254, 27, 41), (268, 256, 27, 38), (303, 255, 26, 39),
         (337, 255, 23, 40), (367, 255, 25, 39), (399, 255, 26, 38), (430, 255, 25, 39)]
for _k, _r in enumerate(RUN_X, 1):
    B[f"U{_k}"] = list(_r)
# His head's columns in the ATACK frames (the top rows are the head alone): the frames are placed by it, so the arm
# grows ahead of a body that stays put
HEAD = {"A1": (11, 15), "A2": (6, 16), "A3": (6, 16), "A4": (6, 16)}


def scaled_sheet():
    """Every frame in B enlarged SCALE times on its own (sheet2ani.scale_nearest: the same pixels, nearest-neighbour),
    shelf-packed 2 px apart onto SCALED (the sheet's background), plus the continue icons' frames as drawn (UNSCALED).
    Returns {frame name: its rect there} (the unscaled ones as "<name>@1")."""
    imgs = {n: sheet2ani.scale_nearest(SRC.crop((x, y, x + w, y + h)), SCALE) for n, (x, y, w, h) in B.items()}
    imgs.update({f"{n}@1": SRC.crop((B[n][0], B[n][1], B[n][0] + B[n][2], B[n][1] + B[n][3])) for n in UNSCALED})
    width, rects, x, y, shelf = 1024, {}, 2, 2, 0
    for n, img in imgs.items():
        if x + img.width + 2 > width:
            x, y, shelf = 2, y + shelf + 2, 0
        rects[n] = [x, y, img.width, img.height]
        x += img.width + 2
        shelf = max(shelf, img.height)
    out = Image.new("RGB", (width, y + shelf + 2), BACKGROUND[0])
    for n, img in imgs.items():
        out.paste(img, tuple(rects[n][:2]))
    SCALED.parent.mkdir(parents=True, exist_ok=True)
    out.save(SCALED)
    return rects


# The continue icons stay their drawn size: enlarged, they'd be the biggest of any extra's and grow the icon boxes every
# package shares (noswap_common.UiSheets), moving every other package's art
UNSCALED = ("J1", "J2")
S = scaled_sheet()  # frame name -> its enlarged frame's rect on SCALED (what every config uses)


def f(*names):
    return [S[n] for n in names]


def by_head(name):
    x, y, w, h = S[name]
    left, width = (round(v * SCALE) for v in HEAD[name])  # (the head's columns, enlarged with the frame)
    return {"rect": S[name], "anchor_box": [x + left, y, width, h]}


RISE = f("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8")
RUN = f(*[f"U{k}" for k in range(1, 15)])
HIT = f("H1", "H2", "H3")
DISSOLVE = f("H1", "H2", "H3", "H4", "H5", "H6")
PUNCH = [by_head(n) for n in ("A1", "A2", "A3", "A3", "A2", "A1")]  # (not A4: his brain is missing there)
PALETTE = {
    "74": "#202020", "75": "#303030",  # outlines
    "76": "#584898", "77": "#6880e0", "78": "#00b8f8", "79": "#80e8f8", "80": "#f8f8f8",  # his water body, dark to light
    "81": "#000060", "82": "#0040e8",  # deep blues
    "83": "#f8b8f8", "84": "#e860c8",  # his brain
    "85": "#106020", "86": "#208810", "87": "#38a800", "88": "#98e048",  # his eyes
}
# his ball: the generic spin ball in his own colours (three of his water body's blues, his white; the outline: the next
# darker blue of his own, generic_ball.outline_for, not his near-black outline)
BALL_COLOURS = generic_ball.colours(dark="#0040e8", mid="#00b8f8", light="#80e8f8", shine="#f8f8f8",
                                    palette=list(PALETTE.values()))
WORKING = HERE / "build" / "Chaos_ball.png"  # SCALED with the ball's frames underneath
BALL = generic_ball.source_with_ball(SCALED, BALL_COLOURS, BACKGROUND[0], WORKING)

ANIMS = {
    "Stopped": {"frames": f("R8")},  # the rise's last frame: standing (also the S3&K save screen picture and the Origins select card)
    "Waiting": {"frames": f("R8")},
    "Looking Up": {"frames": f("R8")},  # (no look-up pose)
    "Looking Down": {"frames": f("R6", "R5", "R4"), "loop": 2},  # sinking halfway into a puddle
    "Walking": {"frames": RUN, "rot": 2, "align": True},  # the run frames (the game plays them slower at a walk)
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("A1")},  # leaning back, arm drawn back
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Bouncing": {"frames": f("J2"), "anchor": "center"},  # arms up
    "Hurt": {"frames": HIT, "speed": 24, "anchor": "center"},  # his body bubbling up
    "Dying": {"frames": DISSOLVE, "speed": 16, "loop": 5, "anchor": "center"},  # bursting into droplets
    "Drowning": {"frames": DISSOLVE, "speed": 16, "loop": 5, "anchor": "center"},
    "Fan Rotate": {"frames": f("FALL"), "anchor": "center"},
    "Breathing": {"frames": f("J2"), "anchor": "center"},
    "Pushing": {"frames": f("U3", "U4", "U5", "U6"), "align": True},  # (no push pose: walking into it)
    "Flailing 1": {"frames": f("J1", "J2"), "align": True},
    "Flailing 2": {"frames": f("J2", "J1"), "align": True},
    "Hanging": {"frames": f("J2"), "anchor": "center"},
    "Clinging On": {"frames": f("FALL"), "anchor": "center"},
    "Corkscrew H": {"frames": RUN, "align": True},
    "Water Slide": {"frames": f("R1", "R2")},  # a puddle
    "Continue": {"frames": RISE, "loop": 7},  # rising from a puddle
    "Continue Up": {"frames": f("J1", "J2"), "loop": 1},
    "Super Transform": {"frames": f("J1", "J2"), "loop": 1, "anchor": "center"},
}
S1_ONLY = {}
S2_ONLY = {
    "Bored!": {"frames": f("R8", "R7", "R6", "R5", "R4", "R5", "R6", "R7"), "loop": 0},  # sagging, then back up
    "Flailing 3": {"frames": f("J1", "J2", "J1", "J2"), "align": True},
    "Grabbed": {"frames": f("H1", "H2"), "anchor": "center"},
    "Twirl H": {"frames": RUN, "rot": 2, "align": True},
}
CD_ONLY = {name: {"frames": RUN, "align": True} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    "41": {"name": "Puddle Drop", "frames": f("FALL"), "anchor": "center"},
    "42": {"name": "Puddle Slide", "frames": RISE, "speed": 0},  # the code picks the frame
    "43": {"name": "Stretch Punch", "frames": PUNCH, "speed": 0},
    "44": {"name": "Stretch Punch Air", "frames": PUNCH, "speed": 0},
    # the water swim's stroke (abilities.py water_swim; CD 48, S3&K extra 5): his RUN frames, every other one, his limbs
    # paddling, centred as his mid-air poses are
    "47": {"name": "Swim", "frames": f("U1", "U3", "U5", "U7", "U9", "U11", "U13"), "anchor": "center", "speed": 80},
}


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
STAND = S["R8"]  # standing (enlarged: 34x41): his head is its middle columns, the top 16 rows its crest, brain, eyes
MID = STAND[0] + round(7 * SCALE) + (round(16 * SCALE) - 16) // 2  # the head's middle 16 columns
ELEMENTS = {
    "life_icon": {"rect": [MID, STAND[1], 16, 16], "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("CHAOS")},
    "monitor_1up": {"rect": [MID, STAND[1] + 1, 16, 14], "trim": False},
    # no signpost art: the standing pose's head (its top 20 rows, 26 wide) on the game's own board (Items2),
    # enlarged 1.3x nearest-neighbour to fill its 40x24 face area (the user's signpost exception; tools/sign_face.py)
    "sign_face": board_face([STAND[0], STAND[1], 26, 20], 1.3),
    # continue icons: no small set on the sheet; the jump's two frames (crouched, arms up), as drawn (UNSCALED)
    "mini_1": {"rect": S["J1@1"], "remap": PLUS_128},
    "mini_2": {"rect": S["J2@1"], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": S["R8"], "remap": PLUS_128},
    "end_pose_1": {"rect": S["J1"], "remap": PLUS_128},  # crouched
    "end_pose_2": {"rect": S["J2"], "remap": PLUS_128},  # arms up
    "end_pose_3": {"rect": S["H3"], "remap": PLUS_128},  # bubbling up (the sheet has no large pose)
    **{f"good_{n}": {"rect": S[k], "remap": PLUS_128} for n, k in enumerate(("R8", "R7", "J1", "J2", "R6", "R8"), 1)},
}

# The frames use 15 colours, none exactly one of Sonic's: all keep their exact values in the extras' slots 74-88.
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}  # (black: the name tag's shadow, Sonic's slot 1)

def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (the photo, the signature, the pixel art's black) in the slot
    of its nearest key colour, so nothing is left to sheet2ani's guess. (No built frame uses one.)"""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


def check_colours():
    """Every colour in a built frame has its own slot (the faithful art rule: nothing merged)."""
    used = set()
    for x, y, w, h in B.values():
        used |= {rgb for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    missing = {"#%02x%02x%02x" % c for c in used} - set(KEY_COLOURS) - set(BACKGROUND)
    if missing:
        sys.exit(f"chaos: frame colours without a slot of their own: {sorted(missing)}")


CREDIT = ("Chaos 0 sprites by ssstGoldy20 (signed SSST_GOLDI20). Chaos (c) SEGA - "
          "https://www.deviantart.com/ssstgoldy20/art/Sonic-Adventure-Boss-Chaos-0-497339391")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the ending poses: crouched, then arms up
S3K_VICTORY = {"frames": f("J1", "J2")}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra24", "credit": CREDIT,
           "source": str(WORKING.relative_to(HERE)), "feet_y": 20, "background": BACKGROUND, "palette": PALETTE,
           "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else S1_ONLY)),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra24SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {}}}]  # (the ball: generic_ball.apply)
        cfg["ui"] = [{"name": "Extra24_UI", "manifest": "Extra24_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra24_UI.gif"},
                     {"name": "Extra24_Ending", "manifest": "Extra24_ending.json", "elements": ENDING,
                      "out": "build/Extra24_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return generic_ball.apply(cfg, BALL, game)  # jump, Spin Dash, special stages, CD's and S3&K's


if __name__ == "__main__":
    for game, out in (("Sonic1", "chaos.json"), ("Sonic2", "chaos_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
