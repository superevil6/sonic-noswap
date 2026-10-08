#!/usr/bin/env python3
"""Writes Ristar's sheet2ani configs (ristar.json for Sonic 1, ristar_s2.json for Sonic 2; CD's and S3&K's come from the
Sonic 2 one).

Ristar (Sega Genesis). A separate download (extras.py "crossover"). Base character Sonic. Its extras.py position gives
its file name (NAME below, looked up, not hard-coded).

Sheets (see SOURCE.txt), both compiled by Drshnaps (drshnaps.com), listed on The Spriters Resource under Jermungandr:
  Ristar_basic.png   "Ristar - Basic Actions and Animations" (TSR asset 12659)
  Ristar_special.png "Ristar Attacks and Arm Actions" (TSR asset 12660)
(Ristar.png, the Game Gear sheet, isn't used.) Periwinkle (#8080ff) page, white section lines and labels; every sprite
faces right. Genesis art, used at 1x.

Frames used (names below; [x, y, w, h] on their sheet):
  basic:   Flora Idle F0-F4, Boss Idle BI0-BI3, Walk W0-W7, Jump J0-J4, Spin/Roll S0-S3, Balancing (forward) BF0-BF3,
           Fall FA0-FA1, Ladder L0-L8, Overhead O0-O8, Fast Swim FS0, Bounce BO0-BO4, Ice Slip IS0 / IS3,
           Injured/Death X0-X2, Victory 1 V0-V2, Misc M0 / M8
  special: the arm-action bodies B0-B8 (the top row: standing, jumping, standing looking up, jumping looking up,
           reaching down, swimming x2, pulling forward x2), the loose hands H0 (open, fingers right), H1 (open, fingers
           up-right), G0 / G1 (their gripping versions), the Meteor Strike ("shooting star") row MH0-MH2 (level) and
           MD0-MD2 (diving), the headbutt HB (back view, fists forward), and 8 of the 48 swing-on-handle frames SW0-SW7
           (every 6th: once round the handle)

Abilities (tools/star_grab.py, the user's design 2026-09-29; wired in abilities.py, build_soniccd.py and the DLL):
  - Y: Grab, aimed 8 ways with the d-pad (nothing held: forward; on the ground not down). His arms stretch out and back;
    the arms are drawn at runtime (two 2 px black lines, as the game draws them: vector lines), his hands (slot 43,
    "Hands": the loose hands turned / mirrored to 8 directions, open 0-7 then gripping 8-15) at their ends. His body is
    slot 41 "Grab" (an attack; the code picks the frame): 0-4 standing reaching, 5-9 in the air, 10-14 pulled forward
    (per aim class: 0 forward, 1 forward-up, 2 up, 3 forward-down, 4 down), 15 the headbutt, 16-30 the Meteor Strike
    (3 frames per aim class, turned by quarter turns).
  - Slot 42 "Hang": 0-8 the Ladder frames (on a wall to his right), 9-17 the Overhead frames (under a ceiling), 18-25
    the swing frames (the Meteor Strike's wind-up, drawn at his grip, the handle's ball on the pivot).
  - Jump / roll: his own Spin/Roll frames.

Frames are whole drawings: build/source.png is a working copy holding each used frame's pixels (the blobs of the sheet
wholly inside its box, copied exactly) in a cell of its own. Crops, quarter turns and mirroring only: nothing is
redrawn, recoloured or resized. The HUD tag "RISTAR" is our lettering in the HUD font the other extras use (the sheet
has none); the life icon / 1-UP are crops of a standing frame's head; the signpost is that head on the game's own
board. Colours: all 15 of his exact, black in Sonic's slot 1, the other 14 in slots 74-87.
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

# "Extra<n>", its extras.py position (before its entry exists, the next one: the first run writes the palette file
# extras.py reads)
NAME = next((e["file"] for e in EXTRAS if e["art"].name == HERE.name), f"Extra{len(EXTRAS) + 1}")
SOURCE = "build/source.png"
BACKGROUND = ["#8080ff"]
BG = (128, 128, 255)
SHEETS = {"b": Image.open(HERE / "Ristar_basic.png").convert("RGB"),
          "s": Image.open(HERE / "Ristar_special.png").convert("RGB")}


def row(sheet, prefix, rects):
    return {f"{prefix}{k}": (sheet, list(r)) for k, r in enumerate(rects)}


# ---------------------------------------------------------------- frames: name -> (sheet, [x, y, w, h]) (tight boxes)
B = {
    **row("b", "F", [(83, 28, 26, 38), (114, 28, 30, 38), (149, 28, 32, 38), (186, 29, 32, 37), (223, 29, 32, 37)]),
    **row("b", "BI", [(264, 162, 30, 38), (299, 162, 32, 38), (336, 163, 32, 37), (373, 163, 32, 37)]),
    **row("b", "W", [(85, 227, 34, 40), (124, 230, 34, 37), (163, 229, 24, 38), (192, 229, 36, 38), (233, 230, 34, 37),
                     (272, 230, 44, 37), (321, 230, 44, 37), (370, 228, 26, 39)]),
    **row("b", "J", [(449, 223, 32, 44), (486, 223, 36, 44), (527, 219, 40, 48), (572, 222, 39, 40), (616, 229, 26, 38)]),
    **row("b", "S", [(717, 240, 30, 21), (752, 235, 31, 27), (788, 233, 29, 34), (822, 240, 29, 21)]),
    **row("b", "BF", [(494, 361, 48, 40), (546, 364, 47, 37), (597, 367, 48, 34), (650, 364, 48, 37)]),
    **row("b", "FA", [(740, 360, 40, 41), (783, 360, 36, 41)]),
    **row("b", "L", [(77, 424, 32, 44), (114, 416, 40, 52), (159, 414, 34, 53), (198, 411, 31, 56), (234, 420, 32, 48),
                     (271, 425, 38, 43), (314, 414, 31, 54), (350, 409, 32, 59), (388, 414, 32, 54)]),
    **row("b", "O", [(500, 412, 24, 56), (529, 412, 38, 55), (572, 412, 38, 56), (616, 412, 37, 56), (658, 412, 34, 53),
                     (697, 412, 40, 54), (741, 412, 30, 56), (776, 412, 52, 56), (833, 412, 50, 50)]),
    **row("b", "FS", [(131, 571, 47, 31)]),
    **row("b", "BO", [(168, 626, 47, 43), (220, 627, 41, 42), (266, 627, 36, 42), (307, 627, 30, 42), (342, 627, 27, 42)]),
    **row("b", "IS", [(110, 704, 40, 32), (154, 704, 32, 32), (191, 700, 28, 36), (224, 705, 39, 31)]),
    **row("b", "X", [(96, 759, 40, 44), (140, 750, 37, 53), (182, 759, 47, 44)]),
    **row("b", "V", [(180, 830, 33, 40), (218, 822, 28, 48), (251, 825, 38, 45)]),
    **row("b", "M", [(43, 899, 32, 38), (80, 898, 36, 39), (121, 897, 40, 40), (166, 898, 36, 39), (207, 899, 32, 38),
                     (244, 899, 37, 38), (286, 901, 40, 36), (331, 901, 40, 36), (393, 903, 32, 34)]),
    **row("s", "B", [(14, 139, 29, 32), (52, 138, 24, 40), (88, 139, 27, 36), (127, 140, 27, 39), (163, 140, 30, 36),
                     (201, 148, 40, 26), (250, 143, 32, 36), (288, 145, 40, 26), (338, 143, 31, 36)]),
    "H0": ("s", [292, 93, 16, 14]), "H1": ("s", [316, 94, 16, 16]),
    "G0": ("s", [293, 116, 13, 12]), "G1": ("s", [314, 116, 14, 14]),
    **row("s", "MH", [(25, 1362, 56, 20), (86, 1362, 52, 20), (145, 1362, 56, 20)]),
    **row("s", "MD", [(206, 1335, 40, 47), (251, 1345, 39, 37), (295, 1342, 39, 40)]),
    "HB": ("s", [62, 1512, 52, 37]),
}
# the swing round the star handle: 48 frames, once round (from the handle on his left, body level); every 6th used
SWING_ALL = [(8, 630, 84, 26), (97, 634, 84, 26), (186, 637, 84, 28), (275, 637, 81, 38), (4, 683, 80, 42),
             (89, 683, 78, 47), (172, 683, 75, 51), (252, 683, 61, 68), (318, 683, 58, 71), (18, 761, 54, 75),
             (77, 761, 47, 80), (129, 761, 43, 83), (177, 761, 38, 85), (220, 761, 28, 88), (253, 761, 26, 88),
             (284, 761, 33, 85), (322, 761, 37, 84), (20, 858, 42, 82), (67, 858, 59, 70), (131, 858, 66, 63),
             (202, 858, 70, 59), (277, 859, 81, 41), (15, 967, 84, 31), (104, 967, 84, 26), (193, 963, 84, 26),
             (282, 948, 81, 36), (8, 1040, 78, 45), (91, 1019, 61, 66), (157, 1016, 58, 69), (220, 1012, 54, 73),
             (279, 1007, 47, 78), (331, 1002, 38, 83), (13, 1101, 34, 84), (52, 1099, 28, 86), (85, 1099, 26, 86),
             (116, 1099, 26, 86), (147, 1099, 26, 86), (178, 1102, 33, 83), (214, 1103, 37, 82), (256, 1108, 46, 77),
             (306, 1121, 63, 64), (42, 1193, 59, 68), (106, 1200, 66, 61), (177, 1204, 70, 57), (252, 1212, 76, 49),
             (56, 1271, 79, 45), (140, 1276, 81, 40), (226, 1280, 82, 36)]
B.update(row("s", "SW", SWING_ALL[::6]))
HANDLE = ["#0048fc", "#00b4fc", "#d80000", "#480000"]  # the star handle's ball (blue, or red when it's pulled)

# ---------------------------------------------------------------- the working copy
LABELS, OBJECTS = {}, {}
for _k, _im in SHEETS.items():
    _bg = np.all(np.array(_im) == BG, axis=2)
    LABELS[_k], _ = ndimage.label(~_bg, structure=np.ones((3, 3)))
    OBJECTS[_k] = ndimage.find_objects(LABELS[_k])


def frame_pixels(sheet, rect):
    """The pixels of the blobs lying wholly inside the rect (a neighbour, a label or a section line reaching in is left
    out)."""
    x, y, w, h = rect
    lab_img, objs = LABELS[sheet], OBJECTS[sheet]
    inside = set()
    for lab in np.unique(lab_img[y:y + h, x:x + w]):
        if lab == 0:
            continue
        sl = objs[lab - 1]
        if sl[0].start >= y and sl[0].stop <= y + h and sl[1].start >= x and sl[1].stop <= x + w:
            inside.add(lab)
    ys, xs = np.nonzero(np.isin(lab_img[y:y + h, x:x + w], list(inside)))
    if not len(xs) or xs.min() != 0 or ys.min() != 0 or xs.max() != w - 1 or ys.max() != h - 1:
        raise SystemExit(f"ristar: {sheet} {rect} isn't the tight box of whole drawings")
    return [(x + a, y + b) for a, b in zip(xs, ys)]


def source_sheet():
    """Each frame's pixels, copied exactly, in a cell of its own (shelves 512 wide). Returns {name: rect in the copy}."""
    cells, x, y, shelf = {}, 2, 2, 0
    for name, (sheet, rect) in B.items():
        w, h = rect[2], rect[3]
        if x + w + 2 > 512:
            x, y, shelf = 2, y + shelf + 3, 0
        cells[name] = (sheet, frame_pixels(sheet, rect), rect, [x, y, w, h])
        x += w + 3
        shelf = max(shelf, h)
    out = Image.new("RGB", (512, y + shelf + 2), BG)
    for sheet, pts, (sx, sy, _, _), (cx, cy, _, _) in cells.values():
        src = SHEETS[sheet]
        for a, b in pts:
            out.putpixel((cx + a - sx, cy + b - sy), src.getpixel((a, b)))
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return {name: c[3] for name, c in cells.items()}, out


