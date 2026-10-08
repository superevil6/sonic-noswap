#!/usr/bin/env python3
"""Writes Bark the Polar Bear's sheet2ani configs (bark.json for Sonic 1, bark_s2.json for Sonic 2; CD's and S3&K's come
from the Sonic 2 one).

Bark, extra 28 (file "Extra28", build ID 34), base character Sonic. Public (credit in mods/NoSwap/README.md).
Sheet: testmods/Bark.png (914x489), "Bark the Polar Bear, custom sprites (Sonic 1 style)" by deltaConduit (see
SOURCE.txt). Its terms, printed on the sheet: "ORIGINAL SPRITES BY SEGA, SONIC TEAM & DELTACONDUIT. FREE TO USE, BUT GIVE
CREDIT. DO NOT EDIT. DON'T USE THESE SPRITES FOR EXE STUFF." So, strictly: frames are only cut out (crops) as drawn; no
scaling, no recolouring, no merged colours, no pieces put together into new frames, nothing .exe-themed.

The sheet: a dark blue page (#242490) with every sprite in a cell (#9090fc, a few #6c6cd8) cut tight round it, under a
yellow label. All three are background. Frames are named by the label they sit under, left to right from 1.

Size: he stands 52 px tall (his "Stopped" frame, cap to soles); Sonic is about 40. Not enlarged (nor shrunk): his
collision box is Sonic's, as for every extra (Big is tall too).

Abilities (tools/abilities.py 34; the moves are wired there, in build_soniccd.py and the DLL):
  - jump ability: Slam Ground, Mighty's Hammer Drop (abilities.py hammer_drop): the drop in SLAM GROUND (RIGHT) 1-2 (slot
    41: his stance, then the fist raised overhead, held), landing bounces him up in his ball as Mighty's does, and sends
    out two ground shockwaves (abilities.py "shot", "input" "slam": the games' own Spin Dash dust, his sheet has none).
  - Y: Bear Rush (the user's rework, 2026-09-28, replacing the Double Kick): a shoulder charge, Mecha Sonic's Jet Boost
    (melee_boost) in his RUN frames (slots 43 / 44, CD 46).
  - heavy physics (Gamma's numbers) and his own SPIN ball / SPINDASH row.

Nothing is redrawn, recoloured or resized: frames are cut as drawn. One crop beyond a cell's edge: the Sonic 1 ending's
big pose (ENDING 8, 145x186) loses its bottom 9 rows (his shoe soles) to fit the 177 px pose box every package's ending
sheet has. The HUD icon, name tag, 1-UP picture, signpost board, continue icons and ending poses are the sheet's own.
Palette: black in Sonic's slot 1, the other 14 colours exactly in slots 74-87; nothing merged (check_colours).
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

SHEET = "../Bark.png"
BACKGROUND = ["#242490", "#9090fc", "#6c6cd8"]  # the page and its two cell colours
SRC = Image.open(HERE / SHEET).convert("RGB")

B = {  # frame -> [x, y, w, h]: its cell (the sprite's own bounding box)
    "STAND": [2, 61, 32, 52],  # the unlabelled standing frame at the left of IDLE
    "IDLE1": [44, 59, 35, 54], "IDLE2": [80, 59, 40, 54], "IDLE3": [121, 59, 35, 54],
    "UP": [166, 56, 33, 57], "CROUCH": [209, 83, 44, 30],
    "WALK1": [263, 60, 40, 53], "WALK2": [304, 58, 57, 50], "WALK3": [362, 59, 42, 54], "WALK4": [405, 60, 43, 53],
    "WALK5": [449, 58, 55, 53], "WALK6": [505, 59, 43, 54],
    "RUN1": [559, 65, 52, 47], "RUN2": [612, 64, 49, 49], "RUN3": [662, 65, 54, 47], "RUN4": [717, 64, 50, 49],
    "SKID1": [777, 66, 51, 47], "SKID2": [829, 66, 51, 47],
    "SLAMR1": [336, 146, 34, 54], "SLAMR2": [371, 134, 35, 66], "SLAMR3": [407, 149, 46, 51],
    "SLAMR4": [454, 156, 41, 44], "SLAMR5": [496, 157, 41, 43],
    "DASH1": [2, 173, 32, 27], "DASH2": [35, 173, 31, 27], "DASH3": [67, 173, 31, 27], "DASH4": [99, 173, 31, 27],
    "DASH5": [131, 173, 31, 27],
    "BALL": [172, 170, 30, 30], "TURN1": [203, 170, 30, 30], "TURN2": [234, 170, 30, 30], "TURN3": [265, 170, 30, 30],
    "TURN4": [296, 170, 30, 30],
    "KICK1": [2, 235, 48, 45], "KICK2": [51, 235, 59, 45], "KICK3": [111, 235, 61, 45],
    "PUSH1": [182, 230, 44, 50], "PUSH2": [227, 229, 33, 51], "PUSH3": [261, 230, 41, 50], "PUSH4": [303, 229, 33, 51],
    "BAL1": [346, 225, 65, 55], "BAL2": [412, 226, 56, 54],
    "SPRING": [478, 216, 30, 64], "GASP": [521, 224, 48, 56],
    "HURT1": [579, 240, 59, 39], "HURT2": [639, 240, 52, 40],
    "FAN1": [701, 245, 48, 33], "FAN2": [750, 245, 52, 34], "FAN3": [803, 245, 55, 35],
    "PIPE1": [2, 334, 67, 24], "PIPE2": [70, 334, 67, 25],
    "DIE": [147, 311, 54, 48], "DROWN": [211, 311, 54, 48],
    "CONT1": [275, 335, 50, 24], "CONT2": [326, 335, 50, 24], "CONT3": [377, 335, 50, 24],
    "ICON1": [846, 145, 18, 23], "ICON2": [865, 145, 17, 23],  # CONTINUE ICON
    "END1": [437, 305, 30, 54], "END2": [468, 305, 36, 54], "END3": [505, 301, 40, 58], "END4": [546, 305, 50, 54],
    "END5": [597, 305, 50, 54], "END6": [648, 313, 48, 46],
    "END_MEDIUM": [697, 301, 69, 90],  # ENDING 7, as drawn
    "END_BIG": [767, 301, 145, 186 - 9],  # ENDING 8 (145x186), its bottom 9 rows cut: the 177 px pose box
}
HUD = [846, 184, 48, 16]  # 1-UP: his head (16x16, black rows above and below), the "BARK" tag, the "x"
SIGN = [788, 152, 48, 32]  # GOAL SIGN: the post's cap (2 rows) and the 30-row board


def f(*names):
    return [B[n] for n in names]


C = lambda frames: {"frames": frames, "anchor": "center"}
WALK = f(*[f"WALK{k}" for k in range(1, 7)])
RUN = f(*[f"RUN{k}" for k in range(1, 5)])
BALL = f("TURN1", "BALL", "TURN2", "BALL", "TURN3", "BALL", "TURN4", "BALL")  # the SPIN row, as Sonic 1's jump
SPINDASH = f(*[f"DASH{k}" for k in range(1, 6)])
TURNING = f("TURN1", "TURN2", "TURN3", "TURN4")
HURT = f("HURT1", "HURT2")
# Bear Rush: his RUN frames twice (the move's timer picks the frame: 8 frames of 3 game frames)
RUSH = RUN * 2
SLAM = f("SLAMR1", "SLAMR2")  # SLAM GROUND (RIGHT): his stance, then the fist raised (held: loop 1)

ANIMS = {
    "Stopped": {"frames": f("STAND")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": f("IDLE1", "IDLE2", "IDLE3", "IDLE2"), "loop": 0},  # IDLE: thumping his gloves
    "Looking Up": {"frames": f("UP")},
    "Looking Down": {"frames": f("CROUCH")},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("SKID1", "SKID2"), "align": True},
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},  # (no peel-out on the sheet: his run)
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
    "Corkscrew H": {"frames": TURNING},
    "Water Slide": C(HURT),  # HURT/FLUME
    "Continue": {"frames": f("CONT1", "CONT2", "CONT3")},  # CONTINUE?
    "Continue Up": {"frames": f("UP")},
    "Super Transform": {"frames": f("IDLE1", "IDLE2", "IDLE3", "IDLE2")},
}
S2_ONLY = {
    "Bored!": {"frames": f("IDLE1", "IDLE2", "IDLE3", "IDLE2"), "loop": 0},
    "Flailing 3": {"frames": f("BAL1", "BAL2"), "align": True},
    "Grabbed": C(HURT),
    "Twirl H": {"frames": TURNING, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    "41": {"name": "Slam Ground", "frames": SLAM, "anchor": "center", "speed": 120, "loop": 1},
    "43": {"name": "Bear Rush", "frames": RUSH, "speed": 0, "align": True},
    "44": {"name": "Bear Rush Air", "frames": RUSH, "anchor": "center", "speed": 0, "align": True},
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art (1-UP)
    "life_icon": {"rect": HUD[:2] + [16, 16], "trim": False},
    "life_name": {"rect": [HUD[0] + 17, HUD[1] + 1, 31, 7]},  # "BARK" (white, black shadow), above the "x"
    "monitor_1up": {"rect": [HUD[0], HUD[1] + 1, 16, 14], "trim": False},  # the icon inside its black rows
    "sign_face": {"rect": SIGN, "trim": False},
    "mini_1": {"rect": B["ICON1"], "remap": PLUS_128},
    "mini_2": {"rect": B["ICON2"], "remap": PLUS_128},
    # Sonic 1's six good-ending frames: the ENDING row. On this sheet, not the ending one: with his big poses those don't
    # fit one 256x256 sheet (build_sonic1.element_image reads either manifest)
    **{f"good_{n}": {"rect": B[f"END{n}"], "remap": PLUS_128} for n in range(1, 7)},
}
ENDING = {  # Sonic 1's ending poses: idle and three poses (small, medium, large)
    "end_idle": {"rect": B["STAND"], "remap": PLUS_128},
    "end_pose_1": {"rect": B["END6"], "remap": PLUS_128},  # the small leap
    "end_pose_2": {"rect": B["END_MEDIUM"], "remap": PLUS_128},
    "end_pose_3": {"rect": B["END_BIG"], "remap": PLUS_128},
}

# 15 colours: black is Sonic's own slot 1; the other 14 keep their exact values in slots 74-87
PALETTE = {
    "74": "#906c00", "75": "#b49024", "76": "#d8b448", "77": "#fcd86c",  # his fur, dark to light
    "78": "#480000", "79": "#900000", "80": "#fc0000", "81": "#d86c00",  # reds (cap, gloves, shoes), orange
    "82": "#006c00", "83": "#24b424",  # the scarf's greens
    "84": "#fcb490",  # his muzzle
    "85": "#ffffff", "86": "#b4b4b4", "87": "#6c6c6c",  # white, greys (soles, the sign)
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet in the slot of its nearest key colour, so nothing is left to
    sheet2ani's guess. check_colours makes sure no built frame uses one."""
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
    used = set()
    for x, y, w, h in list(B.values()) + [HUD, SIGN]:
        used |= {"#%02x%02x%02x" % rgb for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    missing = used - set(KEY_COLOURS) - set(BACKGROUND)
    if missing:
        sys.exit(f"bark: frame colours without a slot of their own: {sorted(missing)}")


def kick_reach(game="Sonic2u", slot=43):
    """(From the retired Double Kick: now slots 43 / 44 are the Bear Rush.) His foot per DOUBLE KICK frame in the built .ani: (right edge, top, bottom) of the frame's pixels right of his
    body's middle, px from the player's centre facing right (for abilities.py 34's melee_reach / top / bottom)."""
    sys.path.insert(0, str(REPO / "tools"))
    import extras
    e = next(x for x in extras.EXTRAS if x["art"] == HERE)
    ani = extras.player_ani(e, game)
    out = []
    for fr in ani["anims"][slot]["frames"]:
        sheet = Image.open(extras.player_build(e, game) / "Sprites" / ani["sheets"][fr["sheet"]])
        im = sheet.crop((fr["x"], fr["y"], fr["x"] + fr["w"], fr["y"] + fr["h"]))
        px = im.load()
        cols = [x for x in range(im.width) for y in range(im.height) if px[x, y]]
        right = max(cols) + fr["px"] + 1
        foot = [y for x in range(im.width) for y in range(im.height) if px[x, y] and x + fr["px"] >= 10]
        out.append((right, min(foot) + fr["py"] if foot else None, max(foot) + fr["py"] + 1 if foot else None))
    return out


CREDIT = ("Bark the Polar Bear (Sonic 1 style) custom sprites by deltaConduit. Original sprites by SEGA, Sonic Team & "
          "deltaConduit - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/541696/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the sheet's ending: a fist up, shouting
S3K_VICTORY = {"frames": f("END1", "END3")}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra28", "credit": CREDIT,
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra28SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(BALL)}}]
        cfg["ui"] = [{"name": "Extra28_UI", "manifest": "Extra28_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra28_UI.gif"},
                     {"name": "Extra28_Ending", "manifest": "Extra28_ending.json", "elements": ENDING,
                      "out": "build/Extra28_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    if "--kick" in sys.argv:
        for slot in (43, 44):
            print(slot, kick_reach(slot=slot))
        sys.exit()
    for game, out in (("Sonic1", "bark.json"), ("Sonic2", "bark_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
