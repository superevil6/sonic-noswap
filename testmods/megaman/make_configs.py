#!/usr/bin/env python3
"""Writes Mega Man's sheet2ani configs (megaman.json for Sonic 1, megaman_s2.json for Sonic 2; CD's and S3&K's come from
the Sonic 2 one).

Mega Man (Mega Man 7, SNES), a CROSSOVER extra (extras.py "crossover": a separate download only, never in the
all-in-one; memory crossover-characters.md). His number (file "Extra<n>", build ID 6 + n) is his place in
tools/extras.py, read from there. Base character Sonic.
Sheet: testmods/megaman/MegaMan.png (1012x1458), ripped by Mister Man for The Spriters Resource (see SOURCE.txt). Its
footer: "Mega Man from Mega Man 7 (SNES) ripped by Mister Man. Please do not steal. Only for tSR." Mega Man (c) Capcom.

The sheet: a magenta page (#b440b4) with every sprite in a darker cell (#841584, shaded #640664 / #470047); all four
are background. Sections labelled in white. Every sprite faces LEFT (the buster's muzzle flash is on the left of the
Fire frames), so the working copy holds each frame mirrored (a mirror: the faithful art rule allows it). Rows used
(sheet coordinates of each frame's tight box, B below):
     38  Teleport (TP1-TP6: the beam, the drop landing, him)          46  Idle, Talk, Look Around (LOOK1-5), Blink
    119  Inch, Run (RUN1-10), Jump (J1-J6: "play in reverse for fall")
    209  Slide (SL1-SL3, SLEND getting up), Item Get (ITEM), Fire (F1-F4)
    299  Fire Inch, Fire Run (FR1-FR10), Fire Jump (FJ1-FJ6)
    391  Charge Shot (CS1-CS5)                                         569  Hit (HIT1-HIT5)
    675  Stun (STUN1-4)                                                915  Posing (POSE1-POSE6)
    994  the palettes section: Mega Buster, Charge 1, Charge 2A, Charge 2B (his idle in each: CHARGE_PALETTES maps his
         own colours to the charge flash colours, a runtime palette effect: the art files keep his own)
Not used: Talk, Climb, Proto Shield, Slash Claw, Shoot, the truck and helmet scenes, Frozen / Burning / Slime, the
ending walk.

Size: he stands 40 px tall (Idle), Sonic's height. Not scaled.

Abilities (tools/abilities.py, his entry; wired in abilities.py, build_soniccd.py and the DLL):
  - Y: Mega Buster, a real projectile (abilities.py "shot", motion "straight"): S3&K's Lightning Shield spark at half
    size (as Gamma's; the sheet's own muzzle flash is part of the Fire frames, not a loose drawing). 3 out at once.
    Pose: slots 43 / 44 (the Fire / Fire Jump frames).
  - Hold Y, let go: the Charge Shot ("shot2", "input" "charge": fired on letting go of a full charge), passing through
    what it hits ("pierce"). Art: the sheet's own teleport drops (TP2 / TP3) turned a quarter (rot90), so the round end
    leads and the tail trails. While charging he flashes his CHARGE_PALETTES colours.
  - Down + jump on the ground: the Slide (abilities.py "slide", slot 42: SL1-SL3), replacing the Spin Dash.
  - No mid-air move. He never curls into a ball (extras.py "no_roll", as Gamma): his jump is J5.

Colours: the 22 most used colours of the built art (and the charge shot's) are exact in his own slots 74-95; the rest go
to their nearest slot (MERGED, printed with pixel counts). The "MEGA MAN" HUD tag isn't on the sheet: our lettering in
the HUD font the other extras use.
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

ME = next(e for e in EXTRAS if e["art"].name == HERE.name)
NAME = ME["file"]  # "Extra<n>"

SHEET = HERE / "MegaMan.png"
SOURCE = "build/source.png"  # working copy: each used frame's pixels, MIRRORED (the sheet faces left), in a cell of its own
BACKGROUND = ["#b440b4", "#841584", "#640664", "#470047"]
BGS = [(180, 64, 180), (132, 21, 132), (100, 6, 100), (71, 0, 71)]
BG = BGS[0]
SRC = Image.open(SHEET).convert("RGB")


def row(names, xs, y, sizes):
    return {n: [x, y + dy, w, h] for n, x, (dy, w, h) in zip(names, xs, sizes)}


# ---------------------------------------------------------------- frames: name -> [x, y, w, h], the tight box on the sheet
B = {
    "TP1": [25, 38, 8, 48], "TP2": [71, 46, 16, 40], "TP3": [117, 54, 25, 32], "TP4": [164, 60, 30, 26],
    "TP5": [213, 68, 32, 18], "TP6": [265, 52, 34, 34],
    "IDLE": [321, 46, 34, 40],
    **{f"LOOK{k + 1}": [x, 46, 34, 40] for k, x in enumerate([433, 483, 533, 583, 633])},
    **{f"BLINK{k + 1}": [x, 46, 34, 40] for k, x in enumerate([689, 739, 789])},
    "INCH": [16, 120, 33, 40],
    "RUN1": [70, 123, 26, 37], "RUN2": [119, 122, 33, 37], "RUN3": [165, 120, 44, 37], "RUN4": [219, 121, 34, 36],
    "RUN5": [270, 123, 27, 37], "RUN6": [320, 125, 25, 35], "RUN7": [370, 123, 26, 37], "RUN8": [415, 120, 37, 35],
    "RUN9": [470, 123, 28, 37], "RUN10": [520, 125, 25, 35],
    "J1": [576, 123, 26, 37], "J2": [629, 121, 26, 40], "J3": [680, 121, 30, 48], "J4": [732, 120, 29, 51],
    "J5": [783, 119, 30, 54], "J6": [832, 119, 31, 53],
    "SL1": [10, 231, 44, 28], "SL2": [68, 231, 48, 28], "SL3": [126, 231, 44, 28], "SLEND": [186, 222, 29, 36],
    "ITEM": [560, 209, 39, 49],
    "F1": [618, 220, 45, 38], "F2": [675, 220, 46, 38], "F3": [732, 220, 47, 38], "F4": [792, 220, 45, 38],
    "FJ4": [843, 300, 38, 51], "FJ5": [902, 299, 39, 54],
    "CS2": [127, 391, 44, 39],
    "HIT1": [328, 577, 32, 43], "HIT4": [477, 573, 36, 48], "HIT5": [527, 573, 36, 48],
    "STUN1": [16, 675, 32, 43],
    "POSE2": [319, 920, 34, 38], "POSE3": [375, 920, 37, 38], "POSE4": [435, 919, 34, 39], "POSE5": [484, 919, 43, 39],
    "POSE6": [551, 919, 41, 39],
}
# The palettes section: his idle in the Mega Buster (normal) palette and the charge palettes, pixel for pixel alike
PALETTE_ROW = {"normal": [11, 994, 34, 40], "charge1": [131, 994, 34, 40], "charge2a": [251, 994, 34, 40],
               "charge2b": [371, 994, 34, 40]}
# The Charge Shot's art (abilities.py "shot2"; build_s3k_shot.py cuts it from the sheet itself): the teleport drops
CHARGE_SHOT = [[71, 46, 16, 40], [117, 54, 25, 32]]

# ---------------------------------------------------------------- the working copy
_bg = np.zeros(SRC.size[::-1], bool)
for _c in BGS:
    _bg |= np.all(np.array(SRC) == _c, axis=2)
LABELS, _ = ndimage.label(~_bg, structure=np.ones((3, 3)))
OBJECTS = ndimage.find_objects(LABELS)


def frame_pixels(rect):
    """The pixels of the blobs lying wholly inside the rect (a neighbour reaching into it is left out)."""
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
        raise SystemExit(f"megaman: {rect} isn't the tight box of whole drawings")
    return [(x + a, y + b) for a, b in zip(xs, ys)]


def source_sheet():
    """Each frame's pixels, copied exactly and mirrored (he faces right, as the engines expect), in a cell of its own
    (shelves 256 wide). Returns {name: rect in the copy}."""
    cells, x, y, shelf = {}, 2, 2, 0
    for name, rect in B.items():
        w, h = rect[2], rect[3]
        if x + w + 2 > 256:
            x, y, shelf = 2, y + shelf + 3, 0
        cells[name] = (frame_pixels(rect), rect, [x, y, w, h])
        x += w + 3
        shelf = max(shelf, h)
    out = Image.new("RGB", (256, y + shelf + 2), BG)
    for pts, (sx, sy, sw, _), (cx, cy, _, _) in cells.values():
        for a, b in pts:
            out.putpixel((cx + (sw - 1 - (a - sx)), cy + b - sy), SRC.getpixel((a, b)))
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return {name: c[2] for name, c in cells.items()}


R = source_sheet()


def f(*names):
    return [R[n] for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)

# ---------------------------------------------------------------- animations
RUN = f(*[f"RUN{k}" for k in range(1, 11)])
JUMP = f("J5")  # no ball: the jump's arms-up frame (as Gamma's and Omega's jump poses)
WAIT = f("IDLE", "BLINK1", "BLINK2", "BLINK3", "IDLE", "LOOK1", "LOOK2", "LOOK3", "LOOK4", "LOOK5")
LOOK = f("LOOK1", "LOOK2", "LOOK3", "LOOK4", "LOOK5")

ANIMS = {
    "Stopped": {"frames": f("IDLE")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": WAIT, "loop": 0, "align": True},
    "Looking Up": {"frames": f("ITEM")},  # no look-up art: Item Get, reaching up
    "Looking Down": {"frames": f("SLEND")},  # the slide's crouch (getting up)
    "Walking": {"frames": RUN, "rot": 2, "align": True},  # (no walk: the run)
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("INCH")},  # a step, braced
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Spin Dash": {"frames": f("SLEND")},  # PLACEHOLDER: he never curls up (down + jump is his Slide)
    "Jumping": C(JUMP),
    "Bouncing": C(f("J6")),  # springs: rising, arms up
    "Hurt": C(f("HIT5")),  # knocked back
    "Dying": C(f("HIT4", "HIT5")),  # the Hit row's loop: the pale flash and back
    "Drowning": C(f("HIT1")),
    "Fan Rotate": C(LOOK),
    "Breathing": C(f("J6")),
    "Pushing": {"frames": f("INCH")},
    "Flailing 1": {"frames": f("HIT5")},
    "Flailing 2": {"frames": f("HIT5")},
    "Hanging": C(f("J6")),  # arms up
    "Clinging On": C(f("J6")),
    "Corkscrew H": {"frames": RUN},
    "Water Slide": C(f("SL1")),  # the slide
    "Continue": {"frames": WAIT, "align": True},
    "Continue Up": {"frames": f("ITEM")},
    "Super Transform": {"frames": f("ITEM")},
}
S2_ONLY = {
    "Bored!": {"frames": LOOK + f("IDLE"), "loop": 0},
    "Flailing 3": {"frames": f("HIT5")},
    "Grabbed": C(f("HIT1")),
    "Twirl H": {"frames": RUN, "rot": 2},
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# Slot 42: the Slide (abilities.py "slide"; not an attack). Sonic 1/2: the .ani's hitbox 3, the low one (top 2 px above
# his centre, feet where they are: [-10, -2, 10, 20]), so he slides under low gaps; CD's .ani has no such box (its own
# standing one, "cd_hitbox"); S3&K: the standing boxes ("s3k_boxes"), on the ground.
# Slots 43 / 44: the Mega Buster's pose (the shot shows their last frame; abilities.py melee_reach has as many
# entries): the arm coming up, then the buster out (F4, no flash: the shot is the flash); in the air Fire Jump's
APPENDED = {
    "42": {"name": "Slide", "frames": f("SL1", "SL2", "SL3", "SLEND"), "speed": 0, "hitbox": 3, "cd_hitbox": 0,
           "s3k_boxes": "idle"},
    "43": {"name": "Mega Buster", "frames": f("F1", "F4"), "speed": 0},
    "44": {"name": "Mega Buster Air", "frames": f("FJ4", "FJ5"), "anchor": "center", "speed": 0},
}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
IDLE = R["IDLE"]
# his head in the (mirrored) idle frame: columns 12-30, rows 0-16. The HUD icon: 16x16 of it (its outline's left column
# and bottom row off)
HEAD = [IDLE[0] + 13, IDLE[1], 16, 16]
FACE = [IDLE[0] + 12, IDLE[1], 19, 17]
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("MEGA MAN")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1] + 1, 16, 14], "trim": False},
    # his head on the game's own board, enlarged to fill it (the user's signpost exception: tools/sign_face.py)
    "sign_face": board_face(FACE, 1.4),
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the HUD head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": R["IDLE"], "remap": PLUS_128},
    "end_pose_1": {"rect": R["ITEM"], "remap": PLUS_128},  # Item Get, arm raised
    "end_pose_2": {"rect": R["POSE6"], "remap": PLUS_128},  # the Posing row's last: pointing
    "end_pose_3": {"rect": R["F4"], "remap": PLUS_128},  # the Mega Buster
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("POSE2", "POSE3", "POSE4", "POSE5", "POSE6", "IDLE"), 1)},
}


# ---------------------------------------------------------------- colours
def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def hexof(rgb):
    return "#%02x%02x%02x" % rgb


def colours():
    """The Charge Shot's colours and the most used of the built art (22 in all) in his own slots 74-95, exact; black in
    Sonic's slot 1; every other sheet colour in its nearest slot (MERGED: those the art uses, with pixel counts)."""
    counts = {}
    ims = [Image.open(HERE / SOURCE).convert("RGB")] + [SRC.crop((x, y, x + w, y + h)) for x, y, w, h in CHARGE_SHOT]
    for im in ims:
        for n, rgb in im.getcolors(1 << 16):
            c = hexof(rgb)
            if c not in BACKGROUND and c != "#000000":
                counts[c] = counts.get(c, 0) + n
    shot = {hexof(rgb) for x, y, w, h in CHARGE_SHOT for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(256)}
    top = sorted(shot - set(BACKGROUND))
    for c in sorted(counts, key=lambda c: (-counts[c], c)):
        if len(top) < 22 and c not in top:
            top.append(c)
    palette = {str(74 + k): c for k, c in enumerate(sorted(top))}
    keys = {"#000000": 1, **{c: int(s) for s, c in palette.items()}}
    near = {hexrgb(c): int(s) for s, c in palette.items()}
    out = dict(keys)
    for _, rgb in SRC.getcolors(1 << 16):
        c = hexof(rgb)
        if c not in out and c not in BACKGROUND:
            out[c] = near[min(near, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))]
    merged = {c: (out[c], n) for c, n in counts.items() if c not in keys}
    return palette, out, merged


