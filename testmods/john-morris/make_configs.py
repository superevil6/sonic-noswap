#!/usr/bin/env python3
"""Writes John Morris' sheet2ani configs (johnmorris.json for Sonic 1, johnmorris_s2.json for Sonic 2; CD's and S3&K's
come from the Sonic 2 one).

John Morris (Castlevania: Bloodlines, Sega Genesis). A separate download (extras.py "crossover": never in the
all-in-one; memory crossover-characters.md). Base character Sonic. His number (file "Extra<n>") is his place in
tools/extras.py, looked up.

Sheets (see SOURCE.txt):
  JohnMorris.png  "John Morris", The Spriters Resource cvbl asset 5797: "Original assets by Konami. Orig. rip by
                  Badbatman3, re-ripped by UltraHype97. Give credit if used!" Genesis art at 1x (he stands 42-46 px).
                  Every sprite faces right. The page (#52466f), the cells (#9685bf) and the darker reused-frame cells
                  (#351850) are background.
  Items.png       "Items and Subweapons", The Spriters Resource cvbl asset 5796: "Extracted by Yawackhary, no credit
                  needed but don't steal. Sprites: Konami". Its sub-weapons are the shots' art (abilities.py, John's
                  "swap_shots": cut from the sheet itself by build_s3k_shot.py, as drawn).

Sections used (the sheet's own labels) and the frame names here (B: each frame's tight box on the sheet):
  Idle STAND1-3, Crouch CROUCH, Walk WALK1-6, Jump JUMP1-3, Attack ATK1-4, Attack (Crouch) CATK1-4, Attack (Aim Up)
  AIMUP1-2, Attack (Aim Down) AIMDN1-2, Damage DAMAGE, Death (Proto) DEATH (his fall, lying down).
Not used: the stairs (no stairs), the grapple / swing (not wanted, the user), the Death palettes (a palette dissolve),
the whips LV2-4 (no whip upgrades, the user), the tweaked sprites.

The whip (the user's pick: the LV1 leather whip with his real body frames). The sheet draws the whips apart from the
body, and its "Assembled whip anims." rows show each attack frame's whip in place round a grey silhouette of the body.
Baked, not drawn at runtime: for each assembled frame, the real body frame is put exactly where its silhouette is (the
offset where their shapes overlap best), and the whip's own pixels as the sheet assembles them go on top (where the
assembled frame shows whip, the whip; where it shows the silhouette, the body). Only existing pixels, pasted together:
nothing is redrawn, recoloured or resized. WHIP below: ground GW1-5 (ATK2 x3 with the whip swinging back and over,
ATK3, ATK4 with it out straight), crouch CW1-5 (CATK2-4 likewise), aim up UW1-2 (AIMUP1 with the whip behind, AIMUP2
with it out diagonally up), aim down DW1-2 (AIMDN1 with it behind, AIMDN2 with it hanging straight down: the sheet's
"Aim Down" is straight down).

Abilities (tools/abilities.py, his entry; the user's design 2026-09-29):
  - Y: the whip (the melee's pose, "melee_whip": slot 43 standing, 44 in the air, 41 crouching, 45 up-forward and 46
    down in the air, by the d-pad as Y is pressed). It hits along its reach at its extended frames.
  - Up + Y: the current sub-weapon (Axe, Cross, Holy Water: abilities.py "swap_shots"), a ring each; monitors swap it
    (abilities.py "monitor_swap").
  - He never curls into a ball (extras.py "no_roll"): his jump is his Jump row's tuck (JUMP2).

The HUD tag "JOHN MORRIS" is our lettering in the HUD font the other extras use (the sheet has none); the life icon /
1-UP are crops of an idle frame's head; the signpost is that head on the game's own board. His colours are the sheet's
16, all exact in his own slots (none merged).
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

# "Extra<n>", its extras.py position (before its entry exists, the next one)
NAME = next((e["file"] for e in EXTRAS if e["art"].name == HERE.name), f"Extra{len(EXTRAS) + 1}")
SHEET = HERE / "JohnMorris.png"
SOURCE = "build/source.png"  # working copy: each used frame (and each baked whip frame) in a cell of its own
SHEET_BG = [(82, 70, 111), (150, 133, 191), (53, 24, 80)]
BACKGROUND = ["#%02x%02x%02x" % c for c in SHEET_BG]
BG = SHEET_BG[0]
SRC = Image.open(SHEET).convert("RGB")
SILHOUETTE = (109, 109, 109)  # the assembled whip rows' grey body silhouettes


def row(prefix, rects, start=1):
    return {f"{prefix}{k}": list(r) for k, r in enumerate(rects, start)}


# ---------------------------------------------------------------- frames: name -> its tight box on the sheet
B = {
    **row("STAND", [(17, 37, 30, 43), (50, 38, 30, 42), (83, 38, 29, 42)]),
    "CROUCH": [123, 47, 30, 34],
    **row("WALK", [(175, 37, 30, 43), (208, 36, 27, 44), (245, 36, 19, 44), (275, 37, 25, 43), (306, 37, 24, 43),
                   (343, 37, 24, 43)]),
    **row("JUMP", [(389, 36, 23, 43), (423, 39, 19, 34), (454, 39, 24, 38)]),
    **row("ATK", [(19, 99, 20, 44), (51, 97, 40, 46), (95, 97, 26, 46), (126, 100, 40, 43)]),
    **row("CATK", [(181, 111, 18, 34), (209, 110, 40, 35), (258, 109, 23, 36), (288, 112, 38, 33)]),
    **row("AIMUP", [(337, 98, 24, 45), (370, 95, 32, 48)]),
    **row("AIMDN", [(411, 98, 24, 45), (450, 102, 20, 38)]),
    "DAMAGE": [17, 169, 31, 32],
    "DEATH": [362, 166, 44, 23],
}
# The assembled LV1 whip frames: name -> (body frame, its grey silhouette's box, the whip's box), all on the sheet
WHIP = {
    "GW1": ("ATK2", (18, 321, 40, 46), (16, 324, 15, 6)),
    "GW2": ("ATK2", (66, 321, 40, 46), (59, 326, 6, 30)),
    "GW3": ("ATK2", (132, 321, 40, 46), (107, 328, 24, 23)),
    "GW4": ("ATK3", (188, 321, 26, 46), (173, 320, 24, 23)),
    "GW5": ("ATK4", (219, 324, 40, 43), (259, 331, 34, 5)),
    "CW1": ("CATK2", (299, 334, 38, 35), (298, 339, 15, 6)),
    "CW2": ("CATK2", (346, 334, 39, 35), (341, 341, 6, 30)),
    "CW3": ("CATK2", (411, 334, 40, 35), (389, 343, 24, 23)),
    "CW4": ("CATK3", (475, 333, 23, 36), (455, 335, 24, 23)),
    "CW5": ("CATK4", (505, 336, 38, 33), (543, 345, 34, 5)),
    "UW1": ("AIMUP1", (603, 322, 24, 45), (581, 336, 21, 11)),
    "UW2": ("AIMUP2", (636, 320, 32, 47), (664, 293, 28, 29)),
    "DW1": ("AIMDN1", (718, 322, 24, 45), (696, 336, 21, 11)),
    "DW2": ("AIMDN2", (756, 326, 20, 38), (768, 356, 5, 34)),
}

# ---------------------------------------------------------------- the working copy
A = np.array(SRC).astype(int)
_BGMASK = np.zeros(A.shape[:2], bool)
for _c in SHEET_BG:
    _BGMASK |= np.all(A == _c, axis=2)
_GREY = np.all(A == SILHOUETTE, axis=2)


def _pixels(box, extra_bg=None):
    """The non-background pixels wholly of the drawing(s) in a box: {(x, y) on the sheet: rgb}."""
    x, y, w, h = box
    m = ~_BGMASK[y:y + h, x:x + w]
    if extra_bg is not None:
        m &= ~extra_bg[y:y + h, x:x + w]
    ys, xs = np.nonzero(m)
    return {(x + int(a), y + int(b)): tuple(A[y + b, x + a]) for a, b in zip(xs, ys)}


def _body(name):
    """A body frame's pixels (its one drawing: the biggest blob in its tight box)."""
    x, y, w, h = B[name]
    lab, _ = ndimage.label(~_BGMASK[y:y + h, x:x + w], structure=np.ones((3, 3)))
    big = np.argmax(np.bincount(lab.ravel())[1:]) + 1
    return {(x + a, y + b): c for (a, b), c in
            ((((xx - x), (yy - y)), c) for (xx, yy), c in _pixels(B[name]).items()) if lab[b, a] == big}


