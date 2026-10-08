#!/usr/bin/env python3
"""Writes Bean the Dynamite's sheet2ani configs (bean.json for Sonic 1, bean_s2.json for Sonic 2; CD's and S3&K's come
from the Sonic 2 one).

Bean, extra 27 (file "Extra27", build ID 33), base character Sonic. Public (credit in mods/NoSwap/README.md).
Sheet: testmods/Bean.png (693x529), "Bean the Dynamite, custom sprites (Sonic 1 style)" by deltaConduit (see SOURCE.txt).
Its terms, printed on the sheet: "ORIGINAL SPRITES BY SEGA, SONIC TEAM & DELTACONDUIT. FREE TO USE, BUT GIVE CREDIT. DO NOT
EDIT. DON'T USE THESE SPRITES FOR EXE STUFF." So, strictly: frames are only cut out (crops) as drawn; no scaling, no
recolouring, no merged colours, no pieces put together into new frames, nothing .exe-themed.

The sheet: a lavender page (#d8b4fc) with every sprite in a cell (#b490fc, a few #906cd8) cut tight round it, under a
green label. All three are background. Frames are named by the label they sit under, left to right from 1. The cell
rects are the sprites' own bounding boxes (connected pieces of everything that isn't the page colour).

Size: he stands 40 px tall (his "Stopped" frame, crest to soles), Sonic's height. Not enlarged.

Abilities (tools/abilities.py 33; the moves are wired there, in build_soniccd.py, tools/shots_v3.py and the DLL):
  - Y: Bomb Throw, a real bouncing shot (abilities.py "shot", motion "bounce", as Mario's fireball) with the sheet's own
    loose bomb (next to his idle frames, cut as-is). By default the low throw (bouncing along the ground); up held as Y
    is pressed: the high throw, lobbed higher (the shot's "up" numbers). The throw pose (slots 43 / 44, CD 46) is the
    last frame of the throw: BOMB THROW (HIGH) 3 after an up throw, BOMB THROW (LOW) 3 otherwise.
  - jump ability: Leap, Trip's double jump (abilities.py double_jump), with the LEAP frame (slot 41).
  - ball: his own SPIN row (the ball between the four turning frames) and SPINDASH row.

Nothing is redrawn, recoloured or resized: frames are cut as drawn. Two crops beyond a cell's edge: the Sonic 1 ending's
medium pose (ENDING 7, 77x65) loses its 6 leftmost columns (the tip of his tail feathers) to fit the 71 px box every
package's ending sheet has; nothing else is cut. The HUD icon, name tag, 1-UP picture, signpost board, continue icons
and ending poses are the sheet's own. Palette: black in Sonic's slot 1, the other 14 colours exactly in slots 74-87;
nothing merged (check_colours stops the build otherwise).
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

SHEET = "../Bean.png"
BACKGROUND = ["#d8b4fc", "#b490fc", "#906cd8"]  # the page and its two cell colours
SRC = Image.open(HERE / SHEET).convert("RGB")

B = {  # frame -> [x, y, w, h]: its cell (the sprite's own bounding box)
    "STAND": [2, 66, 28, 40],  # the unlabelled standing frame at the left of IDLE
    "IDLE1": [40, 70, 35, 36], "IDLE2": [76, 70, 35, 36],  # clapping
    "BOMB": [112, 76, 8, 10],  # the loose bomb beside IDLE (the shot's art)
    "UP": [130, 65, 27, 41], "DUCK": [167, 83, 37, 23],
    "WALK1": [214, 68, 32, 38], "WALK2": [247, 66, 33, 38], "WALK3": [281, 67, 32, 39], "WALK4": [314, 68, 33, 38],
    "WALK5": [348, 66, 35, 38], "WALK6": [384, 67, 33, 39],
    "WALKA1": [427, 61, 26, 40], "WALKA2": [454, 59, 29, 44], "WALKA3": [484, 60, 30, 42], "WALKA4": [515, 61, 31, 44],
    "WALKA5": [547, 59, 31, 47], "WALKA6": [579, 61, 33, 39],
    "RUN1": [2, 136, 37, 35], "RUN2": [40, 136, 37, 35], "RUN3": [78, 136, 37, 35], "RUN4": [116, 136, 37, 35],
    "RUNA1": [163, 128, 29, 43], "RUNA2": [193, 127, 26, 43], "RUNA3": [220, 128, 28, 44], "RUNA4": [249, 128, 26, 43],
    "SKID1": [285, 131, 36, 40], "SKID2": [322, 132, 35, 39],
    "DASH1": [367, 144, 32, 27], "DASH2": [400, 144, 31, 27], "DASH3": [432, 144, 31, 27], "DASH4": [464, 144, 31, 27],
    "DASH5": [496, 144, 31, 27],
    "BALL": [537, 141, 30, 30], "TURN1": [568, 141, 30, 30], "TURN2": [599, 141, 30, 30], "TURN3": [630, 141, 30, 30],
    "TURN4": [661, 141, 30, 30],
    "HIGH1": [2, 195, 37, 41], "HIGH2": [40, 195, 28, 41], "HIGH3": [69, 196, 32, 40],
    "LOW1": [111, 197, 32, 39], "LOW2": [144, 197, 33, 39], "LOW3": [178, 197, 32, 39],
    "LEAP": [220, 197, 33, 39],
    "PUSH1": [263, 200, 34, 36], "PUSH2": [298, 199, 34, 37], "PUSH3": [333, 200, 34, 36], "PUSH4": [368, 199, 34, 37],
    "BAL1": [412, 192, 32, 44], "BAL2": [445, 193, 33, 43],
    "SPRING": [488, 190, 26, 46], "GASP": [524, 195, 33, 41],
    "HURT1": [567, 202, 43, 34], "HURT2": [611, 202, 42, 34],
    "FAN1": [2, 275, 45, 25], "FAN2": [48, 275, 44, 25], "FAN3": [93, 275, 42, 25],
    "PIPE1": [145, 271, 48, 28], "PIPE2": [194, 271, 47, 29],
    "DIE": [251, 255, 35, 45], "DROWN": [296, 257, 35, 43],
    "CONT1": [341, 272, 38, 28], "CONT2": [380, 272, 37, 28], "CONT3": [418, 272, 37, 28],
    "ICON1": [523, 277, 16, 23], "ICON2": [540, 277, 16, 23],  # CONTINUE ICON
    "END1": [2, 325, 23, 40], "END2": [26, 325, 27, 40], "END3": [54, 322, 28, 43], "END4": [83, 325, 31, 40],
    "END5": [115, 325, 31, 40], "END6": [147, 332, 29, 33],
    "END_MEDIUM": [177 + 6, 322, 71, 65],  # ENDING 7 (77x65), its 6 leftmost columns cut: the 71 px pose box
    "END_BIG": [255, 322, 154, 133],  # ENDING 8, as drawn
}
HUD = [465, 284, 48, 16]  # 1-UP: his head (16x16, black rows above and below), the "BEAN" tag, the "x"
SIGN = [566, 252, 48, 32]  # GOAL SIGN: the post's cap (2 rows, his crest over it) and the 30-row board


def f(*names):
    return [B[n] for n in names]


def flip(name):
    return {"rect": B[name], "flip": True}


C = lambda frames: {"frames": frames, "anchor": "center"}
WALK = f(*[f"WALK{k}" for k in range(1, 7)]) + f(*[f"WALKA{k}" for k in range(1, 7)])  # upright, then 45 degrees
RUN = f(*[f"RUN{k}" for k in range(1, 5)]) + f(*[f"RUNA{k}" for k in range(1, 5)])
# the SPIN row: the plain ball between the four turning frames, as Sonic 1's jump alternates its ball
BALL = f("TURN1", "BALL", "TURN2", "BALL", "TURN3", "BALL", "TURN4", "BALL")
SPINDASH = f(*[f"DASH{k}" for k in range(1, 6)])
TURNING = f("TURN1", "TURN2", "TURN3", "TURN4")
HURT = f("HURT1", "HURT2")
# the throw pose: BOMB THROW (HIGH), then (LOW). The pose shows one frame: the last (LOW 3) by default, frame 2 (HIGH 3)
# after an up throw (abilities.py 33 "shot" "up" "pose_frame")
THROW = f("HIGH1", "HIGH2", "HIGH3", "LOW1", "LOW2", "LOW3")
HIGH_POSE = 2

ANIMS = {
    "Stopped": {"frames": f("STAND")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": f("IDLE1", "IDLE2"), "loop": 0},  # IDLE: clapping
    "Looking Up": {"frames": f("UP")},
    "Looking Down": {"frames": f("DUCK")},
    "Walking": {"frames": WALK},  # rot 3 (the template's): the 45-degree half is drawn
    "Running": {"frames": RUN},
    "Skidding": {"frames": f("SKID1", "SKID2"), "align": True},
    "Super Peel Out": {"frames": RUN[:4], "rot": 2},  # (no peel-out on the sheet: the upright run, turned by the engine)
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": C(BALL),
    "Bouncing": C(f("SPRING")),
    "Hurt": C(HURT[:1]),
    "Dying": C(f("DIE")),
    "Drowning": C(f("DROWN")),
    "Fan Rotate": C(f("FAN1", "FAN2", "FAN3")),
    "Breathing": C(f("GASP")),  # AIR GASP
    "Pushing": {"frames": f("PUSH1", "PUSH2", "PUSH3", "PUSH4"), "align": True},
    "Flailing 1": {"frames": f("BAL1", "BAL2"), "align": True},
    "Flailing 2": {"frames": f("BAL1", "BAL2"), "align": True},
    "Hanging": C(f("PIPE1", "PIPE2")),  # PIPE CLING
    "Clinging On": C(f("PIPE1", "PIPE2")),
    "Corkscrew H": {"frames": TURNING},  # Sonic 1's twirl: the turning frames
    "Water Slide": C(HURT),  # HURT/FLUME
    "Continue": {"frames": f("CONT1", "CONT2", "CONT3")},  # CONTINUE?
    "Continue Up": {"frames": f("UP")},
    "Super Transform": {"frames": f("IDLE1", "IDLE2")},
}
S2_ONLY = {
    "Bored!": {"frames": f("IDLE1", "IDLE2"), "loop": 0},
    "Flailing 3": {"frames": f("BAL1", "BAL2"), "align": True},
    "Grabbed": C(HURT),
    "Twirl H": {"frames": TURNING, "rot": 2},
}
# CD-only animations cd_config.py would copy from "Running" (upright then 45 degrees): the upright run only
CD_ONLY = {name: {"frames": RUN[:4]} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    "41": {"name": "Leap", "frames": f("LEAP"), "anchor": "center", "speed": 120, "hitbox": 1},  # (Trip's: the ball's box)
    "43": {"name": "Bomb Throw", "frames": THROW, "speed": 0},
    "44": {"name": "Bomb Throw Air", "frames": THROW, "anchor": "center", "speed": 0},
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art (1-UP)
    "life_icon": {"rect": HUD[:2] + [16, 16], "trim": False},
    "life_name": {"rect": [HUD[0] + 17, HUD[1] + 1, 31, 7]},  # "BEAN" (yellow, black shadow), above the "x"
    "monitor_1up": {"rect": [HUD[0], HUD[1] + 1, 16, 14], "trim": False},  # the icon inside its black rows
    "sign_face": {"rect": SIGN, "trim": False},
    "mini_1": {"rect": B["ICON1"], "remap": PLUS_128},
    "mini_2": {"rect": B["ICON2"], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames: the ENDING row
    "end_idle": {"rect": B["STAND"], "remap": PLUS_128},
    "end_pose_1": {"rect": B["END6"], "remap": PLUS_128},  # the small leap
    "end_pose_2": {"rect": B["END_MEDIUM"], "remap": PLUS_128},
    "end_pose_3": {"rect": B["END_BIG"], "remap": PLUS_128},
    **{f"good_{n}": {"rect": B[f"END{n}"], "remap": PLUS_128} for n in range(1, 7)},
}

# 15 colours: black is Sonic's own slot 1; the other 14 keep their exact values in slots 74-87
PALETTE = {
    "74": "#006c00", "75": "#249000", "76": "#48b424", "77": "#6cd848",  # his greens, dark to light
    "78": "#480000", "79": "#900000", "80": "#fc0000",  # reds (scarf, shoes)
    "81": "#b4b400", "82": "#fcfc00",  # beak and the name tag's yellow
    "83": "#fcfcfc", "84": "#b4b4b4", "85": "#909090", "86": "#484848",  # white, greys (gloves, bomb, the sign)
    "87": "#90fcfc",  # the signpost board's sky
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (the Sonic cameo, the labels) in the slot of its nearest key
    colour, so nothing is left to sheet2ani's guess. check_colours makes sure no built frame uses one."""
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
    """Every colour in a built frame or UI element has a slot of its own (the sheet says DO NOT EDIT: nothing merged)."""
    rects = list(B.values()) + [HUD, SIGN]
    used = set()
    for x, y, w, h in rects:
        used |= {"#%02x%02x%02x" % rgb for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    missing = used - set(KEY_COLOURS) - set(BACKGROUND)
    if missing:
        sys.exit(f"bean: frame colours without a slot of their own: {sorted(missing)}")


CREDIT = ("Bean the Dynamite (Sonic 1 style) custom sprites by deltaConduit. Original sprites by SEGA, Sonic Team & "
          "deltaConduit - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/263920/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the sheet's ending: a fist out, shouting
S3K_VICTORY = {"frames": f("END1", "END3")}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra27", "credit": CREDIT,
           "source": SHEET, "feet_y": 20, "angled_halves": True,  # walk / run: upright, then 45 degrees (S3&K splits them)
           "background": BACKGROUND, "palette": PALETTE, "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra27SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(BALL)}}]
        cfg["ui"] = [{"name": "Extra27_UI", "manifest": "Extra27_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra27_UI.gif"},
                     {"name": "Extra27_Ending", "manifest": "Extra27_ending.json", "elements": ENDING,
                      "out": "build/Extra27_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "bean.json"), ("Sonic2", "bean_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
