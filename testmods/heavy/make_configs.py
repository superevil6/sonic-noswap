#!/usr/bin/env python3
"""Writes Heavy's sheet2ani configs (heavy.json for Sonic 1, heavy_s2.json for Sonic 2; CD's and S3&K's come from the
Sonic 2 one).

Heavy (of Heavy & Bomb, Knuckles' Chaotix), extra 29 (file "Extra29", build ID 35), base character Sonic. Public (credit
in mods/NoSwap/README.md). Sheet: testmods/HeavyBomb.png (1124x606), "Heavy & Bomb (Sonic 1 style)" by Akimaca (see
SOURCE.txt), with Bomb's frames too (testmods/bomb). Its terms, printed on the sheet: "Original sprites by SEGA, Sonic
Team & me (Akimaca). Free to use, just give credit where it's due!!!"

The sheet: a mint page (#7acaab) with every sprite in a darker cell (#3c9270) under a yellow label; both are background.
Only the "Normal" palette is used (not the palette variants at the top right, nor the "Scrapped/Test" box). Frames are
named by the label they sit under, left to right from 1. Every sprite already faces RIGHT like Sonic (the cone's lit front,
the pushing fist and the leading running fist are on the right; 2026-09-27 the user found the old mirrored cut moving
backwards), so frames are cut as drawn, nothing mirrored. The UI art (HUD,
signpost, continue icons) is cut from the sheet as drawn (its "HEAVY" tag must read the right way round).

Size: he stands 31 px tall (Idle), 36 wide: short and wide. Not scaled.

Abilities (tools/abilities.py 35; wired there, in build_soniccd.py and the DLL):
  - breaks walls like Knuckles (abilities.py breaks_walls): walking into the breakable walls of Sonic 1, Sonic 2, CD and
    S3&K smashes them.
  - Y: Charge (abilities.py charge, 2026-09-27, replacing the Dash): held on the ground, a slow push far past his top
    speed, then a long coast. At full charge, down stores a Shine Spark (2026-09-30): jump launches it (his SPRING pose,
    slot 45 / CD 48, up and up-forward; the dash frames forward). Frames: his RUNNING frames (slot 41, CD 45), the same with the sheet's DASH flash in front
    of his fist once he's past his top speed (layered: slot 43, CD 46), and his SLIDE pose while he coasts (slot 44 in
    S1/S2; slot 42 for CD's 47 and S3&K's hover slot).
  - no jump ability. Heavy physics (Gamma's numbers).
  - ball: the sheet has none: the generic spin ball (tools/generic_ball.py: Sonic Mania's plain spin ball, SEGA's
    art) in his greys, for the jump, Spin Dash and special stages (BALL_COLOURS).

Nothing is redrawn, recoloured or resized: frames are cut as drawn. One crop beyond a cell's edge: the big
"End Sprite" (206x141) loses 17 columns on its left and 18 on its right (the ends of his two soles) to fit the 171 px
pose box every package's ending sheet has. Palette: black in Sonic's slot 1, the other 15 colours exactly in slots 74-88;
nothing merged (check_colours).
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import generic_ball  # noqa: E402

SHEET = HERE.parent / "HeavyBomb.png"
BACKGROUND = ["#7acaab", "#3c9270"]  # the page and its cells
SRC = Image.open(SHEET).convert("RGB")
W, H = SRC.size

B = {  # frame -> [x, y, w, h] on the sheet as drawn: its cell
    "IDLE": [410, 92, 36, 31], "WAIT1": [456, 91, 53, 32], "WAIT2": [513, 89, 53, 34],  # WAITING: "Hurry UP!!!"
    "UP": [574, 91, 37, 32], "CROUCH": [617, 94, 47, 29], "SPRING": [676, 76, 35, 47], "FALL": [719, 91, 43, 32],
    "SLIDE": [766, 91, 48, 32],
    "WALK1": [412, 144, 34, 32], "WALK2": [450, 147, 38, 29], "WALK3": [493, 145, 31, 31], "WALK4": [531, 144, 35, 32],
    "WALK5": [571, 147, 38, 29], "WALK6": [615, 145, 30, 31],
    "SKID1": [656, 146, 39, 30], "SKID2": [698, 145, 40, 31],
    "RUN1": [418, 208, 63, 35], "RUN2": [487, 209, 53, 34], "RUN3": [546, 208, 63, 35], "RUN4": [614, 209, 54, 34],
    "DASH": [681, 211, 12, 32],  # the dash flash (an effect on its own)
    "BAL1": [706, 195, 38, 48], "BAL2": [750, 201, 34, 42],
    "PUSH1": [419, 276, 36, 30], "PUSH2": [459, 275, 33, 31], "PUSH3": [496, 276, 33, 30], "PUSH4": [533, 275, 33, 31],
    "CONT1": [576, 266, 48, 40], "CONT2": [629, 266, 48, 40], "DEATH": [686, 259, 63, 47],
    "ICON1": [871, 288, 23, 18], "ICON2": [896, 288, 23, 18],  # CONTINUE ICON
    "NORM1": [419, 326, 39, 31], "NORM2": [464, 326, 54, 31],  # NORMAL ENDING
    "GOOD1": [532, 326, 33, 31], "GOOD2": [569, 326, 38, 31], "GOOD3": [611, 326, 52, 31], "GOOD4": [669, 326, 48, 31],
    "GOOD5": [723, 326, 48, 31], "GOOD6": [777, 326, 54, 31],  # GOOD ENDING
    "END_SMALL": [453, 422, 100, 66],  # END SPRITE, the small one (not used: wider than the medium pose box)
    "END_BIG": [590 + 17, 385, 206 - 35, 141],  # END SPRITE, the big one (206x141), 17 + 18 columns cut: the 171 px box
}
HUD = [816, 290, 49, 16]  # LIFE COUNTER: his head (16x16, black rows above and below), the "HEAVY" tag, the "x"
SIGN = [763, 258, 48, 32]  # SIGNPOST: the post's cap (2 rows) and the 30-row board


def m(name):
    """The frame's rect, as drawn: every sprite on the sheet already faces right (shoe toes, pushing fists), the engines'
    convention, so nothing is mirrored (2026-09-27: the mirrored cut walked backwards in-game)."""
    return list(B[name])


def f(*names):
    return [m(n) for n in names]


C = lambda frames: {"frames": frames, "anchor": "center"}
WALK = f(*[f"WALK{k}" for k in range(1, 7)])
WAIT = f("WAIT1", "WAIT2")  # as drawn, so the "Hurry UP!!!" sign reads the right way round
RUN = f(*[f"RUN{k}" for k in range(1, 5)])
TURNING = WALK  # his walk turns him round


def dash(run):
    """A running frame with the DASH flash just ahead of his leading fist (at his right), level with his
    middle; positioned by his body (anchor layer 0)."""
    body, flash = m(run), m("DASH")
    trim = cut_box(B[run])
    ftrim = cut_box(B["DASH"])
    at = [trim[2] + 1, (trim[3] - ftrim[3]) // 2]
    return {"layers": [{"rect": body, "at": [0, 0]}, {"rect": flash, "at": at}], "anchor_layer": 0}


def cut_box(rect):
    """(x, y, w, h) of the sprite's own pixels inside a cell rect (as sheet2ani trims it)."""
    x, y, w, h = rect
    crop = SRC.crop((x, y, x + w, y + h))
    bg = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in BACKGROUND}
    mask = Image.new("L", crop.size, 0)
    mask.putdata([0 if p in bg else 255 for p in list(crop.getdata())])
    return mask.getbbox()[0], mask.getbbox()[1], mask.getbbox()[2] - mask.getbbox()[0], mask.getbbox()[3] - mask.getbbox()[1]


