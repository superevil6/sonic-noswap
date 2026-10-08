#!/usr/bin/env python3
"""Writes Honey the Cat's sheet2ani configs (honey.json for Sonic 1, honey_s2.json for Sonic 2; CD's and S3&K's come
from the Sonic 2 one).

Honey the Cat (Sonic the Fighters / Sonic Championship), extra 31 (file "Extra31", build ID 37), base character Sonic.
Public (credit in mods/NoSwap/README.md). Sheet: testmods/Honey.png (487x387), by Xeric (see SOURCE.txt). Its terms,
printed on the sheet: "If used, please give credit and link back to my DeviantART page - deviantart.com/xeric-studios".

The sheet: a green page (#8ed784) inside a dark green frame (#516d43, also behind the name, HUD and signpost); both are
background. Nothing is labelled: the rows are her stand (and a wave), walk (8) and run (4); her spin dash (9 flat balls),
curled frames (4) and ball; crouching and crawling poses, then a claw attack (two spinning swipes and a lunge) and a
horizontal dive; four idle frames, a dizzy trio, fists / a claw flash / a point / two arms-out poses; a cheer, a white
flash, a shocked face, a side stand, a front, three-quarter and side-on view (no back view), two steps; the name, HUD and signpost at the top right. She faces
right. Frames are named below by what they show.

Size: she stands 42 px tall (STAND, bow to soles); Sonic is about 40. Not scaled.

Abilities (tools/abilities.py 37; wired there, in build_soniccd.py and the DLL):
  - Y: Spin Attack (abilities.py spin_attack, 2026-09-27, replacing the Claw Swipe and Ray's glide): held, a whirl on
    the ground or in the air, as a 360 turn on the spot (front, three-quarter, side, then those two mirrored: the user's
    pick, replacing the curled frames CURL1-4): slot 41 in the air, slot 43 on the ground, both on her feet; CD 45 / 46.
    Two game frames per turn frame (spin_ticks 2), drawn leaning toward her travel as she moves (spin_lean).
  - no jump ability of her own (the glide is gone: the spin replaces it).
  - ball: her own curled frames and ball, and her own spin dash row.

Nothing is redrawn or resized: frames are cut as drawn. Colours: 28 on the frames; black is Sonic's slot 1 and 21 keep
their exact values in slots 74-94; the six rarest (1 or 2 pixels each: MERGED) go to their nearest slot (the faithful-art
rule's colour exception). She has no continue icons or ending poses of her own: the HUD head stands in for the continue
icons, and her poses (stand, cheer, point, arms out) for the ending.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

SHEET = "../Honey.png"
BACKGROUND = ["#8ed784", "#516d43"]  # the page and its frame
SRC = Image.open(HERE / SHEET).convert("RGB")

B = {
    "STAND": [14, 18, 29, 42], "WAVE": [46, 18, 32, 42],
    **{f"WALK{k+1}": r for k, r in enumerate([[12, 73, 31, 42], [48, 72, 28, 42], [80, 71, 27, 43], [112, 72, 28, 42],
                                              [147, 72, 31, 42], [184, 71, 27, 43], [215, 71, 26, 43], [248, 72, 30, 42]])},
    **{f"RUN{k+1}": r for k, r in enumerate([[280, 74, 38, 40], [325, 74, 40, 40], [378, 75, 39, 39], [426, 74, 39, 40]])},
    "DASH1": [15, 130, 30, 27], **{f"DASH{k}": [46 + 30 * (k - 2), 130, 29, 27] for k in range(2, 10)},  # SPIN DASH row
    "CURL1": [293, 129, 29, 30], "CURL2": [327, 129, 30, 29], "CURL3": [362, 129, 29, 30], "CURL4": [395, 130, 30, 29],
    "BALL": [428, 129, 30, 30],
    "LOW1": [10, 179, 45, 28], "CROUCH": [60, 177, 39, 30], "FRONTCROUCH": [106, 176, 30, 31], "LOW2": [141, 178, 39, 30],
    "DIVE": [186, 178, 38, 28], "LIE": [232, 183, 47, 23],
    "SWIPE1": [294, 169, 34, 39], "SWIPE2": [330, 172, 34, 37], "LUNGE": [370, 170, 43, 38], "GLIDE": [419, 173, 48, 31],
    **{f"IDLE{k+1}": r for k, r in enumerate([[18, 225, 24, 39], [47, 226, 24, 38], [75, 225, 24, 39], [104, 226, 24, 38]])},
    "DIZZY1": [142, 228, 33, 35], "DIZZY2": [185, 228, 33, 35], "DIZZY3": [228, 228, 33, 35],
    "FISTS": [278, 222, 25, 41], "CLAW": [313, 222, 25, 41], "POINT": [343, 221, 30, 42], "SHRUG1": [378, 222, 33, 41],
    "SHRUG2": [413, 222, 33, 41],
    "CHEER": [21, 277, 33, 45], "FLASH": [61, 277, 33, 45], "SHOCK": [103, 274, 33, 48], "SIDE": [149, 276, 26, 47],
    "FRONT": [182, 280, 26, 42], "THREEQ": [212, 280, 23, 42], "PROFILE": [242, 280, 25, 42],  # front, 3/4, side on
    "STEP1": [280, 280, 28, 43], "STEP2": [318, 281, 27, 42],
}
HUD = [376, 47, 48, 16]
SIGN = [425, 15, 48, 32]


def f(*names):
    return [B[n] for n in names]


C = lambda frames: {"frames": frames, "anchor": "center"}
WALK = f(*[f"WALK{k}" for k in range(1, 9)])
RUN = f(*[f"RUN{k}" for k in range(1, 5)])
BALL = f("CURL1", "BALL", "CURL2", "BALL", "CURL3", "BALL", "CURL4", "BALL")  # curled frames between the plain ball
SPINDASH = f(*[f"DASH{k}" for k in range(1, 10)])
IDLE = f("IDLE1", "IDLE2", "IDLE3", "IDLE4")
TURN = f("SIDE", "PROFILE", "FRONT", "THREEQ")  # side on, then round the front
SHRUG = f("SHRUG1", "SHRUG2")
# the Spin Attack: a 360 turn on the spot (the user's pick, 2026-09-27): front, three-quarter, side, then the side and
# three-quarter mirrored (the sheet has no back view), looping (the move's own clock picks the frame)
flip = lambda n: {"rect": B[n], "flip": True}
SPIN = f("FRONT", "THREEQ", "PROFILE") + [flip("PROFILE"), flip("THREEQ")]

ANIMS = {
    "Stopped": {"frames": f("STAND")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": IDLE, "loop": 0},
    "Looking Up": {"frames": f("SIDE")},
    "Looking Down": {"frames": f("CROUCH")},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("LOW1")},
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": C(BALL),
    "Bouncing": C(f("CHEER")),
    "Hurt": C(f("SHOCK")),
    "Dying": C(f("SHOCK")),
    "Drowning": C(f("FLASH")),  # (the white flash: pale)
    "Fan Rotate": C(TURN),
    "Breathing": C(f("SHOCK")),
    "Pushing": {"frames": f("LUNGE")},
    "Flailing 1": {"frames": SHRUG, "align": True},
    "Flailing 2": {"frames": SHRUG, "align": True},
    "Hanging": C(f("CHEER")),
    "Clinging On": C(f("CHEER")),
    "Corkscrew H": {"frames": TURN},
    "Water Slide": C(f("LIE")),
    "Continue": {"frames": IDLE},
    "Continue Up": {"frames": f("CHEER")},
    "Super Transform": {"frames": f("CHEER")},
}
S2_ONLY = {
    "Bored!": {"frames": f("WAVE", "STAND"), "loop": 0},
    "Flailing 3": {"frames": SHRUG, "align": True},
    "Grabbed": C(f("DIZZY1", "DIZZY2", "DIZZY3")),
    "Twirl H": {"frames": TURN, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    # rot / s3k_rot 1: drawn with full rotation, for the spin's lean toward her travel (a runtime draw effect, the
    # frames untouched: abilities.py spin_lean)
    "41": {"name": "Spin Attack", "frames": SPIN, "speed": 0, "rot": 1, "s3k_rot": 1},  # in the air (on her feet line too)
    "43": {"name": "Spin Attack Ground", "frames": SPIN, "speed": 0, "rot": 1, "s3k_rot": 1},  # on the ground: on her feet
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HEAD = HUD[:2] + [16, 16]
ELEMENTS = {  # the sheet's own HUD art
    "life_icon": {"rect": HEAD, "trim": False},  # her head (16x16, no black rows round it)
    "life_name": {"rect": [HUD[0] + 17, HUD[1] + 1, 31, 7]},  # "HONEY" (yellow, black shadow), above the "x"
    "monitor_1up": {"rect": [HUD[0], HUD[1] + 1, 16, 14], "trim": False},  # the head's middle 14 rows
    "sign_face": {"rect": SIGN, "trim": False},
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the HUD head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses, six good-ending frames (2 / 3 alternate: fists, the claw flash)
    "end_idle": {"rect": B["STAND"], "remap": PLUS_128},
    "end_pose_1": {"rect": B["CHEER"], "remap": PLUS_128},
    "end_pose_2": {"rect": B["POINT"], "remap": PLUS_128},
    "end_pose_3": {"rect": B["SHRUG2"], "remap": PLUS_128},  # (no big pose on the sheet)
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128}
       for n, k in enumerate(("STAND", "FISTS", "CLAW", "POINT", "SHRUG1", "SHRUG2"), 1)},
}

# black is Sonic's own slot 1; 21 colours keep their exact values in slots 74-94
PALETTE = {
    "74": "#484848", "75": "#909090", "76": "#b4b4b4", "77": "#fcfcfc",  # hair greys, white (gloves, bow)
    "78": "#400000", "79": "#800000", "80": "#900000", "81": "#940000", "82": "#e00000", "83": "#fc0000",  # reds
    "84": "#906c00", "85": "#9e8301", "86": "#dbcd24", "87": "#fcfc00",  # her gold fur, the tag's yellow
    "88": "#906c48", "89": "#fcb490",  # skin
    "90": "#080000", "91": "#010101", "92": "#202020",  # near-blacks (the ball, the HUD, a few hair pixels)
    "93": "#e7e3e7", "94": "#b5b6b5",  # near-whites / greys (a back view, the signpost)
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}
MERGED = {"#6c0000", "#242448", "#606080", "#980030", "#600000", "#a3632b"}  # 1-2 px each: their nearest slot


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet in the slot of its nearest key colour (MERGED among them)."""
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
    """Every colour in a built frame or UI element has a slot of its own, but the MERGED ones."""
    used = set()
    for x, y, w, h in list(B.values()) + [HUD, SIGN]:
        used |= {"#%02x%02x%02x" % rgb for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    missing = used - set(KEY_COLOURS) - set(BACKGROUND) - MERGED
    if missing:
        sys.exit(f"honey: frame colours without a slot of their own: {sorted(missing)}")


def swipe_reach(game="Sonic2u", slot=43):
    """Her claws per CLAW SWIPE frame in the built .ani: (right edge, top, bottom) of the frame's pixels, px from the
    player's centre facing right (for abilities.py 37's melee_reach)."""
    sys.path.insert(0, str(REPO / "tools"))
    import extras
    e = next(x for x in extras.EXTRAS if x["art"] == HERE)
    ani = extras.player_ani(e, game)
    out = []
    for fr in ani["anims"][slot]["frames"]:
        sheet = Image.open(extras.player_build(e, game) / "Sprites" / ani["sheets"][fr["sheet"]])
        im = sheet.crop((fr["x"], fr["y"], fr["x"] + fr["w"], fr["y"] + fr["h"]))
        px = im.load()
        pts = [(x, y) for x in range(im.width) for y in range(im.height) if px[x, y]]
        out.append((max(x for x, _ in pts) + fr["px"] + 1, min(y for _, y in pts) + fr["py"],
                    max(y for _, y in pts) + fr["py"] + 1))
    return out


CREDIT = ("Honey the Cat (Sonic the Fighters) sprites by Xeric - https://www.deviantart.com/xeric-studios - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/139745/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): fists together, then her cheer
S3K_VICTORY = {"frames": f("FISTS", "CHEER")}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra31", "credit": CREDIT,
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra31SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(BALL)}}]
        cfg["ui"] = [{"name": "Extra31_UI", "manifest": "Extra31_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra31_UI.gif"},
                     {"name": "Extra31_Ending", "manifest": "Extra31_ending.json", "elements": ENDING,
                      "out": "build/Extra31_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    if "--reach" in sys.argv:
        for slot in (43, 44):
            print(slot, swipe_reach(slot=slot))
        sys.exit()
    for game, out in (("Sonic1", "honey.json"), ("Sonic2", "honey_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
