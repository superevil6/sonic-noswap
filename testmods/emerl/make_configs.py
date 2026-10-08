#!/usr/bin/env python3
"""Writes Emerl's sheet2ani configs (emerl.json for Sonic 1, emerl_s2.json for Sonic 2; CD's and S3&K's come from the
Sonic 2 one).

Extra 36 in extras.py (integrated 2026-09-28). Base character Sonic. Public (credit in mods/NoSwap/README.md).

Sheet: testmods/Emerl.png (505x453, RGBA), the Mod.Gen Project sheet: "Emerl by Xeric and Deebs" (see SOURCE.txt). Its
terms, printed on the sheet: "Use these sheets for whatever you like! ... Give credit please to the "Mod.Gen Project
Team"". The sprite panel is light slate (#95b1c8) inside a dark slate page (#546d8e); the lime measuring lines
(#a8e61d) run behind some sprites: all three are background. Every sprite faces right.
Not used: the first two rows (16 palette variants with their swatches: only the default gold Emerl is used), the
two older-style standing frames at the left of the row with Sonic (OLD1 / OLD2: other shading), Sonic himself (the size
reference), the wireframe head, the Mod.Gen logo and the text.
Rows and frame names (no labels on the sheet; named by what they show):
  heads (y 107-131)   loose heads: H0 (three-quarter front, [18,109,19,22]) and H1 (turning, [43,109,20,22]) are used
                      for the HUD, signpost and continue icons; the rest (the back, side on, expressions, crestless,
                      the crest bending) are unused
  y 138-182           standing frames (the same as R5_1), unused
  y 193-237           R5_0 stand, eyes dark (powered down); R5_1 stand; R5_2 stand, eyes RED (his copy flash);
                      R5_3-R5_8 fighting stance, fists up (a bob); R5_9 a kick down and forward; R5_10 a flying leap,
                      fist out, legs back
  y 245-292           R6_0 guard; R6_1 low jab (crouched); R6_2 long lunge punch; R6_3-R6_5 the SPIN SWIRL (a
                      spinning sweep with a brown swirl trail, loose trail bits cut together); R6_6 recovering
  y 302-352           R7_0 claw slash (its red trail beside it, not cut), R7_1 claws out; R7_2 a jump (knee up, fist
                      back); LIE1 / LIE2 lying flat (eyes lit / dark); FRONT1 / FRONT2 facing us, arms loose
The sheet has NO walk, run, push, balance, hurt-recoil or spin ball: stand-ins are chosen below (a fuller Emerl sheet
would help; only the user can source one).

Size: he stands 43 px (R5_1, crest to soles; the fighting stance 40-44), 50 facing us; the sheet's own Sonic (in the
row of standing frames) is 39. Not scaled.

Abilities ("Copycat", the user's design; abilities.py extra 36, "ability_cycle"): four jump abilities, Y cycles which
one is active (double jump, dive, air dash, float). Slots (every engine's ability map has them: CD 45, 47, 46):
  41 the attack moves, one frame each, the code showing the active move's (its place in the cycle; speed 0):
     frame 0 "Double Jump" R5_10 (the flying leap) turned 45 degrees to point up (the user's pick, 2026-09-29: the
     old R7_2 read as his hurt pose; copy_heads.tilt, a pixel-art rotation), frame 1 "Dive" R5_9 (the kick down and forward, at Mecha
     Sonic's Spike Ball's angle), frame 2 "Air Dash" R5_10 (the flying leap, fist out).
  42 "Float" (hover-type, not an attack): FRONT1 / FRONT2 (arms loose, facing us, bobbing). Alternative: the spin
     swirl R6_3-R6_5 as a whirling hover.
  43 / 44 "Copy Switch" (Y, CD 46: the melee's pose): standing, eyes flash RED, standing again (R5_1, R5_2, R5_1): the
     sheet's own copy flash. In the air (44) the same, centred.
  Run: his one flying-leap frame (R5_10) with an energy ball behind him, as Metal Sonic's run: the sheet has none, so
  it is Metal Sonic's own "Hover" ball from Akimaca's Metal Sonic sheet (testmods/metal-sonic/249964.png, credited),
  exact pixels in the game's own Sonic blues and white (slots 3-6, as Metal's). Walk: the same hover (R5_10) and ball,
  its two smaller sizes only (WALK_ENERGY_SIZES; the stance bob looked jarring).
  Copy heads (the user, 2026-09-29; copy_heads.py): a head per move, the four loose variant heads at the right of the
  heads row, pasted as drawn: Double Jump [222,109,23,22] (crest swept up), Dive [296,109,20,22] (red eyes), Air Dash
  [246,110,25,21] (crest folded back into fins), Float [273,113,20,18] (crest folded flat). On slot 41's frames and
  the float, and on sets of his idle, stance, walk, run and copy flash per move (add_copy_heads below).
  Ball: the sheet has none (the "ball" row is his loose heads): the generic spin ball (tools/generic_ball.py:
  Sonic Mania's plain spin ball, SEGA's art) in his golds (BALL_COLOURS), as Chaos / Heavy / Bomb.

Nothing is redrawn, recoloured or resized: frames are cut as drawn. The name tag is our own lettering in the HUD font
the other extras use; the life icon / 1-UP are crops of H0; the signpost is H0 on the game's own board (the signpost
exception). Colours: 31 on the used frames: 3 in Sonic's own slots (exact), 22 exact in slots 74-95, 6 MERGED
(see PALETTE: near-blacks, 1-px shades and one near-identical orange).
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
import generic_ball  # noqa: E402
from sign_face import board_face  # noqa: E402

NAME = "Extra36"  # (its extras.py position)
SHEET = "../Emerl.png"
BACKGROUND = ["#95b1c8", "#546d8e", "#a8e61d"]  # the panel, the page and the measuring lines
SRC = Image.open(HERE / SHEET).convert("RGB")


def row(prefix, rects):
    return {f"{prefix}_{k}": list(r) for k, r in enumerate(rects)}


B = {  # frame -> [x, y, w, h] (its bounding box on the sheet; loose trail bits included)
    # heads: H0 three-quarter front, H1 turning (the others on the row are unused: see the notes)
    "H0": [18, 109, 19, 22], "H1": [43, 109, 20, 22],
    **row("R5", [(18, 197, 22, 40), (46, 194, 20, 43), (73, 197, 22, 40), (100, 195, 22, 42), (126, 194, 22, 43),
                 (154, 193, 23, 44), (184, 193, 23, 44), (212, 197, 23, 40), (241, 196, 21, 41), (270, 195, 33, 42),
                 (312, 194, 34, 42)]),
    **row("R6", [(18, 249, 26, 42), (49, 251, 30, 40), (89, 251, 41, 40), (134, 248, 35, 43), (176, 245, 47, 46),
                 (227, 251, 49, 41), (283, 254, 37, 37)]),
    "R7_0": [18, 310, 33, 39], "R7_1": [67, 310, 33, 39], "R7_2": [107, 303, 28, 46],
    "LIE1": [141, 306, 43, 21], "LIE2": [141, 328, 43, 21], "FRONT1": [197, 302, 28, 50], "FRONT2": [237, 302, 28, 50],
}


def f(*names):
    return [B[n] for n in names]


def run(prefix, first, last):
    return f(*[f"{prefix}_{k}" for k in range(first, last + 1)])


C = lambda frames: {"frames": frames, "anchor": "center"}
STANCE = run("R5", 3, 8)  # fighting stance, fists up
SWIRL = run("R6", 3, 5)  # the spin swirl
LEAP = f("R5_10")
# the energy ball behind his run: Metal Sonic's own run ball (the "Hover" balls of Akimaca's Metal Sonic sheet, as
# testmods/metal-sonic uses them: 12, 20, 28 px and back), exact pixels, pasted under the sheet in the working copy
# (config), cut as layers under R5_10. (It replaced our own drawn disc, 2026-09-30: no AI-drawn art.)
METAL_SHEET = "../metal-sonic/249964.png"
METAL_BG = {(30, 136, 24), (122, 202, 127)}  # that sheet's green cell and page
ENERGY_RECTS = {12: [329, 117, 12, 12], 20: [342, 113, 20, 20], 28: [363, 109, 28, 28]}
# its colours: the game's own Sonic blues and white, slots 3-6, exactly as Metal Sonic's config maps them
ENERGY_COLOURS = {"#4848b4": 3, "#6c6cd8": 4, "#9090fc": 5, "#fcfcfc": 6}
ENERGY_SIZES = [12, 20, 28, 20]
# his walk (the user, 2026-09-29: the stance bob looked jarring): the same hover and ball, the ball smaller at walking
# speeds, the two smaller sizes only (S3&K's Walk / Jog and CD's walk come from this one too)
WALK_ENERGY_SIZES = [12, 20, 20, 12]
ENERGY_CENTRE = (6, 24)  # its centre, px from R5_10's top left: behind his back and hips
LIE = f("LIE1")
FLASH = f("R5_1", "R5_2", "R5_1")  # eyes flash red: his copy

ANIMS = {
    "Stopped": {"frames": f("R5_1")},  # (also the Origins select card and the S3&K save screen picture)
    "Waiting": {"frames": STANCE, "loop": 0},
    "Looking Up": {"frames": f("FRONT1")},  # (no look-up pose: facing us)
    "Looking Down": {"frames": f("R6_1")},  # crouched low
    "Walking": {"frames": LEAP, "rot": 2},  # (no walk on the sheet: the run's hover, config() puts a smaller ball behind it)
    "Running": {"frames": LEAP, "rot": 2},  # (no run: the flying leap; config() puts the energy ball behind it)
    "Skidding": {"frames": f("R6_0")},  # guard
    "Super Peel Out": {"frames": LEAP, "rot": 2},  # (the energy ball too)
    "Bouncing": C(f("R7_2")),
    "Hurt": C(LIE),
    "Dying": C(f("LIE2")),  # eyes dark
    "Drowning": C(f("LIE2")),
    "Fan Rotate": C(SWIRL),
    "Breathing": C(f("R7_2")),
    "Pushing": {"frames": f("R6_2"), "align": True},  # the lunge punch
    "Flailing 1": {"frames": f("R7_1", "R7_0"), "align": True},  # claws out
    "Flailing 2": {"frames": f("R7_0", "R7_1"), "align": True},
    "Hanging": C(f("R7_2")),
    "Clinging On": C(f("R7_2")),
    "Corkscrew H": {"frames": SWIRL},
    "Water Slide": C(LIE),
    "Continue": {"frames": STANCE},
    "Continue Up": {"frames": f("R7_2")},
    "Super Transform": {"frames": f("R5_0", "R5_1", "R5_2", "R5_1"), "loop": 1},  # powering up, the red flash
}
S2_ONLY = {
    "Bored!": {"frames": f("R5_1", "R5_0", "R5_1"), "loop": 0},  # powering down a moment
    "Flailing 3": {"frames": f("R7_1", "R7_0"), "align": True},
    "Grabbed": C(f("R6_1")),
    "Twirl H": {"frames": SWIRL, "rot": 2},
}
CD_ONLY = {name: {"frames": LEAP} for name in ["Launcher"] + [f"3D Ramp {n}" for n in range(1, 7)]}

APPENDED = {
    # the attack moves (CD 45): the code shows the active one's frame, its place in the cycle (abilities.py ability_cycle).
    # Each with its move's head (copy_heads.py; add_copy_heads puts them in): frame 0 the double jump, the flying leap
    # turned 45 degrees to point up (the user's pick, 2026-09-29: R7_2 read as his hurt pose), frame 1 the dive kick,
    # frame 2 the air dash's leap
    "41": {"name": "Copy Attack", "frames": f("R5_10", "R5_9", "R5_10"), "anchor": "center", "speed": 0},
    "42": {"name": "Float", "frames": f("FRONT1", "FRONT2"), "anchor": "center", "speed": 30},  # (CD 47; the float's head)
    "43": {"name": "Copy Switch", "frames": FLASH, "speed": 0},  # Y: the code picks the frame (CD 46)
    "44": {"name": "Copy Switch Air", "frames": FLASH, "anchor": "center", "speed": 0},
}
# alternatives for the Float, if the user prefers a whirl: {"frames": SWIRL, "anchor": "center", "speed": 120}
EXTRA_GROUPS = {"alt Float (swirl)": SWIRL}  # (only for the contact sheet)


PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
HEAD = B["H0"]  # 19x22, three-quarter front: crest, ear disc, blue visor
ELEMENTS = {
    "life_icon": {"rect": [HEAD[0] + 2, HEAD[1] + 5, 16, 16], "trim": False},  # the visor and ear (crest tip cut)
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("EMERL")},
    "monitor_1up": {"rect": [HEAD[0] + 2, HEAD[1] + 6, 16, 14], "trim": False},
    # no signpost art: H0 on the game's own board (Items2), enlarged 1.1x nearest-neighbour to fill its face area
    # (the user's signpost exception; tools/sign_face.py)
    "sign_face": board_face(HEAD, 1.1),
    "mini_1": {"rect": B["H0"], "remap": PLUS_128},  # continue icons: two of the sheet's loose heads
    "mini_2": {"rect": B["H1"], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B["R5_1"], "remap": PLUS_128},
    "end_pose_1": {"rect": B["R7_2"], "remap": PLUS_128},  # the leap
    "end_pose_2": {"rect": B["FRONT1"], "remap": PLUS_128},  # facing us
    "end_pose_3": {"rect": B["R6_2"], "remap": PLUS_128},  # the lunge punch (no big pose on the sheet)
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128}
       for n, k in enumerate(("R5_1", "R5_2", "R5_3", "R6_0", "R6_2", "FRONT2"), 1)},
}

# The used frames and UI crops have 31 colours (no pure black). Three are exactly Sonic's: #e0e0e0 (slot 6), #e00000
# and #800000 (12, 13: the red-eye flash). 22 keep their exact values in slots 74-95, and 6 are MERGED into their
# nearest slot (the faithful-art rule's colour exception): three near-blacks into #201f20 (#202020 418 px, #212021 24,
# #211c21 1: 1-3 RGB steps apart, invisible), #e7e7e7 and #b56942 (1 px each, R5_0) and #ee8627 into #f09030 (105 px,
# 14 steps: two near-identical oranges). No merge at all is possible by dropping the dark-eyed frames (R5_0, LIE2:
# #404055, #606080, #e7e7e7, #b56942), then only the near-blacks merge.
PALETTE = {
    "74": "#653a01", "75": "#a76102", "76": "#a56121", "77": "#e39500", "78": "#f09030", "79": "#eecd82",  # golds
    "80": "#683820", "81": "#b05830", "82": "#c09b63", "83": "#d9c49b",  # browns, tans
    "84": "#483820", "85": "#524923", "86": "#605028", "87": "#776b33", "88": "#807040",  # the olive joints / hands
    "89": "#201f20",  # his outline
    "90": "#0f47c0", "91": "#3e8ed9", "92": "#8ad4fd",  # the visor's blues
    "93": "#404055", "94": "#606080",  # the dark (powered-down) visor
    "95": "#ff7575",  # the red eyes' shine
}
KEY_COLOURS = {"#e0e0e0": 6, "#e00000": 12, "#800000": 13, **{c: int(s) for s, c in PALETTE.items()}}
MERGED = {"#202020", "#212021", "#211c21", "#e7e7e7", "#b56942", "#ee8627"}

# the generic ball in his own golds (outline: generic_ball.outline_for, a shade of his own just darker than the body)
BALL_COLOURS = generic_ball.colours(dark="#a76102", mid="#e39500", light="#eecd82", shine="#e0e0e0",
                                    palette=list(PALETTE.values()))


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet in the slot of its nearest key colour (MERGED among them)."""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in SRC.getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


