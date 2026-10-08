#!/usr/bin/env python3
"""Writes Cream's sheet2ani configs (cream.json for Sonic 1, cream_s2.json for Sonic 2).

Cream flies like Tails (the games' own Tails flight code), so her .ani follows TAILS' animation list
(extracted/<game>/Data/Animations/Tails.ani is the template), like Charmy's: Flying, Flying Tired, Swimming,
Swimming Tired (slots 24-27) and the carrying animations 39-42. Cheese is masked out of her frames (decheese): he only shows as her thrown shot.
She has no pre-angled frames, so Walking, Running and Super Peel Out use Sonic's free rotation (rot 2).

The sheet (Cream.png, "Cream & Cheese" by FroggyMudd; see SOURCE.txt) has no labels or boxes. Frames are
numbered as detected: connected components of everything that isn't white, with each loose Cheese, antenna
ball or sparkle attached to the nearest Cream (Cheese within 10 px, specks within 3 px), rows top to bottom,
left to right. The tired-flight frames keep their Cheese as union rects (Cheese sits just clear of Cream).
Nothing is redrawn or resized. The sheet mixes rips with slightly different palettes; near-identical shades
share one of her 22 own colours (palette slots 74-95).

Output goes to the mod (out_dir), as for the integrated extras.
"""
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
import hud_font  # noqa: E402
B = {  # box number -> [x, y, w, h]
    0: [6, 15, 30, 46], 8: [296, 15, 32, 46], 9: [334, 15, 30, 46], 10: [370, 14, 29, 46], 13: [159, 66, 22, 63],
    22: [12, 78, 22, 53], 48: [390, 208, 31, 35], 49: [422, 208, 29, 35], 50: [453, 208, 29, 35], 57: [138, 284, 43, 28],
    59: [229, 264, 29, 48], 68: [97, 325, 23, 62], 69: [125, 323, 25, 64], 70: [186, 323, 29, 63], 71: [220, 324, 23, 62],
    72: [258, 332, 30, 45], 73: [291, 330, 31, 46], 74: [324, 329, 32, 47], 75: [359, 327, 29, 49], 76: [391, 327, 29, 49],
    81: [10, 326, 25, 64], 82: [37, 325, 28, 64], 83: [67, 325, 29, 63], 84: [155, 323, 27, 65], 94: [332, 388, 41, 53],
    95: [379, 386, 31, 57], 99: [7, 456, 33, 46], 100: [43, 458, 33, 46], 103: [197, 461, 30, 46], 104: [229, 461, 30, 46],
    105: [261, 461, 30, 46], 106: [293, 461, 30, 46], 108: [364, 455, 34, 53], 109: [402, 454, 32, 53], 110: [437, 454, 32, 53],
    111: [476, 454, 32, 46], 112: [514, 456, 32, 46], 114: [593, 455, 34, 46], 118: [48, 519, 30, 46], 119: [83, 519, 32, 46],
    120: [120, 517, 32, 46], 121: [156, 519, 33, 47], 122: [195, 517, 32, 46], 123: [233, 517, 30, 46], 124: [269, 515, 30, 46],
    125: [308, 513, 30, 46], 136: [75, 597, 33, 24], 137: [110, 596, 32, 25], 138: [145, 594, 33, 29], 139: [186, 591, 39, 29],
    140: [229, 590, 38, 30], 141: [272, 587, 37, 33], 147: [506, 569, 31, 46], 148: [541, 568, 38, 46], 156: [73, 635, 71, 35],
    157: [148, 636, 27, 35], 163: [411, 626, 36, 54], 164: [448, 626, 34, 54], 165: [483, 626, 33, 54], 166: [517, 627, 33, 54],
    167: [551, 627, 33, 54], 168: [586, 627, 34, 54], 169: [621, 627, 36, 54], 178: [270, 696, 33, 36], 179: [311, 698, 27, 34],
    187: [8, 741, 33, 44], 193: [247, 733, 28, 50], 196: [379, 750, 37, 52], 197: [418, 751, 28, 51], 198: [450, 751, 26, 51],
    199: [478, 750, 28, 51], 208: [778, 763, 23, 35], 209: [74, 812, 18, 25], 210: [122, 815, 18, 25], 211: [170, 814, 18, 25],
    212: [217, 815, 18, 25], 213: [259, 816, 23, 25], 219: [311, 817, 18, 25], 222: [54, 829, 30, 31], 223: [101, 827, 30, 33],
    224: [149, 827, 30, 32], 225: [196, 825, 30, 35], 226: [243, 829, 30, 32], 227: [290, 827, 30, 35], 231: [463, 836, 44, 27],
    234: [591, 804, 28, 61], 235: [621, 805, 33, 60], 295: [538, 1106, 16, 23], 296: [560, 1106, 16, 23], 297: [614, 1088, 48, 48],
    305: [606, 1151, 62, 88],
}
f = lambda *nums: [B[n] for n in nums]
ORIGINAL = "Cream.png"  # the sheet as downloaded (Cheese's shot frames are cut from it: abilities.py)
SHEET = "build/Cream_nocheese.png"  # her frames: the sheet with Cheese masked out of them (decheese)
BACKGROUND = ["#ffffff"]


