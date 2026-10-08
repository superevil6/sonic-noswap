#!/usr/bin/env python3
"""Writes Sticks the Badger's sheet2ani configs (sticks.json for Sonic 1, sticks_s2.json for Sonic 2).

Sticks, extra 23 (file "Extra23", build ID 29), base character Sonic. PRIVATE for now (extras.py "private"): the
user is still asking the artists for permission.
Sheet: testmods/Sticks2.png (929x1406), "Sprite by Neo-Fire-Sonic and UberHawg. Ripped from Sonic Legends." (see
SOURCE.txt). The big official portrait at the top right (SEGA art) and the small head icon it touches are not used.

Frames are the sprites on the sheet, numbered as detected: connected components of everything that isn't the
#0088ff sheet background (8-connected), sorted by top edge, then left edge. Every sprite faces right.

Layout (y):
     2-33  idle: her fighting stance, breathing (1-4)
    35-78  a wait: turning round (5, 6, 10, 11, 7, 8), then noticing something (12, 14 with its "!" 9 / 13 / 16) and
           reaching for it (15, 17, 18, 19)
    75-112 the walk, 8 frames (20, 23, 21, 24, 22, 26, 27, 25)
   114-151 the run, 4 frames (29, 28, 30, 31)
   155-220 the jump: arms up (32, 33), curling (34-36), falling (37, 38); thrown back (39, 40); crouching (41-43)
   206-287 front-on (44-46); leaning back (47, 48, the skid); punches (49-51)
   283-420 kicks and a tail whirl (53-70; 58 and 71 are loose swooshes); kicks (75-79)
   423-520 air punches (80-89)
   531-622 air kicks (90-95), a sit-down slide (100) and slide kicks with dust (101, 99, 102)
   633-725 more kicks (103-114), dash kicks (115-117)
   738-832 kicks, crouches, turns (118-126); a hand shading her eyes (127, 128)
   848-935 leaning in with her arms out (131, 132, 130, 129); straining, eyes shut (135, 133, 134); knocked back,
           dizzy (136, 137)
   938-1025 a somersault seen from behind (138-140, 141-149, 151, 150, 152, landing 153)
  1033-1114 front-on: hands over her face (156, 155), star-jumps (158, 161, 162), 159; poses (160, 157, 154); her tail
           (166, 167) and a tail swipe (163-165)
  1125-1190 the whirl slash with her boomerang (black swooshes: 171, 168, 169, 170, 172, 173; 184, 185, 192, 194
           loose); the boomerang throw: 178 (held back), 177 (the swing, its black trail), 179 / 174 / 175 (it spins
           in her hand: the big black disc, loose pieces 181, 193, 186, 176, 197, 182, 199), 183 / 187 (let go: the
           smaller spinning boomerang, loose pieces 198, 196), 189 / 191 / 190 / 188 (arm out, empty hand)
  1192-1360 pole swings (201-219; 207 a loose swoosh)
Her boomerang is black on this sheet.

Template: Sonic's .ani (Sonic's moveset). The sheet has no curled-up jump: her jump, Spin Dash and special stage
ball are Tails' own ball in her colours, from each game's own Tails (tools/sonic_ball.py, who="Tails": Sonic 1 / 2 /
CD's Tails.ani, S3&K's 3K_Players/Tails.bin; his tails are a separate object in all of them, so the frames are the
ball alone). The user asked for Tails' ball over Sonic's (2026-09-27: Sonic's looked like a recoloured Sonic). The
Sonic 2 config carries CD's (cd_animations, tools/cd_config.py) and S3&K's (s3k_animations, build_s3k_art.py) too.

Size: the sheet draws her about 32 px tall against Sonic's 40, so every frame of her own art is enlarged 1.2x
(SCALE), nearest-neighbour: the user's exception to the faithful art rule, for her only (2026-09-27). Each frame is
enlarged on its own (sheet2ani.scale_nearest) onto a working sheet (build/Sticks2_scaled.png) that every build reads
(S1 / S2 / CD / S3&K, HUD, continue, ending, her select card), so pivots, feet and anchors follow from the enlarged
frames; the hand-set numbers (the wall cling's wall, the throw's reach and the boomerang, abilities.py) are for the
enlarged size. The borrowed ball is not enlarged (SEGA's, and already Sonic's size).

Placement ("one foot baseline, no body drift"): feet-anchored animations stand on their lowest row (sheet2ani's feet
anchor) and multi-frame ones are aligned on their body ("align": each frame nudged sideways to best overlap the
first), so arms, tail and the boomerang move around a body that stays put.

Abilities (appended slots; the moves are wired in tools/abilities.py and the DLL):
  47 "Wall Cling": Trip's wall cling and climb. The sheet has no side-on climb; the user's pick (2026-09-27, over the
      from-behind arms-up 138 / 139, which looked hurt): 127 / 128, a hand on her head and a knee up, facing right as
      drawn, so she faces a wall on her right as Trip does; her right edge 11 px from the player's centre (Trip's
      wall), vertically centred.
  43 / 44 "Boomerang" / "Boomerang Air": the throw pose for her Y move (the boomerang itself is the shot's own
      projectile art, made elsewhere): held back (178), let go (187, the spinning boomerang still at her hand), arm out
      with the hand empty (189: the last frame, the one the shot's pose shows). CD: 46.

Nothing is redrawn or recoloured (and only the 1.2x above resizes): frames are cut (the "!" over 14 is cut with her); the HUD icons are crops
of her front-on head (45); only the "STICKS" name tag (not on the sheet) is our own lettering in the HUD font the
other extras use, and the ball is Tails' (SEGA's). Every sheet colour used has its own palette slot (all 22 of the
extras' slots 74-95): no colour is merged.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
import sheet2ani  # noqa: E402
from sign_face import board_face  # noqa: E402
import sonic_ball  # noqa: E402

SHEET = "../Sticks2.png"
BACKGROUND = ["#0088ff"]
SRC = Image.open(HERE / SHEET).convert("RGB")
SCALE = 1.2  # her frames enlarged (the user's exception for her: see the notes)
SCALED = HERE / "build" / "Sticks2_scaled.png"

B = {  # sprite number -> [x, y, w, h] (its bounding box)
    # idle, the wait
    1: [0, 2, 35, 31], 2: [35, 2, 35, 31], 3: [71, 3, 34, 30], 4: [106, 3, 34, 30],
    12: [194, 39, 25, 33], 14: [222, 37, 37, 36],  # (14 with its "!", 9 / 13 / 16)
    15: [262, 44, 35, 29], 17: [303, 45, 34, 29], 18: [344, 46, 31, 31], 19: [379, 47, 28, 31],
    # the walk, the run
    20: [2, 75, 23, 35], 23: [34, 77, 24, 34], 21: [69, 76, 26, 33], 24: [100, 77, 24, 33],
    22: [130, 76, 23, 35], 26: [157, 78, 24, 33], 27: [189, 78, 26, 33], 25: [224, 77, 24, 34],
    29: [5, 116, 32, 30], 28: [40, 114, 33, 31], 30: [75, 119, 37, 29], 31: [117, 123, 33, 28],
    # the jump, thrown back, crouching
    32: [8, 155, 20, 40], 33: [34, 156, 22, 41], 39: [205, 175, 35, 39], 40: [240, 175, 35, 43],
    41: [281, 187, 27, 31], 42: [312, 187, 26, 31], 43: [343, 188, 24, 32],
    # front-on, leaning back
    44: [6, 206, 28, 32], 45: [38, 207, 30, 31], 46: [71, 208, 28, 32],
    47: [7, 243, 28, 35], 48: [41, 244, 27, 35],
    76: [122, 377, 30, 38],  # a hop, face turned up
    100: [15, 588, 34, 31],  # the sit-down slide
    118: [232, 738, 24, 31], 123: [20, 743, 33, 25], 126: [330, 744, 30, 30],
    127: [24, 792, 28, 32], 128: [58, 796, 27, 32],
    # leaning in, straining
    131: [16, 851, 31, 32], 132: [54, 851, 31, 32], 130: [90, 849, 32, 32], 129: [127, 848, 32, 34],
    135: [161, 852, 32, 32], 133: [199, 851, 34, 32], 134: [241, 851, 30, 30],
    # the somersault
    138: [18, 938, 28, 34], 139: [55, 939, 28, 34], 140: [92, 939, 31, 35], 141: [130, 939, 32, 31],
    145: [170, 942, 34, 26], 142: [216, 939, 33, 32], 143: [257, 940, 33, 33], 147: [295, 943, 36, 23],
    144: [338, 941, 33, 29], 146: [378, 942, 37, 27], 149: [419, 947, 36, 26], 148: [461, 943, 32, 30],
    151: [22, 989, 31, 30], 150: [61, 986, 32, 32], 152: [105, 991, 30, 32], 153: [142, 998, 30, 27],
    # front-on, poses
    155: [59, 1034, 30, 33], 158: [97, 1036, 31, 30], 161: [135, 1038, 36, 29], 162: [178, 1038, 36, 30],
    154: [329, 1033, 29, 37], 157: [296, 1035, 29, 36], 160: [262, 1036, 23, 33],
    # the boomerang throw
    178: [424, 1151, 30, 35],
    187: [708, 1155, 42, 36],  # (with the spinning boomerang's loose piece 196 in front of her hand)
    189: [762, 1156, 29, 36],
}


def scaled_sheet():
    """Every frame in B enlarged SCALE times on its own (sheet2ani.scale_nearest: the same pixels, nearest-neighbour),
    shelf-packed 2 px apart onto SCALED (the sheet's background). Returns {sprite number: its rect there}."""
    imgs = {n: sheet2ani.scale_nearest(SRC.crop((x, y, x + w, y + h)), SCALE) for n, (x, y, w, h) in sorted(B.items())}
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


S = scaled_sheet()  # sprite number -> its enlarged frame's rect on SCALED (what every config uses)


def f(*nums):
    return [S[n] for n in nums]


IDLE = f(1, 2, 3, 4)
WALK = f(20, 23, 21, 24, 22, 26, 27, 25)
RUN = f(29, 28, 30, 31)
FLIP = f(138, 139, 140, 141, 145, 142, 143, 147, 144, 146, 149, 148, 151, 150, 152)  # the somersault
TUMBLE = f(141, 145, 142, 143, 147)  # its upside-down part
# the boomerang throw: held back, let go, arm out (the last frame is the shot's pose)
THROW = f(178, 187, 189)


def cling():
    """The wall cling: 127 / 128 (the user's pick), placed so her right edge is 11 px right of the player's centre (as
    Trip's: the wall, so not enlarged), vertically centred: an anchor box whose middle is 11 px left of that edge."""
    out = []
    for n in (127, 128):
        x, y, w, h = S[n]
        out.append({"rect": S[n], "anchor_box": [x + w - 11 - 8, y + h // 2 - 8, 16, 16]})
    return out


ANIMS = {
    "Stopped": {"frames": f(1)},  # her fighting stance (also the Origins select card)
    "Waiting": {"frames": IDLE + f(3, 2), "loop": 0, "align": True},  # breathing in her stance
    "Looking Up": {"frames": f(20, 76), "loop": 1, "align": True},  # face turned up
    "Looking Down": {"frames": f(41, 42, 43), "loop": 2, "align": True},  # crouching
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f(47, 48), "loop": 1, "align": True},  # leaning back, a foot planted
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Bouncing": {"frames": f(33), "anchor": "center"},  # arms up
    "Hurt": {"frames": f(39), "anchor": "center"},  # thrown back
    "Dying": {"frames": f(158), "anchor": "center"},  # front-on, arms and legs out
    "Drowning": {"frames": f(155), "anchor": "center"},  # front-on, hands over her face
    "Fan Rotate": {"frames": TUMBLE, "anchor": "center"},
    "Breathing": {"frames": f(45), "anchor": "center"},  # front-on
    "Pushing": {"frames": f(135, 133, 134, 133), "align": True},  # straining, eyes shut
    "Flailing 1": {"frames": f(131, 132), "align": True},  # leaning in, arms out
    "Flailing 2": {"frames": f(130, 129), "align": True},
    "Hanging": {"frames": f(33, 32), "anchor": "center"},  # arms up
    "Clinging On": {"frames": f(123), "anchor": "center"},  # stretched out level
    "Corkscrew H": {"frames": FLIP, "anchor": "center"},
    "Water Slide": {"frames": f(100)},  # the sit-down slide
    "Continue": {"frames": f(127, 128), "align": True},  # shading her eyes, looking out
    "Continue Up": {"frames": f(118, 33), "loop": 1, "align": True},
    "Super Transform": {"frames": f(44, 45, 46, 158, 161, 162), "loop": 3, "align": True},
}
S1_ONLY = {}
S2_ONLY = {
    "Bored!": {"frames": f(12, 14, 15, 17, 18, 19), "loop": 4, "align": True},  # "!", then reaching for it
    "Flailing 3": {"frames": f(131, 132, 130, 129), "align": True},
    "Grabbed": {"frames": f(39, 40), "anchor": "center"},
    "Twirl H": {"frames": FLIP, "rot": 2, "anchor": "center"},
}
CD_ONLY = {name: {"frames": RUN, "align": True} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    "43": {"name": "Boomerang", "frames": THROW, "speed": 60, "align": True},
    "44": {"name": "Boomerang Air", "frames": THROW, "speed": 60, "anchor": "center", "align": True},
    "47": {"name": "Wall Cling", "frames": cling(), "anchor": "center", "speed": 20},
}


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
HEAD_TOP = 0  # (rows down from the top of her head to the icons' first)
HEAD = S[45]  # front-on (enlarged: 36x37): the head is its top 18 rows, ears to cheek tufts
MID = HEAD[0] + (HEAD[2] - 16) // 2  # its middle 16 columns
ELEMENTS = {
    # her front-on head's middle 16 columns (ears, eyes and muzzle), 16 rows (the HUD's size) from HEAD_TOP down
    "life_icon": {"rect": [MID, HEAD[1] + HEAD_TOP, 16, 16], "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("STICKS")},
    "monitor_1up": {"rect": [MID, HEAD[1] + HEAD_TOP + 1, 16, 14], "trim": False},
    # no signpost art: the front-on pose's head (its top 23 rows, ears to collar, 36 wide) on the game's own board
    # (Items2), enlarged 1.15x nearest-neighbour to fill its 40x24 face area (the user's signpost exception;
    # tools/sign_face.py: the ear tips are trimmed)
    "sign_face": board_face([HEAD[0], HEAD[1], HEAD[2], 23], 1.15),
    # continue icons: no small set on the sheet; shading her eyes, looking out (two frames)
    "mini_1": {"rect": S[127], "remap": PLUS_128},
    "mini_2": {"rect": S[128], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": S[1], "remap": PLUS_128},
    "end_pose_1": {"rect": S[154], "remap": PLUS_128},  # hand raised
    "end_pose_2": {"rect": S[161], "remap": PLUS_128},  # a star-jump
    "end_pose_3": {"rect": S[40], "remap": PLUS_128},  # arms flung wide (the sheet has no large pose)
    **{f"good_{n}": {"rect": S[k], "remap": PLUS_128} for n, k in enumerate((1, 20, 157, 154, 127, 128), 1)},
}

# The frames use 22 colours, none exactly one of Sonic's: all keep their exact values in the extras' slots 74-95.
PALETTE = {
    "74": "#202020", "75": "#181c18",  # outlines
    "76": "#ef8123", "77": "#c4511a", "78": "#6b2d12", "79": "#f8a850", "80": "#985010",  # orange fur
    "81": "#75393a", "82": "#442026",  # brown hair
    "83": "#7c6058", "84": "#b79991",  # shoes, wraps
    "85": "#f8f898", "86": "#f8f8f8",  # muzzle, eye whites
    "87": "#707070", "88": "#b0b0b0",  # greys
    "89": "#866d4f", "90": "#534431",  # her skirt
    "91": "#a8c8d8", "92": "#2040f8",  # eyes
    "93": "#000400", "94": "#080c08", "95": "#292829",  # the boomerang (black)
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}  # (black: the name tag's shadow, Sonic's slot 1)

# Tails' ball in her colours (tools/sonic_ball.py, by Tails' colours, the same in all four games; his palette indices
# differ in CD): his three fur shades (dark to light) to her darkest, main and light fur, the white glint to her white,
# the few skin pixels to her muzzle
BALL_COLOURS = {"#a06040": "#6b2d12", "#e08000": "#ef8123", "#e0a000": "#f8a850", "#e0e0e0": "#f8f8f8",
                "#e0a080": "#f8f898"}
# S3&K's Jump has 8 frames (the game's code counts them), Tails' ball 3: his cycle with a frame held twice, so it
# only ever turns forward
S3K_JUMP = [0, 1, 2, 2, 0, 1, 1, 2]


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet (the portrait, other poses) in the slot of its nearest key
    colour, so nothing is left to sheet2ani's guess. (No built frame uses one.)"""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


CREDIT = ("Sprite by Neo-Fire-Sonic and UberHawg. Ripped from Sonic Legends. Sticks the Badger (c) SEGA - "
          "https://www.deviantart.com/silverwarudo33/art/Sticks-Sprite-Sheet-by-NeoFireSonic-848604044")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the ending poses: a hand raised, then the star-jump
S3K_VICTORY = {"frames": f(154, 161)}


def config(game):
    ex = REPO / "extracted" / game
    source = HERE / "build" / f"source_{game}.png"
    tails = lambda sheet, g, anims: sonic_ball.source_with_ball(sheet, g, BALL_COLOURS, BACKGROUND[0], source,
                                                                anims=anims, who="Tails")
    ball = tails(SCALED, game, ("Jumping", "Spin Dash"))
    jump = {"frames": ball["Jumping"], "anchor": "center"}
    cfg = {"name": "Extra23", "credit": CREDIT,
           "source": f"build/source_{game}.png", "feet_y": 20, "background": BACKGROUND, "palette": PALETTE,
           "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, Jumping=jump, **{"Spin Dash": {"frames": ball["Spin Dash"]}},
                              **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else S1_ONLY)),
           "appended_animations": APPENDED}
    if game == "Sonic2":  # CD's and S3&K's own Tails ball, on the same working sheet (CD's config and S3&K's come
        cd = tails(source, "SonicCD", ("Jumping", "Spin Dash"))  # from this one)
        s3k = tails(source, "Sonic3K", ("Jump", "Spindash"))
        cfg["cd_animations"] = {"Jumping": {"frames": cd["Jumping"], "anchor": "center"},
                                "Spin Dash": {"frames": cd["Spin Dash"]}}
        cfg["s3k_animations"] = {"Jump": {"frames": [s3k["Jump"][k] for k in S3K_JUMP], "anchor": "center"},
                                 "Spindash": {"frames": s3k["Spindash"]}}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra23SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": jump}}]
        cfg["ui"] = [{"name": "Extra23_UI", "manifest": "Extra23_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra23_UI.gif"},
                     {"name": "Extra23_Ending", "manifest": "Extra23_ending.json", "elements": ENDING,
                      "out": "build/Extra23_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "sticks.json"), ("Sonic2", "sticks_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