def used_rects():
    return (list(B.values()) + [el["rect"] for el in ELEMENTS.values() if "rect" in el and "base" not in el]
            + [ELEMENTS["sign_face"]["rect"]])


def check_colours():
    """Every colour in a built frame or UI element has a slot of its own, but the MERGED ones."""
    used = set()
    for x, y, w, h in used_rects():
        used |= {"#%02x%02x%02x" % rgb for _, rgb in SRC.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    used |= set(BALL_COLOURS.values())
    missing = used - set(KEY_COLOURS) - set(BACKGROUND) - MERGED
    if missing:
        sys.exit(f"emerl: frame colours without a slot of their own: {sorted(missing)}")


CREDIT = ("Emerl sprites by Xeric and Deebs, the Mod.Gen Project Team. Emerl (c) SEGA - "
          "https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/143123/")


def energy_ball(size):
    """Metal Sonic's run ball of `size` px (ENERGY_RECTS), cut from Akimaca's sheet as drawn: RGBA, its green cell clear."""
    x, y, w, h = ENERGY_RECTS[size]
    img = Image.open(HERE / METAL_SHEET).convert("RGBA").crop((x, y, x + w, y + h))
    img.putdata([(0, 0, 0, 0) if p[:3] in METAL_BG else p for p in img.getdata()])
    return img


def add_energy_balls(source):
    """The run's energy balls (Metal Sonic's, one of each size) in a strip under the working copy `source` (the sheet
    itself is untouched). Returns the running frames: each ball layered behind R5_10."""
    img = Image.open(source).convert("RGB")
    sizes = sorted(set(ENERGY_SIZES) | set(WALK_ENERGY_SIZES))
    y = img.height + 2
    out = Image.new("RGB", (img.width, y + max(sizes) + 2), tuple(int(BACKGROUND[0][i:i + 2], 16) for i in (1, 3, 5)))
    out.paste(img, (0, 0))
    rects, x = {}, 2
    for s in sizes:
        ball = energy_ball(s)
        out.paste(ball, (x, y), ball)
        rects[s] = [x, y, s, s]
        x += s + 2
    out.save(source)
    cx, cy = ENERGY_CENTRE
    layered = lambda sizes: [{"layers": [{"rect": rects[s], "at": [cx - s // 2, cy - s // 2]},
                                         {"rect": B["R5_10"], "at": [0, 0]}], "anchor_layer": 1} for s in sizes]
    return layered(ENERGY_SIZES), layered(WALK_ENERGY_SIZES)


# Copy heads (the user's request, 2026-09-29; copy_heads.py): a head of his own per Copycat move, the sheet's four
# loose variant heads, pasted onto his frames at build time. The attack frames and the float have their move's head
# (above); his idle, stance, walk, run (and peel out) and copy flash come in four sets, one per move, at slots
# COPY_HEAD_SLOT + COPY_HEAD_STRIDE * move + place in COPY_HEAD_ANIMS (CD one on: cd_config.py; S3&K from the
# "copy_heads" swap table: build_s3k_art.py). The game shows the active move's set in place of the game's own while
# animating and drawing (abilities.py copy_head_in_out, build_soniccd.cd_copy_heads, the DLL's CopyHeadShow). The rest
# (hurt, push, look up / down, skid, teeter...) keep his default head. In the copy flash, the red-eyed middle frame
# (R5_2) stays as drawn: the flash, then the new head.
from abilities import ABILITIES, COPY_HEAD_SLOT, COPY_HEAD_STRIDE, cycle  # noqa: E402
COPY_MOVES = cycle(next(i for i, c in ABILITIES.items() if c.get("copy_heads")))  # (ability_cycle's order)
# the animations a set has, in abilities.COPY_HEAD_ANIMS' order (numbers: appended ones)
COPY_HEAD_ANIMS = ["Stopped", "Waiting", "Walking", "Running", "Super Peel Out", "43", "44"]


def add_copy_heads(source, anims, appended):
    """The copy-head frames (copy_heads.py), in a strip under the working copy `source` (the sheet itself is
    untouched), each positioned by the frame it came from (its anchor box: the pivot stays put). Puts each move's head
    on the attack frames and the float, and returns (the variant animations {slot: spec}, the S3&K swap table: per
    move {frame key: its frame})."""
    import copy_heads
    import sheet2ani
    img = Image.open(source).convert("RGBA")
    bg = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in BACKGROUND}
    made = {}  # (frame key, move or "tilt") -> (RGBA image, anchor box in it)

    def render(fr):
        if isinstance(fr, dict) and "layers" in fr:
            im, mask, anchor = sheet2ani.cut_layered(img, fr, bg)
        else:
            im, mask = sheet2ani.cut_frame(img, fr, bg)
            anchor = (0, 0, im.width, im.height)
        im = im.copy()
        im.putalpha(mask)
        return im, anchor

    def make(fr, move):
        key = (sheet2ani.frame_key(fr), move)
        if key not in made:
            im, (ax, ay, aw, ah) = render(fr)
            if move == "tilt":  # the double jump: the leap with its head, turned 45 degrees to point up
                im = copy_heads.tilt(copy_heads.swap_head(im, "double_jump")[0], 45)
                made[key] = (im, None)
            else:
                im, (ox, oy) = copy_heads.swap_head(im, move)
                bx, by, _, _ = im.getbbox()
                made[key] = (im.crop(im.getbbox()), (ax + ox - bx, ay + oy - by, aw, ah))
        return key

    specs = {
        "41": [make(B["R5_10"], "tilt"), make(B["R5_9"], "screw_kick"), make(B["R5_10"], "jet_dash")],
        "42": [make(fr, "umbrella") for fr in appended["42"]["frames"]],
    }
    sets = []
    for move in COPY_MOVES:
        sets.append({})
        for name in COPY_HEAD_ANIMS:
            spec = appended[name] if name in appended else anims[name]
            sets[-1][name] = [fr if fr == B["R5_2"] else make(fr, move) for fr in spec["frames"]]
    # the strip: rows of cells under the sheet
    x, y, row_h, width = 2, img.height + 2, 0, img.width
    placed = []
    for key, (im, anchor) in made.items():
        if x + im.width + 2 > width:
            x, y, row_h = 2, y + row_h + 2, 0
        placed.append((key, x, y))
        x, row_h = x + im.width + 2, max(row_h, im.height)
    out = Image.new("RGB", (width, y + row_h + 2), tuple(int(BACKGROUND[0][i:i + 2], 16) for i in (1, 3, 5)))
    out.paste(img.convert("RGB"), (0, 0))
    frame_of = {}
    for key, x, y in placed:
        im, anchor = made[key]
        out.paste(im, (x, y), im)
        rect = [x, y, im.width, im.height]
        frame_of[key] = rect if anchor is None else {"rect": rect, "anchor_box": [x + anchor[0], y + anchor[1],
                                                                                  anchor[2], anchor[3]]}
    out.save(source)
    pick = lambda fr: frame_of[fr] if isinstance(fr, tuple) and fr in frame_of else fr
    appended["41"] = dict(appended["41"], frames=[pick(k) for k in specs["41"]])
    appended["42"] = dict(appended["42"], frames=[pick(k) for k in specs["42"]])
    variants, swap = {}, []
    for m, move in enumerate(COPY_MOVES):
        swap.append({})
        for j, name in enumerate(COPY_HEAD_ANIMS):
            spec = appended[name] if name in appended else anims[name]
            like = spec.get("name", name)
            frames = [pick(k) for k in sets[m][name]]
            variants[str(COPY_HEAD_SLOT + COPY_HEAD_STRIDE * m + j)] = dict(
                {k: v for k, v in spec.items() if k not in ("name", "frames")},
                name=f"{like} ({move} head)", like=like, frames=frames)
            for old, new in zip(spec["frames"], frames):
                if old != new:
                    swap[-1][json.dumps(old, sort_keys=True)] = new
    return variants, swap


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): no celebration on the sheet: the leap, then facing us (bobbing)
S3K_VICTORY = {"frames": f("R7_2", "FRONT1", "FRONT2"), "pose": 1}


def config(game):
    check_colours()
    ex = REPO / "extracted" / game
    source = HERE / "build" / f"source_{game}.png"
    ball = generic_ball.source_with_ball(HERE / SHEET, BALL_COLOURS, BACKGROUND[0], source)
    run_frames, walk_frames = add_energy_balls(source)
    anims = dict(ANIMS, **(dict(S2_ONLY, **CD_ONLY) if game == "Sonic2" else {}))
    anims["Running"] = dict(anims["Running"], frames=run_frames)
    anims["Super Peel Out"] = dict(anims["Super Peel Out"], frames=run_frames)
    anims["Walking"] = dict(anims["Walking"], frames=walk_frames)
    appended = json.loads(json.dumps(APPENDED))
    variants, swap = add_copy_heads(source, anims, appended)
    cfg = {"name": NAME, "credit": CREDIT,
           "source": f"build/source_{game}.png", "feet_y": 20, "background": BACKGROUND, "palette": PALETTE,
           "colours": dict(all_colours(), **ENERGY_COLOURS),
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": anims,
           "appended_animations": dict(appended, **variants),
           # the copy heads for S3&K (build_s3k_art.py): per move, each frame's copy with that move's head
           "copy_heads": {"slot": COPY_HEAD_SLOT, "stride": COPY_HEAD_STRIDE, "swap": swap}}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": f"{NAME}SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {}}}]  # (the ball: generic_ball.apply)
        cfg["ui"] = [{"name": f"{NAME}_UI", "manifest": f"{NAME}_ui.json", "elements": ELEMENTS,
                      "out": f"build/{NAME}_UI.gif"},
                     {"name": f"{NAME}_Ending", "manifest": f"{NAME}_ending.json", "elements": ENDING,
                      "out": f"build/{NAME}_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
    return generic_ball.apply(cfg, ball, game)  # jump, Spin Dash, special stages, CD's and S3&K's


if __name__ == "__main__":
    for game, out in (("Sonic1", "emerl.json"), ("Sonic2", "emerl_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
