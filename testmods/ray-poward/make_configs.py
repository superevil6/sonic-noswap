#!/usr/bin/env python3
"""Writes Ray Poward's sheet2ani configs (raypoward.json for Sonic 1, raypoward_s2.json for Sonic 2; CD's and S3&K's come
from the Sonic 2 one).

Ray Poward, from Contra: Hard Corps (Sega Genesis). A CROSSOVER extra (extras.py "crossover": a separate download only,
never in the all-in-one). NOT Ray the Flying Squirrel (testmods/ray): everything here is "ray-poward" / "Ray Poward".
Base character Sonic. Its extras.py position gives its file name (NAME below, looked up, not hard-coded).

Sheet: testmods/ray-contra/RayContra.png (985x631), ripped by Eckles D. Fum (contributor Marksiks), The Spriters Resource
(see SOURCE.txt). Printed on it: "No need for credits but don't claim as your own" (credited anyway). Green (#00ff00)
section panels on a blue (#0000ff) page, black section lines and labels; every sprite faces right. Genesis art, used
at 1x (he stands 40 px, Sonic's height).
Sections (the sheet's own labels) and the frame names used here:
  Idle                I0 standing, gun level; I1-I3 gun raised upright (shifting)
  Running             R0-R5, gun level
  Running while Aiming  U0-U5 gun up-forward, D0-D5 gun down-forward (not used: the aim pose shows standing / in the air)
  Aiming              A0 up-forward, A1 straight up, A2 down-forward, A3 straight down
  Jumping             J0-J3: the somersault, one drawing in four quarter turns (the sheet's own four)
  Defeated            X0 hit, X1-X4 the tumble (quarter turns), X5 lying flat
  Hanging             H0-H8 (arms up; H4-H8 hanging and firing)
  Climbing            C0-C7 clinging and firing, C8-C10 climbing (arms up, the wall on his right)
  Duck/Slide          P0 prone, P1 the slide (prone, a knee up), P2 kneeling, gun level
  Slopes              S0-S3 (running on slopes)
  Misc                PORTRAIT (the boxed face), FACE (the big head), FRONT (standing, facing us); the big pose (over
                      100 px) isn't used
  weapons             BULLET: weapon A's standard shot (6x6, the projectile: abilities.py "shot"); its muzzle flashes,
                      the laser, B, C and D aren't used

Abilities (tools/abilities.py, the user's design 2026-09-29; wired there, in build_soniccd.py and the DLL):
  - Y: Run-and-gun: weapon A's bullet (a projectile, aimed with the d-pad: 5 ways on the ground, 8 in the air; HOLD Y
    for autofire). Slots 43 / 44 (CD 46) are its aim poses, one frame per aim (the shot's "aim_pose"): 0 level (I0), 1
    up-forward (A0), 2 up (A1), 3 down-forward (A2), 4 down (A3).
  - Jump: the somersault (Jumping), no generic ball; not an attack (abilities.py no_stomp). Roll: his slide (P1, slot 49).
  - Slide (down + jump on the ground, instead of the Spin Dash): slot 42 "Slide" (CD 47), the code picks the frame: 0 the
    slide (P1), 1 prone (P0), 2 kneeling (P2).
  - Wall climb: Trip's / Sticks' wall_cling, slot 47 "Wall Cling" (CD 48): C8-C10 mirrored (drawn with the wall on his left).
  - No mid-air move.

Frames are whole drawings: build/source.png is a working copy holding each used frame's pixels (the blobs of the sheet
inside its box, copied exactly) in a cell of its own, so a crop never catches a neighbour or a section line. Nothing is
redrawn, recoloured or resized. The HUD tag "POWARD" is our lettering in the HUD font the other extras use (the sheet
has none); the life icon / 1-UP are crops of FRONT's head; the signpost is the Misc portrait (inside its frame) on the
game's own board, at 1x. Colours: see PALETTE.
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
SHEET = HERE.parent / "ray-contra" / "RayContra.png"
SOURCE = "build/source.png"  # working copy: each used frame's blobs in a cell of its own (source_sheet)
BACKGROUND = ["#00ff00"]
BG = (0, 255, 0)
SHEET_BG = [(0, 255, 0), (0, 0, 255), (0, 128, 128)]  # the panels, the page, the text box
SRC = Image.open(SHEET).convert("RGB")


def row(prefix, rects):
    return {f"{prefix}{k}": list(r) for k, r in enumerate(rects)}


# ---------------------------------------------------------------- frames: name -> [x, y, w, h] (tight boxes on the sheet)
B = {
    **row("I", [(1, 36, 40, 40), (42, 21, 25, 55), (68, 22, 24, 54), (93, 23, 24, 53)]),
    **row("R", [(126, 29, 38, 40), (165, 29, 39, 40), (205, 30, 38, 39), (244, 29, 39, 40), (283, 29, 39, 40),
                (323, 30, 46, 39)]),
    **row("A", [(765, 30, 31, 47), (797, 22, 29, 55), (827, 36, 30, 41), (858, 37, 29, 40)]),
    **row("J", [(909, 32, 24, 20), (934, 28, 20, 24), (930, 53, 24, 20), (909, 53, 20, 24)]),
    **row("X", [(4, 106, 30, 38), (35, 112, 23, 32), (59, 121, 32, 23), (92, 112, 23, 32), (116, 121, 32, 23),
                (149, 131, 48, 13)]),
    **row("H", [(206, 110, 28, 48), (235, 110, 22, 48), (258, 113, 26, 45), (285, 110, 21, 48), (307, 110, 39, 48),
                (347, 110, 29, 48), (377, 102, 29, 56), (407, 110, 30, 48), (438, 110, 30, 48)]),
    **row("C", [(481, 118, 48, 45), (530, 116, 40, 47), (571, 106, 24, 57), (596, 116, 27, 47), (624, 118, 38, 45),
                (663, 118, 27, 45), (691, 118, 27, 45), (719, 118, 38, 45), (758, 115, 16, 48), (775, 122, 15, 41),
                (791, 117, 16, 46)]),
    **row("P", [(54, 176, 53, 16), (108, 168, 48, 24), (157, 161, 40, 31)]),
    **row("S", [(211, 197, 40, 43), (252, 198, 40, 42), (218, 241, 40, 35), (259, 241, 40, 34)]),
    "PORTRAIT": [310, 200, 30, 30], "FRONT": [315, 236, 27, 40],
}
BULLET = [122, 324, 6, 6]  # weapon A's standard shot (abilities.py "shot" art, cut from the sheet itself)

# ---------------------------------------------------------------- the working copy
_BGMASK = np.zeros(SRC.size[::-1], bool)
for _c in SHEET_BG:
    _BGMASK |= np.all(np.array(SRC) == _c, axis=2)
LABELS, _ = ndimage.label(~_BGMASK, structure=np.ones((3, 3)))
OBJECTS = ndimage.find_objects(LABELS)


def frame_pixels(rect):
    """The pixels of the blobs lying wholly inside the rect (a neighbour or a section line reaching in is left out)."""
    x, y, w, h = rect
    inside = set()
    for lab in np.unique(LABELS[y:y + h, x:x + w]):
        if lab == 0:
            continue
        sl = OBJECTS[lab - 1]
        if sl[0].start >= y and sl[0].stop <= y + h and sl[1].start >= x and sl[1].stop <= x + w:
            inside.add(lab)
    ys, xs = np.nonzero(np.isin(LABELS[y:y + h, x:x + w], list(inside)))
    if not len(xs) or xs.min() != 0 or ys.min() != 0 or xs.max() != w - 1 or ys.max() != h - 1:
        raise SystemExit(f"ray-poward: {rect} isn't the tight box of whole drawings")
    return [(x + a, y + b) for a, b in zip(xs, ys)]


def source_sheet():
    """Each frame's pixels, copied exactly, in a cell of its own (shelves 512 wide). Returns {name: rect in the copy}."""
    cells, x, y, shelf = {}, 2, 2, 0
    for name, rect in B.items():
        w, h = rect[2], rect[3]
        if x + w + 2 > 512:
            x, y, shelf = 2, y + shelf + 3, 0
        cells[name] = (frame_pixels(rect), rect, [x, y, w, h])
        x += w + 3
        shelf = max(shelf, h)
    out = Image.new("RGB", (512, y + shelf + 2), BG)
    for pts, (sx, sy, _, _), (cx, cy, _, _) in cells.values():
        for a, b in pts:
            out.putpixel((cx + a - sx, cy + b - sy), SRC.getpixel((a, b)))
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return {name: c[2] for name, c in cells.items()}


