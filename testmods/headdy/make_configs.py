#!/usr/bin/env python3
"""Writes Dynamite Headdy's sheet2ani configs (headdy.json for Sonic 1, headdy_s2.json for Sonic 2; CD's and S3&K's come
from the Sonic 2 one).

Dynamite Headdy (Sega Genesis, Treasure). A separate download (extras.py "crossover"). Base character Sonic. Its
extras.py position gives its file name (NAME below, looked up, not hard-coded).

Sheet (see SOURCE.txt): Headdy.png, "Dynamite Headdy ripped by Sonicfan32. Credit is optional, but don't steal. This
game belongs to Treasure and Sega." (The Spriters Resource, genesis/dynahead asset 11723). A 265x6247 strip: every
sprite is a Genesis hardware sprite box (dark teal #002424, or navy #00006c for the same frame on the other priority
layer) on the page (#3f48cc). The in-game art is in BODY n (his headless body poses) and HEAD n (head sets) sections.
The body's green neck bolt (#00fc00) is where the game puts the head.

Headdy is a composite, as in his game: every frame here is a body with a head put on at its neck bolt (the head box's
bottom, 12 px in from its right edge, on the bolt: the placement read off his idle frame). The pieces are copied
exactly into build/source.png (a working copy: each frame's body, then its head over it, in a cell of its own); nothing
is redrawn, recoloured or resized (placing existing pieces only). Three walk frames turned away from us have no bolt:
their neck is set by hand (NECK below).

Box numbers below are the sheet's sprite boxes, as [x, y, w, h] in BOX.

Normal animations (bodies from BODY 1 / BODY 9, heads from HEAD 1):
  stand       body 27 + head 56 (blinking: 58, 60)       walk / run  bodies 19-26 + head 56 / 57 (hair streaming)
  look up     body 28 + head 82                          crouch      body 30 + head 83 (squashed)
  skid        body 29 + head 56                          jump        bodies 36 / 37 (arms up) + head 57: no ball
  hurt        body 47 + head 64 (shocked)                die         body 48 + head 65
  balance     bodies 47 / 48 + head 58                   push        body 51 + head 56
  hang        body 43 + head 82                          bored       bodies 618-620 (BODY 9's waving) + head 56
  victory     bodies 618 -> 621 / 622 (arms up) + head 85 (his front face, smiling)

Head Throw (tools/head_throw.py; slots 41 / 43):
  slot 41 "Throw": his body alone (the head's away), per aim class 0 forward, 1 forward-up, 2 up, 3 forward-down,
    4 down: bodies 51, 53, 50, 54, 54 (the throwing arm), on the ground (0-4) and in the air (5-9)
  slot 42 "Headless": body 27 alone (unused by the code; keeps the slots contiguous)
  slot 43 "Heads": per head variant (HEAD_VARIANTS; only index 0, his normal head, is built now) 10 frames: the flying
    head for aim class 0-4 going out (HEAD 1 row 3: 69, 68, 66, 70, 67, mouth open) then coming back (row 4: 75, 73,
    71, 74, 72), drawn facing right (the code mirrors them with his facing)

Power-up heads, for later (the shared monitor_swap module): every HEAD n section has the same layout as HEAD 1 (row 1
the head at rest / blinking, row 2 shocked, rows 3-4 the flying head by aim, row 5 spinning, then front views). Their
section's y range on the sheet and the boxes of their flying-head rows (out, back; order forward, forward-up, up,
forward-down, down) are in HEAD_VARIANTS. Only "normal" is in the build (BUILT_VARIANTS): the others' colours don't
fit his palette slots yet (22 at most; the normal head and body use 11).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
from sign_face import board_face  # noqa: E402
from extras import EXTRAS  # noqa: E402

NAME = next((e["file"] for e in EXTRAS if e["art"].name == HERE.name), f"Extra{len(EXTRAS) + 1}")
SOURCE = "build/source.png"
PAGE = (63, 72, 204)
BOX_BG = [(0, 36, 36), (0, 0, 108)]
BACKGROUND = ["#3f48cc"]  # the working copy's background (the page)
NECK_GREEN = (0, 252, 0)
SHEET = Image.open(HERE / "Headdy.png").convert("RGB")
PIX = np.array(SHEET).astype(int)

# ---------------------------------------------------------------- the sheet's sprite boxes used ([x, y, w, h])
BOX = {
    # BODY 1
    19: (1, 246, 16, 24), 20: (18, 246, 24, 24), 21: (43, 246, 32, 24), 22: (76, 246, 24, 24), 23: (101, 246, 16, 24),
    24: (118, 246, 16, 24), 25: (135, 246, 24, 24), 26: (160, 246, 24, 24), 27: (1, 271, 32, 24),
    28: (1, 296, 24, 24), 29: (26, 296, 32, 24), 30: (1, 321, 32, 16), 36: (168, 338, 24, 24), 37: (193, 338, 24, 24),
    43: (76, 375, 24, 24), 47: (1, 425, 32, 24), 48: (34, 425, 32, 24), 49: (1, 450, 24, 24), 50: (26, 450, 24, 24),
    51: (51, 450, 24, 24), 52: (1, 475, 24, 24), 53: (26, 475, 24, 24), 54: (51, 483, 24, 16),
    # BODY 9
    618: (1, 5006, 32, 24), 619: (34, 5006, 24, 24), 620: (84, 5006, 24, 24), 621: (1, 5031, 24, 32),
    622: (26, 5031, 24, 32),
    # HEAD 1
    56: (1, 517, 24, 24), 57: (26, 517, 32, 24), 58: (59, 517, 24, 24), 59: (84, 517, 32, 24), 60: (117, 517, 24, 24),
    64: (1, 542, 24, 32), 65: (26, 542, 24, 32),
    66: (1, 575, 24, 32), 67: (109, 575, 24, 32), 68: (26, 579, 24, 24), 69: (51, 579, 32, 24), 70: (84, 579, 24, 24),
    71: (5, 608, 16, 32), 72: (113, 608, 16, 32), 73: (26, 616, 24, 24), 74: (84, 616, 24, 24), 75: (51, 620, 32, 16),
    81: (26, 666, 24, 24), 82: (51, 666, 24, 24), 83: (1, 674, 24, 16), 85: (18, 691, 24, 24),
}
# the neck of the bodies whose bolt is out of view (turned away), px in their box
NECK = {24: (9, 9), 25: (14, 8), 26: (13, 8)}

# Head variants (the sheet's HEAD sections). Index 0 is built; the rest are listed for the monitor_swap module (their
# section's y range, their flying-head boxes: out then back, each forward, forward-up, up, forward-down, down). What
# each does in Dynamite Headdy is in SOURCE.txt.
HEAD_VARIANTS = [
    {"name": "normal", "section": (504, 820), "out": [69, 68, 66, 70, 67], "back": [75, 73, 71, 74, 72]},
    {"name": "hammer", "section": (820, 1111)},     # HEAD 2: grey steel head (Hammer Head)
    {"name": "crest", "section": (1111, 1377)},     # HEAD 3: green crest
    {"name": "goggles", "section": (1377, 1643)},   # HEAD 4: red head in goggles
    {"name": "spike", "section": (1643, 1885)},     # HEAD 5: purple spiked ball (Spike Head)
    {"name": "hood", "section": (1885, 2151)},      # HEAD 6: dark blue hooded head
    {"name": "fire", "section": (2151, 2507)},      # HEAD 7: flaming head
    {"name": "outline", "section": (2507, 2748)},   # HEAD 8: outline only (with BODY 2's outline body)
    {"name": "mini", "section": (2986, 3156)},      # HEAD 9: tiny head (with BODY 3's tiny body)
    {"name": "bomb", "section": (3351, 3612)},      # HEAD 10: black bomb (Bang Head)
    {"name": "vacuum", "section": (3612, 3819)},    # HEAD 11: green nozzle head (Vacuum Head)
    {"name": "pig", "section": (3861, 4086)},       # HEAD 12: pink pig (Pig Head)
    {"name": "counter", "section": (4086, 4261)},   # HEAD 13: numbered display head
    {"name": "speakers", "section": (4311, 4460)},  # HEAD 14: big speaker head with lips (BODY 5)
    {"name": "sleep", "section": (4494, 4627)},     # HEAD 15: nightcap (Sleep Head; BODY 6 lying down)
    {"name": "rocket", "section": (5483, 5558)},    # HEAD 18: purple rocket head
    {"name": "plane", "section": (5558, 5625)},     # HEAD 19: orange plane head
    {"name": "bird", "section": (5625, 5708)},      # HEAD 20: brown bird head
]
BUILT_VARIANTS = 1  # (HEAD_VARIANTS[:1]; tools/head_throw.py HEAD_FRAMES per variant in slot 43)


def mask(k):
    x, y, w, h = BOX[k]
    sub = PIX[y:y + h, x:x + w]
    m = np.ones((h, w), bool)
    for c in BOX_BG + [PAGE]:
        m &= ~np.all(sub == c, axis=2)
    return sub, m


def neck(k):
    if k in NECK:
        return NECK[k]
    sub, _ = mask(k)
    ys, xs = np.nonzero(np.all(sub == NECK_GREEN, axis=2))
    if not len(xs):
        raise SystemExit(f"headdy: body {k} has no neck bolt and no NECK entry")
    return int(round(xs.mean())), int(round(ys.mean()))


def head_at(body, head):
    """The head box's top-left relative to the body box's: its bottom, 12 px in from its right edge, on the bolt."""
    nx, ny = neck(body)
    return nx - (BOX[head][2] - 12), ny - BOX[head][3]


# ---------------------------------------------------------------- frames: name -> [(box, dx, dy, flip)] (back first)
FR = {}


def comp(name, body, head=None):
    FR[name] = [(body, 0, 0, False)] + ([(head, *head_at(body, head), False)] if head else [])
    return name


def solo(name, box, flip=False):
    FR[name] = [(box, 0, 0, flip)]
    return name


for b in range(19, 27):
    comp(f"W{b}", b, 56)
    comp(f"R{b}", b, 57)
for n, (b, h) in {"STAND": (27, 56), "BLINK1": (27, 58), "BLINK2": (27, 60), "LOOKUP": (28, 82), "CROUCH": (30, 83),
                  "SKID": (29, 56), "JUMP1": (36, 57), "JUMP2": (37, 57), "HURT": (47, 64), "DIE": (48, 65),
                  "BAL1": (47, 58), "BAL2": (48, 58), "PUSH": (51, 56), "HANG": (43, 82), "BORED1": (618, 56),
                  "BORED2": (619, 56), "BORED3": (620, 56), "WIN1": (621, 85), "WIN2": (622, 85)}.items():
    comp(n, b, h)
for b in (27, 50, 51, 53, 54):
    solo(f"B{b}", b)
for v in HEAD_VARIANTS[:BUILT_VARIANTS]:
    for k in v["out"] + v["back"]:
        solo(f"H{k}", k)


def source_sheet():
    """Each frame's pieces copied exactly into a cell of its own (shelves 512 wide). Returns {name: (cell rect, body box
    inside the copy)}."""
    cells, x, y, shelf = {}, 2, 2, 0
    for name, parts in FR.items():
        x0 = min(dx for _, dx, _, _ in parts)
        y0 = min(dy for _, _, dy, _ in parts)
        w = max(dx + BOX[k][2] for k, dx, _, _ in parts) - x0
        h = max(dy + BOX[k][3] for k, _, dy, _ in parts) - y0
        if x + w + 2 > 512:
            x, y, shelf = 2, y + shelf + 3, 0
        cells[name] = (x - x0, y - y0, [x, y, w, h])
        x += w + 3
        shelf = max(shelf, h)
    out = np.zeros((y + shelf + 2, 512, 3), int)
    out[:] = PAGE
    rects = {}
    for name, parts in FR.items():
        ox, oy, rect = cells[name]
        body = None
        for k, dx, dy, flip in parts:
            sub, m = mask(k)
            if flip:
                sub, m = sub[:, ::-1], m[:, ::-1]
            h, w = m.shape
            reg = out[oy + dy:oy + dy + h, ox + dx:ox + dx + w]
            reg[m] = sub[m]
            if body is None:
                ys, xs = np.nonzero(m)
                body = [ox + dx + int(xs.min()), oy + dy + int(ys.min()), int(xs.max() - xs.min() + 1),
                        int(ys.max() - ys.min() + 1)]
        rects[name] = (rect, body)
    (HERE / "build").mkdir(exist_ok=True)
    img = Image.fromarray(out.astype("uint8"))
    img.save(HERE / SOURCE)
    return rects, img


R, COPY = source_sheet()


def fr(name, center=False):
    """A frame placed by its body (the head's hair doesn't shift him): the body's box as the anchor."""
    rect, body = R[name]
    return {"rect": rect, "anchor_box": body}


