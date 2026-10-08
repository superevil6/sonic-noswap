#!/usr/bin/env python3
"""Writes Big the Cat's sheet2ani configs (big.json for Sonic 1, big_s2.json for Sonic 2; CD's and S3&K's come from the
Sonic 2 one).

Big the Cat, extra 3 (file "Extra3", build ID 9), base character Sonic. Public (credit in mods/NoSwap/README.md).
Sheet: testmods/Big2.png (782x1048), "Remix: Bigger, Better, Refined" by DBurraki, "Credit & Many Thanks to... Cylent
Nite", found as a re-upload by ajlew on DeviantArt (see SOURCE.txt and "testmods/Big2 Link.txt"). Its terms, printed on
the sheet: "DO: Use this sheet as you like, but GIVE CREDIT. DO NOT: Claim this sheet as your own or otherwise steal."
(The old sheet's config, by Oppolo / Cylent Nite / AkumaTh / Reo, is kept unused as make_configs_old.py.)

The sheet: a transparent page, labelled sections. He faces right. Frame names used here (sheet boxes in B):
  gestures    STAND (standing), (standing with Froggy on his head: not used), BEHIND (hands behind his back: head and
              body are two drawings), SIT, SCRATCH (scratching his head), POINT, SIT2 (sitting, scratching), WAVE,
              DOWN (head tipped back, ears flat: his look-up)
  actions     (a walking step: not used), R1-R3 (his stride, arms swinging), SKID (startled, leaning back, mouth open),
              UMB_STAND (under his umbrella), PANIC (hands on his head), UMB (hanging from the open umbrella, legs
              dangling: the float), LEAP (a leap, arms down), FLAIL1 / FLAIL2 (arms spread, legs kicking: the swim),
              UMB_WALK1-4 (walking under the umbrella: not used)
  attacks     the overhead fishing-rod cast: CAST_BACK (rod swung back, lure behind), two swings (not used), CAST_UP (the
              line up over his head, lure out in front), reeled in (not used); PUSH (lunging forward, arms out), FLOP (flat on
              his belly); the loose lures LURE1-LURE3 (5x6 / 6x5 green and gold drawings, the lure at the line's end)
  zomg injuries  HURT1-HURT3 (tumbling)
  fishing     sitting and casting (FISH: the line out, sitting), standing with the rod (not used)
  alt colour palettes  only "Original" (the user's pick): the frames above are all in it
  emotions, froggy     not used (Froggy is kept for a later Froggy shield)

Size: he stands 66 px tall (STAND), against Sonic's 40. Not scaled (the user: no scaling).

Frames are whole drawings: build/source.png is a working copy holding each used frame's pixels (its drawings, plus any
loose speck lying wholly inside its box, copied exactly) in a cell of its own on a solid background (#004040, not one
of his colours: the sheet itself is transparent and his belly is opaque white), so a rect crop never catches a
neighbour. The loose lures in the cast frames' boxes are left out of them (EXCLUDE): the lure is the projectile.
Each frame is pivoted on his belly (the middle of its #e0e0e0 belly-white pixels), so he doesn't slide sideways when
his arms or tail swing out (FLOP, lying flat, on its middle). Only the frames used are copied (B).

Abilities (tools/abilities.py 9; wired there, in build_soniccd.py and in the S3&K DLL):
  - jump in mid-air, out of water: the parasol float (slot 42 "Umbrella": UMB).
  - jump in mid-air UNDERWATER: a swim stroke, repeatable (abilities.py water_swim; slot 47 "Swim": FLAIL1 / FLAIL2,
    arms and legs paddling).
  - Y: Fishing Cast, a real projectile (abilities.py "shot"): the lure, aimed with the d-pad in 5 directions. Its throw
    pose: CAST_BACK then CAST_UP (slots 43 / 44; CD 46).
  - ball: the sheet has none: the generic spin ball (tools/generic_ball.py: Sonic Mania's plain spin ball, SEGA's art) in his
    purples, 40 px (he's big: Mania's 30 px ball resized nearest-neighbour, the user's exception 2026-09-30).

Colours: his frames and the lure use 39 colours; the extras have 22 own slots (74-95). Exact in Sonic's own slots:
#e0e0e0 -> 6, #404040 -> 9, #800000 -> 13. The 20 most used of the rest and the lure's two main greens get own slots,
exact; the others (each at most 378 px over all his frames: shades of gold, grey and purple, the lure's 1 px highlight,
the skid frame's mouth reds) go to the nearest own slot, the faithful-art rule's colour exception (MERGED, printed with
pixel counts). The "BIG" HUD tag isn't on the sheet: our lettering in the HUD font the other extras use.
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
import generic_ball  # noqa: E402
import hud_font  # noqa: E402
from sign_face import board_face  # noqa: E402

NAME = "Extra3"
SHEET = HERE.parent / "Big2.png"
SOURCE = "build/source.png"
BACKGROUND = ["#004040"]
BG = (0x00, 0x40, 0x40)
RGBA = np.array(Image.open(SHEET).convert("RGBA"))
SRC = RGBA[..., :3]
SOLID = RGBA[..., 3] > 0

B = {  # name -> the tight boxes [x, y, w, h] of its drawings on the sheet (the body first)
    "STAND": [[171, 26, 79, 66]], "BEHIND": [[93, 48, 71, 44], [120, 26, 37, 23]],
    "SIT": [[252, 26, 81, 61]], "SCRATCH": [[99, 93, 75, 66]], "SIT2": [[263, 94, 81, 61]], "DOWN": [[268, 168, 79, 60]],
    "R1": [[92, 258, 95, 60]], "R2": [[188, 255, 95, 67]], "R3": [[283, 258, 95, 66]],
    "SKID": [[11, 332, 79, 66]], "UMB_STAND": [[93, 320, 87, 84]], "PANIC": [[198, 328, 76, 76]],
    "UMB": [[284, 329, 79, 98]], "LEAP": [[39, 415, 68, 77]], "FLAIL1": [[118, 413, 96, 62]],
    "FLAIL2": [[226, 425, 96, 66]],
    "CAST_UP": [[265, 614, 71, 106]], "CAST_BACK": [[12, 735, 71, 104]],
    "PUSH": [[256, 724, 96, 62]], "FLOP": [[246, 785, 119, 54]],
    "HURT1": [[11, 865, 69, 64]], "HURT2": [[82, 863, 62, 69]], "HURT3": [[150, 863, 56, 75]],
    "FISH": [[665, 270, 100, 61]],
    "WAVE1": [[98, 160, 82, 66]], "WAVE2": [[182, 162, 84, 66]],  # the gestures' wave (S3&K's act clear)
}
# the loose lures (the Fishing Cast's projectile art, abilities.py 9 "shot"); inside the cast frames' boxes, left out of them
LURES = [[734, 419, 5, 6], [220, 628, 5, 6], [30, 640, 6, 5]]
EXCLUDE = LURES + [[331, 642, 6, 5]]

MIDDLE = {"FLOP"}  # (lying flat: pivoted on its middle, not the belly)
LABELS, _ = ndimage.label(SOLID, structure=np.ones((3, 3)))
OBJECTS = ndimage.find_objects(LABELS)


def box_of(sl):
    return [sl[1].start, sl[0].start, sl[1].stop - sl[1].start, sl[0].stop - sl[0].start]


def frame_pixels(boxes):
    """The pixels of the listed drawings (each must be one whole drawing's tight box), plus every loose drawing lying
    wholly inside one of their boxes (specks: a whisker, a sparkle), except the EXCLUDE ones (the lures)."""
    labs = set()
    for x, y, w, h in boxes:
        whole = [lab for lab in np.unique(LABELS[y:y + h, x:x + w]) if lab and box_of(OBJECTS[lab - 1]) == [x, y, w, h]]
        if not whole:
            raise SystemExit(f"big: {[x, y, w, h]} isn't the tight box of a whole drawing")
        for lab in np.unique(LABELS[y:y + h, x:x + w]):
            if not lab:
                continue
            bx, by, bw, bh = box_of(OBJECTS[lab - 1])
            if bx >= x and by >= y and bx + bw <= x + w and by + bh <= y + h and [bx, by, bw, bh] not in EXCLUDE:
                labs.add(lab)
    ys, xs = np.nonzero(np.isin(LABELS, list(labs)))
    return list(zip(xs.tolist(), ys.tolist()))


def source_sheet():
    """Each frame's pixels, copied exactly, in a cell of its own (shelves 512 wide; STAND first, at 2,2: extras.py's
    card rect). Returns {name: (rect in the copy, pivot x in it)}."""
    cells, x, y, shelf = {}, 2, 2, 0
    for name, boxes in B.items():
        pts = frame_pixels(boxes)
        fx, fy = min(p[0] for p in pts), min(p[1] for p in pts)
        w, h = max(p[0] for p in pts) - fx + 1, max(p[1] for p in pts) - fy + 1
        if x + w + 2 > 512:
            x, y, shelf = 2, y + shelf + 3, 0
        belly = [a for a, b in pts if tuple(SRC[b, a]) == (0xE0, 0xE0, 0xE0)]
        pivot = round(sum(belly) / len(belly)) - fx if belly and name not in MIDDLE else w // 2
        cells[name] = (pts, fx, fy, [x, y, w, h], pivot)
        x += w + 3
        shelf = max(shelf, h)
    out = np.zeros((y + shelf + 2, 512, 3), np.uint8)
    out[...] = BG
    for pts, fx, fy, (cx, cy, _, _), _ in cells.values():
        for a, b in pts:
            out[cy + b - fy, cx + a - fx] = SRC[b, a]
    for _, _, _, (cx, cy, w, h), _ in cells.values():
        out[cy:cy + h, cx:cx + w] = page_white(out[cy:cy + h, cx:cx + w])
    (HERE / "build").mkdir(exist_ok=True)
    Image.fromarray(out).save(HERE / SOURCE)
    return {name: (c[3], c[4]) for name, c in cells.items()}


WHITE = (0xFF, 0xFF, 0xFF)


def page_white(cell):
    """The sheet's white page, sorted out (the upload's transparency is a flood fill of the white page from outside):
    - his white chest fur (#ffffff), which the fill reached through the open fur strokes on his chest in some frames
      (STAND, BEHIND, DOWN, SKID, LEAP, UMB, FISH) and cut out, is put back: the see-through pixels inside his outline
      (inside it once gaps up to 6 px are closed, with drawing on all four sides of them; patches of 20 px or more)
      become #ffffff again, the colour the fill took out;
    - the white page the fill didn't reach, enclosed between an arm, his tail and his body (patches of opaque #ffffff of
      10 px or more: R1-R3, FLAIL, PANIC, PUSH, HURT...), is background, as the page round him is.
    Nothing else changes (his #e0e0e0 belly and 1-4 px #ffffff highlights stay)."""
    cell = cell.copy()
    bg = (cell == BG).all(axis=2)
    white = (cell == WHITE).all(axis=2)
    lab, n = ndimage.label(white, structure=np.ones((3, 3)))
    sizes = ndimage.sum(white, lab, range(1, n + 1))
    holes = np.isin(lab, [k + 1 for k in range(n) if sizes[k] >= 10])
    solid = ~bg
    r = 3
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    padded = np.pad(solid, r + 1)
    inside = ndimage.binary_fill_holes(ndimage.binary_closing(padded, structure=xx * xx + yy * yy <= r * r))
    inside = inside[r + 1:-r - 1, r + 1:-r - 1]
    walled = (np.maximum.accumulate(solid, axis=1) & np.maximum.accumulate(solid[:, ::-1], axis=1)[:, ::-1]
              & np.maximum.accumulate(solid, axis=0) & np.maximum.accumulate(solid[::-1], axis=0)[::-1])
    chest = inside & walled & bg
    lab, n = ndimage.label(chest)
    sizes = ndimage.sum(chest, lab, range(1, n + 1))
    chest = np.isin(lab, [k + 1 for k in range(n) if sizes[k] >= 20])
    cell[holes] = BG
    cell[chest] = WHITE
    return cell


CELLS = source_sheet()
R = {name: rect for name, (rect, _) in CELLS.items()}
assert R["STAND"] == [2, 2, 79, 66], R["STAND"]
assert CELLS["WAVE1"] == ([105, 374, 82, 66], 54), CELLS["WAVE1"]  # (extras.py's "card" rect and pivot)


def f(*names):
    """Frames pivoted on his belly (sheet2ani "pivot_x" on a single layer: the frame is the cell's crop)."""
    return [{"layers": [{"rect": CELLS[n][0], "at": [0, 0]}], "anchor_layer": 0, "pivot_x": CELLS[n][1]} for n in names]


C = lambda frames, **kw: dict({"frames": frames, "anchor": "center"}, **kw)
STRIDE = f("R1", "R2", "R3")  # his stride, arms swinging (the sheet has no other walk)
SWIM = f("FLAIL1", "FLAIL2")  # arms spread, legs kicking: paddling
BELT = {"FLAIL1": 39, "FLAIL2": 39, "LEAP": 33}  # the belt's top row at the pivot column, in the frame


def belted(*names):
    """Frames placed by one point: 8 px above the belt's top at the belly pivot (sheet2ani anchor_box, a 1x1 box; with
    "center" that point is the frame's origin, where FLAIL1's centre was), so his body stays put when the pose's height
    or tail changes."""
    return [{"rect": CELLS[n][0], "anchor_box": [CELLS[n][0][0] + CELLS[n][1], CELLS[n][0][1] + BELT[n] - 8, 1, 1]}
            for n in names]


# the water swim's stroke: reach (arms spread), pull (arms swept down to his sides: LEAP), glide (arms out, legs
# trailing). The old FLAIL1 / FLAIL2 pair only moved the legs and bobbed 2 px (centred on frames of unequal height)
STROKE = belted("FLAIL1", "LEAP", "FLAIL2")
IDLE = f("STAND", "BEHIND")

ANIMS = {
    "Stopped": {"frames": f("STAND")},  # (also the S3&K save screen picture; the Origins card is extras.py's "card")
    "Waiting": {"frames": IDLE, "loop": 0},  # hands to his back and back
    "Looking Up": {"frames": f("DOWN")},  # head tipped back, ears flat, eyes up (the sheet's "head bowed" read as looking
    # up in-game, the user; it's LEAP's head); also S3&K's Look Up
    "Looking Down": {"frames": f("SIT")},  # sitting down: lowered, clearly a crouch (also S3&K's Crouch)
    "Walking": {"frames": STRIDE, "rot": 2},
    "Running": {"frames": STRIDE, "rot": 2},
    "Skidding": {"frames": f("SKID")},
    "Super Peel Out": {"frames": STRIDE, "rot": 2},
    "Bouncing": C(f("LEAP")),
    "Hurt": C(f("HURT1")),
    "Dying": C(f("HURT2")),
    "Drowning": C(f("HURT3")),
    "Fan Rotate": C(SWIM),
    "Breathing": C(f("SKID")),  # mouth open
    "Pushing": {"frames": f("PUSH")},  # lunging in, arms out
    "Flailing 1": {"frames": f("PANIC", "SKID")},
    "Flailing 2": {"frames": f("PANIC", "SKID")},
    "Hanging": C(f("PANIC")),  # arms up
    "Clinging On": C(f("PANIC")),
    "Corkscrew H": {"frames": STRIDE},
    "Water Slide": C(f("FLOP")),  # on his belly
    "Continue": {"frames": IDLE},
    "Continue Up": C(f("LEAP")),
    "Super Transform": C(f("LEAP")),
}
S2_ONLY = {
    "Flailing 3": {"frames": f("PANIC", "SKID")},
    "Grabbed": C(f("HURT1")),
    "Twirl H": {"frames": STRIDE, "rot": 2},
    "Bored!": {"frames": f("SIT", "SIT2"), "loop": 0},  # sits down and scratches his head
}

# The Fishing Cast's pose (slots 43 / 44, CD 46): the rod swung back, then the line up over his head (the shot shows the
# slots' last frame; abilities.py 9's melee_reach: 2 entries). The lure itself is the shot (LURES).
CAST = f("CAST_BACK", "CAST_UP")
APPENDED = {
    "42": C(f("UMB"), name="Umbrella", speed=60),  # the parasol float (CD 47)
    "43": {"name": "Cast", "frames": CAST, "speed": 0},  # the code picks the frame
    "44": C(CAST, name="Cast Air", speed=0),
    "47": C(STROKE, name="Swim", speed=48),  # the water swim's stroke (abilities.py water_swim; CD 48, S3&K extra 5)
}

# ---------------------------------------------------------------- HUD, signpost, continue, ending
S = R["STAND"]
HEAD = [S[0] + 34, S[1] + 5, 16, 16]  # his face (eyes and muzzle), a crop of the standing frame
FACE = [S[0] + 22, S[1], 40, 26]  # his head, the top of the standing frame
PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
ELEMENTS = {
    "life_icon": {"rect": HEAD, "trim": False},
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("BIG")},  # Rayan C.'s letters (tools/hud_font.py)
    "monitor_1up": {"rect": [HEAD[0], HEAD[1] + 1, 16, 14], "trim": False},
    # no signpost art: his head on the game's own board (the user's signpost exception; tools/sign_face.py)
    "sign_face": board_face(FACE),
    # no continue icons and nothing shrunk: crops of his head from two frames
    "mini_1": {"rect": [S[0] + 26, S[1], 34, 24], "remap": PLUS_128},
    "mini_2": {"rect": [R["SCRATCH"][0] + 20, R["SCRATCH"][1], 40, 24], "remap": PLUS_128},
}
def crop(name, w, h, top=False):
    """A crop of frame `name`, at most w x h: w columns round his belly (its pivot), its bottom h rows (the feet kept; an
    ear tip may go), or with top its top h rows (the head kept; the feet may go)."""
    (x, y, fw, fh), p = CELLS[name]
    cw, ch = min(w, fw), min(h, fh)
    cx = min(max(x + p - cw // 2, x), x + fw - cw)
    return [cx, y if top else y + fh - ch, cw, ch]


# Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames. Their boxes on the shared
# Ending/Objects_NoSwap sheet (and Sonic 2's Tornado ending) are sized by the largest of every extra's
# (build_sonic1.UI_SHEETS), and his old art set three of them (end_pose_2 91 rows, good_4 / good_5 68): his new ones are
# exactly those heights, so no other package's boxes move. He's big, so they're crops of his frames that fit the boxes
# (round his belly: his tail and a hand cut off; the medium pose, the cast, loses the top of its line).
ENDING = {
    "end_idle": {"rect": crop("STAND", 46, 62), "remap": PLUS_128},
    "end_pose_1": {"rect": crop("SCRATCH", 68, 61), "remap": PLUS_128},
    "end_pose_2": {"rect": crop("CAST_UP", 71, 91), "remap": PLUS_128},  # the line up over his head (71x91)
    "end_pose_3": {"rect": R["FISH"], "remap": PLUS_128},  # sitting, fishing (whole: fits its 171x177)
    **{f"good_{n}": {"rect": crop(k, w, h, top), "remap": PLUS_128}
       for n, (k, w, h, top) in enumerate((("STAND", 46, 62, False), ("BEHIND", 46, 60, False),
                                           ("SCRATCH", 46, 59, False), ("LEAP", 58, 68, True), ("LEAP", 60, 68, True),
                                           ("SIT2", 58, 60, False)), 1)},
}
ENDING_SIZES = {"end_pose_2": (71, 91), "good_4": (58, 68), "good_5": (60, 68)}  # (checked in __main__: see above)

# ---------------------------------------------------------------- colours
# 22 own slots: the 20 most used body colours (not in Sonic's slots) and the lure's two main greens, exact
PALETTE = {
    "74": "#22064f", "75": "#462e81", "76": "#490eab", "77": "#301f56", "78": "#320a78", "79": "#5a3aa1",
    "80": "#7a5405", "81": "#7b7d7b", "82": "#634721", "83": "#7454c2", "84": "#bdbebd", "85": "#a5a2a5",
    "86": "#ab7607", "87": "#7e5b2a", "88": "#c58f41", "89": "#a27432", "90": "#d49409", "91": "#ffffff",
    "92": "#5b11d7", "93": "#eeb848", "94": "#077c35", "95": "#0aa200",
}
SONIC_EXACT = {"#e0e0e0": 6, "#404040": 9, "#800000": 13}  # (the same in Sonic's S1, S2 and CD palettes)
KEY_COLOURS = {"#000000": 1, "#fcfc00": 15, **SONIC_EXACT, **{c: int(s) for s, c in PALETTE.items()}}
# the generic ball in his own purples (outline: generic_ball.outline_for, a shade of his just darker than the body)
BALL_COLOURS = generic_ball.colours(dark="#320a78", mid="#490eab", light="#7454c2", shine="#e0e0e0",
                                    palette=list(PALETTE.values()))


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def all_colours():
    """KEY_COLOURS, plus every other colour of the working copy and the lures in the nearest own slot (or one of Sonic's
    exact ones). MERGED: those, with pixel counts."""
    targets = {**{c: int(s) for s, c in PALETTE.items()}, **SONIC_EXACT}
    out = dict(KEY_COLOURS)
    counts = {"#%02x%02x%02x" % rgb: n for n, rgb in Image.open(HERE / SOURCE).getcolors(1 << 16)}
    for x, y, w, h in LURES:
        for c in (SRC[y:y + h, x:x + w][SOLID[y:y + h, x:x + w]]):
            k = "#%02x%02x%02x" % tuple(int(v) for v in c)
            counts[k] = counts.get(k, 0) + 1
    merged = {}
    for c, n in counts.items():
        if c in out or c in BACKGROUND:
            continue
        near = min(targets, key=lambda t: sum((a - b) ** 2 for a, b in zip(hexrgb(t), hexrgb(c))))
        out[c] = targets[near]
        merged[c] = (near, n)
    return out, merged


COLOURS, MERGED = all_colours()
CREDIT = ("Big the Cat sprites: \"Remix: Bigger, Better, Refined\" by DBurraki, with credit and many thanks to Cylent Nite "
          "(sheet found as a re-upload by ajlew: https://www.deviantart.com/ajlew/art/Big-The-Cat-Sprite-Sheet-717939798). "
          "Big the Cat (c) SEGA / Sonic Team")


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the gestures' wave, both frames looping
S3K_VICTORY = {"frames": f("WAVE1", "WAVE2"), "pose": 0}


def config(game):
    ex = REPO / "extracted" / game
    source = HERE / "build" / f"source_{game}.png"
    ball = generic_ball.source_with_ball(HERE / SOURCE, BALL_COLOURS, BACKGROUND[0], source, size=40)
    cfg = {"name": NAME, "credit": CREDIT,
           "source": f"build/source_{game}.png", "feet_y": 20, "background": BACKGROUND, "palette": PALETTE,
           "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
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
    for game, out in (("Sonic1", "big.json"), ("Sonic2", "big_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
    for k, size in ENDING_SIZES.items():  # (the trimmed crops must keep these sizes: the shared boxes)
        x, y, w, h = ENDING[k]["rect"]
        pts = [(a, b) for b in range(y, y + h) for a in range(x, x + w)
               if Image.open(HERE / SOURCE).getpixel((a, b)) != BG]
        tw = max(a for a, _ in pts) - min(a for a, _ in pts) + 1
        th = max(b for _, b in pts) - min(b for _, b in pts) + 1
        if (tw, th) != size:
            sys.exit(f"big: ending {k} trims to {tw}x{th}, not {size[0]}x{size[1]} (the shared box: see ENDING)")
    print("height (STAND):", R["STAND"][3], "px; pivots:", ", ".join(f"{k} {p}" for k, (_, p) in CELLS.items()))
    print("merged colours (colour -> slot colour, pixels):",
          ", ".join(f"{c}->{t} x{n}" for c, (t, n) in sorted(MERGED.items(), key=lambda kv: -kv[1][1])))
