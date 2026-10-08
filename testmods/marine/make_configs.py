#!/usr/bin/env python3
"""Writes Marine the Raccoon's sheet2ani configs (marine.json for Sonic 1, marine_s2.json for Sonic 2; CD's and S3&K's
come from the Sonic 2 one).

Marine the Raccoon, extra 34 (file "Extra34", build ID 40), base character Sonic. Public (credit in mods/NoSwap/README.md).
Sheet: testmods/Marine.png (482x404), Sonic 3 style, by Nintendo_6444 (see SOURCE.txt). Its terms, printed on the
sheet: "Credit goes to Deebs, FireX, Vol, Frario, and Rathe Ethransu for Various things. And me (Nintendo_6444) for
making these. Just give credit."

The sheet: a blue-grey page (#95b1c8, the background; a faint portrait of her fills its right side), nothing
labelled. She faces right. Rows (y, sheet coordinates; the names are the ones used below):
    3  standing (S0), idle: tapping, blinking, arms folded (S1-S5); a kick and a green whirl (not used)
   39  the run (R1-R8)
   80  her ball (BALL), crouching (CROUCH), a pose, skidding (SKID), crawling, a kick, pointing (not used but these three)
  118  facing us (FRONT), arms flung out (FLAIL), pointing (POINT), a finger up (UP), jumping arms up (SPRING), hands
       to her face (FACE), carried by Tails (not used)
  157  lying (LIE), hunched, gazing up (HUNCH), falling (FALL), hurt (HURT), flat on the ground (not used), leaning in (LEAN)
  214  firing the electric blast (FIRE: the spark in her hand); 238 the blast flying (its spark, cut from its tail) and
       a small spark (the Electric Blast's two frames); a glove piece (not used)
  259  two more standing frames (not used)
  305  heads (not used), 353 faces (FACE1: the HUD icon and signpost), the palette swatches, a comparison with Sonic and
       Tails, a portrait (not used)

Size: she stands 33 px tall (S0), smaller than Sonic's 40 (Sticks' 32 was enlarged with the user's exception; Marine's
isn't). Not scaled.

Frames are whole drawings: build/source.png is a working copy holding each used frame's pixels (the blobs inside its box,
copied exactly) in a cell of its own, so a rect crop never catches a neighbour. Her jump ball is her one ball drawing
turned a quarter at a time (a rotation; the rule allows it).

Abilities (tools/abilities.py 40; the user's rework, 2026-09-29):
  - Y: Anchor Throw (tools/anchor_throw.py, all four games): she throws an anchor in an arc on a chain (the chain drawn at
    runtime); a wall or ceiling it bites into reels her in. Its pose is POINT (slot 41; CD 45), the anchor the user's own
    drawing (anchor_marine.png, slot 43; CD 46).
  - Water walk (tools/water_walk.py): the water's surface is ground for her; down dives. She never drowns.
  - No jump ability (the user's design; the sheet has no mid-air move of hers either: its kicks and whirl are melee).
  - Ball: her own.

Colours: her frames use more colours than the 22 own slots: the 22 most used are exact; the rest (near-blacks, a few
shades of a pixel or two) go to their nearest slot, the faithful-art rule's colour exception (MERGED, printed with pixel
counts); near-identical ones (three near-blacks) share one. Black is Sonic's slot 1. The "MARINE" HUD tag isn't on the sheet: our lettering in the HUD font the other
extras use.
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

SHEET = HERE.parent / "Marine.png"
SOURCE = "build/source.png"
BACKGROUND = ["#95b1c8"]
BG = (0x95, 0xB1, 0xC8)
SRC = Image.open(SHEET).convert("RGB")

B = {  # name -> [x, y, w, h] on the sheet: the tight box of the drawing's blobs
    **{f"S{k}": r for k, r in enumerate([[2, 3, 30, 33], [34, 3, 30, 33], [66, 3, 31, 33], [100, 3, 30, 33],
                                         [132, 4, 30, 32], [165, 2, 25, 34]])},
    **{f"R{k + 1}": r for k, r in enumerate([[2, 39, 35, 35], [41, 38, 34, 35], [78, 38, 29, 37], [110, 39, 34, 36],
                                             [147, 40, 36, 35], [184, 39, 33, 36], [219, 39, 31, 36],
                                             [252, 39, 33, 36]])},
    "BALL": [2, 84, 28, 28], "CROUCH": [35, 82, 25, 31], "SKID": [107, 80, 36, 33],
    "FRONT": [3, 118, 30, 38], "FLAIL": [36, 122, 33, 33], "POINT": [72, 122, 37, 33], "UP": [113, 121, 33, 33],
    "SPRING": [149, 115, 33, 46], "FACE": [186, 125, 29, 30],
    "LIE": [2, 166, 39, 24], "HUNCH": [45, 160, 24, 30], "FALL": [79, 157, 22, 37], "HURT": [109, 157, 31, 39],
    "LEAN": [187, 157, 35, 33],
    "FIRE": [56, 214, 38, 33],
    "FACE1": [50, 353, 19, 18],
}
# the old Electric Blast's frames (retired by the Anchor Throw, 2026-09-29): the flying spark without its tail and the small
# spark. Their colours still take her first palette slots (colours() below), so her palette (and every built sheet's
# indices) stays as it was
SPARKS = [[120, 238, 11, 11], [134, 237, 9, 9]]

# the Anchor Throw's anchor: the user's own drawing (Superevil; "Marine's anchor: drawn by Superevil"), recoloured by us
# into her own greys (#e4e0e4, #a0a0c0, #606080) with a 1 px outline in her #21201d (the user: "it's my graphic, so you can
# go nuts with edits"); 34x34, its drawing in the box below (ring up, flukes down)
ANCHOR = Image.open(HERE / "anchor_marine.png").convert("RGBA")
ANCHOR_BOX = list(ANCHOR.getbbox())
ANCHOR_BOX[2:] = [ANCHOR_BOX[2] - ANCHOR_BOX[0], ANCHOR_BOX[3] - ANCHOR_BOX[1]]

LABELS, _ = ndimage.label(np.any(np.array(SRC) != BG, axis=2), structure=np.ones((3, 3)))
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
        raise SystemExit(f"marine: {rect} isn't the tight box of whole drawings")
    return [(x + a, y + b) for a, b in zip(xs, ys)]


def source_sheet():
    """Each frame's pixels, copied exactly, in a cell of its own (shelves 256 wide). Returns {name: rect in the copy}."""
    cells, x, y, shelf = {}, 2, 2, 0
    for name, rect in B.items():
        w, h = rect[2], rect[3]
        if x + w + 2 > 256:
            x, y, shelf = 2, y + shelf + 3, 0
        cells[name] = (frame_pixels(rect), rect, [x, y, w, h])
        x += w + 3
        shelf = max(shelf, h)
    # the Anchor Throw's anchor (the user's own drawing, testmods/marine/anchor_marine.png: its opaque pixels, already in
    # her palette's greys and outline) in a cell of its own after hers
    aw, ah = ANCHOR_BOX[2], ANCHOR_BOX[3]
    if x + aw + 2 > 256:
        x, y, shelf = 2, y + shelf + 3, 0
    anchor_cell = [x, y, aw, ah]
    shelf = max(shelf, ah)
    out = Image.new("RGB", (256, y + shelf + 2), BG)
    for pts, (sx, sy, _, _), (cx, cy, _, _) in cells.values():
        for a, b in pts:
            out.putpixel((cx + a - sx, cy + b - sy), SRC.getpixel((a, b)))
    for a in range(aw):
        for b in range(ah):
            px = ANCHOR.getpixel((ANCHOR_BOX[0] + a, ANCHOR_BOX[1] + b))
            if px[3]:
                out.putpixel((anchor_cell[0] + a, anchor_cell[1] + b), px[:3])
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return dict({name: c[2] for name, c in cells.items()}, ANCHOR=anchor_cell)