def f(*names):
    return [fr(n) for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)

# ---------------------------------------------------------------- animations
IDLE = f(*["STAND"] * 6, "BLINK1", "BLINK2", "BLINK1")
WALK = f(*[f"W{b}" for b in range(19, 27)])
RUN = f(*[f"R{b}" for b in range(19, 27)])
JUMP = f("JUMP1", "JUMP2")
BALANCE = f("BAL1", "BAL2")

ANIMS = {
    "Stopped": {"frames": f("STAND")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": IDLE, "loop": 0},
    "Looking Up": {"frames": f("LOOKUP")},
    "Looking Down": {"frames": f("CROUCH")},
    "Walking": {"frames": WALK},
    "Running": {"frames": RUN},
    "Skidding": {"frames": f("SKID")},
    "Super Peel Out": {"frames": RUN},
    "Spin Dash": {"frames": f("CROUCH")},  # PLACEHOLDER: he never curls up (extras.py "no_roll")
    "Jumping": C(JUMP),
    "Bouncing": C(f("JUMP1")),
    "Hurt": C(f("HURT")),
    "Dying": C(f("DIE")),
    "Drowning": C(f("DIE")),
    "Fan Rotate": C(JUMP),
    "Breathing": C(f("HURT")),
    "Pushing": {"frames": f("PUSH")},
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": C(f("HANG")),
    "Clinging On": C(f("HANG")),
    "Corkscrew H": {"frames": RUN},
    "Water Slide": C(f("SKID")),
    "Continue": {"frames": IDLE},
    "Continue Up": {"frames": f("WIN1")},
    "Super Transform": {"frames": f("WIN2")},
}
S2_ONLY = {
    "Bored!": {"frames": f("BORED1", "BORED2", "BORED3", "BORED2"), "loop": 0},
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": C(f("HURT")),
    "Twirl H": {"frames": RUN, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# Slot 41 "Throw" (tools/head_throw.py picks the frame): his headless body per aim class, ground 0-4, air 5-9
THROW_BODY = ["B51", "B53", "B50", "B54", "B54"]
# Slot 43 "Heads": per built variant, the flying head per aim class out (0-4) then back (5-9), centred
HEADS = [{"rect": R[f"H{k}"][0]} for v in HEAD_VARIANTS[:BUILT_VARIANTS] for k in v["out"] + v["back"]]
APPENDED = {
    "41": {"name": "Throw", "frames": [fr(n) for n in THROW_BODY] * 2, "speed": 0},
    "42": {"name": "Headless", "frames": f("B27"), "speed": 0},
    "43": {"name": "Heads", "frames": HEADS, "anchor": "center", "speed": 0},
}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
# the standing frame's head (the head box 56, its face: the 16x16 right of the hair)
_S, _B = R["STAND"]
_HX, _HY = _S[0] + (head_at(27, 56)[0] - 0) + 8, _S[1] + 6
HEAD = [_HX, _HY, 16, 16]
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("HEADDY")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1], 16, 14], "trim": False},
    "sign_face": board_face([_S[0], _S[1], _S[2], 24]),  # his head on the game's own board, 1x
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": R["STAND"][0], "remap": PLUS_128},
    "end_pose_1": {"rect": R["WIN1"][0], "remap": PLUS_128},
    "end_pose_2": {"rect": R["WIN2"][0], "remap": PLUS_128},
    "end_pose_3": {"rect": R["LOOKUP"][0], "remap": PLUS_128},
    **{f"good_{n}": {"rect": R[k][0], "remap": PLUS_128}
       for n, k in enumerate(("BORED1", "BORED2", "BORED3", "WIN1", "WIN2", "STAND"), 1)},
}


