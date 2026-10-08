#!/usr/bin/env python3
"""Build each extra's S3&K HUD file: 3K_Global/HUD_Extra.bin (+ a small sheet of its art), its signpost, and its
special stage results (3K_HPZ/SpecialClear_Extra.bin: its name in "CHARMY GOT A"...; build_special_clear).

Output: under the fixed names (extras.S3K_FIXED) in extras.s3k_build(extra), outside the mod; build_packages.py copies
them into the extra's package, and the DLL loads them (served from the playing extra's package) instead of the game's.

S3&K's 3K_Global/HUD.bin has one frame per character in "Life Icons" (HUD icon), "Life Names" (the
small tag under it) and "Player Name" (the big name on the results screen); frame 0 is Sonic's. The
extra plays as Sonic in costume, so its copy of HUD.bin points those three frames at its own art, and
the NoSwap DLL loads the copy instead of HUD.bin.

The results name is built in S3&K's own results font. Its blue letters (from KNUCKLES, SONIC, AMY and
MILES) are topped up with letters from the white words (GOT THROUGH, GAME OVER, TIME OVER),
recoloured with the blue scheme, cut to the blue letters' height and outlined like them; F, G, B, D and P
are built from blue letters (D: E's stem and arms, I's stem, O's right side), W is an upside-down M and Z an N on its side. The letters are set with the
font's own spacing, and the name ends where the base character's does, so "GOT" follows it as usual.
"""
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import ani_v5
from extras import EXTRAS, s3k_build, ui_manifest
from gifio import save_sheet

REPO = Path(__file__).resolve().parent.parent
S3K = REPO / "extracted" / "Sonic3K" / "Data" / "Sprites"

HUD = ani_v5.read_bin(S3K / "3K_Global" / "HUD.bin")
SHEETS = [Image.open(S3K / s) for s in HUD["sheets"]]


def frame_image(anim, k):
    f = next(a for a in HUD["anims"] if a["name"] == anim)["frames"][k]
    return SHEETS[f["sheet"]].crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))


BLUE_BODY, BLUE_OUTLINE = (2, 3, 4), (8, 9)  # the name font: light to dark blue, orange outline
WHITE_BODY, WHITE_OUTLINE = (16, 12, 13), (15,)  # GOT THROUGH etc.: light to dark grey, dark outline


def letters(word_img, text, body):
    """Split a word into its letters. Letters in these fonts touch (shared outlines, sometimes even
    bodies): each letter is a run of columns with body pixels, with the outline around it (up to 2 columns
    without body on either side). Letters whose bodies touch (T and A in TAILS, G and O in GOT...) are split
    at the thinnest column in the middle third of the run; the widest run is split first."""
    w, h = word_img.size
    count = [sum(word_img.getpixel((x, y)) in body for y in range(h)) for x in range(w)]
    chars = text.replace(" ", "")
    runs, x = [], 0
    while x < w:
        if count[x]:
            start = x
            while x < w and count[x]:
                x += 1
            runs.append([start, x])
        x += 1
    while len(runs) < len(chars):
        i = max(range(len(runs)), key=lambda i: runs[i][1] - runs[i][0])
        a, b = runs[i]
        third = (b - a) // 3
        cut = min(range(a + third, b - third), key=lambda x: (count[x], -x))
        runs[i:i + 1] = [[a, cut + 1], [cut + 1, b]]
    if len(runs) != len(chars):
        sys.exit(f"{text}: {len(runs)} letters found")
    # each body pixel goes to its letter: by the column run its connected part (4-neighbours) mostly lies in,
    # so a kerned neighbour's corner (A's foot under T's arm) stays with its own letter
    owner, seen = {}, set()
    for x0 in range(w):
        for y0 in range(h):
            if (x0, y0) in seen or word_img.getpixel((x0, y0)) not in body:
                continue
            part, todo = [], [(x0, y0)]
            seen.add((x0, y0))
            while todo:
                x, y = todo.pop()
                part.append((x, y))
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= n[0] < w and 0 <= n[1] < h and n not in seen and word_img.getpixel(n) in body:
                        seen.add(n)
                        todo.append(n)
            letter_of = lambda x: next(i for i, (a, b) in enumerate(runs) if x < b) if x < runs[-1][1] else len(runs) - 1
            votes = Counter(letter_of(x) for x, _ in part)
            if len(votes) > 1 and votes.most_common(2)[1][1] > len(part) // 4:
                for x, y in part:  # a real join of two letters: split by the columns
                    owner[(x, y)] = letter_of(x)
            else:
                for x, y in part:
                    owner[(x, y)] = votes.most_common(1)[0][0]
    out = {}
    for i, ch in enumerate(chars):
        mine = [xy for xy, k in owner.items() if k == i]
        left = max(0, min(x for x, _ in mine) - 2)
        right = min(w, max(x for x, _ in mine) + 3)
        g = Image.new("P", (right - left, h), 0)
        g.putpalette(word_img.getpalette())
        near = {(x + dx, y + dy) for x, y in mine for dx in range(-2, 3) for dy in range(-2, 3)}
        for x in range(left, right):
            for y in range(h):
                v = word_img.getpixel((x, y))
                if (x, y) in owner:
                    if owner[(x, y)] == i:
                        g.putpixel((x - left, y), v)
                elif v and (x, y) in near:  # outline (or shadow) round this letter's body
                    g.putpixel((x - left, y), v)
        out[ch] = g
    return out