# Boxes Cheese is NOT masked out of: the signpost board (297: a picture, masking would leave a hole) and his own frames
# (156, 209-227: never her player frames)
KEEP_CHEESE = {156, 297} | set(range(209, 228))


def decheese():
    """Cheese masked out of her frames (the user, 2026-09-28: he shows only as the thrown projectile, so her frames
    don't carry him). A crop, nothing redrawn: in each box (B, the flight rects) Cheese's pixels become background.
    His pixels: his cyan/teal body and outline with everything it encloses (eyes, bowtie), grown into whole pieces of his
    own gold (feet, antenna) and pink (bow, cheeks) within 8 px, then into any bit touching him (outline specks) that
    has none of her fur, orange, dress-white or lavender within 2 px; then the box's largest piece (her) and any
    piece clear of him are kept. Written to SHEET; every frame's pixels are the sheet's own."""
    import numpy as np
    from scipy import ndimage
    im = np.array(Image.open(HERE / ORIGINAL).convert("RGB")).astype(int)
    out = im.copy()
    white = (im == 255).all(2)
    rects = [v for k, v in B.items() if k not in KEEP_CHEESE] + [EARS_DOWN, EARS_OUT, EARS_UP, CROUCH]
    for x, y, w, h in rects:
        s = im[y:y + h, x:x + w]
        r, g, b = s[..., 0], s[..., 1], s[..., 2]
        cyan = (g > r + 50) & (b > r + 50)
        if not cyan.any():
            continue
        # closed first: an eye that touches her outline (95: he peeks over her ear) isn't a hole of the bare cyan
        ch = ndimage.binary_fill_holes(ndimage.binary_closing(cyan, np.ones((3, 3)), iterations=2) | cyan)
        his = np.zeros(cyan.shape, bool)
        for c in ("#92891d", "#e1d215", "#f85080", "#f3a7c4"):  # his gold and pink
            his |= (s == hexrgb(c)).all(2)
        # whole pieces of his gold/pink with any pixel within 8 px of him (95: his antenna ball, clear of its stalk)
        zone = ndimage.binary_dilation(ch, iterations=8)
        lab, n = ndimage.label(his & ~ch, structure=np.ones((3, 3)))
        if n:
            ch |= np.isin(lab, np.unique(lab[zone & (lab > 0)]))
        ch = ndimage.binary_fill_holes(ch)
        solid = ~white[y:y + h, x:x + w]
        fur = (r >= 0x90) & (g >= 0x70) & (b >= 0x30) & ~cyan & solid & (b >= g - 0x60) & ~((r > 0xE0) & (g < 0x80))
        lav = (b >= r) & (b > 0x60) & ~cyan
        # her ear tips (95: his stalk touched her ear's edge): orange pieces of 30+ px (his bowtie is under 25; 305)
        olab, on = ndimage.label((r >= 0x90) & (g < 0x80) & (b < 0x20) & ~ch, structure=np.ones((3, 3)))
        big = [i + 1 for i, sz in enumerate(ndimage.sum(olab > 0, olab, range(1, on + 1))) if sz >= 30]
        orange = np.isin(olab, big)
        hers = ndimage.binary_dilation((fur | lav | orange) & ~ch, iterations=2)
        for _ in range(3):
            ch |= ndimage.binary_dilation(ch) & solid & ~hers
        body = solid & ~ch
        lab, n = ndimage.label(body, structure=np.ones((3, 3)))
        if n == 0:
            continue
        # her largest piece, plus any piece clear of him (CROUCH: her hands on the ground, apart from her head)
        near = np.unique(lab[ndimage.binary_dilation(ch, iterations=8) & (lab > 0)])
        keep = (lab == 1 + int(np.argmax(ndimage.sum(body, lab, range(1, n + 1))))) | ((lab > 0) & ~np.isin(lab, near))
        out[y:y + h, x:x + w][solid & ~keep] = 255
    (HERE / SHEET).parent.mkdir(exist_ok=True)
    Image.fromarray(out.astype("uint8")).save(HERE / SHEET)


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def union(*nums):
    xs = [B[n][0] for n in nums]; ys = [B[n][1] for n in nums]
    x1 = max(B[n][0] + B[n][2] for n in nums); y1 = max(B[n][1] + B[n][3] for n in nums)
    return [min(xs), min(ys), x1 - min(xs), y1 - min(ys)]