def _whip_frame(name):
    """(pixels {(x, y): rgb} relative to the body's top-left, the body's box (0, 0, w, h)): the body frame placed where
    its silhouette is (the offset with the most overlap), then the whip's pixels as the sheet assembles them on top."""
    body_name, sil, whip = WHIP[name]
    body = _body(body_name)
    bx, by, bw, bh = B[body_name]
    sx, sy, sw, sh = sil
    grey = {(a, b) for b in range(sy - 4, sy + sh + 4) for a in range(sx - 4, sx + sw + 4) if _GREY[b, a]}
    best = None
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            ox, oy = sx - bx + dx, sy - by + dy  # body sheet px -> assembled px
            hit = sum((a + ox, b + oy) in grey for a, b in body)
            miss = len(body) - hit + len(grey) - hit
            if best is None or (miss, abs(dx) + abs(dy)) < best[0]:
                best = ((miss, abs(dx) + abs(dy)), ox, oy)
    _, ox, oy = best
    out = {(a + ox, b + oy): c for (a, b), c in body.items()}
    for p, c in _pixels(whip, _GREY).items():  # (the whip where the assembled frame shows it: on top)
        out[p] = c
    top_left = (bx + ox, by + oy)
    return {(a - top_left[0], b - top_left[1]): c for (a, b), c in out.items()}, (0, 0, bw, bh), best[0][0]


