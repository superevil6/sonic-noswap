#!/usr/bin/env python3
"""Writes E-102 Gamma's sheet2ani configs (gamma.json for Sonic 1, gamma_s2.json for Sonic 2).

Sheet: testmods/Gamma2.png, "Gamma (E-102 Gamma)" on The Spriters Resource (custom edits, asset 95734; see
SOURCE.txt). Its credits: Cylent Nite (original Gamma sprites), Nebula (sprites), Quicksilver Tai Allister (poses),
HC Missile (original booster and claw).

Layout. Below the title the sheet draws Gamma in four blocks of six rows, each block with different arms: plain
hands (y 260), the claw (y 680), his short arm gun (y 1100) and the MACHINE GUN (y 1520, a long dark gatling-style
gun held level in both hands). The user picked the machine-gun block; only its frames are used. Each row is drawn
twice: the left half faces RIGHT (toes and gun point right), the right half is the same poses facing left (mirror
images, bar a few highlight pixels). Everything is cut from the left half. Rows of the machine-gun block (left half):
  0 (y 1520): standing A (knees bent), crouch B, standing tall C, legs dangling D (airborne); in the middle, E: the
              upper body alone (legs tucked away; not used)
  1 (y 1597): the walk, six frames W1-W6 (the row's other six are the same walk facing left)
  2 (y 1670): row 0's poses again (pixel-identical bodies) with a detached red booster bar behind his head ("aim"
              row: his gun is level in every frame of this block anyway)
  3 (y 1747): the walk again with the booster bars
  4 (y 1813): hover crouched: B over the booster with its blue jet flame (four flame frames, a few loose sparks)
  5 (y 1863): hover with the legs dangling: D over the same four flames (used for his Hover)
The frames are whole bodies: nothing is composed. The only piecing is that a hover frame's flame (with its booster
bar and sparks) is a separate blob on the sheet, a pixel or two from the next frame; build/source.png is a working
copy holding each used frame's blobs exactly where the sheet has them (every pixel copied, nothing moved within a
frame) in a cell of its own, so a rect crop can't catch a neighbour's pixels.

Pivot: every body has the same upper body (head, chest, gun: pixel-identical, only shifted 0 / 1 / 7 px in its box
by a leg stretched out behind), so each frame's pivot is put on that torso (TORSO px right of the torso's left
edge, the middle of his head and chest; measured per frame by matching the standing frame's top rows), and his
body doesn't slide sideways between frames while the legs move. Ground poses stand on their lowest pixel (feet_y),
the soles on one line; air poses are centred.

He never curls into a ball (the user's choice): "Jumping" is the legs-dangling pose; "Spin Dash" is only a
placeholder (his crouch; he has no Spin Dash); the Sonic 1 special stage uses the jump pose (the stage turns it).

Abilities (appended slots; wired elsewhere):
  42 "Hover": row 5, legs dangling over the booster's jet flame (four flicker frames).
  43 "Arm Cannon" / 44 "Arm Cannon Air": his aimed machine-gun shot: the level-gun pose, held (A on the ground,
      D in the air), repeated AIM_FRAMES times (the same frame, so it costs no sprite memory) so a script that
      steps through the shot's frames always lands on it. The shot itself is drawn by the shot code.

Missing art and stand-ins (noted per animation below): look up, skid, push, balance, hurt, death, fan, hanging,
continue, bored and the super transform have no art of their own.
Nothing is redrawn, recoloured, filtered or shrunk: frames are crops; the large ending pose is an exact 2x
nearest-neighbour enlargement; the "GAMMA" HUD tag is lettered in the game's HUD style, as for the other extras
whose sheets have none.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
SHEET = HERE.parent / "Gamma2.png"
SOURCE = "build/source.png"  # working copy: each used frame's blobs in a cell of its own (source_sheet)
BACKGROUND = ["#004040"]
BG = (0x00, 0x40, 0x40)
SRC = Image.open(SHEET).convert("RGB")

# ---------------------------------------------------------------- frames (the machine-gun block, left half)
# name -> the tight boxes [x, y, w, h] of its blobs on the sheet, the body first (its torso is measured)
PIECES = {
    "A": [[21, 1533, 46, 46]], "B": [[85, 1542, 46, 37]], "C": [[139, 1520, 46, 57]], "D": [[199, 1520, 46, 62]],
    "W1": [[18, 1600, 46, 51]], "W2": [[89, 1597, 46, 54]], "W3": [[153, 1599, 53, 52]],
    "W4": [[232, 1600, 53, 49]], "W5": [[306, 1597, 47, 52]], "W6": [[377, 1597, 46, 52]],
    # row 5: D's body over the booster bar + flame (its sparks are inside the flame's box: taken with it)
    "H1": [[30, 1863, 46, 62], [15, 1867, 17, 28]], "H2": [[90, 1863, 46, 62], [75, 1867, 17, 38]],
    "H3": [[150, 1863, 46, 62], [135, 1867, 17, 26]], "H4": [[210, 1863, 46, 62], [195, 1867, 17, 21]],
}


def blobs():
    """8-connected blobs of the machine-gun block's left half: {box: pixel set} (boxes as [x, y, w, h] tuples)."""
    x0, y0, x1, y1 = 0, 1515, 440, SRC.height
    px, seen, out = SRC.load(), set(), {}
    for y in range(y0, y1):
        for x in range(x0, x1):
            if px[x, y] == BG or (x, y) in seen:
                continue
            stack, pts = [(x, y)], []
            seen.add((x, y))
            while stack:
                a, b = stack.pop()
                pts.append((a, b))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        c, d = a + dx, b + dy
                        if x0 <= c < x1 and y0 <= d < y1 and (c, d) not in seen and px[c, d] != BG:
                            seen.add((c, d))
                            stack.append((c, d))
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out[(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)] = pts
    return out