DASH = [dash(r) for r in ("RUN1", "RUN2", "RUN3", "RUN4")]

ANIMS = {
    "Stopped": {"frames": f("IDLE")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": WAIT, "loop": 0},  # WAITING: "Hurry UP!!!"
    "Looking Up": {"frames": f("UP")},
    "Looking Down": {"frames": f("CROUCH")},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("SKID1", "SKID2"), "align": True},
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},  # (no peel-out on the sheet: his run)
    "Bouncing": C(f("SPRING")),  # SPRING/JUMP
    "Hurt": C(f("FALL")),
    "Dying": C(f("DEATH")),
    "Drowning": C(f("DEATH")),
    "Fan Rotate": C(f("FALL")),
    "Breathing": C(f("SPRING")),
    "Pushing": {"frames": f("PUSH1", "PUSH2", "PUSH3", "PUSH4"), "align": True},
    "Flailing 1": {"frames": f("BAL1", "BAL2"), "align": True},
    "Flailing 2": {"frames": f("BAL1", "BAL2"), "align": True},
    "Hanging": C(f("SPRING")),  # (no hanging art: the spring pose, fists up)
    "Clinging On": C(f("SPRING")),
    "Corkscrew H": {"frames": TURNING},
    "Water Slide": C(f("SLIDE")),
    "Continue": {"frames": f("CONT1", "CONT2")},
    "Continue Up": {"frames": f("UP")},
    "Super Transform": {"frames": f("IDLE")},
}
S2_ONLY = {
    "Bored!": {"frames": WAIT, "loop": 0},
    "Flailing 3": {"frames": f("BAL1", "BAL2"), "align": True},
    "Grabbed": C(f("FALL")),
    "Twirl H": {"frames": TURNING, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# The Charge (abilities.py 35; the code picks the frame from the distance he covers): running, running past his top speed
# with the dash flash, and coasting on his SLIDE pose (slot 44 in S1/S2, where it counts as an attack; slot 42 for CD and
# S3&K, whose own code makes the coast an attack)
SLIDE = {"name": "Charge Slide", "frames": f("SLIDE"), "speed": 0, "rot": 2}
SPARK = {"name": "Shine Spark", "frames": f("SPRING"), "anchor": "center", "speed": 0}
APPENDED = {
    "41": {"name": "Charge", "frames": RUN, "speed": 0, "rot": 2},
    "42": SLIDE,
    "43": {"name": "Charge Dash", "frames": DASH, "speed": 0, "rot": 2},
    "44": SLIDE,
    # the Shine Spark (abilities.py 35 "spark_*", 2026-09-30) flying up or up-forward: his SPRING/JUMP pose, fists up, as
    # drawn (slot 45, S3&K's attack-up slot; slot 47 only for CD's 48: cd_config.py maps no 45). Forward it shows the
    # charge's dash frames (43)
    "45": SPARK,
    "47": SPARK,
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art (LIFE COUNTER), as drawn
    "life_icon": {"rect": HUD[:2] + [16, 16], "trim": False},
    "life_name": {"rect": [HUD[0] + 17, HUD[1] + 1, 32, 7]},  # "HEAVY" (yellow, black shadow), above the "x"
    "monitor_1up": {"rect": [HUD[0], HUD[1] + 1, 16, 14], "trim": False},  # the icon inside its black rows
    "sign_face": {"rect": SIGN, "trim": False},
    "mini_1": {"rect": B["ICON1"], "remap": PLUS_128},
    "mini_2": {"rect": B["ICON2"], "remap": PLUS_128},
}


def ending(name):
    return {"rect": m(name), "remap": PLUS_128}


# Sonic 1's ending poses (as drawn: facing right): idle, three poses (small, medium, large), six good-ending frames. Each
# must fit the box every package shares (tools/build_sonic1.py element_pivot): the good-ending row's third frame (52 px)
# is wider than the third box (46), so the six are NORMAL ENDING 1, then GOOD ENDING 1-4 and 6 (1 / 2, the fist flash,
# alternate as Sonic's emerald shine does)
ENDING = {
    "end_idle": ending("IDLE"),
    "end_pose_1": ending("SPRING"),  # the small leap
    "end_pose_2": ending("NORM2"),  # the medium pose: fists out (the small END SPRITE is 100 px, the box 71)
    "end_pose_3": ending("END_BIG"),
    **{f"good_{n}": ending(k) for n, k in enumerate(("NORM1", "GOOD1", "GOOD2", "GOOD3", "GOOD4", "GOOD6"), 1)},
}

# 16 colours: black is Sonic's own slot 1; the other 15 keep their exact values in slots 74-88
PALETTE = {
    "74": "#484848", "75": "#909090", "76": "#b4b4b4", "77": "#fcfcfc",  # his greys, dark to light, and white
    "78": "#480000", "79": "#800000", "80": "#900000", "81": "#fc0000", "82": "#fc6c6c",  # reds (fists), dark to light
    "83": "#fcfc00", "84": "#909000",  # the dash flash and the "HEAVY" tag's yellows
    "85": "#fcb490", "86": "#b46c48",  # the "Hurry UP!!!" sign
    "87": "#6c6cd8",  # the signpost board's sky
    "88": "#010101",  # a near-black in the HUD icon, kept as drawn
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}

# The generic ball (tools/generic_ball.py) in his own colours: his three body greys, white shine
BALL_COLOURS = generic_ball.colours(dark="#484848", mid="#909090", light="#b4b4b4", shine="#fcfcfc",
                                    palette=list(PALETTE.values()))  # (outline: his dark grey, not black)


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
    """Every colour in a built frame or UI element has a slot of its own (nothing merged)."""
    used = set()
    for x, y, w, h in list(B.values()) + [HUD, SIGN]:
        used |= {"#%02x%02x%02x" % rgb for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    used |= set(BALL_COLOURS.values())
    missing = used - set(KEY_COLOURS) - set(BACKGROUND)
    if missing:
        sys.exit(f"heavy: frame colours without a slot of their own: {sorted(missing)}")


def base_source():
    """The working source's base: the sheet as drawn (frames are cut from it unmirrored)."""
    (HERE / "build").mkdir(parents=True, exist_ok=True)
    return SHEET


def dash_reach(game="Sonic2u", slot=43):
    """His front edge per Dash frame in the built .ani (the flash's far edge), px from the player's centre facing right
    (for abilities.py 35's melee_reach)."""
    import extras
    e = next(x for x in extras.EXTRAS if x["art"] == HERE)
    ani = extras.player_ani(e, game)
    out = []
    for fr in ani["anims"][slot]["frames"]:
        sheet = Image.open(extras.player_build(e, game) / "Sprites" / ani["sheets"][fr["sheet"]])
        im = sheet.crop((fr["x"], fr["y"], fr["x"] + fr["w"], fr["y"] + fr["h"]))
        px = im.load()
        cols = [x for x in range(im.width) for y in range(im.height) if px[x, y]]
        out.append(max(cols) + fr["px"] + 1)
    return out


CREDIT = ("Heavy (Heavy & Bomb, Sonic 1 style) custom sprites by Akimaca. Original sprites by SEGA, Sonic Team & "
          "Akimaca - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/228293/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): GOOD ENDING into NORMAL ENDING's fists out (the medium ending pose)
S3K_VICTORY = {"frames": f("GOOD1", "NORM2")}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    source = HERE / "build" / f"source_{game}.png"
    ball = generic_ball.source_with_ball(base_source(), BALL_COLOURS, BACKGROUND[0], source)
    jump = {"frames": ball, "anchor": "center"}
    cfg = {"name": "Extra29", "credit": CREDIT,
           "source": f"build/source_{game}.png", "feet_y": 20, "background": BACKGROUND, "palette": PALETTE,
           "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra29SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": jump}}]
        cfg["ui"] = [{"name": "Extra29_UI", "manifest": "Extra29_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra29_UI.gif"},
                     {"name": "Extra29_Ending", "manifest": "Extra29_ending.json", "elements": ENDING,
                      "out": "build/Extra29_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return generic_ball.apply(cfg, ball, game)  # jump, Spin Dash, special stages, CD's and S3&K's


if __name__ == "__main__":
    if "--reach" in sys.argv:
        for slot in (43, 44):
            print(slot, dash_reach(slot=slot))
        sys.exit()
    for game, out in (("Sonic1", "heavy.json"), ("Sonic2", "heavy_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