R = source_sheet()


def f(*names):
    return [R[n] for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)
flip = lambda n: {"rect": R[n], "flip": True}
turn = lambda n, a: {"rect": R[n], "rotate": a} if a else R[n]

IDLE = f("S1", "S2", "S3", "S4", "S5")
RUN = f(*[f"R{k}" for k in range(1, 9)])
BALL = [turn("BALL", a) for a in (0, 90, 180, 270)]  # her ball, a quarter turn at a time
TURN = [R["S0"], R["FRONT"], flip("S0"), R["FRONT"]]

ANIMS = {
    "Stopped": {"frames": f("S0")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": IDLE, "loop": 0, "align": True},
    "Looking Up": {"frames": f("HUNCH")},  # hunched, gazing up (the user: HUNCH as Looking Down showed her looking up)
    "Looking Down": {"frames": f("CROUCH")},  # the sheet's crouch, head bowed (also S3&K's Crouch)
    "Walking": {"frames": RUN, "rot": 2, "align": True},  # (no walk on the sheet: the run)
    "Running": {"frames": RUN, "rot": 2, "align": True},
    "Skidding": {"frames": f("SKID")},
    "Super Peel Out": {"frames": RUN, "rot": 2, "align": True},
    "Spin Dash": {"frames": BALL},
    "Jumping": C(BALL),
    "Bouncing": C(f("SPRING")),
    "Hurt": C(f("HURT")),
    "Dying": C(f("FALL")),
    "Drowning": C(f("HURT")),
    "Fan Rotate": C(TURN),
    "Breathing": C(f("FACE")),
    "Pushing": {"frames": f("LEAN")},
    "Flailing 1": {"frames": f("FLAIL")},
    "Flailing 2": {"frames": f("FLAIL")},
    "Hanging": C(f("SPRING")),
    "Clinging On": C(f("SPRING")),
    "Corkscrew H": {"frames": TURN, "anchor": "feet"},  # (feet + aligned: the 33 / 38 px frames jittered on springs; the user, 2026-09-29)
    "Water Slide": C(f("LIE")),
    "Continue": {"frames": IDLE, "align": True},
    "Continue Up": {"frames": f("SPRING")},
    "Super Transform": {"frames": f("SPRING")},
}
S2_ONLY = {
    "Bored!": {"frames": f("POINT", "S0"), "loop": 0},
    "Flailing 3": {"frames": f("FLAIL")},
    "Grabbed": C(f("HURT")),
    "Twirl H": {"frames": TURN, "rot": 2, "anchor": "feet"},  # (as Corkscrew H)
}
CD_ONLY = {name: {"frames": RUN} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# The Anchor Throw (tools/anchor_throw.py picks the frames): slot 41 "Anchor Throw", her throwing pose held while the anchor
# is out (an attack; S3&K keeps her standing boxes): POINT, the sheet's arm flung forward, open hand (the old blast pose,
# FIRE, has the electric spark drawn into her hand); slot 43
# "Anchor", the anchor drawn at runtime at the end of its chain: 0 flukes forward (a quarter turn, ring back toward her),
# 1 flukes up (a half turn), 2 flukes down (as drawn); mirrored with her facing
APPENDED = {
    "41": {"name": "Anchor Throw", "frames": f("POINT"), "speed": 0, "s3k_boxes": "idle"},
    "43": {"name": "Anchor", "frames": [turn("ANCHOR", 270), turn("ANCHOR", 180), R["ANCHOR"]], "anchor": "center",
           "speed": 0},
}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
FACE1 = R["FACE1"]
HEAD = [FACE1[0] + 1, FACE1[1], 16, 16]  # the face, 16x16 (its leftmost column and right whisker tips, its chin row off)
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("MARINE")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1] + 1, 16, 14], "trim": False},
    # the whole face on the game's own board, enlarged to fill it (the user's signpost exception: tools/sign_face.py)
    "sign_face": board_face(FACE1, 1.3),
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the HUD face, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: her poses stand in
    "end_idle": {"rect": R["S0"], "remap": PLUS_128},
    "end_pose_1": {"rect": R["SPRING"], "remap": PLUS_128},
    "end_pose_2": {"rect": R["POINT"], "remap": PLUS_128},
    "end_pose_3": {"rect": R["UP"], "remap": PLUS_128},
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("S0", "S1", "UP", "SPRING", "POINT", "S0"), 1)},
}