R, COPY = source_sheet()


def f(*names):
    return [R[n] for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)


def feet(name):
    """A frame placed by its bottom (standing on the ground, Sonic's feet line 20 px below the centre) in a "center"
    animation: an anchor box whose middle is 20 px above the frame's bottom."""
    x, y, w, h = R[name]
    return {"rect": R[name], "anchor_box": [x + w // 2 - 1, y + h - 21, 2, 2]}


def turned(name, rotate=0, flip=False):
    fr = {"rect": R[name]}
    if rotate:
        fr["rotate"] = rotate
    if flip:
        fr["flip"] = True
    return fr


def handle_box(name):
    """A swing frame placed by its star handle's ball (the pivot: drawn at his grip)."""
    x, y, w, h = R[name]
    pts = [(a, b) for b in range(y, y + h) for a in range(x, x + w)
           if "#%02x%02x%02x" % COPY.getpixel((a, b)) in HANDLE]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if not pts or max(xs) - min(xs) > 9 or max(ys) - min(ys) > 9:
        raise SystemExit(f"ristar: {name}: no single handle ball")
    cx, cy = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
    return {"rect": R[name], "anchor_box": [cx - 1, cy - 1, 2, 2]}


# ---------------------------------------------------------------- animations
IDLE = f("F0", "F1", "F2", "F3", "F4", "F3", "F2", "F1")
WALK = f("W0", "W1", "W2", "W3", "W4", "W5", "W6", "W7")
SPIN = f("S0", "S1", "S2", "S3")  # his own Spin/Roll (his jump and roll)
BALANCE = f("BF0", "BF1", "BF2", "BF3")

ANIMS = {
    "Stopped": {"frames": f("M0")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": IDLE, "loop": 0, "align": True},  # the Flora idle
    "Looking Up": {"frames": f("J4")},
    "Looking Down": {"frames": f("IS3")},  # squatting (Ice Slip)
    "Walking": {"frames": WALK, "align": True},
    "Running": {"frames": WALK, "align": True},  # (no run on the sheet: the walk, faster)
    "Skidding": {"frames": f("IS0")},
    "Super Peel Out": {"frames": WALK, "align": True},
    "Spin Dash": C(SPIN),
    "Jumping": C(SPIN),
    "Bouncing": C(f("BO0")),  # springs: the Bounce row, arms out
    "Hurt": C(f("X0")),
    "Dying": C(f("X1")),
    "Drowning": C(f("X2")),
    "Fan Rotate": C(f("BO0", "BO1", "BO2", "BO3", "BO4")),
    "Breathing": C(f("M8")),
    "Pushing": {"frames": f("W5", "W6"), "align": True},
    "Flailing 1": {"frames": BALANCE, "align": True},
    "Flailing 2": {"frames": BALANCE, "align": True},
    "Hanging": C(f("O0")),
    "Clinging On": C(f("O0")),
    "Corkscrew H": {"frames": SPIN},
    "Water Slide": C(f("FS0")),
    "Continue": {"frames": IDLE, "align": True},
    "Continue Up": {"frames": f("V1")},
    "Super Transform": {"frames": f("V1")},
}
S2_ONLY = {
    "Bored!": {"frames": f("BI0", "BI1", "BI2", "BI3"), "loop": 0, "align": True},
    "Flailing 3": {"frames": BALANCE, "align": True},
    "Grabbed": C(f("X0")),
    "Twirl H": {"frames": SPIN, "rot": 2},
}
CD_ONLY = {name: {"frames": WALK} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# Slot 41 "Grab" (the code picks the frame; see the docstring and tools/star_grab.py): per aim class (0 forward,
# 1 forward-up, 2 up, 3 forward-down, 4 down)
GROUND_BODY = ["B0", "B0", "B2", "B0", "B0"]
AIR_BODY = ["B1", "B1", "B3", "B4", "B4"]
PULL_BODY = ["B7", "B8", "B8", "B7", "B7"]
# the Meteor Strike: the level row (flying right) and the diving row (down-right), turned by quarter turns (clockwise)
METEOR = [("MH", 0), ("MD", 270), ("MH", 270), ("MD", 0), ("MH", 90)]
GRAB = ([feet(n) for n in GROUND_BODY] + [{"rect": R[n]} for n in AIR_BODY] + [{"rect": R[n]} for n in PULL_BODY]
        + [{"rect": R["HB"]}]
        + [turned(f"{row_}{k}", rot) for row_, rot in METEOR for k in range(3)])
# Slot 43 "Hands": absolute directions 0 right, 1 up-right, 2 up, 3 up-left, 4 left, 5 down-left, 6 down, 7 down-right
# (drawn facing right), open then gripping
HAND_TURNS = [(0, 0, False), (1, 0, False), (0, 270, False), (1, 0, True), (0, 0, True), (1, 180, False), (0, 90, False),
              (1, 90, False)]
HANDS = [turned(("H", "G")[g] + str(k), rot, flip) for g in (0, 1) for k, rot, flip in HAND_TURNS]
HANG = f(*[f"L{k}" for k in range(9)], *[f"O{k}" for k in range(9)])
APPENDED = {
    "41": {"name": "Grab", "frames": GRAB, "anchor": "center", "speed": 0},
    "42": {"name": "Hang", "frames": HANG + [handle_box(f"SW{k}") for k in range(8)], "anchor": "center", "speed": 0},
    "43": {"name": "Hands", "frames": HANDS, "anchor": "center", "speed": 0},
}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
_S = R["M0"]
HEAD = [_S[0] + 8, _S[1] + 2, 16, 16]  # the standing frame's face (the life icon)
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("RISTAR")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1], 16, 14], "trim": False},
    # his star head on the game's own board, at 1x
    "sign_face": board_face([_S[0], _S[1], _S[2], 22]),
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": R["M0"], "remap": PLUS_128},
    "end_pose_1": {"rect": R["V1"], "remap": PLUS_128},  # Victory 1
    "end_pose_2": {"rect": R["V2"], "remap": PLUS_128},
    "end_pose_3": {"rect": R["V0"], "remap": PLUS_128},
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("V0", "V1", "V2", "F1", "F2", "M0"), 1)},
}