R = source_sheet()


def f(*names):
    return [R[n] for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)


def cling():
    """The wall cling (C8-C10, arms up). As drawn, his raised hand grips a wall on his LEFT (Hard Corps: he holds on
    with one hand and aims away from the wall); the engines draw the cling on a wall to the player's right, so the
    frames are mirrored (the user, 2026-09-29: he climbed backwards). The wall edge, his hand side (the left edge as
    drawn, the right once mirrored), 11 px right of the player's centre (Trip's and Sticks' wall), vertically
    centred: an anchor box whose middle is 11 px in from that edge (sheet2ani mirrors the box with the frame)."""
    out = []
    for n in ("C8", "C9", "C10"):
        x, y, w, h = R[n]
        out.append({"rect": R[n], "flip": True, "anchor_box": [x + 11 - 8, y + h // 2 - 8, 16, 16]})
    return out


# ---------------------------------------------------------------- animations
IDLE = f("I1", "I2", "I3", "I2")
RUN = f("R0", "R1", "R2", "R3", "R4", "R5")
FLIP = f("J0", "J1", "J2", "J3")  # the somersault (his jump and roll: no ball)
TUMBLE = f("X1", "X2", "X3", "X4")
ARMS_UP = f("H1", "H2")

ANIMS = {
    "Stopped": {"frames": f("I0")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": IDLE, "loop": 0, "align": True},  # gun raised upright
    "Looking Up": {"frames": f("A1")},  # aiming straight up
    "Looking Down": {"frames": f("P2")},  # kneeling
    "Walking": {"frames": RUN, "rot": 2, "align": True},  # (no walk on the sheet: the run)
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("S2")},  # the low slope run, leaning back
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Spin Dash": {"frames": f("P1")},  # PLACEHOLDER: the Slide replaces his Spin Dash (abilities.py "slide")
    "Jumping": C(FLIP),
    "Bouncing": C(f("H0")),  # springs: arms up
    "Hurt": C(f("X0")),  # a Defeated frame
    "Dying": C(TUMBLE),  # the Defeated tumble
    "Drowning": C(f("X1")),
    "Fan Rotate": C(TUMBLE),
    "Breathing": C(f("FRONT")),
    "Pushing": {"frames": f("S0"), "align": True},  # leaning in
    "Flailing 1": {"frames": ARMS_UP, "align": True},
    "Flailing 2": {"frames": ARMS_UP, "align": True},
    "Hanging": C(f("H3")),
    "Clinging On": C(f("H3")),
    "Corkscrew H": {"frames": FLIP},
    "Water Slide": C(f("P0")),  # prone
    "Continue": {"frames": IDLE, "align": True},
    "Continue Up": {"frames": f("H0")},
    "Super Transform": {"frames": f("FRONT")},
}
S2_ONLY = {
    "Bored!": {"frames": f("I1", "I2", "I3", "I2"), "loop": 0, "align": True},
    "Flailing 3": {"frames": ARMS_UP, "align": True},
    "Grabbed": C(f("X0")),
    "Twirl H": {"frames": FLIP, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# The aim poses (slots 43 / 44, CD 46): one frame per aim, the shot's "aim_pose" shows its aim's (0 level, 1 up-forward,
# 2 up, 3 down-forward, 4 down; aimed back he turns first). abilities.py's melee_reach has as many entries
AIM = f("I0", "A0", "A1", "A2", "A3")
APPENDED = {
    "42": {"name": "Slide", "frames": f("P1", "P0", "P2"), "speed": 0},  # the code picks the frame (slide, prone, kneel)
    "43": {"name": "Run and Gun", "frames": AIM, "speed": 0},
    "44": {"name": "Run and Gun Air", "frames": AIM, "anchor": "center", "speed": 0},
    "47": {"name": "Wall Cling", "frames": cling(), "anchor": "center", "speed": 20},  # on a wall to his right
    # no_stomp (the user, 2026-10-02): rolling is his slide, not the somersault (extras.py "roll"; the somersault stays his
    # jump, not an attack): the Duck/Slide section's slide (P1)
    "49": {"name": "Rolling", "frames": f("P1")},
}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
_F = R["FRONT"]
HEAD = [_F[0] + 5, _F[1], 16, 16]  # FRONT's head and shoulders (the life icon)
_P = R["PORTRAIT"]
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("POWARD")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1], 16, 14], "trim": False},
    # the Misc portrait (inside its frame line, from the sheet itself) on the game's own board, 1x: its bottom 24 rows
    "sign_face": board_face([_P[0] + 1, _P[1] + 1, _P[2] - 2, _P[3] - 2]),
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": R["I0"], "remap": PLUS_128},
    "end_pose_1": {"rect": R["A1"], "remap": PLUS_128},  # aiming up
    "end_pose_2": {"rect": R["FRONT"], "remap": PLUS_128},  # facing us
    "end_pose_3": {"rect": R["I1"], "remap": PLUS_128},  # gun raised
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("FRONT", "I1", "I2", "A0", "P2", "I0"), 1)},
}

