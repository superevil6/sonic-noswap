#!/usr/bin/env python3
"""Writes Sparkster's sheet2ani configs (sparkster.json for Sonic 1, sparkster_s2.json for Sonic 2; CD's and S3&K's come
from the Sonic 2 one).

Sparkster, the Rocket Knight (Rocket Knight Adventures, Sega Genesis). A separate download (extras.py "crossover": never in
the all-in-one; memory crossover-characters.md). Base character Sonic. His number (file "Extra<n>") is his place in
tools/extras.py, looked up.

Sheet: testmods/sparkster/Sparkster.png (1408x1024), "Rocket Knight Adventures - Sparkster/Rocket Knight", The Spriters
Resource asset 29167 (see SOURCE.txt). Its note: "Assets (c) Konami. Original rip by Jack Rost, re-ripped by UltraHype97.
Give credit if used!" Genesis art, used at 1x (he stands about 40-44 px, Sonic's height). Every sprite faces right.
The page (#83c3cf), the cells (#5e9da9) and their darker "sprite area" boxes (#1a7c8f, #0e5a69), the reused-frame boxes
(#3629a0, #230e64, #13053e) and the unused-frame boxes (#9b8f1d, #72690f, #433d04) are all background.

Sections used (the sheet's own labels) and the frame names here (B: each frame's main drawing, its tight box on the
sheet; the small loose bits around it, e.g. the sword's swooshes and sweat drops, go with the nearest main drawing):
  Stand STAND1-5 (loops forward/back), Waiting WAIT1-5 and LETSGO1-2 ("Let's go"), Walk WALK1-12, Turn TURN1-2,
  Balance BAL1-3, Stationary Jump SJ1-4, Moving Jump MJ1-4, Crouch CROUCH1-2, Damage, Backfire, Death DEATH1-4,
  Slash SLASH1-4, Spin Attack SPIN1-4, Dash Attack DASHATK, Rocket Dash RD_DOWN / RD_DDIAG / RD_FWD / RD_UDIAG / RD_UP
  (RD_UP is the sheet's reused frame: RD_DOWN turned over), Exhausted EXH1-2, Flight FLIGHT1-2, Fly Slash FLYSLASH1-4,
  and the cutscenes' Look Up, Pleased, Surprise, Serious, Peeved.
Not used: Hang / Hang Move / Hang Slash (poles: no hang, the user), Sliding, Swim, Death (Alt), the escape pod, the
palettes, Staff Roll, the effects.

Abilities (tools/abilities.py, his entry; the user's design 2026-09-29; wired in abilities.py, build_soniccd.py, the DLL):
  - Y: Sword Slash, the melee's pose (slots 43 / 44: Slash on the ground, Fly Slash in the air) with a real projectile,
    the sword's energy wave (the sheet's Projectile frames, abilities.py "shot", motion "straight").
  - Hold jump in mid-air: Rocket Burst (abilities.py rocket_burst). Slot 41, the code picks the frame: 0 charging
    (CROUCH1, braced), 1 its flash (BACKFIRE), 2-6 the Rocket Dash angles (down, down-forward, forward, up-forward, up),
    7-10 the Spin Attack (the Rocket Spin, released with no direction held).
  - He never curls into a ball (extras.py "no_roll", as Gamma): his jump is MJ2.

Frames are whole drawings: build/source.png is a working copy holding each used frame's pixels copied exactly in a cell
of its own. Nothing is redrawn, recoloured or resized. The HUD tag "SPARKSTER" is our lettering in the HUD font the
other extras use (the sheet has none); the life icon / 1-UP are crops of the Pleased frame's head; the signpost is that
head on the game's own board.
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
from sign_face import board_face  # noqa: E402
from extras import EXTRAS  # noqa: E402

NAME = next(e["file"] for e in EXTRAS if e["art"].name == HERE.name)  # "Extra<n>", its extras.py position
SHEET = HERE / "Sparkster.png"
SOURCE = "build/source.png"  # working copy: each used frame's blobs in a cell of its own (source_sheet)
SHEET_BG = [(131, 195, 207), (94, 157, 169), (26, 124, 143), (14, 90, 105), (54, 41, 160), (35, 14, 100), (19, 5, 62),
            (155, 143, 29), (114, 105, 15), (67, 61, 4)]
BACKGROUND = ["#%02x%02x%02x" % c for c in SHEET_BG]
BG = SHEET_BG[0]
SRC = Image.open(SHEET).convert("RGB")


def row(prefix, rects, start=1):
    return {f"{prefix}{k}": list(r) for k, r in enumerate(rects, start)}


# ---------------------------------------------------------------- frames: name -> the main drawing's tight box on the sheet
B = {
    **row("STAND", [(16, 73, 40, 39), (78, 72, 43, 40), (143, 68, 43, 44), (207, 72, 44, 40), (277, 73, 39, 39)]),
    **row("WAIT", [(356, 68, 40, 44), (421, 68, 40, 44), (486, 68, 40, 44), (562, 68, 35, 44), (627, 68, 32, 44)]),
    **row("LETSGO", [(692, 68, 40, 44), (749, 68, 40, 44)]),
    **row("WALK", [(21, 164, 43, 36), (82, 158, 39, 42), (143, 155, 43, 45), (211, 152, 40, 48), (273, 154, 43, 46),
                   (335, 155, 47, 45), (410, 162, 48, 38), (469, 158, 47, 42), (533, 154, 43, 46), (598, 155, 43, 45),
                   (667, 158, 39, 42), (735, 160, 41, 40)]),
    **row("TURN", [(819, 160, 40, 40), (884, 160, 32, 40)]),
    **row("BAL", [(1017, 160, 45, 40), (1081, 156, 45, 44), (1145, 154, 46, 46)]),
    **row("SJ", [(20, 234, 40, 48), (85, 234, 40, 40), (150, 231, 40, 43), (215, 231, 44, 43)]),
    **row("MJ", [(291, 237, 40, 48), (364, 234, 32, 43), (421, 232, 40, 44), (486, 232, 40, 48)]),
    **row("CROUCH", [(566, 240, 48, 40), (636, 252, 43, 28)]),
    "DAMAGE": [703, 240, 48, 40], "BACKFIRE": [794, 241, 41, 39],
    **row("DEATH", [(875, 248, 40, 32), (940, 248, 40, 32), (1005, 253, 40, 27), (1070, 259, 40, 21)]),
    **row("SLASH", [(8, 313, 48, 47), (89, 312, 52, 48), (162, 322, 56, 38), (235, 322, 50, 38)]),
    **row("SPIN", [(455, 316, 42, 44), (520, 328, 44, 42), (575, 328, 42, 44), (638, 318, 44, 42)]),
    "DASHATK": [722, 323, 65, 37],
    "RD_DOWN": [827, 312, 32, 63], "RD_DDIAG": [883, 312, 48, 56], "RD_FWD": [948, 329, 63, 29],
    "RD_UDIAG": [1021, 313, 56, 48], "RD_UP": [1094, 297, 32, 63],
    **row("EXH", [(1169, 327, 45, 33), (1239, 329, 48, 40)]),
    **row("FLIGHT", [(819, 595, 56, 28), (885, 592, 56, 31)]),
    **row("FLYSLASH", [(969, 580, 56, 44), (1035, 574, 68, 48), (1111, 595, 69, 31), (1181, 592, 64, 34)]),
    "LOOKUP": [312, 706, 40, 46], "PLEASED": [616, 708, 40, 44], "SURPRISE": [160, 708, 44, 48],
    "SERIOUS": [241, 709, 39, 43], "PEEVED1": [400, 708, 40, 44], "PEEVED2": [465, 708, 32, 44],
}
# The sword's energy wave (the Projectile section: four 32x24 cells, the last two the sheet's reused frames), cut from the
# sheet itself by abilities.py "shot" (its cells, as drawn; the section label sits above them)
PROJECTILE = [[292, 304, 32, 24], [325, 304, 32, 24], [358, 304, 32, 24], [391, 304, 32, 24]]

# ---------------------------------------------------------------- the working copy
_BGMASK = np.zeros(SRC.size[::-1], bool)
for _c in SHEET_BG:
    _BGMASK |= np.all(np.array(SRC) == _c, axis=2)
LABELS, _ = ndimage.label(~_BGMASK, structure=np.ones((3, 3)))
OBJECTS = ndimage.find_objects(LABELS)
MAIN = 300  # a blob of at least this many pixels is a main drawing (smaller: loose bits, e.g. swooshes)
MARGIN = 4  # loose bits whose centre is this close to a main drawing's box go with it


def _box(sl):
    return sl[1].start, sl[0].start, sl[1].stop - sl[1].start, sl[0].stop - sl[0].start


def _dist(box, cx, cy):
    x, y, w, h = box
    return max(x - cx, 0, cx - (x + w - 1)) + max(y - cy, 0, cy - (y + h - 1))


def _frames():
    """{name: set of blob labels}: each frame's main drawing plus the loose bits nearest to it."""
    mains = {}
    for lab, sl in enumerate(OBJECTS, 1):
        if tuple(_box(sl)) in {tuple(r) for r in B.values()}:
            mains[tuple(_box(sl))] = lab
    missing = [n for n, r in B.items() if tuple(r) not in mains]
    if missing:
        raise SystemExit(f"sparkster: no drawing with the tight box of {missing}")
    out = {n: {mains[tuple(r)]} for n, r in B.items()}
    counts = ndimage.sum(np.ones(LABELS.shape), LABELS, range(1, len(OBJECTS) + 1))
    for lab, sl in enumerate(OBJECTS, 1):
        if counts[lab - 1] >= MAIN:
            continue
        x, y, w, h = _box(sl)
        cx, cy = x + w // 2, y + h // 2
        near = [(_dist(r, cx, cy), n) for n, r in B.items() if _dist(r, cx, cy) <= MARGIN]
        if near:
            out[min(near)[1]].add(lab)
    return out


