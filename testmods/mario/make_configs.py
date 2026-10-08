#!/usr/bin/env python3
"""Writes Mario's sheet2ani configs (mario.json for Sonic 1, mario_s2.json for Sonic 2).

Frames are the sprites on testmods/Mario.png ("Mario (Sonic 1-Style)" by Jon Gandee; see SOURCE.txt), numbered
as detected: connected components of everything that isn't the #1b5999 sheet background or the #93bbec boxes
(8-connected, numbered in scan order). The sheet follows Sonic 1's own sheet: standing, look up, crouch, a 6-frame
walk, a 4-frame run, push, jump / curl / ball, spring, skid, a slow walk, breathing, water slide, death, drown,
the Labyrinth fan spin, life icon, continue, clinging on, the ending poses (small, big and huge), the continue
minis and a signpost.

Template: Sonic's .ani. His moves (wired by the integration step):
  slot 41 "Triple Jump Flip": the sheet's tumbling frames (26, 30, 27, 29), a real somersault
  slots 43 / 44 "Fireball" / "Fireball Air": a wind-up, then the throw with a fireball flying ahead of him.
      The fireball is the game's own S3&K Fire Shield flame ("Fire Attack" drawings, as tools/fire_dash.py cuts
      them), shrunk to half size with nearest-neighbour (the user's one exception to the art rule for him).
      Leading-edge reach per frame: FIREBALL_REACH / FIREBALL_REACH_AIR below (printed when run).
  slot 49 "Rolling": the sheet's own curl (26, 30, 27, 29, then the red ball 28), for when rolling gets its own
      animation; Sonic's "Jumping" (which rolling uses too) is Mario's fist-up jump, as the user chose.

Not used: the slow walk (20, 23, 21, 24: arms down, SMB-style), the swim-like leaps 43 and 45 (43 is used for
Clinging On), the Sonic 1 cameo (112) and the side-by-side Mario (111), the credit text.
Nothing of Mario is redrawn, recoloured or resized: frames are cut (the ball is turned in quarter turns), the
HUD icon, signpost and minis are the sheet's own; only the "MARIO" HUD tag is drawn in the game's HUD letter
style, as for other extras whose sheets have none.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
import fire_dash  # noqa: E402

SHEET = HERE.parent / "Mario.png"
SOURCE = "build/source.png"  # the sheet plus the shrunk flames in a strip underneath (written by source_sheet)
BACKGROUND = ["#1b5999", "#93bbec"]  # the sheet, and the boxes the frames sit in

B = {  # sprite number -> [x, y, w, h]
    # row 1: stand, look up, crouch, walk (6), run (4), push (7 with its two sweat drops, sprites 0 and 15)
    8: [5, 6, 21, 39], 14: [36, 8, 22, 37], 16: [70, 23, 22, 22],
    1: [103, 4, 22, 37], 3: [133, 5, 22, 39], 9: [162, 6, 22, 39], 2: [191, 4, 22, 37], 4: [220, 5, 22, 39],
    10: [249, 6, 21, 39],
    11: [278, 6, 28, 37], 5: [307, 5, 28, 40], 12: [336, 6, 28, 37], 6: [365, 5, 28, 40],
    13: [402, 6, 21, 39], 7: [428, 3, 24, 42],
    # row 2: jump (18 arm down, 17 fist up), curl / tumble (26, 30, 27, 29), ball (28), fist-up leap (19),
    # skid (22 arm back, 25 arm up), slow walk (20, 23, 21, 24)
    17: [2, 50, 26, 36], 18: [35, 50, 25, 36],
    26: [73, 58, 22, 32], 30: [100, 64, 32, 22], 27: [137, 58, 22, 32], 29: [166, 62, 32, 22], 28: [200, 59, 30, 30],
    19: [237, 50, 26, 38], 22: [269, 52, 28, 38], 25: [301, 53, 25, 37],
    20: [335, 51, 21, 39], 23: [363, 52, 25, 38], 21: [393, 51, 21, 39], 24: [422, 52, 23, 38],
    # row 3: gasping (31), lying flat turning (36 side, 37 front, 38 back, 39/40 other side), tucked (32, 33),
    # front arms up (34), front mouth open (35), life icon (41)
    31: [4, 96, 22, 35], 36: [39, 108, 38, 22], 37: [87, 108, 40, 26], 38: [137, 108, 38, 23],
    39: [185, 108, 38, 24], 40: [234, 108, 39, 24],
    32: [289, 96, 26, 35], 33: [318, 96, 26, 34], 34: [349, 96, 32, 36], 35: [386, 98, 32, 34],
    41: [423, 119, 16, 16],
    # row 4: sitting (52, 53), floating leaps (42, 43 fist forward; 44, 45 arm back), ending (46 stand, 47 sparkle,
    # 50 side, 48/49 front arms out, 51 idle), continue minis (54, 55)
    52: [2, 146, 27, 34], 53: [31, 147, 27, 33],
    42: [63, 141, 25, 34], 43: [92, 141, 25, 36], 44: [121, 141, 25, 34], 45: [150, 141, 25, 36],
    46: [187, 141, 21, 39], 47: [216, 141, 24, 39], 50: [241, 143, 25, 37], 48: [270, 141, 28, 39],
    49: [299, 141, 28, 39], 51: [330, 143, 26, 37], 54: [361, 160, 16, 20], 55: [378, 160, 16, 20],
    # big ending art (71x90, 107x135) and the signpost (board rows 2-31, pole below)
    57: [1, 181, 71, 90], 58: [73, 181, 107, 135], 59: [181, 181, 48, 48],
}
f = lambda *nums: [B[n] for n in nums]

WALK = f(1, 3, 9, 2, 4, 10)
RUN = f(11, 5, 12, 6)
TUMBLE = f(26, 30, 27, 29)  # a somersault: tucked upright, tipping forward, upside down, round again
CURL = TUMBLE + f(28)  # the sheet's Sonic 1-style jump: curl frames, then the ball
BALL_HOLD = 2  # frames each quarter turn is shown (the game's roll speed blurs single frames)
BALL = [{"rect": B[28], "rotate": r} for r in (0, 90, 180, 270) for _ in range(BALL_HOLD)]  # the ball, turning clockwise
SKID = f(22, 25)

ANIMS = {
    "Stopped": {"frames": f(8)},  # also Origins' character select card
    "Waiting": {"frames": f(8, 52, 53), "loop": 1},  # sits down
    "Looking Up": {"frames": f(14), "loop": 0},
    "Looking Down": {"frames": f(16), "loop": 0},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": SKID, "align": True},
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},  # no peel-out art
    "Spin Dash": {"frames": BALL, "anchor": "center"},  # the red ball, turning
    "Jumping": {"frames": f(19), "anchor": "center"},  # the classic fist-up jump (he doesn't curl up)
    "Bouncing": {"frames": f(17), "anchor": "center"},  # springs: the forward-facing fist-up hop
    "Hurt": {"frames": f(32), "anchor": "center"},  # tucked, mouth open
    "Dying": {"frames": f(34), "anchor": "center"},  # front, arms up (Sonic 1's death pose)
    "Drowning": {"frames": f(35), "anchor": "center"},  # front, mouth open
    "Fan Rotate": {"frames": f(36, 37, 38, 39, 40), "anchor": "center", "align": True},  # lying flat, turning
    "Breathing": {"frames": f(31), "anchor": "center"},  # head back, gasping
    "Pushing": {"frames": f(13, 7), "align": True},  # the second with sweat drops
    "Flailing 1": {"frames": f(25, 22), "align": True},  # no balance art: the skid's leaning back, arms waving
    "Flailing 2": {"frames": f(25, 22), "align": True},
    "Hanging": {"frames": f(19), "anchor": "center"},  # fist up
    "Clinging On": {"frames": f(42, 43), "anchor": "center", "align": True},  # floating, fist forward
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": f(32, 33), "anchor": "center", "align": True},  # tucked, sliding
    "Continue": {"frames": f(52, 53)},  # sitting
    "Continue Up": {"frames": f(53, 16, 8), "loop": 2},  # gets up
    "Super Transform": {"frames": f(8), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": f(25, 22), "align": True},
    "Grabbed": {"frames": f(32), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(52, 53), "loop": 0},  # sitting
}

# ---------------------------------------------------------------- the fireball
# S3&K's "Fire Attack" flame drawings 1-3 (fire_dash.FIRE), halved with nearest-neighbour: 1 is the burst (the
# throw), 2 and 3 the round-headed fireball (flight, alternating like S3&K's own flame).
FLAME_SCALE = 2


def shrunk_flame(k):
    img, _ = fire_dash.flame(k, 0)
    img = img.resize((img.width // FLAME_SCALE, img.height // FLAME_SCALE), Image.NEAREST)
    return img.crop(img.getbbox())


FLAMES = {k: shrunk_flame(k) for k in (1, 2, 3)}


def source_sheet():
    """The sheet plus the shrunk flames in a strip underneath (the original file is untouched).
    Returns {drawing: rect on the working copy}."""
    src = Image.open(SHEET).convert("RGB")
    h = max(im.height for im in FLAMES.values())
    out = Image.new("RGB", (src.width, src.height + h + 4), tuple(int(BACKGROUND[0][i:i + 2], 16) for i in (1, 3, 5)))
    out.paste(src, (0, 0))
    rects, x = {}, 2
    for k, im in FLAMES.items():
        out.paste(im, (x, src.height + 2), im)
        rects[k] = [x, src.height + 2, im.width, im.height]
        x += im.width + 2
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return rects


FLAME_RECTS = source_sheet()
# Where the fireball goes, relative to the throwing pose's top-left: the burst over his fist, then the
# fireball 12 px further each frame. The pose's far fist is at its right edge; its middle row is HAND_Y.
FLIGHT = [(1, 16), (2, 22), (3, 34), (2, 46), (3, 58)]  # (flame drawing, left edge x)


def fireball(windup, throw, hand_y, anchor):
    """Wind-up, throw with the burst at his fist, the fireball flying out (4 frames), follow-through.
    Returns (animation, leading edge of the fireball per frame in px from his centre)."""
    body = B[throw]
    half = body[2] // 2  # his centre (sheet2ani's anchor): half the pose's width from its left edge
    frames, reach = [B[windup]], [B[windup][2] - B[windup][2] // 2]
    for k, x in FLIGHT:
        w, h = FLAME_RECTS[k][2:]
        frames.append({"layers": [{"rect": FLAME_RECTS[k], "at": [x, hand_y - h // 2]}, {"rect": body, "at": [0, 0]}],
                       "anchor_layer": 1})
        reach.append(x + w - half)
    frames.append(body)
    reach.append(body[2] - half)
    return {"frames": frames, "anchor": anchor, "speed": 80}, reach


# ground: wind-up (25, hand back by his head), the throw (50, the far fist punched forward, fist rows 19-23)
FIREBALL, FIREBALL_REACH = fireball(25, 50, 21, "feet")
# air: arm back (44), fist forward (42, fist rows 22-25)
FIREBALL_AIR, FIREBALL_REACH_AIR = fireball(44, 42, 23, "center")

APPENDED = {
    "41": {"name": "Triple Jump Flip", "frames": TUMBLE, "anchor": "center", "speed": 120},
    "43": dict(FIREBALL, name="Fireball"),
    "44": dict(FIREBALL_AIR, name="Fireball Air"),
    "49": {"name": "Rolling", "frames": CURL, "anchor": "center", "speed": 240},
}

# ---------------------------------------------------------------- HUD, signpost, continue, ending


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
LIFE, SIGN = B[41], B[59]
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {
    "life_icon": {"rect": LIFE, "trim": False},  # his head (16x16, black rows top and bottom)
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("MARIO")},  # the sheet has no name tag
    "monitor_1up": {"rect": [LIFE[0], LIFE[1] + 1, 16, 14], "trim": False},  # the icon's middle rows
    # the board (30 rows: his face and a V sign) and the top 2 rows of the pole under it: Sonic's 48x32
    "sign_face": {"rect": [SIGN[0], SIGN[1] + 2, 48, 32], "trim": False},
    "mini_1": {"rect": B[54], "remap": PLUS_128},
    "mini_2": {"rect": B[55], "remap": PLUS_128},
}
ENDING = {  # the sheet's own Sonic 1 ending set, in Sonic's order
    "end_idle": {"rect": B[51], "remap": PLUS_128},
    "end_pose_1": {"rect": B[48], "remap": PLUS_128},  # front, arms out (small pose)
    "end_pose_2": {"rect": B[57], "remap": PLUS_128},  # the big leap, fist up (71x90)
    "end_pose_3": {"rect": B[58], "remap": PLUS_128},  # the huge leap (107x135)
    # good ending: standing, the sparkle, side, front arms out
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((46, 46, 47, 50, 48, 49), 1)},
}

PALETTE = {  # Mario's own colours (exact), in the extras' shared global palette slots 74+
    "74": "#fc0000", "75": "#900000", "76": "#480000",  # red cap and shirt, light to dark (and his shoes)
    "77": "#fcb490", "78": "#b46c48",  # skin
    "79": "#fcfcfc", "80": "#b4b4b4", "81": "#909090", "82": "#484848",  # white gloves and greys
    "83": "#242490", "84": "#4848b4", "85": "#6c6cd8",  # blue overalls, dark to light
    "86": "#fcfc00",  # buttons, signpost board, HUD tag
    "87": "#e00000", "88": "#fc9000",  # the fireball's red outline and orange rim (S3&K's flame colours)
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (the text's pure white, the Sonic cameo) in the slot of
    its nearest key colour, so nothing is left to sheet2ani's guess."""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in Image.open(HERE / SOURCE).convert("RGB").getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


COLOURS = all_colours()


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the fist-up leap, then the ending's front arms out
S3K_VICTORY = {"frames": f(19, 48)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra17",
           "credit": "Mario (Sonic 1-Style) by Jon Gandee - https://www.spriters-resource.com/custom_edited/mariocustoms/asset/202710/"
                     " (Mario is Nintendo's); fireball: Sonic 3 & Knuckles' Fire Shield flame (SEGA / Sonic Team)",
           "source": SOURCE, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        # the special stage spins him like Sonic's ball: the sheet's own curl and ball
        cfg["extra_anis"] = [{"name": "Extra17SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": CURL, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra17_UI", "manifest": "Extra17_ui.json", "elements": ELEMENTS, "out": "build/Extra17_UI.gif"},
                     {"name": "Extra17_Ending", "manifest": "Extra17_ending.json", "elements": ENDING,
                      "out": "build/Extra17_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "mario.json"), ("Sonic2", "mario_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("melee_reach (Fireball):", FIREBALL_REACH)
    print("melee_reach (Fireball Air):", FIREBALL_REACH_AIR)