# ---------------------------------------------------------------- colours
# All his colours exact: black in Sonic's slot 1, the others in his own slots 74+ (the most used first)
def hexof(rgb):
    return "#%02x%02x%02x" % rgb


_COUNTS = {}
for _n, _rgb in COPY.getcolors(1 << 16):
    if hexof(_rgb) not in BACKGROUND and hexof(_rgb) != "#000000":
        _COUNTS[hexof(_rgb)] = _n
if len(_COUNTS) > 22:
    raise SystemExit(f"headdy: {len(_COUNTS)} colours, more than slots 74-95")
PALETTE = {str(74 + k): c for k, c in enumerate(sorted(_COUNTS, key=lambda c: (-_COUNTS[c], c)))}
COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}
CREDIT = ("Dynamite Headdy ripped by Sonicfan32 (The Spriters Resource, asset 11723); Dynamite Headdy (c) Treasure and "
          "Sega")

# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose" the pose
# looped): both arms up, his smiling front face
S3K_VICTORY = {"frames": f("BORED1", "WIN1", "WIN2"), "pose": 1}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": NAME, "credit": CREDIT,
           "source": SOURCE, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": f"{NAME}SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(JUMP)}}]  # no ball: his jump pose
        cfg["ui"] = [{"name": f"{NAME}_UI", "manifest": f"{NAME}_ui.json", "elements": ELEMENTS,
                      "out": f"build/{NAME}_UI.gif"},
                     {"name": f"{NAME}_Ending", "manifest": f"{NAME}_ending.json", "elements": ENDING,
                      "out": f"build/{NAME}_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "headdy.json"), ("Sonic2", "headdy_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("palette:", PALETTE)