def source_sheet():
    """Each frame's pixels, copied exactly, in a cell of its own (shelves 512 wide). Returns {name: rect in the copy}."""
    blobs = _frames()
    cells, x, y, shelf = {}, 2, 2, 0
    for name, labs in blobs.items():
        ys, xs = np.nonzero(np.isin(LABELS, list(labs)))
        sx, sy, w, h = int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
        if x + w + 2 > 512:
            x, y, shelf = 2, y + shelf + 3, 0
        cells[name] = (list(zip(xs, ys)), (sx, sy), [x, y, int(w), int(h)])
        x += w + 3
        shelf = max(shelf, h)
    out = Image.new("RGB", (512, y + shelf + 2), BG)
    for pts, (sx, sy), (cx, cy, _, _) in cells.values():
        for a, b in pts:
            out.putpixel((int(cx + a - sx), int(cy + b - sy)), SRC.getpixel((int(a), int(b))))
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return {name: c[2] for name, c in cells.items()}


R = source_sheet()


def f(*names):
    return [R[n] for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)

# ---------------------------------------------------------------- animations
STAND = f("STAND1", "STAND2", "STAND3", "STAND4", "STAND5", "STAND4", "STAND3", "STAND2")  # (loops forward/back)
WAIT = STAND + f("WAIT1", "WAIT2", "WAIT3", "WAIT4", "WAIT5", "WAIT4", "WAIT3", "WAIT2")
WALK = f(*[f"WALK{k}" for k in range(1, 13)])
JUMP = f("MJ2")  # no ball: the moving jump's tuck (as Gamma's jump pose)
BALANCE = f("BAL1", "BAL2", "BAL3", "BAL2")
DEATH = f("DEATH1")