PALETTE, COLOURS, MERGED = colours()


def charge_palettes():
    """{palette name: {own slot: "#rrggbb"}}: each own slot's colour in the charge palettes, read pixel for pixel from the
    palettes section (his idle in the normal palette against the same idle in each charge palette). Only slots whose
    colour differs; a slot not in the idle keeps its colour."""
    nx, ny, w, h = PALETTE_ROW["normal"]
    normal = SRC.crop((nx, ny, nx + w, ny + h))
    out = {}
    for name in ("charge1", "charge2a", "charge2b"):
        x, y, _, _ = PALETTE_ROW[name]
        other = SRC.crop((x, y, x + w, y + h))
        m = {}
        for yy in range(h):
            for xx in range(w):
                a, b = normal.getpixel((xx, yy)), other.getpixel((xx, yy))
                if a in BGS or b in BGS:
                    continue
                slot = COLOURS.get(hexof(a))
                if slot and slot >= 74 and hexof(b) != PALETTE[str(slot)]:
                    m.setdefault(str(slot), hexof(b))
        out[name] = dict(sorted(m.items(), key=lambda kv: int(kv[0])))
    return out


CHARGE_PALETTES = charge_palettes()
CREDIT = ("Mega Man (Mega Man 7, SNES) ripped by Mister Man, The Spriters Resource - "
          "https://www.spriters-resource.com/snes/mm7/asset/31570/ (Mega Man (c) Capcom)")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held): the sheet's Posing row
S3K_VICTORY = {"frames": f("POSE2", "POSE3", "POSE4", "POSE5", "POSE6")}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": NAME, "credit": CREDIT,
           "source": SOURCE, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "charge_palettes": CHARGE_PALETTES,  # (read by abilities.py: the Charge Shot's flash)
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        # no ball: the special stage turns his jump pose (as Gamma's)
        cfg["extra_anis"] = [{"name": f"{NAME}SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(JUMP)}}]
        cfg["ui"] = [{"name": f"{NAME}_UI", "manifest": f"{NAME}_ui.json", "elements": ELEMENTS,
                      "out": f"build/{NAME}_UI.gif"},
                     {"name": f"{NAME}_Ending", "manifest": f"{NAME}_ending.json", "elements": ENDING,
                      "out": f"build/{NAME}_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "megaman.json"), ("Sonic2", "megaman_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("palette:", PALETTE)
    print("charge palettes:", CHARGE_PALETTES)
    print("merged colours (colour: slot, pixels):",
          ", ".join(f"{c}: {s} x{n}" for c, (s, n) in sorted(MERGED.items(), key=lambda kv: -kv[1][1])))