# ---------------------------------------------------------------- colours
# All 15 of his colours exact: black in Sonic's slot 1, the other 14 in his own slots 74-87 (the most used first)
def hexof(rgb):
    return "#%02x%02x%02x" % rgb


_COUNTS = {}
for _n, _rgb in COPY.getcolors(1 << 16):
    if hexof(_rgb) not in BACKGROUND and hexof(_rgb) != "#000000":
        _COUNTS[hexof(_rgb)] = _n
for _im in SHEETS.values():  # (every colour of the sheets, used or not, so none is ever merged)
    for _n, _rgb in _im.getcolors(1 << 16):
        if hexof(_rgb) not in BACKGROUND and hexof(_rgb) != "#000000":
            _COUNTS.setdefault(hexof(_rgb), 0)
if len(_COUNTS) > 22:
    raise SystemExit(f"ristar: {len(_COUNTS)} colours, more than slots 74-95")
PALETTE = {str(74 + k): c for k, c in enumerate(sorted(_COUNTS, key=lambda c: (-_COUNTS[c], c)))}
COLOURS = {"#000000": 1, **{c: int(s) for s, c in PALETTE.items()}}
CREDIT = ("Ristar sprites compiled by Drshnaps (drshnaps.com), ripped by Jermungandr (The Spriters Resource, assets 12659 "
          "and 12660); Ristar (c) Sega")

# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose" the pose
# looped): Victory 1
S3K_VICTORY = {"frames": f("V0", "V1", "V2"), "pose": 1}


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
                              "animations": {"Special Stage": C(SPIN)}}]
        cfg["ui"] = [{"name": f"{NAME}_UI", "manifest": f"{NAME}_ui.json", "elements": ELEMENTS,
                      "out": f"build/{NAME}_UI.gif"},
                     {"name": f"{NAME}_Ending", "manifest": f"{NAME}_ending.json", "elements": ENDING,
                      "out": f"build/{NAME}_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "ristar.json"), ("Sonic2", "ristar_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("palette:", PALETTE)