def white_to_blue(img):
    """A letter of the white words (GOT THROUGH...) in the blue name font: recoloured, 14 rows tall like
    the blue letters' bodies (a repeated row near the middle left out, twice), and given their orange
    outline (the white font has only a shadow, which becomes the dark blue side)."""
    img = own_part(img)
    rows = [[img.getpixel((x, y)) for x in range(img.width)] for y in range(img.height)]
    while len(rows) > 14:
        same = [y for y in range(1, len(rows)) if rows[y] == rows[y - 1]]
        mid = len(rows) / 2
        y = min(same, key=lambda y: abs(y - mid)) if same else len(rows) - 1
        del rows[y]
    colour = {16: 2, 12: 3, 13: 4, 15: 4}
    w = img.width + 4
    out = Image.new("P", (w, 16), 0)
    out.putpalette(SHEETS[1].getpalette())
    for y, row in enumerate(rows):
        for x, v in enumerate(row):
            if v:
                out.putpixel((x + 2, y + 1), colour.get(v, v))
    return outline(out)


def own_part(img):
    """Only the letter's own pixels: the 4-connected parts that have some body in them. letters() gives a white
    letter the pixels near its body, which can include a scrap of its neighbour's shadow (V in OVER got the
    shadow down O's right side), and that scrap would become body in the blue font and widen the letter."""
    todo_all = {(x, y) for x in range(img.width) for y in range(img.height) if img.getpixel((x, y))}
    out = Image.new("P", img.size, 0)
    out.putpalette(img.getpalette())
    while todo_all:
        part, todo = set(), [todo_all.pop()]
        while todo:
            x, y = todo.pop()
            part.add((x, y))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in todo_all:
                    todo_all.discard(n)
                    todo.append(n)
        if any(img.getpixel(xy) in WHITE_BODY for xy in part):
            for xy in part:
                out.putpixel(xy, img.getpixel(xy))
    return out


def make_b(r):
    """B from the white R: its stem and bowl (the rows above the leg: the top bar, the bowl's sides, the
    middle bar and the bowl's shaded underside), with the same section again below from the bowl's lower
    top-bar row on, in place of the leg: 14 rows, as white_to_blue makes every letter."""
    rows = [[r.getpixel((x, y)) for x in range(r.width)] for y in range(r.height)]
    runs = [len(body_runs_of(row)) for row in rows]
    sides = [y for y in range(len(rows)) if runs[y] == 2]
    bar = next(y for y in range(sides[0], len(rows)) if runs[y] == 1)  # the middle bar, under the bowl's sides
    leg = next(y for y in range(bar, len(rows)) if runs[y] == 2)  # where the leg parts from the stem
    upper = rows[:bar + 1]
    lower = rows[sides[0] - 1:leg]
    b = Image.new("P", (r.width, len(upper) + len(lower)), 0)
    b.putpalette(r.getpalette())
    for y, row in enumerate(upper + lower):
        for x, v in enumerate(row):
            b.putpixel((x, y), v)
    return b


def body_runs_of(row, body=WHITE_BODY + WHITE_OUTLINE):
    """The number of letter runs in a row of white-font pixels (body and shadow)."""
    runs, inside = [], False
    for v in row:
        if (v in body) != inside:
            inside = not inside
            if inside:
                runs.append(v)
    return runs