WALK = f(81, 82, 83, 68, 69, 84, 70, 71)  # walking, Cheese bobbing above her
RUN = f(118, 119, 120, 121, 122, 123, 124, 125)
PEEL = f(48, 49, 50)  # running flat out, arms back (Cheese can't keep up)
BALL = f(139, 140, 141)  # her roll
SPINDASH = f(136, 137, 138)
# Flight: the side-on ear flaps in row 5 (x 15-126, y 262), Cheese riding above: ears drooped, spread, raised.
# (163-169, first used here, are her flying seen from BEHIND: in game she wiggled her tail at the camera.)
EARS_DOWN, EARS_OUT, EARS_UP = [15, 262, 29, 50], [50, 262, 41, 50], [95, 262, 31, 50]


def body(rect):
    """A flap frame placed by her body, not its trimmed size: the three boxes have her at the same height (feet on
    the box's bottom row), but trimmed and centred, the raised ears' frame sat 8 px lower than the drooped one and
    she bobbed 8 px every frame of the flap. The anchor: 20 rows centred 33 rows down the box (the spread-ears
    frame's old centre, so the spread pose is where it was); "align" still lines her up sideways."""
    x, y, w, h = rect
    return {"rect": rect, "anchor_box": [x, y + h - 27, w, 20]}  # (by the box's bottom row: 57's box is only her)


# The flap: drooped, spread, swept back (57, the row's 4th pose), spread. Not the raised ears: Cheese sits on her right
# ear there, and masking him out left a hole in it (the user, 2026-09-29)
EARS_BACK = B[57]
FLY = [body(EARS_DOWN), body(EARS_OUT), body(EARS_BACK), body(EARS_OUT)]
# tired flight: the same flap, slower and never rising past spread (222-227 are a dizzy knocked-down pose)
TIRED = [body(EARS_OUT), body(EARS_DOWN)]
# Sonic 1/2's flight code sets her animation speed every frame (240 rising: a new frame each game frame, 120 falling),
# which flapped her ears 15 times a second (Tails' 2 frames are only his body; his tails are separate): each pose
# held 4 game frames (sheet2ani "hold") makes about 4 flaps a second rising, 2 falling. CD strips it (cd_config.py),
# S3&K: Tails' Fly / Fly Lift poses are 1 frame (his flapping is his separate tails object), so her flap only showed
# its first pose there; S3K_ANIMS gives them her own 4 ("own_count"), the hold as 4x each frame's duration.
HOLD = 4
BALANCE = f(99, 100)
# Looking Down: her squat, hands on the ground (row 8, x 492: the Sonic Advance crouch; unnumbered, detected with Cheese
# as one piece). 59, used before, is her bent over tired, hands on knees (the user, 2026-09-30)
CROUCH = [492, 509, 22, 46]