ANIMS = {
    "Stopped": {"frames": f("STAND1")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": WAIT, "loop": 8, "align": True},
    "Looking Up": {"frames": f("LOOKUP")},
    "Looking Down": {"frames": f("CROUCH1", "CROUCH2"), "loop": 1},
    "Walking": {"frames": WALK, "rot": 2, "align": True},
    "Running": {"frames": WALK, "rot": 2, "align": True},  # (no run on the sheet: the walk, faster)
    "Skidding": {"frames": f("TURN1")},
    "Super Peel Out": {"frames": WALK, "rot": 2, "align": True},
    "Spin Dash": {"frames": f("CROUCH2")},  # PLACEHOLDER: he never curls up (extras.py "no_roll")
    "Jumping": C(JUMP),
    "Bouncing": C(f("SJ1")),  # springs: stretched up
    "Hurt": C(f("DAMAGE")),
    "Dying": C(f("SURPRISE")),
    "Drowning": C(f("SURPRISE")),
    "Fan Rotate": C(f("SPIN1", "SPIN2", "SPIN3", "SPIN4")),
    "Breathing": C(f("SJ1")),
    "Pushing": {"frames": f("DASHATK")},  # leaning in, the sword forward
    "Flailing 1": {"frames": BALANCE, "align": True},
    "Flailing 2": {"frames": BALANCE, "align": True},
    "Hanging": C(f("SJ1")),  # (no pole hang: the user)
    "Clinging On": C(f("SJ1")),
    "Corkscrew H": {"frames": WALK},
    "Water Slide": C(f("CROUCH2")),
    "Continue": {"frames": WAIT, "align": True},
    "Continue Up": {"frames": f("LETSGO1")},
    "Super Transform": {"frames": f("LETSGO2")},
}
S2_ONLY = {
    "Bored!": {"frames": f("WAIT1", "WAIT2", "WAIT3", "WAIT4", "WAIT5", "WAIT4", "WAIT3", "WAIT2"), "loop": 0,
               "align": True},
    "Flailing 3": {"frames": BALANCE, "align": True},
    "Grabbed": C(f("DAMAGE")),
    "Twirl H": {"frames": WALK, "rot": 2},
}
CD_ONLY = {name: {"frames": WALK} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# Slot 41: the Rocket Burst (abilities.py rocket_burst: the code picks the frame, ROCKET_FRAMES there): 0 charging, 1 the
# charge's flash, 2-6 the Rocket Dash by angle (down, down-forward, forward, up-forward, up; aimed back he faces back),
# 7-10 the Rocket Spin (the Spin Attack's four)
ROCKET = f("CROUCH1", "BACKFIRE", "RD_DOWN", "RD_DDIAG", "RD_FWD", "RD_UDIAG", "RD_UP", "SPIN1", "SPIN2", "SPIN3", "SPIN4")
# Slots 43 / 44: the Sword Slash's pose (the melee's; abilities.py melee_reach has as many entries): the Slash on the
# ground, the Fly Slash in the air, the swing and its full swoosh; the shot (the energy wave) shows their last frame
APPENDED = {
    "41": {"name": "Rocket Burst", "frames": ROCKET, "anchor": "center", "speed": 0},
    "43": {"name": "Sword Slash", "frames": f("SLASH2", "SLASH3"), "speed": 0},
    "44": {"name": "Fly Slash", "frames": f("FLYSLASH2", "FLYSLASH3"), "anchor": "center", "speed": 0},
}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
_P = R["PLEASED"]
HEAD = [_P[0] + 19, _P[1] + 8, 16, 16]  # the Pleased frame's face and goggles (the life icon)
FACE = [_P[0] + 15, _P[1] + 1, 22, 22]  # ...its head, ears' base to chin (the signpost)
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("SPARKSTER")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1], 16, 14], "trim": False},
    "sign_face": board_face(FACE),  # his head on the game's own board, 1x
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": R["STAND1"], "remap": PLUS_128},
    "end_pose_1": {"rect": R["LETSGO1"], "remap": PLUS_128},  # "Let's go"
    "end_pose_2": {"rect": R["PLEASED"], "remap": PLUS_128},
    "end_pose_3": {"rect": R["LOOKUP"], "remap": PLUS_128},
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("WAIT1", "WAIT2", "WAIT3", "LETSGO1", "LETSGO2", "PLEASED"), 1)},
}