# ---------------------------------------------------------------- colours
# His frames use the game's own 17-colour player palette (black is Sonic's slot 1): the other 16 exact in 74-89. The
# portrait (the signpost) adds its own shades; the bullet its reds. Each exact in a slot of its own while there's room
# (90-95), the rarest after that merged into their nearest slot (MERGED, printed with pixel counts).
PALETTE = {
    "74": "#484848", "75": "#686868", "76": "#b0b0b0", "77": "#f8f8f8",  # greys (the gun, armour, boots)
    "78": "#682000", "79": "#904800", "80": "#b04820", "81": "#d86820", "82": "#f89048", "83": "#f8b068",  # skin
    "84": "#f8d868", "85": "#484800", "86": "#906800",  # hair, the trousers
    "87": "#004868", "88": "#0090b0", "89": "#90d8f8",  # the shirt
}
KEY_COLOURS = {"#000000": 1, "#fcfc00": 15}


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def extra_slots():
    """The colours the built art uses beyond his 16 (the portrait's, the bullet's), the commonest first, into the free
    slots 90-95."""
    counts = {}
    ims = [Image.open(HERE / SOURCE).convert("RGB"), SRC.crop((BULLET[0], BULLET[1], BULLET[0] + BULLET[2],
                                                               BULLET[1] + BULLET[3]))]
    for im in ims:
        for n, rgb in im.getcolors(1 << 16):
            c = "#%02x%02x%02x" % rgb
            if c not in BACKGROUND and c not in PALETTE.values() and c not in KEY_COLOURS:
                counts[c] = counts.get(c, 0) + n
    return counts


