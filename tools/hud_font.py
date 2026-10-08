"""The extras' HUD name-tag letters (the life icon's "SONIC"-style tag), cut from a human-made sheet.

Source: testmods/_fonts/Sonic1_Fonts_RayanC.png, "Sonic 1 Title Card / HUD / General Font (Expanded)" by Rayan C.
(Rayan64_C), The Spriters Resource asset 493842 (testmods/_fonts/SOURCE.txt; credit appreciated, given in the README).
Its yellow small alphabet (y 564-571, the white row above it recoloured by Rayan) is the Sonic 1 life-icon name font:
its S, O, N, I, C, T, A, L, M, E, K and Y are the game's own SONIC / TAILS / MILES / K·T·E / AMY letters, the rest
are Rayan's in the same style. Each cell already carries its black shadow (right and below). The pixels are copied
unchanged: yellow -> "f", black -> "1" (the build maps those to the HUD colours: pixel_colours), anything else
(Rayan's cell backgrounds, which mark each letter's origin) -> "." (transparent). Nothing is redrawn.

tag(word) lays the letters out as the game's own tags do: each letter's pixels, then one blank column."""

from functools import lru_cache
from pathlib import Path

from PIL import Image

SHEET = Path(__file__).resolve().parent.parent / "testmods" / "_fonts" / "Sonic1_Fonts_RayanC.png"
TOP, BOTTOM = 564, 572  # the yellow row: 6 letter rows, the shadow row, and Q's tail
# (x0, x1) of each cell, inclusive, in the sheet's order: 0-9, A A B C D E E F G H I J K K L M N O P Q R S T T U V W W
# X Y Y Z, then · . , : ; ! ? (the close box after them is left out)
CELLS = [(4, 10), (12, 15), (17, 23), (25, 31), (33, 39), (41, 47), (49, 55), (57, 63), (65, 71), (73, 79),
         (81, 86), (88, 93), (95, 100), (102, 107), (109, 114), (116, 121), (123, 129), (131, 136), (138, 144),
         (146, 151), (153, 155), (157, 162), (164, 171), (173, 179), (181, 185), (187, 194), (196, 202), (204, 209),
         (211, 216), (218, 223), (225, 230), (232, 237), (239, 245), (247, 253), (255, 260), (262, 267), (269, 277),
         (279, 286), (288, 293), (295, 302), (304, 310), (312, 317), (319, 321), (323, 325), (327, 329), (331, 333),
         (335, 337), (339, 341), (343, 348)]
# Where the sheet has two versions of a letter, the first (the game's own: TAILS' A, MILES' E, K·T·E's K and T, AMY's
# Y) is used; W is Rayan's first (plain) one.
ORDER = ("0123456789", "A", None, "BCDE", None, "FGHIJK", None, "LMNOPQRST", None, "UVW", None, "X", "Y", None, "Z",
         "·.,:;!?")
YELLOW, BLACK = (252, 252, 0), (0, 0, 0)
SPACE = 4  # blank columns for " " (plus the usual one after each letter)


def _chars():
    out = []
    for part in ORDER:
        out.extend([None] if part is None else list(part))
    assert len(out) == len(CELLS), (len(out), len(CELLS))
    return out


@lru_cache(maxsize=None)
def glyphs():
    """{character: [row strings]} of "f" (letter), "1" (shadow) and "." (transparent), trimmed to the pixels."""
    im = Image.open(SHEET).convert("RGBA")
    out = {}
    for ch, (x0, x1) in zip(_chars(), CELLS):
        if ch is None:
            continue
        rows = []
        for y in range(TOP, BOTTOM):
            s = ""
            for x in range(x0, x1 + 1):
                p = im.getpixel((x, y))
                s += "f" if p[3] and p[:3] == YELLOW else "1" if p[3] and p[:3] == BLACK else "."
            rows.append(s)
        while rows and not rows[-1].strip("."):
            rows.pop()
        cols = [i for i in range(len(rows[0])) if any(r[i] != "." for r in rows)]
        out[ch] = [r[cols[0]:cols[-1] + 1] for r in rows]
    return out


def tag(word):
    """The name tag for `word` (upper case letters, digits, spaces) as pixel rows for a config's "pixels"."""
    g = glyphs()
    height = max(len(g[c]) for c in word if c != " ")
    rows = [""] * height
    for ch in word:
        if ch == " ":
            rows = [r + "." * SPACE for r in rows]
            continue
        glyph = g[ch]
        w = len(glyph[0])
        for r in range(height):
            rows[r] += (glyph[r] if r < len(glyph) else "." * w) + "."
    return [r.rstrip(".") for r in rows]


# A typed name tag (character.json "ui": {"life_name": {"text": "NAME"}}, or left out: the character's "name"): these
# letters in the HUD's yellow and shadow, as the make_configs.py characters' HUD_FONT
HUD_COLOURS = {"f": "#fcfc00", "1": "#000000"}


# The room the HUD keeps for a name tag in every package: noswap_common.UI_RESERVE["life_name"] (0, 0, 72, 7), copied
# here because importing noswap_common loads every character (extras.py). A longer or taller tag would grow the shared
# box and move every other package's art.
ROOM = (72, 7)


def room():
    return ROOM


def size(word):
    """(w, h) of tag(word) in px. KeyError for a letter the font doesn't have."""
    rows = tag(word)
    return max(map(len, rows)), len(rows)


def problems(word):
    """Why `word` can't be a name tag, as messages (none: it can)."""
    g = glyphs()
    if not isinstance(word, str) or not word.strip():
        return ["the name tag is empty"]
    bad = sorted({c for c in word if c != " " and c not in g})
    if bad:
        return [f"letter{'s' * (len(bad) > 1)} {' '.join(repr(c) for c in bad)} not in the HUD font (it has A-Z, 0-9, "
                "space and · . , : ; ! ?; capitals only)"]
    w, h = size(word)
    rw, rh = room()
    out = []
    if w > rw:
        out.append(f"{word!r} is {w} px wide: the HUD has room for {rw} (shorten it)")
    if h > rh:
        tall = "".join(sorted({c for c in word if c in g and len(g[c]) > rh}))
        out.append(f"{tall} reach{'es' * (len(tall) == 1)} below the {rh}-px room ({h} px tall): leave {'it' if len(tall) == 1 else 'them'} out")
    return out


def element(text, colours=None):
    """sheet2ani's UI element for a typed tag: the same as the make_configs characters' {"pixel_colours": HUD_FONT,
    "pixels": hud_font.tag(NAME)}."""
    return {"pixel_colours": colours or dict(HUD_COLOURS), "pixels": tag(text)}


if __name__ == "__main__":
    import sys
    for line in tag(" ".join(sys.argv[1:]) or "SONIC"):
        print(line)