def make_d(e, o, i):
    """D: E's stem with its top and bottom arms, O's right side, and I's plain stem on the rows of E's middle arm
    (E cut in half keeps a stub of that arm, which showed inside the D): only the game's own pixels, placed."""
    w, h = e.size
    half = w // 2 + 1
    stem = min(r[0][1] - r[0][0] for r in (body_runs(e, y) for y in range(h)) if r)
    arms, y = [], 0
    while y < h:  # E's arms: groups of rows whose body reaches past the stem
        if body_runs(e, y) and body_runs(e, y)[0][1] - body_runs(e, y)[0][0] > stem + 1:
            start = y
            while y < h and body_runs(e, y) and body_runs(e, y)[0][1] - body_runs(e, y)[0][0] > stem + 1:
                y += 1
            arms.append(range(start, y))
        y += 1
    if len(arms) != 3:
        sys.exit(f"make_d: E has {len(arms)} arms")
    shift = body_runs(e, arms[1][0])[0][0] - body_runs(i, arms[1][0])[0][0]  # I's stem onto E's stem columns
    stem_part = e.crop((0, 0, half, h))
    for y in arms[1]:
        for x in range(1, half):  # (column 0 stays E's: its outline starts lower)
            v = i.getpixel((x - shift, y)) if 0 <= x - shift < i.width else 0
            stem_part.putpixel((x, y), v)
    right = o.crop((o.width // 2, 0, o.width, h))
    d = Image.new("P", (stem_part.width + right.width, h), 0)
    d.putpalette(e.getpalette())
    d.paste(right, (stem_part.width, 0))
    d.paste(stem_part, (0, 0), stem_part.point(lambda i: 255 if i else 0).convert("L"))
    return d


def body_runs(img, y):
    """The runs of body columns (start, end) in row y of a blue letter."""
    runs, x = [], 0
    while x < img.width:
        if img.getpixel((x, y)) in BLUE_BODY:
            start = x
            while x < img.width and img.getpixel((x, y)) in BLUE_BODY:
                x += 1
            runs.append((start, x))
        x += 1
    return runs


def keep_runs(img, rows):
    """A blue letter with some rows' body cut down to the given column runs ({row: [(start, end)]}), and
    its outline drawn again round what's left."""
    out = Image.new("P", img.size, 0)
    out.putpalette(img.getpalette())
    for y in range(img.height):
        for x in range(img.width):
            v = img.getpixel((x, y))
            if v in BLUE_BODY and (y not in rows or any(a <= x < b for a, b in rows[y])):
                out.putpixel((x, y), v)
    return outline(out)


def outline(img):
    """The blue font's orange outline round a letter's body: 2 columns at the sides, a row above and below."""
    out = Image.new("P", img.size, 0)
    out.putpalette(img.getpalette())
    body = {(x, y) for x in range(img.width) for y in range(img.height) if img.getpixel((x, y)) in BLUE_BODY}
    for x, y in body:
        out.putpixel((x, y), img.getpixel((x, y)))
    for x, y in {(x + dx, y + dy) for x, y in body for dx in range(-2, 3) for dy in (-1, 0, 1)} - body:
        if 0 <= x < img.width and 0 <= y < img.height:
            out.putpixel((x, y), BLUE_OUTLINE[0])
    return out


def font():
    blue = {}
    # KNUCKLES is drawn in his red scheme (red 6/7, orange highlight 9, green outline 5/14): recoloured to the
    # blue scheme, it supplies letters no blue name has (K, U); the blue names' own letters win
    RED_TO_BLUE = {6: 3, 7: 4, 9: 2, 5: 8, 14: 9}
    for ch, img in letters(frame_image("Player Name", 2), "KNUCKLES", (6, 7, 9)).items():
        blue[ch] = img.point(lambda i: RED_TO_BLUE.get(i, i))
    for k, text in ((0, "SONIC"), (1, "TAILS"), (3, "AMY"), (5, "MILES")):
        blue.update(letters(frame_image("Player Name", k), text, BLUE_BODY))
    white = {}
    for anim, k, text in (("Got Through", 0, "GOT"), ("Got Through", 1, "THROUGH"), ("Game Over", 0, "GAME"),
                          ("Game Over", 1, "OVER"), ("Time Over", 0, "TIME")):
        white.update(letters(frame_image(anim, k), text, WHITE_BODY))
    # G isn't in blue: GOT's (a C built into a G read as a lowercase e). B is in no word of this font (the
    # results' BONUS is the small yellow tally font): OVER's R, its stem and bowl twice (make_b)
    blue["G"] = white_to_blue(letters(frame_image("Got Through", 0), "GOT", WHITE_BODY)["G"])
    blue["B"] = white_to_blue(make_b(white["R"]))
    blue["D"] = make_d(blue["E"], blue["O"], blue["I"])
    blue["W"] = blue["M"].transpose(Image.FLIP_TOP_BOTTOM)  # an upside-down M
    # an N on its side. Turned, it is 18 rows tall with its body a row lower than the other letters' and 1-column
    # outlines at the sides: its body alone, on the other letters' rows (1-14), outlined as they are
    n = blue["N"].transpose(Image.ROTATE_90)
    rows = [y for y in range(n.height) if any(n.getpixel((x, y)) in BLUE_BODY for x in range(n.width))]
    z = Image.new("P", (n.width + 2, 16), 0)
    z.putpalette(n.getpalette())
    for y in range(rows[0], rows[-1] + 1):
        for x in range(n.width):
            if n.getpixel((x, y)) in BLUE_BODY:
                z.putpixel((x + 1, y - rows[0] + 1), n.getpixel((x, y)))
    blue["Z"] = outline(z)
    if "F" not in blue:  # E without its bottom arm: from the bottom up, rows cut back to the stem
        e = blue["E"]
        stem = min(r[0][1] - r[0][0] for r in (body_runs(e, y) for y in range(e.height)) if r)
        rows = {}
        for y in range(e.height - 1, -1, -1):
            r = body_runs(e, y)
            if not r:
                continue
            if r[0][1] - r[0][0] <= stem + 1:
                break
            rows[y] = [(r[0][0], r[0][0] + stem)]
        blue["F"] = keep_runs(e, rows)
    for ch, img in white.items():  # anything else missing: the white letters, in the blue font's colours
        if ch not in blue:
            blue[ch] = white_to_blue(img)
    if "P" not in blue and "R" in blue:  # R without its leg: the rows under the bowl keep only the stem
        r = blue["R"]
        rows = {}
        for y in range(r.height - 1, -1, -1):
            runs = body_runs(r, y)
            if len(runs) < 2 and runs:
                break
            if runs:
                rows[y] = runs[:1]
        blue["P"] = keep_runs(r, rows)
    if "J" not in blue and "U" in blue:  # U without the top half of its left stem: the hook
        u = blue["U"]
        rows = {y: body_runs(u, y)[1:] for y in range(u.height // 2) if len(body_runs(u, y)) == 2}
        blue["J"] = keep_runs(u, rows)
    if "X" not in blue and "V" in blue:  # V's top half (arms closing in) over the same half upside down
        v = blue["V"]
        x = Image.new("P", v.size, 0)
        x.putpalette(v.getpalette())
        top = v.crop((0, 0, v.width, v.height // 2))
        x.paste(top, (0, 0))
        x.paste(top.transpose(Image.FLIP_TOP_BOTTOM), (0, v.height - top.height))
        blue["X"] = x
    return blue


def word(text, glyphs, gap=3, space=8):
    """The name in the results font, spaced as the game's own names are: each letter as close as it can go with
    its body `gap` clear columns from the letters before it on every row (and the rows next to it), so a letter
    tucks under a neighbour's slant or arm as the game's T and A in TAILS do (measured over SONIC, TAILS, MILES,
    AMY and KNUCKLES: 2-3 clear columns on the closest row, whatever the letters' boxes do). Outlines go under
    the bodies where neighbours overlap. A space is `space` columns more, from the widest point before it."""
    profile = {}  # each letter's body: leftmost and rightmost column per row
    for c, g in glyphs.items():
        rows = {}
        for y in range(g.height):
            xs = [x for x in range(g.width) if g.getpixel((x, y)) in BLUE_BODY]
            if xs:
                rows[y] = (xs[0], xs[-1])
        profile[c] = rows
    place = []
    right = {}  # the words so far: rightmost body column per row
    for c in text:
        if c == " ":
            edge = max(right.values())
            right = {y: edge + space for y in right}
            continue
        rows = profile[c]
        if not place:
            left = 2 - min(a for a, _ in rows.values())  # the body from column 2, after its outline
        else:
            left = max(right[y2] + gap + 1 - a for y, (a, _) in rows.items() for y2 in (y - 1, y, y + 1)
                       if y2 in right)
            left = max(left, place[-1][1] + 1)  # (never at or before the last letter)
        place.append((glyphs[c], left))
        for y, (_, b) in rows.items():
            right[y] = max(right.get(y, -99), left + b)
    width = max(right.values()) + 3  # the last body column, then its 2 outline columns (as the game's names end)
    img = Image.new("P", (width, 16), 0)
    for body in (False, True):  # outlines first, then every body over them
        for g, left in place:
            for y in range(min(g.height, 16)):
                for gx in range(g.width):
                    i = g.getpixel((gx, y))
                    if i and (i in BLUE_BODY) == body and 0 <= left + gx < width:
                        img.putpixel((left + gx, y), i)
    return img


def remap_to_display(img, src_pal, keep, disp=None):
    """Recolour UI art (S1-style palette) to S3&K's Display.gif colours (or `disp`'s); own palette slots stay."""
    disp = disp or SHEETS[1]
    dpal = disp.getpalette()
    used = [i for _, i in disp.getcolors(256) if i]
    rgb = lambda pal, i: tuple(pal[3 * i:3 * i + 3])
    lut = {}
    for _, i in img.getcolors(256):
        if i == 0:
            continue
        j = i - 128 if i >= 128 else i
        if j in keep:
            lut[i] = j
        else:
            c = rgb(src_pal, j)
            lut[i] = min(used, key=lambda k: sum((a - b) ** 2 for a, b in zip(c, rgb(dpal, k))))
    return img.point(lambda i: lut.get(i, 0))


def build(extra, glyphs):
    manifest = ui_manifest(extra, "ui")
    ui = Image.open(manifest["sheet"])
    cut = lambda k: ui.crop((manifest["frames"][k][0], manifest["frames"][k][1],
                             manifest["frames"][k][0] + manifest["frames"][k][2],
                             manifest["frames"][k][1] + manifest["frames"][k][3]))
    keep = set(extra["palette"])
    art = {"icon": remap_to_display(cut("life_icon"), ui.getpalette(), keep),
           "tag": remap_to_display(cut("life_name"), ui.getpalette(), keep),
           "name": word(extra["name"], glyphs)}
    sheet = Image.new("P", (256, 64), 0)
    sheet.putpalette(SHEETS[1].getpalette())
    placed, x = {}, 0
    for k in ("icon", "tag", "name"):
        img = art[k]
        if x + img.width > 256:
            sys.exit(f"{extra['name']}: HUD art too wide")
        sheet.paste(img, (x, 0))
        placed[k] = (x, 0, img.width, img.height)
        x += img.width + 1
    sheet_rel = "3K_Global/HUD_Extra.gif"  # (fixed names: extras.S3K_FIXED)
    out = s3k_build(extra)
    (out / "3K_Global").mkdir(parents=True, exist_ok=True)
    save_sheet(sheet, out / sheet_rel)

    hud = ani_v5.read_bin(S3K / "3K_Global" / "HUD.bin")
    hud["sheets"].append(sheet_rel)
    sid = len(hud["sheets"]) - 1
    # the base character's frames (extras.py "base"): Sonic 0, Tails 1 (and "MILES", Player Name 5 /
    # Life Names 7), Knuckles 2
    frames_of = {"sonic": {}, "tails": {"Player Name": [1, 5], "Life Names": [1, 7]}, "knuckles": {}}[extra["base"]]
    index = {"sonic": 0, "tails": 1, "knuckles": 2}[extra["base"]]
    for anim, key in (("Life Icons", "icon"), ("Life Names", "tag"), ("Player Name", "name")):
        frames = next(a for a in hud["anims"] if a["name"] == anim)["frames"]
        for k in frames_of.get(anim, [index]):
            f = frames[k]
            x, y, w, h = placed[key]
            if anim == "Player Name":
                # the name ends where the base's own does ("GOT" follows it 8 px on: Sonic's and Tails'
                # end 8 px right of the position, Knuckles' 8 px left, with his own "GOT" frame further left)
                f["px"] = f["px"] + f["w"] - w
            f.update(sheet=sid, x=x, y=y, w=w, h=h)
    ani_v5.write_bin(out / "3K_Global" / "HUD_Extra.bin", hud)
    print(f"{extra['art'].name} HUD_Extra.bin: {extra['name']} (name {placed['name'][2]} px)")


SIGNPOST = S3K / "3K_Global" / "SignPost.bin"


def build_signpost(extra):
    """3K_Global/SignPost_Extra.bin: S3&K's signpost with every use of Sonic's face (48x32; the
    "Sonic" animation and the spin) pointed at the extra's own sign art. The NoSwap DLL loads it
    instead of SignPost.bin."""
    sign = ani_v5.read_bin(SIGNPOST)
    objects = Image.open(S3K / sign["sheets"][0])
    manifest = ui_manifest(extra, "ui")
    ui = Image.open(manifest["sheet"])
    x, y, w, h = manifest["frames"]["sign_face"]
    face = remap_to_display(ui.crop((x, y, x + w, y + h)), ui.getpalette(), set(extra["palette"]), objects)
    sheet = Image.new("P", (64, 32), 0)
    sheet.putpalette(objects.getpalette())
    sheet.paste(face, (0, 0))
    rel = "3K_Global/SignPost_Extra.gif"  # (fixed names: extras.S3K_FIXED)
    out = s3k_build(extra)
    (out / "3K_Global").mkdir(parents=True, exist_ok=True)
    save_sheet(sheet, out / rel)
    sign["sheets"].append(rel)
    sid = len(sign["sheets"]) - 1
    base = {"sonic": "Sonic", "tails": "Tails", "knuckles": "Knuckles"}[extra["base"]]  # whose face it replaces
    sonic = next(a for a in sign["anims"] if a["name"] == base)["frames"][0]
    key = (sonic["sheet"], sonic["x"], sonic["y"], sonic["w"], sonic["h"])
    count = 0
    for a in sign["anims"]:
        for f in a["frames"]:
            if (f["sheet"], f["x"], f["y"], f["w"], f["h"]) == key:
                f.update(sheet=sid, x=0, y=0, w=face.width, h=face.height)
                count += 1
    ani_v5.write_bin(out / "3K_Global" / "SignPost_Extra.bin", sign)
    print(f"{extra['art'].name} SignPost_Extra.bin: {extra['name']} ({count} frames)")


SPECIAL_CLEAR = S3K / "3K_HPZ" / "SpecialClear.bin"
# the results lines that name the character, per base ("{}": Sonic / Tails / Knuckles). "Continue Sonic"... are not
# names but little pictures (Display.gif) and stay the game's
SPECIAL_CLEAR_LINES = ("{} Got A", "{} Got All", "Now {} Can", "Be Super {}", "{} Can Go To")
SPECIAL_CLEAR_FONT = 128  # the special stage results draw the blue name font 128 palette slots up from the HUD's


def special_clear_names(clear, sheets, base):
    """The frames in the base's results lines that are its name: those whose pixels are the HUD's "Player Name" frame
    (Sonic 0; Tails 1, and 5 "MILES"; Knuckles 2) 128 slots up (the same art, checked, not assumed)."""
    index = {"sonic": [0], "tails": [1, 5], "knuckles": [2]}[base]
    names = []
    for k in index:
        names.append(frame_image("Player Name", k).point(lambda i: i + SPECIAL_CLEAR_FONT if i else 0).tobytes())
    rects = set()
    for a in clear["anims"]:
        for f in a["frames"]:
            crop = sheets[f["sheet"]].crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])).tobytes()
            if crop in names:
                rects.add((f["sheet"], f["x"], f["y"], f["w"], f["h"], names.index(crop)))
    return rects


def build_special_clear(extra, glyphs):
    """3K_HPZ/SpecialClear_Extra.bin: the special stage results with the extra's own name in the lines that name its
    base ("CHARMY GOT A", "NOW CHARMY CAN" / "BE SUPER CHARMY", "CHARMY GOT ALL", "CHARMY CAN GO TO"), its name the
    act results' (build: word()) 128 palette slots up, as the game's own names here are the HUD's. The line keeps the
    base line's gaps between its words, and is centred as the game centres the base's: left end at -(width // 2)
    plus the base line's own offset from that. Every other animation and frame is the game's; only these lines'
    positions (px) and their name frames change, and the name's frames name a third sheet,
    3K_HPZ/SpecialClear_Extra.gif. The NoSwap DLL loads it instead of SpecialClear.bin."""
    clear = ani_v5.read_bin(SPECIAL_CLEAR)
    sheets = [Image.open(S3K / s) for s in clear["sheets"]]
    names = special_clear_names(clear, sheets, extra["base"])
    if len(names) != {"tails": 2}.get(extra["base"], 1):
        sys.exit(f"SpecialClear.bin: {extra['base']}'s name frames not found ({names})")
    name = word(extra["name"], glyphs).point(lambda i: i + SPECIAL_CLEAR_FONT if i else 0)
    sheet = Image.new("P", (256, 16), 0)
    sheet.putpalette(sheets[0].getpalette())
    if name.width > sheet.width:
        sys.exit(f"{extra['name']}: special stage results name too wide")
    sheet.paste(name, (0, 0))
    rel = "3K_HPZ/SpecialClear_Extra.gif"  # (fixed names: extras.S3K_FIXED)
    out = s3k_build(extra)
    (out / "3K_HPZ").mkdir(parents=True, exist_ok=True)
    save_sheet(sheet, out / rel)
    clear["sheets"].append(rel)
    sid = len(clear["sheets"]) - 1
    who = {"sonic": "Sonic", "tails": "Tails", "knuckles": "Knuckles"}[extra["base"]]
    is_name = lambda f: any(f["sheet"] == r[0] and (f["x"], f["y"], f["w"], f["h"]) == r[1:5] for r in names)
    # Knuckles' "BE SUPER KNUCKLES" has a red SUPER to go with his red name: the extra's name is blue (as in its act
    # results), so its SUPER is the blue one Sonic's and Tails' lines use (the game's frame, same size)
    blue_super = next(a for a in clear["anims"] if a["name"] == "Be Super Sonic")["frames"][1]
    red_super = next(a for a in clear["anims"] if a["name"] == "Be Super Knuckles")["frames"][1]
    for f in next(a for a in clear["anims"] if a["name"] == "Be Super Knuckles")["frames"] if who == "Knuckles" else []:
        if (f["sheet"], f["x"], f["y"]) == (red_super["sheet"], red_super["x"], red_super["y"]):
            f.update({k: blue_super[k] for k in ("sheet", "x", "y", "w", "h")})
    widths = {}
    for line in SPECIAL_CLEAR_LINES:
        frames = next(a for a in clear["anims"] if a["name"] == line.format(who))["frames"]
        # the words left to right: the name once (Tails' "MILES" frame is the same place's other spelling)
        main = [f for f in frames if not is_name(f) or (f["sheet"], f["x"], f["y"], f["w"], f["h"], 0) in names]
        main.sort(key=lambda f: f["px"])
        base_left, base_width = main[0]["px"], main[-1]["px"] + main[-1]["w"] - main[0]["px"]
        offset = base_left + base_width // 2  # the base line's own offset from centred (0 mostly, "Got All" -2)
        x, lefts = 0, []
        for k, f in enumerate(main):
            if k:
                x += f["px"] - (main[k - 1]["px"] + main[k - 1]["w"])  # the base line's gap before this word
            lefts.append(x)
            x += name.width if is_name(f) else f["w"]
        left = -(x // 2) + offset
        for f, lx in zip(main, lefts):
            f["px"] = left + lx
            if is_name(f):
                name_px = f["px"]
        for f in frames:
            if is_name(f):
                f.update(sheet=sid, x=0, y=0, w=name.width, h=name.height, px=name_px)
        widths[line.format(extra["name"])] = (left, left + x)
    ani_v5.write_bin(out / "3K_HPZ" / "SpecialClear_Extra.bin", clear)
    print(f"{extra['art'].name} SpecialClear_Extra.bin: {extra['name']} (name {name.width} px; lines "
          + ", ".join(f"{k} {a}..{b}" for k, (a, b) in widths.items()) + ")")
    return widths


if __name__ == "__main__":
    glyphs = font()
    for e in EXTRAS:
        build(e, glyphs)
        build_signpost(e)
        build_special_clear(e, glyphs)
