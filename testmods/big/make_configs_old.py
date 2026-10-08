#!/usr/bin/env python3
"""UNUSED (kept for reference): Big's configs from the OLD sheet (18173.png), before the switch to Big2.png on
2026-09-28 (make_configs.py). Don't run it: it would overwrite big.json / big_s2.json with the old art's.

Writes Big's sheet2ani configs (big.json for Sonic 1, big_s2.json for Sonic 2).

Frames are boxes on 18173.png (Oppolo, Cylent Nite, AkumaTh and Reo; see SOURCE.txt), numbered as
detected, left to right and top to bottom."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
B = {  # box number -> [x, y, w, h]
    0: [1, 15, 51, 46], 1: [55, 13, 51, 48], 2: [109, 15, 42, 46], 4: [199, 15, 50, 46],
    5: [252, 10, 45, 51], 6: [300, 13, 46, 48], 7: [349, 6, 42, 55], 8: [394, 13, 56, 48],
    10: [512, 15, 59, 46], 11: [190, 64, 43, 68], 12: [236, 64, 43, 68], 13: [1, 87, 58, 45],
    15: [152, 98, 35, 34], 16: [282, 72, 49, 60], 17: [334, 86, 42, 46], 18: [379, 85, 42, 47],
    19: [424, 85, 54, 47], 20: [481, 86, 50, 46], 21: [534, 86, 42, 46], 22: [1, 139, 48, 47],
    23: [52, 139, 55, 47], 24: [211, 139, 51, 47], 28: [110, 140, 44, 46], 29: [157, 140, 51, 46],
    32: [55, 205, 42, 61], 34: [372, 205, 51, 61], 35: [426, 208, 56, 58], 38: [100, 218, 56, 48],
    39: [207, 220, 54, 46], 40: [264, 220, 51, 46], 41: [318, 220, 51, 46], 52: [240, 284, 42, 48],
    53: [291, 286, 42, 46], 58: [479, 284, 43, 40], 59: [531, 288, 37, 25], 65: [235, 343, 154, 101], 67: [11, 367, 95, 77],
    69: [406, 358, 53, 86],
}
f = lambda *nums: [B[n] for n in nums]
SHEET = "18173_noswap.png"  # the sheet plus our edits (make_sheet), in the sheet's own colours
UPRIGHT = [595, 10, 70, 110]  # where make_sheet puts the upright-umbrella pose


def make_sheet():
    """The original sheet widened, with Big's umbrella pose redrawn holding the umbrella upright:
    the tilted canopy is erased from pose 69 and the loose umbrella (58) is turned 40 degrees and
    put behind his raised fist."""
    from PIL import Image
    BG = (0, 64, 64, 255)
    src = Image.open(HERE / "18173.png").convert("RGBA")
    out = Image.new("RGBA", (src.width + 80, src.height), BG)
    out.paste(src, (0, 0))

    def cut(x, y, w, h):
        c = src.crop((x, y, x + w, y + h))
        px = c.load()
        for j in range(h):
            for i in range(w):
                if px[i, j] == BG:
                    px[i, j] = (0, 0, 0, 0)
        return c

    body = cut(*B[69])
    px = body.load()
    for j in range(body.height):
        for i in range(body.width):
            r, g, b_, a = px[i, j]
            white = r > 150 and g > 150 and b_ > 150 and 26 <= i <= 35 and 16 <= j <= 30  # the handle's hook
            if j < 25 or (i >= 34 and j < 34) or white:  # everything above his fist is umbrella
                px[i, j] = (0, 0, 0, 0)
    umbrella = cut(*B[58]).rotate(40, resample=Image.NEAREST, expand=True)
    # line the shaft up with his fist (x 20 in pose 69, top at row 25), canopy rim above it
    ub = umbrella.getbbox()
    shaft_x = [i for i in range(umbrella.width) if umbrella.getpixel((i, ub[3] - 3))[3]]
    shaft_x = sum(shaft_x) // len(shaft_x)
    rim = max(j for j in range(umbrella.height)
              if sum(1 for i in range(umbrella.width) if umbrella.getpixel((i, j))[3]) > 20)
    ux, uy = 20 - shaft_x, 14 - rim
    X0, Y0 = min(0, ux), min(0, uy)
    canvas = Image.new("RGBA", (max(body.width, ux + umbrella.width) - X0, max(body.height, uy + umbrella.height) - Y0))
    canvas.paste(umbrella, (ux - X0, uy - Y0), umbrella)
    canvas.paste(body, (-X0, -Y0), body)
    x, y, w, h = UPRIGHT
    assert canvas.width <= w and canvas.height <= h, canvas.size
    out.paste(canvas, (x, y), canvas)
    out.save(HERE / SHEET)
    # the body: pose 69's bottom 46 rows, wherever they landed
    return [x - X0, y - Y0 + B[69][3] - 46, 46, 46], [x, y, canvas.width, canvas.height]
BALL = [{"rect": B[15], "rotate": r} for r in (0, 90, 180, 270)]  # one ball frame, turned
WALK = f(17, 18, 19, 20, 21)
RUN = f(22, 23, 28, 29, 24)

ANIMS = {
    "Stopped": {"frames": f(2)},
    "Waiting": {"frames": f(0, 1), "loop": 0},
    "Looking Up": {"frames": f(5), "loop": 0},
    "Looking Down": {"frames": f(38), "loop": 0},
    "Walking": {"frames": WALK, "rot": 2},
    "Running": {"frames": RUN, "rot": 2},
    "Skidding": {"frames": f(10)},
    "Super Peel Out": {"frames": RUN, "rot": 2},
    "Spin Dash": {"frames": BALL},
    "Jumping": {"frames": BALL, "anchor": "center"},
    "Bouncing": {"frames": f(11, 12), "anchor": "center"},
    "Hurt": {"frames": f(35), "anchor": "center"},
    "Dying": {"frames": f(16), "anchor": "center"},
    "Drowning": {"frames": f(16), "anchor": "center"},
    "Fan Rotate": {"frames": BALL, "anchor": "center"},
    "Breathing": {"frames": f(6), "anchor": "center"},
    "Pushing": {"frames": f(39, 40, 41)},
    "Flailing 1": {"frames": f(4, 8)},
    "Flailing 2": {"frames": f(4, 8)},
    "Hanging": {"frames": f(32, 34), "anchor": "center"},
    "Clinging On": {"frames": f(13), "anchor": "center"},
    "Corkscrew H": {"frames": WALK},
    "Water Slide": {"frames": f(59), "anchor": "center"},
    "Continue": {"frames": f(52, 53)},
    "Continue Up": {"frames": f(7), "loop": 0},
    "Super Transform": {"frames": f(2), "loop": 0},
}
S2_ONLY = {
    "Flailing 3": {"frames": f(4, 8)},
    "Grabbed": {"frames": f(35), "anchor": "center"},
    "Twirl H": {"frames": WALK, "rot": 2},
    "Bored!": {"frames": f(0, 1), "loop": 0},
}

# The umbrella and fishing-rod frames are positioned by Big's body, not the whole picture
UPRIGHT_BODY, UPRIGHT = make_sheet()
UMBRELLA = {"rect": UPRIGHT, "anchor_box": UPRIGHT_BODY}
CAST = {"rect": B[67], "anchor_box": [11, 398, 46, 46]}  # lure ~72 px ahead of his centre


def cast(anchor):
    """Wind up, then the line out for five steps, then back. Reach per frame: tools/abilities.py."""
    return {"frames": [B[32], CAST, CAST, CAST, CAST, CAST, B[2]], "anchor": anchor, "speed": 60}


APPENDED = {
    "42": {"name": "Umbrella", "frames": [UMBRELLA], "anchor": "center"},
    "43": dict(cast("feet"), name="Cast"),
    "44": dict(cast("center"), name="Cast Air"),
}

PLUS_128 = {str(i): 128 + i for i in range(1, 16)}
HUD_FONT = {"f": "#fcfc00", "1": "#000000"}
ELEMENTS = {
    "life_icon": {"rect": [259, 288, 16, 16], "trim": False},
    # "BIG" in the style of the game's own name tags (2 px letters with a shadow)
    "life_name": {"pixel_colours": HUD_FONT, "pixels": [
        "ffff1..ff1..ffff1",
        "ff1ff1.ff1.ff1111",
        "ffff1..ff1.ff1ff1",
        "ff1ff1.ff1.ff1.f1",
        "ff1ff1.ff1.ff1ff1",
        "ffff1..ff1..fff1.",
        "1111...111..111..",
    ]},
    "monitor_1up": {"rect": [259, 289, 16, 14], "trim": False},
    # Big's head on the game's own signpost board (its yellow interior is 40x24 at 4,5)
    "sign_face": {"rect": [241, 284, 40, 24], "trim": False, "at": [4, 5],
                  "base": {"file": str(REPO / "extracted/Sonic1/Data/Sprites/Global/Items2.gif"),
                           "rect": [34, 182, 48, 32], "clear": [4, 5, 40, 24, 15],
                           "recolour": {"12": 8, "13": 8, "14": 8}}},  # Eggman's red bits on the frame
    "mini_1": {"rect": B[52], "scale": 0.5, "remap": PLUS_128},
    "mini_2": {"rect": B[53], "scale": 0.5, "remap": PLUS_128},
}
ENDING = {
    "end_idle": {"rect": B[2], "remap": PLUS_128},
    "end_pose_1": {"rect": B[7], "remap": PLUS_128},
    "end_pose_2": {"rect": UPRIGHT, "remap": PLUS_128},  # under his umbrella
    "end_pose_3": {"rect": B[65], "remap": PLUS_128},  # the one that didn't get away
    **{f"good_{n}": {"rect": B[k], "remap": PLUS_128} for n, k in enumerate((52, 53, 7, 11, 12, 5), 1)},
}

PALETTE = {  # Big's own colours in global palette slots 81-95 (Fang has 74-80)
    "81": "#182152", "82": "#292994", "83": "#4a4abd", "84": "#424263", "85": "#31395a",
    "86": "#636394", "87": "#5a639c", "88": "#733918", "89": "#bd5a21", "90": "#efa542",
    "91": "#d6d6e7", "92": "#a5a5bd", "93": "#848c29", "94": "#b59418", "95": "#adb563",  # 95: his eyes
}
COLOURS = {"#081018": 1, "#081800": 1, "#212121": 1, "#f0f4f4": 6, "#f8f9f9": 6, "#e7e7e7": 6,
           "#a5a5ad": 7, "#a5a5b5": 7, "#525a63": 9, "#fcfc00": 15, "#000000": 1,
           **{c: int(s) for s, c in PALETTE.items()}}


def config(game):
    ex = REPO / "extracted" / game
    cfg = {"name": "Extra3",
           "credit": "Big the Cat by Oppolo, Cylent Nite, AkumaTh and Reo - https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/18173/",
           "source": SHEET, "feet_y": 20, "background": ["#004040"], "palette": PALETTE, "colours": COLOURS,
           "template_ani": str(ex / "Data/Animations/Sonic.ani"),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),
           "out_dir": str(REPO / "mods/NoSwap" / (game + "u")),
           "animations": dict(ANIMS, **(S2_ONLY if game == "Sonic2" else {})),
           "appended_animations": APPENDED}
    if game == "Sonic1":
        cfg["extra_anis"] = [{"name": "Extra3SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                              "animations": {"Special Stage": {"frames": BALL, "anchor": "center"}}}]
        cfg["ui"] = [{"name": "Extra3_UI", "manifest": "Extra3_ui.json", "elements": ELEMENTS, "out": "build/Extra3_UI.gif"},
                     {"name": "Extra3_Ending", "manifest": "Extra3_ending.json", "elements": ENDING,
                      "out": "build/Extra3_Ending.gif"}]
    return cfg


if __name__ == "__main__":
    for game, out in (("Sonic1", "big.json"), ("Sonic2", "big_s2.json")):
        (HERE / out).write_text(json.dumps(config(game), indent=1))
        print("wrote", out)