BLOBS = blobs()


def frame_pixels(name):
    """The frame's pixels: its listed blobs, plus any blob lying wholly inside one of their boxes (sparks)."""
    pts = []
    for box in PIECES[name]:
        if tuple(box) not in BLOBS:
            raise SystemExit(f"{name}: no blob at {box}")
        x, y, w, h = box
        for (bx, by, bw, bh), p in BLOBS.items():
            if (bx, by, bw, bh) == tuple(box) or (x <= bx and bx + bw <= x + w and y <= by and by + bh <= y + h):
                pts += p
    return pts


# His pivot: TORSO px right of the torso's left edge (the middle of his head and chest; the gun reaches out ahead
# of it). Every body's top TORSO_ROWS rows match the standing frame A's, shifted by the leg that sticks out behind.
# (19 rather than the head's middle, 17-18: the Origins card picture is the standing frame 8x, pivot on the centre of
# a 440 px cell, so at most 27 px may reach ahead of the pivot; his gun reaches 46 - 19 = 27.)
TORSO, TORSO_ROWS = 19, 30


def torso_shift(body):
    """How far body's torso sits right of A's, both measured from their box's left edge."""
    def pix(box):
        x, y, w, h = box
        return {(i, j): SRC.getpixel((x + i, y + j)) for j in range(h) for i in range(w)
                if SRC.getpixel((x + i, y + j)) != BG}
    ref = {k: v for k, v in pix(PIECES["A"][0]).items() if k[1] < TORSO_ROWS}
    own = pix(body)
    best = max(((dx, dy) for dx in range(-12, 13) for dy in range(-12, 13)),
               key=lambda d: sum(own.get((i + d[0], j + d[1])) == c for (i, j), c in ref.items()))
    score = sum(own.get((i + best[0], j + best[1])) == c for (i, j), c in ref.items())
    if score < 0.95 * len(ref):
        raise SystemExit(f"torso of {body}: only {score} of {len(ref)} pixels match the standing frame's")
    return best[0]


def source_sheet():
    """Each frame's pixels (copied exactly, in their places on the sheet) in a cell of its own, in a row.
    Returns {name: (rect in the working copy, pivot x in it)}."""
    cells, x = {}, 2
    for name in PIECES:
        pts = frame_pixels(name)
        fx, fy = min(p[0] for p in pts), min(p[1] for p in pts)
        w, h = max(p[0] for p in pts) - fx + 1, max(p[1] for p in pts) - fy + 1
        bx = PIECES[name][0][0]
        cells[name] = (pts, fx, fy, [x, 2, w, h], bx - fx + torso_shift(PIECES[name][0]) + TORSO)
        x += w + 4
    out = Image.new("RGB", (x, max(c[3][3] for c in cells.values()) + 4), BG)
    for name, (pts, fx, fy, (cx, cy, w, h), _) in cells.items():
        for a, b in pts:
            out.putpixel((cx + a - fx, cy + b - fy), SRC.getpixel((a, b)))
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return {name: (c[3], c[4]) for name, c in cells.items()}


CELLS = source_sheet()
R = {name: rect for name, (rect, _) in CELLS.items()}