# ---------------------------------------------------------------- colours
def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def colours():
    """The Electric Blast's colours and the most used of the built art (22 in all) (the working copy, the sparks, the HUD tag's yellow) in her own slots
    74-95, exact; black in Sonic's slot 1; every other sheet colour in its nearest slot (MERGED: those the art uses,
    with pixel counts)."""
    counts = {}
    ims = [Image.open(HERE / SOURCE).convert("RGB")] + [SRC.crop((x, y, x + w, y + h)) for x, y, w, h in SPARKS]
    for im in ims:
        for n, rgb in im.getcolors(1 << 16):
            c = "#%02x%02x%02x" % rgb
            if c not in BACKGROUND and c != "#000000":
                counts[c] = counts.get(c, 0) + n
    spark = {"#%02x%02x%02x" % rgb for x, y, w, h in SPARKS for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(256)}
    # (its #71c693, 12 px of its green core, goes to the core's #8ed2aa, freeing a slot for her fur's #cc7100)
    top = sorted(spark - set(BACKGROUND) - {"#71c693"})  # the Electric Blast's colours first (exact), then the most used; a colour within a few steps of one already taken (the three near-blacks) isn't
    # taken again: it merges into that one
    for c in sorted(counts, key=lambda c: (-counts[c], c)):
        if len(top) < 22 and all(sum((a - b) ** 2 for a, b in zip(hexrgb(c), hexrgb(o))) > 64 for o in top):
            top.append(c)
    palette = {str(74 + k): c for k, c in enumerate(sorted(top))}
    keys = {"#000000": 1, **{c: int(s) for s, c in palette.items()}}
    near = {hexrgb(c): int(s) for s, c in palette.items()}
    out = dict(keys)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            out[c] = near[min(near, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))]
    merged = {c: (out[c], n) for c, n in counts.items() if c not in keys}
    return palette, out, merged


PALETTE, COLOURS, MERGED = colours()
CREDIT = ("Marine the Raccoon (Sonic 3 style) sprites made by Nintendo_6444, with credit to Deebs, FireX, Vol, Frario and "
          "Rathe Ethransu - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/111914/ "
          "(Marine the Raccoon (c) SEGA / Sonic Team)")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the ending poses: a finger up, then the arms-up leap
S3K_VICTORY = {"frames": f("UP", "SPRING")}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra34", "credit": CREDIT,
           "source": SOURCE, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra34SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": C(BALL)}}]
        cfg["ui"] = [{"name": "Extra34_UI", "manifest": "Extra34_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra34_UI.gif"},
                     {"name": "Extra34_Ending", "manifest": "Extra34_ending.json", "elements": ENDING,
                      "out": "build/Extra34_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "marine.json"), ("Sonic2", "marine_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("palette:", PALETTE)
    print("merged colours (colour: slot, pixels):",
          ", ".join(f"{c}: {s} x{n}" for c, (s, n) in sorted(MERGED.items(), key=lambda kv: -kv[1][1])))