_EXTRA = sorted(extra_slots().items(), key=lambda kv: -kv[1])
for _k, (_c, _n) in enumerate(_EXTRA[:6]):
    PALETTE[str(90 + _k)] = _c


def all_colours():
    """KEY_COLOURS and PALETTE, plus every other colour of the sheet in the slot of its nearest own colour. MERGED: those
    the built art uses, with pixel counts."""
    keys = {hexrgb(c): int(s) for s, c in PALETTE.items()}
    out = dict(KEY_COLOURS, **{c: int(s) for s, c in PALETTE.items()})
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            out[c] = keys[min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))]
    merged = {c: (out[c], n) for c, n in _EXTRA[6:]}
    return out, merged


COLOURS, MERGED = all_colours()
CREDIT = ("Ray Poward (Contra: Hard Corps) ripped by Eckles D. Fum, with Marksiks, The Spriters Resource - "
          "https://www.spriters-resource.com/sega_genesis/contrahc/asset/28048/ (Contra (c) Konami)")

# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose" the pose
# looped): standing, then the gun raised upright (his idle)
S3K_VICTORY = {"frames": f("I0", "I1", "I2", "I3", "I2"), "pose": 1}


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
                              "animations": {"Special Stage": C(FLIP)}}]  # the somersault
        cfg["ui"] = [{"name": f"{NAME}_UI", "manifest": f"{NAME}_ui.json", "elements": ELEMENTS,
                      "out": f"build/{NAME}_UI.gif"},
                     {"name": f"{NAME}_Ending", "manifest": f"{NAME}_ending.json", "elements": ENDING,
                      "out": f"build/{NAME}_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "raypoward.json"), ("Sonic2", "raypoward_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("own slots 90-95:", ", ".join(f"{c} x{n}" for c, n in _EXTRA[:6]))
    print("merged colours (colour: slot, pixels):",
          ", ".join(f"{c}: {s} x{n}" for c, (s, n) in sorted(MERGED.items(), key=lambda kv: -kv[1][1])))