def f(name):
    """A frame pivoted on his torso (sheet2ani "pivot_x" on a single layer: the frame is the cell's crop)."""
    rect, pivot = CELLS[name]
    return {"layers": [{"rect": rect, "at": [0, 0]}], "anchor_layer": 0, "pivot_x": pivot}


# ---------------------------------------------------------------- animations
STAND, CROUCH, TALL, AIR = f("A"), f("B"), f("C"), f("D")
WALK = [f(f"W{k}") for k in range(1, 7)]
JUMP = [AIR]  # legs dangling
BALANCE = [TALL, STAND]  # no balance art: straightening up and bending the knees

ANIMS = {
    "Stopped": {"frames": [STAND]},  # also the Origins character-select card picture
    "Waiting": {"frames": [TALL], "loop": 0},  # standing up straight
    "Looking Up": {"frames": [TALL], "loop": 0},  # no look-up art: standing tall
    "Looking Down": {"frames": [CROUCH], "loop": 0},  # row 0's crouch
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": WALK, "rot": 2},  # no run art: the walk (the game speeds it up)
    "Skidding": {"frames": [CROUCH]},  # no skid art: the crouch
    "Super Peel Out": {"frames": WALK, "rot": 2},
    "Spin Dash": {"frames": [CROUCH]},  # PLACEHOLDER: he doesn't curl up (no Spin Dash)
    "Jumping": {"frames": JUMP, "anchor": "center"},  # no ball: legs dangling
    "Bouncing": {"frames": JUMP, "anchor": "center"},  # springs
    "Hurt": {"frames": JUMP, "anchor": "center"},  # no hurt art
    "Dying": {"frames": JUMP, "anchor": "center"},  # no death art
    "Drowning": {"frames": JUMP, "anchor": "center"},
    "Fan Rotate": {"frames": JUMP, "anchor": "center"},  # no spin art
    "Breathing": {"frames": [TALL], "anchor": "center"},
    "Pushing": {"frames": WALK[1:5], "speed": 8},  # no push art: the walk's mid-stride frames
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": JUMP, "anchor": "center"},  # legs dangling
    "Clinging On": {"frames": JUMP, "anchor": "center"},
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": [CROUCH], "anchor": "center"},  # crouched
    "Continue": {"frames": [STAND]},  # no continue art: standing
    "Continue Up": {"frames": [CROUCH, STAND, TALL], "loop": 2},  # rising from the crouch
    "Super Transform": {"frames": [STAND, TALL], "loop": 1},
}
S2_ONLY = {
    "Flailing 3": {"frames": BALANCE},
    "Grabbed": {"frames": JUMP, "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": [TALL], "loop": 0},
}

# ---------------------------------------------------------------- abilities
HOVER = [f(f"H{k}") for k in range(1, 5)]
# the aimed shot's pose: the gun held level, one frame repeated (tools/abilities.py's shot steps through the slot's
# frames; 8 = the length of its per-frame tables, so any frame it picks is this pose)
AIM_FRAMES = 8

APPENDED = {
    "42": {"name": "Hover", "frames": HOVER, "anchor": "center", "speed": 60},
    "43": {"name": "Arm Cannon", "frames": [STAND] * AIM_FRAMES, "speed": 0},
    "44": {"name": "Arm Cannon Air", "frames": [AIR] * AIM_FRAMES, "anchor": "center", "speed": 0},
}

# ---------------------------------------------------------------- HUD, signpost, continue, ending
A = R["A"]
HEAD = [A[0] + 12, A[1], 16, 16]  # his eyes, head band and the top of his chest (crop of the standing frame)
FACE = [A[0] + 2, A[1], 40, 24]  # his head and chest, the top of the standing frame


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("GAMMA")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1] + 1, 16, 14], "trim": False},
    # his head on the game's own signpost board (its yellow interior is 40x24 at 4,5), like Silver's
    "sign_face": {"rect": FACE, "trim": False, "at": [4, 5],
                  "base": {"file": str(REPO / "extracted/Sonic1/Data/Sprites/Global/Items2.gif"),
                           "rect": [34, 182, 48, 32], "clear": [4, 5, 40, 24, 15],
                           "recolour": {"12": 8, "13": 8, "14": 8}}},  # Eggman's red bits on the frame
    # no continue icons and nothing is shrunk: crops of his head from two standing frames
    "mini_1": {"rect": [A[0] + 3, A[1], 36, 24], "remap": PLUS_128},
    "mini_2": {"rect": [R["C"][0] + 3, R["C"][1], 36, 24], "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": R["A"], "remap": PLUS_128},
    "end_pose_1": {"rect": R["C"], "remap": PLUS_128},  # standing tall, gun level
    "end_pose_2": {"rect": R["D"], "remap": PLUS_128},  # the jump
    "end_pose_3": {"rect": R["A"], "scale": 2, "remap": PLUS_128},  # standing, exactly 2x (nearest-neighbour)
    # good ending: straightening up, crouching, jumping and landing
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("A", "C", "B", "D", "C", "A"), 1)},
}