ANIMS = {
    "Stopped": {"frames": f(0)},
    "Waiting": {"frames": f(8, 9, 10), "loop": 0},  # looking around
    "Bored!": {"frames": f(72, 73, 74), "loop": 0},
    "Looking Up": {"frames": f(22), "loop": 0},
    "Looking Down": {"frames": [CROUCH], "loop": 0},
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2},
    "Skidding": {"frames": f(108, 109, 110)},  # heels dug in, kicking up dust
    # top speed: her whole 8-frame run (the 3 flat-out frames, two nearly alike, flickered at that speed; the user,
    # 2026-09-29; Shadow's fix)
    "Super Peel Out": {"frames": RUN, "rot": 2},
    "Spin Dash": {"frames": SPINDASH},
    "Jumping": {"frames": BALL, "anchor": "center"},
    "Bouncing": {"frames": f(95), "anchor": "center"},  # ears straight up
    "Hurt": {"frames": f(187), "anchor": "center"},
    "Dying": {"frames": f(76), "anchor": "center"},  # front-on, arms out, mouth open (75 grinned: the user picked 76, 2026-09-30)
    "Drowning": {"frames": f(76), "anchor": "center"},
    "Fan Rotate": {"frames": f(178, 179, 193), "anchor": "center"},  # tumbling
    "Breathing": {"frames": f(13), "anchor": "center"},  # looking up
    "Pushing": {"frames": f(103, 104, 105, 106)},  # hands out in front
    "Flailing 1": {"frames": BALANCE},
    "Flailing 2": {"frames": BALANCE},
    "Hanging": {"frames": f(234, 235), "anchor": "center"},  # hanging from Cheese
    "Clinging On": {"frames": f(57, 231), "anchor": "center"},  # lying flat
    "Corkscrew H": {"frames": WALK},  # Sonic 1 (Tails has none)
    "Twirl H": {"frames": WALK, "rot": 2},  # Sonic 2
    "Water Slide": {"frames": f(187, 178), "anchor": "center"},
    "Continue": {"frames": f(111, 112)},  # sitting
    "Continue Up": {"frames": f(22), "loop": 0},
    "Super Transform": {"frames": f(0), "loop": 0},
    # Tails' flight set
    "Flying": {"frames": FLY, "anchor": "center", "align": True, "hold": HOLD},  # aligned: her ears widen some frames (she jittered in S3&K)
    "Flying Tired": {"frames": TIRED, "anchor": "center", "align": True, "hold": HOLD},
    "Swimming": {"frames": FLY, "anchor": "center", "align": True},  # no swimming art: she flies through the water
    "Swimming Tired": {"frames": TIRED, "anchor": "center", "align": True},
    "Fly Lift Down": {"frames": FLY, "anchor": "center", "align": True, "hold": HOLD},  # carrying a partner (never happens: extras play alone)
    "Fly Lift Up": {"frames": FLY, "anchor": "center", "align": True, "hold": HOLD},
    "Fly Lift Tired": {"frames": TIRED, "anchor": "center", "align": True, "hold": HOLD},
    "Swim Lift": {"frames": FLY, "anchor": "center", "align": True},
}
# Sonic 3 & Knuckles, by its (Mania's) names (build_s3k_art.py "s3k_animations"); the rest from the ones above. Tails'
# Fly Tired / Fly Lift Tired already have 2 frames (her 2 tired poses); Swim has 5.
S3K_ANIMS = {n: dict(ANIMS["Flying"], own_count=True) for n in ("Fly", "Fly Lift", "Fly Lift Down")}
# Run and Dash (top speed): her whole 8-frame run ("own_count": the game only sets their speed). Tails' have 4 and 2
# frames, which took every other / every fourth stride and flickered between two poses at full speed (the user,
# 2026-09-30; as Shadow's and Silver's)
S3K_ANIMS.update({"Run": {"frames": RUN, "own_count": True},
                  "Dash": {"frames": RUN, "own_count": True, "hold": 3}})  # (Tails' Dash frames last a third of his Run's: a blur)
S2_ONLY = {
    # Sonic 2's slot 20 is Tails' (empty) "Sliding" but Sonic's "Flailing 3"
    "Sliding": {"frames": BALANCE},
    "Grabbed": {"frames": f(187), "anchor": "center"},
}

# Chao Attack (Y, slots 43/44): she winds up (147), swings (148) and holds her arm out, Cheese gone (157: the sheet's
# frame after the fling, without the Cheese it's drawn with elsewhere). Cheese himself is the shot (abilities.py
# "shot": a homing projectile, his two flying frames on this sheet); the last frame is the throw pose. 4 game frames each.
CHAO_THROW = f(147, 148, 157)

APPENDED = {
    "43": {"name": "Chao Attack", "frames": CHAO_THROW, "speed": 60, "anchor": "feet"},
    "44": {"name": "Chao Attack Air", "frames": CHAO_THROW, "speed": 60, "anchor": "center"},
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}


HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
ELEMENTS = {
    "life_icon": {"rect": [785, 765, 16, 16], "trim": False},  # her face, cropped from frame 208 (Cream alone)
    "life_name": {"pixel_colours": HUD_FONT, "pixels": hud_font.tag("CREAM")},  # the sheet has no name tag
    "monitor_1up": {"rect": [785, 766, 16, 14], "trim": False},
    "sign_face": {"rect": [B[297][0], B[297][1], 48, 32], "trim": False},  # the sheet's signpost board
    "mini_1": {"rect": B[295], "remap": PLUS_128},  # small Cream (16x23)
    "mini_2": {"rect": B[296], "remap": PLUS_128},
}
ENDING = {  # Sonic 1's ending poses: idle, three poses (small, medium, large), six good-ending frames
    "end_idle": {"rect": B[0], "remap": PLUS_128},
    "end_pose_1": {"rect": B[114], "remap": PLUS_128},  # front-on
    "end_pose_2": {"rect": B[94], "remap": PLUS_128},  # leaping, ears streaming
    "end_pose_3": {"rect": B[305], "remap": PLUS_128},  # the large pose with Cheese (62x88)
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((196, 197, 198, 199, 75, 76), 1)},
}

PALETTE = {  # Cream's own colours, in the extras' shared global palette slots 74-95
    "74": "#fdeed5", "75": "#fbddac", "76": "#e1af64", "77": "#977337", "78": "#49391d",  # cream fur, light to dark
    "79": "#ff790b", "80": "#d95c00", "81": "#954000",  # orange dress and ear tips
    "82": "#c0c0e0", "83": "#a0a0c0", "84": "#8787b2", "85": "#606080", "86": "#202020",  # lavender-white, outline
    "87": "#6060e0",  # her blue tie
    "88": "#60e3e3", "89": "#41b3bc", "90": "#007080",  # Cheese
    "91": "#f85080", "92": "#f3a7c4",  # Cheese's bow, cheeks
    "93": "#e1d215", "94": "#92891d",  # gold (Cheese's ball, shoes)
    "95": "#1ab925",  # the signpost's green
}
KEY_COLOURS = {  # exact matches go in Sonic's slots; the rest are Cream's own
    "#000000": 1, "#202080": 2, "#e0e0e0": 6, "#fcfc00": 15,
    **{c: int(s) for s, c in PALETTE.items()},
}


def all_colours():
    """KEY_COLOURS, plus every other colour on the sheet in the slot of its nearest key colour (the sheet
    mixes rips, so many shades differ by a few steps), so nothing is left to sheet2ani's guess."""
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    keys = {hexrgb(c): s for c, s in KEY_COLOURS.items()}
    out = dict(KEY_COLOURS)
    for _, rgb in Image.open(HERE / ORIGINAL).convert("RGB").getcolors(1 << 16):
        c = "#%02x%02x%02x" % rgb
        if c not in out and c not in BACKGROUND:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[c] = keys[near]
    return out


COLOURS = all_colours()


# Sonic 3 & Knuckles' act clear celebration (build_s3k_art.py "s3k_victory": the build-up, then from "pose", default
# the last frame, the pose held or looped): the good ending: into arms up, cheering with Cheese
S3K_VICTORY = {"frames": f(199, 75)}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra13",
           "credit": "Cream & Cheese by FroggyMudd (sprites made/ripped by Clyent Nite, t0ms0nic, Zig Sonar, Ult. Knux People, AkumaTH, Damien, DBurraki, OcrilioTH, MoonWarrior, Arachnefox, Rittz, Miguel, SSJ Zac, Bonzai, Grim Gabriel, Daniel Sidney and the Ult. Tails Sheet people) - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/111916/",
           "source": SHEET, "feet_y": 20, "background": BACKGROUND, "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Tails.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra13SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": BALL, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra13_UI", "manifest": "Extra13_ui.json", "elements": ELEMENTS, "out": "build/Extra13_UI.gif"},
                     {"name": "Extra13_Ending", "manifest": "Extra13_ending.json", "elements": ENDING,
                      "out": "build/Extra13_Ending.gif"}]
    if game == "Sonic2":  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = S3K_VICTORY
        cfg["s3k_animations"] = S3K_ANIMS
    return cfg


if __name__ == "__main__":
    decheese()
    for game, out in (("Sonic1", "cream.json"), ("Sonic2", "cream_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
