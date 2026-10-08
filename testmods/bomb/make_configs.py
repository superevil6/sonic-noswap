#!/usr/bin/env python3
"""Writes Bomb's sheet2ani configs (bomb.json for Sonic 1, bomb_s2.json for Sonic 2; CD's and S3&K's come from the
Sonic 2 one).

Bomb (of Heavy & Bomb, Knuckles' Chaotix), extra 30 (file "Extra30", build ID 36), base character Sonic. Public (credit
in mods/NoSwap/README.md). Sheet: testmods/HeavyBomb.png (1124x606), "Heavy & Bomb (Sonic 1 style)" by Akimaca (see
SOURCE.txt), shared with Heavy (testmods/heavy). Its terms, printed on the sheet: "Original sprites by SEGA, Sonic Team &
me (Akimaca). Free to use, just give credit where it's due!!!"

The sheet: a mint page (#7acaab) with every sprite in a darker cell (#3c9270) under a yellow label; both are background.
Only the "Normal" palette is used (not the palette variants at the top right, nor the "Scrapped/Test" box). Frames are
named by the label they sit under, left to right from 1. Every sprite already faces RIGHT like Sonic (his red face, shoe
toes and pushing glove point right; 2026-09-27 the user found the old mirrored cut walking backwards), so frames are
cut as drawn, nothing mirrored. The UI art (HUD with its "BOMB" tag,
signpost, continue icons) is cut as drawn.

Size: he stands 26 px tall (Idle, fuse to soles; 21 wide): tiny. Not scaled.

Abilities (tools/abilities.py 36; wired there, in build_soniccd.py and the DLL):
  - Y: Self-Destruct, the melee: DETONATING 1-3, then EXPLOSION 1-5 and back down 4-1 as he reforms (slots 43 / 44,
    CD 46). As the blast goes off, a half-screen nuke (Tails Doll's Screen Nuke without its flash: abilities.py
    melee_nuke) hits everything in a box round him. Nothing hurts him meanwhile (melee_safe); then it costs him a
    normal hit (melee_cost: rings scattered, or his shield; at 0 rings he dies). He stands still for it on the ground.
  - jump ability: Hop, Trip's double jump (abilities.py double_jump), in his SPRING/JUMP pose (slot 41).
  - ball: his LABYRINTH SPIN is him turning round with his arms and legs out, not a ball, so he jumps, Spin Dashes and
    rolls through special stages in the generic spin ball (tools/generic_ball.py: Sonic Mania's plain spin ball, SEGA's art,
    mapped to his own colours): a black bomb with a grey shine (BALL_COLOURS).

Nothing is redrawn or recoloured: frames are cut as drawn; nothing cut beyond a cell. Only the EXPLOSION frames are
resized: a pixel-exact 4x (nearest-neighbour, the faithful art rule's integer enlargement; the user's rework, 2026-09-28:
double the old 2x) for the half-screen nuke, 152 px across at its peak, centred on him (BLAST_SCALE). Palette:
black in Sonic's slot 1, the other 16 colours exactly in slots 74-89; nothing merged (check_colours).
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
    "IDLE": [21, 97, 21, 26], "WAIT1": [50, 97, 30, 26], "WAIT2": [84, 97, 30, 26], "UP": [120, 99, 25, 24],
    "CROUCH": [150, 100, 33, 23], "SPRING": [188, 91, 21, 32], "FALL": [218, 97, 32, 26],
    "WALK1": [19, 143, 30, 28], "WALK2": [53, 144, 27, 27], "WALK3": [85, 143, 28, 28], "WALK4": [119, 143, 31, 28],
    "WALK5": [155, 144, 30, 27], "WALK6": [190, 143, 32, 28],
    "SKID1": [231, 146, 31, 25], "SKID2": [265, 146, 31, 25],
    "RUN1": [19, 191, 37, 26], "RUN2": [61, 191, 35, 26], "RUN3": [100, 191, 37, 26], "RUN4": [141, 191, 33, 26],
    "BAL1": [182, 186, 26, 31], "BAL2": [214, 187, 27, 30],
    "HURT1": [255, 186, 42, 31], "HURT2": [302, 186, 43, 31],  # HURT/SLIDE
    "PUSH1": [26, 237, 21, 27], "PUSH2": [53, 236, 20, 28], "PUSH3": [78, 237, 22, 27], "PUSH4": [106, 236, 20, 28],
    "CLING1": [140, 242, 38, 22], "CLING2": [182, 242, 38, 22],
    "SPIN1": [233, 237, 33, 27], "SPIN2": [269, 237, 35, 27], "SPIN3": [308, 237, 36, 27],  # LABYRINTH SPIN
    "CONT1": [22, 300, 41, 30], "CONT2": [70, 300, 41, 30], "DEATH": [119, 294, 45, 36],  # DEATH/EXPLODE
    "ICON1": [285, 315, 15, 15], "ICON2": [301, 315, 15, 15],  # CONTINUE ICON
    "NORM1": [28, 352, 31, 27], "NORM2": [62, 353, 29, 26],  # NORMAL ENDING
    "GOOD1": [109, 352, 22, 27], "GOOD2": [133, 352, 24, 27], "GOOD3": [159, 352, 33, 27], "GOOD4": [196, 352, 40, 27],
    "GOOD5": [240, 352, 40, 27], "GOOD6": [284, 353, 29, 26],  # GOOD ENDING
    "END_SMALL": [60, 438, 52, 53], "END_BIG": [130, 400, 162, 115],  # END SPRITE, small and big
    "DET1": [919, 360, 32, 29], "DET2": [955, 356, 32, 33], "DET3": [991, 354, 32, 35],  # EXTRAS: DETONATING
    "EXP1": [922, 420, 19, 16], "EXP2": [948, 406, 28, 30], "EXP3": [984, 404, 32, 32], "EXP4": [1026, 398, 38, 38],
    "EXP5": [1074, 398, 38, 38],  # EXTRAS: EXPLOSION
}
HUD = [233, 314, 44, 16]  # LIFE COUNTER: his head (16x16, black rows above and below), the "BOMB" tag, the "x"
SIGN = [177, 282, 48, 32]  # SIGNPOST: the post's cap (2 rows) and the 30-row board


def m(name):
    """The frame's rect, as drawn: every sprite on the sheet already faces right (shoe toes, pushing fists), the engines'
    convention, so nothing is mirrored (2026-09-27: the mirrored cut walked backwards in-game)."""
    return list(B[name])


def f(*names):
    return [m(n) for n in names]


C = lambda frames: {"frames": frames, "anchor": "center"}
WALK = f(*[f"WALK{k}" for k in range(1, 7)])
RUN = f(*[f"RUN{k}" for k in range(1, 5)])
SPIN = f("SPIN1", "SPIN2", "SPIN3", "SPIN2")  # LABYRINTH SPIN: turning round
HURT = f("HURT1", "HURT2")
# The EXPLOSION frames enlarged BLAST_SCALE times, pixel-exact (whole pixels, nearest-neighbour: the faithful art
# rule's integer enlargement). 4x (the user's nuke rework, 2026-09-28: double the old 2x): EXP5 38 -> 152 px across,
# drawn as his own frames, centred on him. Only the explosion: DETONATING (him) keeps his size. The enlarged frames go in a strip under the sheet on the working
# source (base_source; HeavyBomb.png itself is untouched).
BLAST_SCALE = 4
EXPLOSION = [f"EXP{k}" for k in range(1, 6)]


def _bbox(name):
    """The bbox of what isn't background in the frame's cell: (x, y, w, h) inside the cell."""
    x, y, w, h = B[name]
    img = SRC.crop((x, y, x + w, y + h))
    bg = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in BACKGROUND}
    xs = [i for i in range(w) for j in range(h) if img.getpixel((i, j)) not in bg]
    ys = [j for i in range(w) for j in range(h) if img.getpixel((i, j)) not in bg]
    return min(xs), min(ys), max(xs) + 1 - min(xs), max(ys) + 1 - min(ys)


def _trimmed(name):
    """The frame's pixels (RGB, its cell's background left in) cut to the bbox of what isn't background."""
    x, y, _w, _h = B[name]
    bx, by, w, h = _bbox(name)
    return SRC.crop((x + bx, y + by, x + bx + w, y + by + h))