# ---------------------------------------------------------------- colours
# The machine-gun frames use 28 colours; the extras have 22 own slots (74-95). Near-exact in Sonic's slots: black
# #0c0c0c -> 1 (#080000, as every extra's black), #464646 -> 9 (#404040). The other 22 most-used get own slots,
# exact. Four merge into a neighbour (MERGED, printed with pixel counts): #b0b0b0 -> #aeaeae and #ececec -> #f4f4f4
# (2 and 8 steps), the lens's #3b5ad8 -> #2c7cec, and the eyes' dark green #03593c -> #009500.
PALETTE = {
    "74": "#1c1c1c", "75": "#2f2f2f", "76": "#757575", "77": "#ff6414", "78": "#fe0000", "79": "#470101",
    "80": "#aeaeae", "81": "#980001", "82": "#f4f4f4", "83": "#ffaa01", "84": "#f3da5c", "85": "#565656",
    "86": "#92effe", "87": "#3b9fec", "88": "#2c7cec", "89": "#64c7ee", "90": "#8decec", "91": "#1871e7",
    "92": "#4ac5ec", "93": "#009500", "94": "#a24314", "95": "#03f701",
}
KEY_COLOURS = {"#000000": 1, "#0c0c0c": 1, "#464646": 9, "#fcfc00": 15,
               "#b0b0b0": 80, "#ececec": 82, "#3b5ad8": 88, "#03593c": 93,
               **{c: int(s) for s, c in PALETTE.items()}}


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def slot_rgb(s):
    for c, v in PALETTE.items():
        if int(c) == s:
            return hexrgb(v)
    tpl = Image.open(REPO / "extracted/Sonic1/Data/Sprites/Players/Sonic1.gif").getpalette()
    return tuple(tpl[3 * s:3 * s + 3])


def all_colours():
    """KEY_COLOURS, plus any other colour of the working copy in the slot (Sonic's 1-15 or his own) nearest to it
    (none today: all 28 are listed). MERGED: the colours not in a slot of their own, with pixel counts."""
    slots = sorted(set(range(1, 16)) | {int(s) for s in PALETTE})
    out = dict(KEY_COLOURS)
    counts = {"#%02x%02x%02x" % rgb: n for n, rgb in Image.open(HERE / SOURCE).getcolors(1 << 16)}
    for c in counts:
        if c not in out and c not in BACKGROUND:
            out[c] = min(slots, key=lambda s: sum((a - b) ** 2 for a, b in zip(slot_rgb(s), hexrgb(c))))
    merged = {c: (out[c], n) for c, n in counts.items()
              if c not in BACKGROUND and c not in PALETTE.values() and c != "#000000"}
    return out, merged


COLOURS, MERGED = all_colours()
CREDIT = ("E-102 Gamma sprites: original Gamma sprites by Cylent Nite; sprites by Nebula; poses by Quicksilver Tai "
          "Allister; original booster and claw by HC Missile - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/95734/ "
          "(E-102 Gamma (c) SEGA / Sonic Team)")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): no celebration on the sheet: the ending's jump, then standing tall
S3K_VICTORY = {"frames": [f("D"), f("C")]}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra20", "credit": CREDIT,
           "source": SOURCE, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        # no ball: the special stage turns his jump pose
        cfg["extra_anis"] = [{"name": "Extra20SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": JUMP, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra20_UI", "manifest": "Extra20_ui.json", "elements": ELEMENTS,
                      "out": "build/Extra20_UI.gif"},
                     {"name": "Extra20_Ending", "manifest": "Extra20_ending.json", "elements": ENDING,
                      "out": "build/Extra20_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "gamma.json"), ("Sonic2", "gamma_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("pivots (px from each frame's left edge):", ", ".join(f"{k} {p}" for k, (_, p) in CELLS.items()))
    print("merged colours (colour: slot, pixels):",
          ", ".join(f"{c}: {s} x{n}" for c, (s, n) in sorted(MERGED.items(), key=lambda kv: -kv[1][1])))