def source_sheet():
    """Each frame in a cell of its own (shelves 512 wide), pixels copied exactly. Returns ({name: rect in the copy},
    {name: the body's box in the copy} for the whip frames, {name: silhouette misfit px})."""
    cells = {}
    for name in B:
        pts = _body(name)
        x0, y0 = B[name][0], B[name][1]
        cells[name] = ({(a - x0, b - y0): c for (a, b), c in pts.items()}, None)
    fit = {}
    for name in WHIP:
        pts, body, fit[name] = _whip_frame(name)
        cells[name] = (pts, body)
    rects, anchors, x, y, shelf = {}, {}, 2, 2, 0
    placed = []
    for name, (pts, body) in cells.items():
        xs = [a for a, _ in pts]
        ys = [b for _, b in pts]
        mx, my = min(xs), min(ys)
        w, h = max(xs) - mx + 1, max(ys) - my + 1
        if x + w + 2 > 512:
            x, y, shelf = 2, y + shelf + 3, 0
        rects[name] = [x, y, w, h]
        if body is not None:
            anchors[name] = [x - mx + body[0], y - my + body[1], body[2], body[3]]
        placed.append((pts, x - mx, y - my))
        x += w + 3
        shelf = max(shelf, h)
    out = Image.new("RGB", (512, y + shelf + 2), BG)
    for pts, ox, oy in placed:
        for (a, b), c in pts.items():
            out.putpixel((a + ox, b + oy), c)
    (HERE / "build").mkdir(exist_ok=True)
    out.save(HERE / SOURCE)
    return rects, anchors, fit


R, ANCHOR, FIT = source_sheet()