# ---------------------------------------------------------------- colours
# The sheet's sprites use the game's own 16-colour palette (black is Sonic's slot 1); the other colours the built art and
# the energy wave use go exact in his own slots 74-95.
KEY_COLOURS = {"#000000": 1}


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def own_colours():
    counts = {}
    ims = [Image.open(HERE / SOURCE).convert("RGB")] + [SRC.crop((x, y, x + w, y + h)) for x, y, w, h in PROJECTILE]
    for im in ims:
        for n, rgb in im.getcolors(1 << 16):
            c = "#%02x%02x%02x" % rgb
            if c not in BACKGROUND and c not in KEY_COLOURS:
                counts[c] = counts.get(c, 0) + n
    return sorted(counts.items(), key=lambda kv: -kv[1])


_OWN = own_colours()
if len(_OWN) > 22:
    raise SystemExit(f"sparkster: {len(_OWN)} own colours, 22 slots")
PALETTE = {str(74 + k): c for k, (c, _) in enumerate(sorted(_OWN))}


def all_colours():
    """KEY_COLOURS and PALETTE, plus every other colour of the sheet in the slot of its nearest own colour."""
    keys = {hexrgb(c): int(s) for s, c in PALETTE.items()}
    out = dict(KEY_COLOURS, **{c: int(s) for s, c in PALETTE.items()})
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            out[c] = keys[min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))]
    return out


COLOURS = all_colours()
CREDIT = ("Sparkster (Rocket Knight Adventures): original rip by Jack Rost, re-ripped by UltraHype97, The Spriters "
          "Resource, asset 29167 (Assets (c) Konami)")

# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose" the pose
# held): "Let's go"
S3K_VICTORY = {"frames": f("STAND1", "LETSGO1", "LETSGO2"), "pose": 2}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": NAME, "credit": CREDIT,
           "source": SOURCE, "feet_y": 20, "background": [BACKGROUND[0]], "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": f"{NAME}SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(JUMP)}}]  # no ball: his jump pose (as Gamma's)
        cfg["ui"] = [{"name": f"{NAME}_UI", "manifest": f"{NAME}_ui.json", "elements": ELEMENTS,
                      "out": f"build/{NAME}_UI.gif"},
                     {"name": f"{NAME}_Ending", "manifest": f"{NAME}_ending.json", "elements": ENDING,
                      "out": f"build/{NAME}_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "sparkster.json"), ("Sonic2", "sparkster_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("own colours:", ", ".join(f"{c} x{n}" for c, n in _OWN))