def _big_strip():
    """[(name, enlarged image, its rect on the working source)] for the explosion frames, left to right under the
    sheet (2 px apart)."""
    out, x = [], 2
    for n in EXPLOSION:
        img = _trimmed(n)
        big = img.resize((img.width * BLAST_SCALE, img.height * BLAST_SCALE), Image.NEAREST)
        out.append((n, big, [x, H + 2, big.width, big.height]))
        x += big.width + 2
    return out


BIG = _big_strip()
BIG_RECT = {n: r for n, _, r in BIG}


def big_on_centre(n, feet=True):
    """An enlarged explosion frame, its middle on the player's centre (where the damage circle is centred). On the
    feet anchor (slot 43, the ground: Sonic's feet line is 20 px below his centre) an anchor box whose bottom edge is
    20 px below the frame's middle; in the air (slot 44, centred) the frame as it is."""
    x, y, w, h = BIG_RECT[n]
    if not feet:
        return [x, y, w, h]
    return {"rect": [x, y, w, h], "anchor_box": [x, y + h // 2 + 20 - 1, w, 1]}


def on_centre(name):
    """A frame of his (as cut) with its middle on the player's centre, on the feet anchor: an anchor box as wide as the
    frame, its bottom edge 20 px below the frame's middle (as big_on_centre), so an animation on the feet anchor shows
    it as a centred one would."""
    x, y, _w, _h = B[name]
    bx, by, w, h = _bbox(name)
    return {"rect": m(name), "anchor_box": [x + bx, y + by + h // 2 + 20 - 1, w, 1]}


# Self-Destruct: detonating, the blast (enlarged), then the blast backwards as he reforms (the timer picks the frame).
# Both poses are on the feet anchor and share the enlarged frames (each cut once: at 4x a 152 px frame fills most of a
# 256 px sheet); in the air his DETONATING frames are centred on him (on_centre), on the ground they stand on the floor
_ORDER = ["EXP1", "EXP2", "EXP3", "EXP4", "EXP5", "EXP4", "EXP3", "EXP2", "EXP1"]
BLAST = f("DET1", "DET2", "DET3") + [big_on_centre(n) for n in _ORDER]
BLAST_AIR = [on_centre(n) for n in ("DET1", "DET2", "DET3")] + [big_on_centre(n) for n in _ORDER]

ANIMS = {
    "Stopped": {"frames": f("IDLE")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": f("WAIT1", "WAIT2"), "loop": 0},
    "Looking Up": {"frames": f("UP")},
    "Looking Down": {"frames": f("CROUCH")},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("SKID1", "SKID2"), "align": True},
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},  # (no peel-out on the sheet: his run)
    "Bouncing": C(f("SPRING")),  # SPRING/JUMP
    "Hurt": C(HURT[:1]),
    "Dying": C(f("DEATH")),
    "Drowning": C(f("DEATH")),
    "Fan Rotate": C(SPIN),
    "Breathing": C(f("SPRING")),
    "Pushing": {"frames": f("PUSH1", "PUSH2", "PUSH3", "PUSH4"), "align": True},
    "Flailing 1": {"frames": f("BAL1", "BAL2"), "align": True},
    "Flailing 2": {"frames": f("BAL1", "BAL2"), "align": True},
    "Hanging": C(f("CLING1", "CLING2")),  # CLING
    "Clinging On": C(f("CLING1", "CLING2")),
    "Corkscrew H": {"frames": SPIN},
    "Water Slide": C(HURT),  # HURT/SLIDE
    "Continue": {"frames": f("CONT1", "CONT2")},
    "Continue Up": {"frames": f("UP")},
    "Super Transform": {"frames": f("IDLE")},
}
S2_ONLY = {
    "Bored!": {"frames": f("WAIT1", "WAIT2"), "loop": 0},
    "Flailing 3": {"frames": f("BAL1", "BAL2"), "align": True},
    "Grabbed": C(HURT),
    "Twirl H": {"frames": SPIN, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    "41": {"name": "Hop", "frames": f("SPRING"), "anchor": "center", "speed": 120, "hitbox": 1},  # (Trip's: the ball's box)
    "43": {"name": "Self-Destruct", "frames": BLAST, "speed": 0},
    "44": {"name": "Self-Destruct Air", "frames": BLAST_AIR, "speed": 0},  # (centred by its anchor boxes)
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {  # the sheet's own HUD art (LIFE COUNTER), as drawn
    "life_icon": {"rect": HUD[:2] + [16, 16], "trim": False},
    "life_name": {"rect": [HUD[0] + 17, HUD[1] + 1, 27, 7]},  # "BOMB" (yellow, black shadow), above the "x"
    "monitor_1up": {"rect": [HUD[0], HUD[1] + 1, 16, 14], "trim": False},  # the icon inside its black rows
    "sign_face": {"rect": SIGN, "trim": False},
    "mini_1": {"rect": B["ICON1"], "remap": PLUS_128},
    "mini_2": {"rect": B["ICON2"], "remap": PLUS_128},
}


def ending(name):
    return {"rect": m(name), "remap": PLUS_128}


# Sonic 1's ending poses (as drawn: facing right): idle, three poses (small, medium, large: the END SPRITEs), six
# good-ending frames: the GOOD ENDING row
ENDING = {
    "end_idle": ending("IDLE"),
    "end_pose_1": ending("SPRING"),  # the small leap
    "end_pose_2": ending("END_SMALL"),
    "end_pose_3": ending("END_BIG"),
    **{f"good_{n}": ending(f"GOOD{n}") for n in range(1, 7)},
}

# 17 colours: black is Sonic's own slot 1; the other 16 keep their exact values in slots 74-89
PALETTE = {
    "74": "#484848", "75": "#909090", "76": "#b4b4b4", "77": "#fcfcfc",  # greys (fuse, shoes, highlights), white
    "78": "#480000", "79": "#800000", "80": "#900000", "81": "#fc0000", "82": "#fc6c6c",  # reds, dark to light
    "83": "#484800", "84": "#909000", "85": "#fcfc00",  # his yellow gloves, dark to light
    "86": "#6c6cd8",  # the signpost board's sky
    "87": "#010101", "88": "#222034",  # a near-black (HUD icon) and a dark blue-grey (a few pixels), kept as drawn
}
KEY_COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}

# The generic ball (tools/generic_ball.py) in his own colours: black body (so a black outline), his dark blue-grey and dark grey
# for the lit side, white shine: a black bomb with a grey shine
BALL_COLOURS = generic_ball.colours(dark="#000000", mid="#222034", light="#484848", shine="#fcfcfc",
                                    palette=list(PALETTE.values()))  # (outline: his black body's own black)
# He's only about 26 px tall: his ball is 24 px across (Mania's 30 px ball resized nearest-neighbour, the user's exception
# 2026-09-30; 2026-09-27: 30 was too big for him)
BALL_SIZE = 24


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
        sys.exit(f"bomb: frame colours without a slot of their own: {sorted(missing)}")


def base_source():
    """The working source's base: the sheet as drawn (frames are cut from it unmirrored), with the enlarged explosion
    frames (BIG) in a strip underneath."""
    (HERE / "build").mkdir(parents=True, exist_ok=True)
    out = Image.new("RGB", (W, H + 4 + max(r[3] for _, _, r in BIG)), BACKGROUND[0])
    out.paste(SRC, (0, 0))
    for _, big, (x, y, _w, _h) in BIG:
        out.paste(big, (x, y))
    path = HERE / "build" / "source_base.png"
    out.save(path)
    return out


def blast_extent(game="Sonic2u", slot=43):
    """How far each Self-Destruct frame reaches from the player's centre (the farthest pixel, any side), px."""
    import extras
    e = next(x for x in extras.EXTRAS if x["art"] == HERE)
    ani = extras.player_ani(e, game)
    out = []
    for fr in ani["anims"][slot]["frames"]:
        xs = (fr["px"], fr["px"] + fr["w"])
        ys = (fr["py"], fr["py"] + fr["h"])
        out.append(max(abs(v) for v in xs + ys))
    return out


CREDIT = ("Bomb (Heavy & Bomb, Sonic 1 style) custom sprites by Akimaca. Original sprites by SEGA, Sonic Team & "
          "Akimaca - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/228293/")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): GOOD ENDING into NORMAL ENDING's fists out
S3K_VICTORY = {"frames": f("GOOD1", "NORM2")}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    source = HERE / "build" / f"source_{game}.png"
    ball = generic_ball.source_with_ball(base_source(), BALL_COLOURS, BACKGROUND[0], source, BALL_SIZE)
    jump = {"frames": ball, "anchor": "center"}
    cfg = {"name": "Extra30", "credit": CREDIT,
           "source": f"build/source_{game}.png", "feet_y": 20, "background": BACKGROUND, "palette": PALETTE,
           "colours": all_colours(),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra30SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": jump}}]
        cfg["ui"] = [{"name": "Extra30_UI", "manifest": "Extra30_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra30_UI.gif"},
                     {"name": "Extra30_Ending", "manifest": "Extra30_ending.json", "elements": ENDING,
                      "out": "build/Extra30_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return generic_ball.apply(cfg, ball, game)  # jump, Spin Dash, special stages, CD's and S3&K's


if __name__ == "__main__":
    if "--blast" in sys.argv:
        for slot in (43, 44):
            print(slot, blast_extent(slot=slot))
        sys.exit()
    for game, out in (("Sonic1", "bomb.json"), ("Sonic2", "bomb_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