def f(*names):
    """Frame specs: a plain frame is its rect in the copy; a whip frame is positioned by its body (anchor_box), so the
    whip doesn't shift him."""
    return [{"rect": R[n], "anchor_box": ANCHOR[n]} if n in ANCHOR else R[n] for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)

# ---------------------------------------------------------------- animations
STAND = f("STAND1", "STAND2", "STAND3", "STAND2")
WALK = f(*[f"WALK{k}" for k in range(1, 7)])
JUMP = f("JUMP2")  # no ball: his jump's tuck (as Gamma's / Sparkster's jump pose)

ANIMS = {
    "Stopped": {"frames": f("STAND1")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": STAND, "loop": 0, "align": True},
    "Looking Up": {"frames": f("AIMUP1")},  # (no look-up frame on the sheet: the aim-up's first, arm raised)
    "Looking Down": {"frames": f("CROUCH")},
    "Walking": {"frames": WALK, "align": True},
    "Running": {"frames": WALK, "align": True},  # (no run on the sheet: the walk, faster)
    "Skidding": {"frames": f("CATK1")},  # (braced low)
    "Super Peel Out": {"frames": WALK, "align": True},
    "Spin Dash": {"frames": f("CROUCH")},  # PLACEHOLDER: he never curls up (extras.py "no_roll")
    "Jumping": C(JUMP),
    "Bouncing": C(f("JUMP1")),  # springs: stretched up
    "Hurt": C(f("DAMAGE")),
    "Dying": C(f("DAMAGE")),
    "Drowning": C(f("DAMAGE")),
    "Fan Rotate": C(f("JUMP1", "JUMP2", "JUMP3", "JUMP2")),
    "Breathing": C(f("JUMP1")),
    "Pushing": {"frames": f("WALK4")},
    "Flailing 1": {"frames": f("ATK1", "STAND1"), "align": True},
    "Flailing 2": {"frames": f("ATK1", "STAND1"), "align": True},
    "Hanging": C(f("JUMP1")),
    "Clinging On": C(f("JUMP1")),
    "Corkscrew H": {"frames": WALK},
    "Water Slide": C(f("CROUCH")),
    "Continue": {"frames": STAND, "align": True},
    "Continue Up": {"frames": f("ATK1")},
    "Super Transform": {"frames": f("AIMUP2")},
}
S2_ONLY = {
    "Bored!": {"frames": STAND, "loop": 0, "align": True},
    "Flailing 3": {"frames": f("ATK1", "STAND1"), "align": True},
    "Grabbed": C(f("DAMAGE")),
    "Twirl H": {"frames": WALK},
}
CD_ONLY = {name: {"frames": WALK} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

# The whip (abilities.py melee_whip: every pose 7 frames, the extended one held for the last 3; the code picks the
# frame, speed 0): 43 standing, 44 in the air (the same frames, centred), 41 crouching, 45 up-forward and 46 down in
# the air (the wind-up held for 4, then out)
WHIP_GROUND = f("GW1", "GW2", "GW3", "GW4", "GW5", "GW5", "GW5")
APPENDED = {
    "41": {"name": "Crouch Whip", "frames": f("CW1", "CW2", "CW3", "CW4", "CW5", "CW5", "CW5"), "speed": 0},
    "43": {"name": "Whip", "frames": WHIP_GROUND, "speed": 0},
    "44": {"name": "Air Whip", "frames": WHIP_GROUND, "anchor": "center", "speed": 0},
    "45": {"name": "Whip Up", "frames": f("UW1", "UW1", "UW1", "UW1", "UW2", "UW2", "UW2"), "anchor": "center",
           "speed": 0},
    "46": {"name": "Whip Down", "frames": f("DW1", "DW1", "DW1", "DW1", "DW2", "DW2", "DW2"), "anchor": "center",
           "speed": 0},
}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
_S = R["STAND1"]
HEAD = [_S[0] + 8, _S[1], 16, 16]  # the idle frame's head and hair (the life icon)
FACE = [_S[0] + 6, _S[1], 20, 20]  # ...a little more of it (the signpost)
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("JOHN")},  # the sheet has no name tag
    "monitor_1up": {"rect": [HEAD[0], HEAD[1], 16, 14], "trim": False},
    "sign_face": board_face(FACE),  # his head on the game's own board, 1x
    "mini_1": {"rect": HEAD, "remap": PLUS_128},  # (no continue icons on the sheet: the head, twice)
    "mini_2": {"rect": HEAD, "remap": PLUS_128},
}
ENDING = {  # no ending art: his poses stand in
    "end_idle": {"rect": R["STAND1"], "remap": PLUS_128},
    "end_pose_1": {"rect": R["ATK1"], "remap": PLUS_128},
    "end_pose_2": {"rect": R["AIMUP2"], "remap": PLUS_128},
    "end_pose_3": {"rect": R["STAND2"], "remap": PLUS_128},
    **{f"good_{n}": {"rect": R[k], "remap": PLUS_128}
       for n, k in enumerate(("STAND1", "STAND2", "STAND3", "ATK1", "AIMUP1", "AIMUP2"), 1)},
}

# ---------------------------------------------------------------- colours
# All of his colours (the body's and the whip's) go exact in his own slots 74-95 (black: none on his sheet).
KEY_COLOURS = {}


def own_colours():
    counts = {}
    for n, rgb in Image.open(HERE / SOURCE).convert("RGB").getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in BACKGROUND and c not in KEY_COLOURS:
            counts[c] = counts.get(c, 0) + n
    return sorted(counts.items(), key=lambda kv: -kv[1])


_OWN = own_colours()
if len(_OWN) > 22:
    raise SystemExit(f"john-morris: {len(_OWN)} own colours, 22 slots")
PALETTE = {str(74 + k): c for k, (c, _) in enumerate(sorted(_OWN))}


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


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
CREDIT = ("John Morris (Castlevania: Bloodlines): original rip by Badbatman3, re-ripped by UltraHype97, The Spriters "
          "Resource, asset 5797; items and sub-weapons extracted by Yawackhary, asset 5796 (Sprites (c) Konami)")

# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose" the pose
# held): the whip cracked out straight
S3K_VICTORY = {"frames": f("STAND1", "GW4", "GW5"), "pose": 2}


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


def reach_report():
    """Each whip frame's whip, px from his centre as the game places the frame (the body's box centred; feet on the
    ground line 20 px below the centre for the ground poses, the body's middle on the centre in the air): the numbers
    abilities.py's melee_reach / melee_whip boxes are taken from."""
    for name in WHIP:
        pts, (bx, by, bw, bh), _ = _whip_frame(name)
        body_name, _, whip = WHIP[name]
        centre = name.startswith(("U", "D")) or False
        cx = bx + bw // 2
        cy = by + bh // 2 if centre else by + bh - 20
        wp = [(a - cx, b - cy) for (a, b), c in pts.items()]
        whip_pts = set(_pixels(whip, _GREY))
        # (the whip's own pixels, by where they came from: the frame's pixels that aren't the body's)
        xs = [a for a, _ in wp]
        ys = [b for _, b in wp]
        print(f"  {name}: frame x {min(xs)}..{max(xs)}, y {min(ys)}..{max(ys)} (feet-anchored)" if not centre else
              f"  {name}: frame x {min(xs)}..{max(xs)}, y {min(ys)}..{max(ys)} (centred)")


if __name__ == "__main__":
    for game, out in (("Sonic1", "johnmorris.json"), ("Sonic2", "johnmorris_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    print("own colours:", ", ".join(f"{c} x{n}" for c, n in _OWN))
    print("whip frames, silhouette misfit (px):", ", ".join(f"{k} {v}" for k, v in FIT.items()))
    reach_report()
