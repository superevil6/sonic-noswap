#!/usr/bin/env python3
"""Each extra's S3&K UI accent: the three shades (light to dark) the act results draw its name and the blue streaks
beside BONUS / TOTAL in. Written into its package's noswap_character.json as "ui_accent" (build_packages.character_json);
the S3&K DLL (NoSwapS3K.cpp, namespace accent) puts them in bank 0 slots 2-4 while the results object draws.

S3&K's results font and Sonic's streaks use slots 2, 3, 4 (Sonic's own blues: light, main, dark shade); Tails' and
Knuckles' streaks are their own frames in their own slots, and every extra's built name uses 2-4. So an extra's accent
is exactly three colours. A runtime palette effect only (faithful-art rule): no art file changes.

The accent is extras.UI_ACCENT's hand-set shades for that character, else picked from its own palette: the hue family
its sprites use most (by pixel count in its S3&K sheet), its most-used shade as the main one, and the nearest brighter
and darker shades of that family around it (made lighter / darker from the main one when the family has none).
None: no accent of its own (no own colours, as Metal Sonic in Sonic's): it keeps Sonic's blue.
"""
import colorsys
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

SHADES = 3  # the results font's body: slots 2 (light), 3 (main), 4 (dark)
READABLE = (45, 180)  # the main shade's luma range (Sonic's blue: 69)


def _hex(c):
    return f"#{c:06X}"


def _rgb(c):
    return (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF


def _luma(c):
    r, g, b = _rgb(c)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _hsv(c):
    r, g, b = _rgb(c)
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)


def _mix(c, to, amount):
    return int.from_bytes(bytes(round(a + (b - a) * amount) for a, b in zip(_rgb(c), _rgb(to))), "big")


def _counts(extra):
    """Pixels per palette slot in its S3&K player sheet (empty when it isn't built yet: every colour counts 1)."""
    from extras import s3k_build
    sheet = s3k_build(extra) / "3K_Players" / "Extra.gif"
    if not sheet.exists():
        return Counter()
    from PIL import Image
    im = Image.open(sheet)
    return Counter(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())


def automatic(extra):
    """Three shades from its own palette (light to dark), or None when it has no own colours."""
    pal = extra["palette"]
    if not pal:
        return None
    counts = _counts(extra)
    used = {s: c for s, c in pal.items() if counts.get(s, 1) > 0}
    chroma = {s: c for s, c in used.items() if _hsv(c)[1] >= 0.3 and _hsv(c)[2] >= 0.2}
    pool = chroma or used
    weight = lambda s: counts.get(s, 1)  # noqa: E731

    def same_family(a, b, degrees=20):
        if not chroma:
            return True  # all greys: one family
        d = abs(_hsv(a)[0] - _hsv(b)[0]) % 1.0
        return min(d, 1 - d) <= degrees / 360

    # the hue family with the most pixels: each colour's family is the colours within 20 degrees of it
    best = max(pool, key=lambda s: (sum(weight(t) for t in pool if same_family(pool[s], pool[t])), weight(s), -s))
    family = {s: pool[s] for s in pool if same_family(pool[best], pool[s])}
    # its main shade: the most-used one bright enough to read as the letters' body (Sonic's is luma 69), else the
    # one nearest that
    readable = [s for s in family if READABLE[0] <= _luma(family[s]) <= READABLE[1]]
    main = (max(readable, key=lambda s: (weight(s), -s)) if readable
            else min(family, key=lambda s: abs(_luma(family[s]) - 90)))
    m = family[main]
    near = [c for c in family.values() if same_family(m, c, 15)]
    brighter = sorted((c for c in near if _luma(c) > _luma(m) + 12), key=_luma)
    darker = sorted((c for c in near if _luma(c) < _luma(m) - 12), key=_luma, reverse=True)
    light = brighter[0] if brighter else _mix(m, 0xFFFFFF, 0.35)
    dark = darker[0] if darker else _mix(m, 0x000000, 0.45)
    return [light, m, dark]


def accent(extra):
    """Its "ui_accent" for noswap_character.json: ["#RRGGBB"] * 3, light to dark; None: Sonic's blue."""
    from extras import UI_ACCENT
    hand = UI_ACCENT.get(extra["art"].name)
    shades = [int(str(c).lstrip("#"), 16) if isinstance(c, str) else c for c in hand] if hand else automatic(extra)
    if shades is None:
        return None
    if len(shades) != SHADES:
        raise SystemExit(f"ui_accent: {extra['name']} needs {SHADES} shades (light to dark), has {len(shades)}")
    return [_hex(c) for c in shades]


# Sonic Mania's act clear / UFO results name ("<NAME> GOT THROUGH", SpecialClear's): the extra's built name is in
# SONIC's letters' global slots (tools/build_mania_hud.py: 2, 3, 4 the 3D side and drop shadow, darkest first; 5 the
# face's lower part, 6 its body, 7 its lit rim, 11 its highlight; 40, the top glint, is the white the HUD's numbers
# share, so it stays). Mania picks Tails' and Knuckles' name colours the same way: their name frames are drawn in their
# own slots (19-23 / 47, 80-85 / 14), Sonic's in these. NoSwapMania (ManiaHud.h) writes these 7 colours there only
# while the name draws (ActClear / SpecialClear), then puts the scene's back: a runtime palette effect.
MANIA_NAME_SLOTS = (2, 3, 4, 5, 6, 7, 11)


def mania_name(extra):
    """Its Mania results name's colours for MANIA_NAME_SLOTS ("#RRGGBB" each), a ramp of its S3&K accent (light, main,
    dark): the body its main shade, the rim its light one, the 3D side its dark one; the steps between and beyond are
    those shades mixed (toward each other, white or black) as Sonic's blues step. None: Sonic's blue (no accent)."""
    # (a Mania-only package (tools/mania_only.py) has no S3&K accent: its entry's own "ui_accent", if any)
    shades = accent(extra) if "palette" in extra else extra.get("ui_accent")
    if shades is None:
        return None
    light, main, dark = (int(c.lstrip("#"), 16) for c in shades)
    ramp = {2: _mix(dark, 0x000000, 0.5), 3: dark, 4: _mix(main, dark, 0.7), 5: _mix(main, dark, 0.35),
            6: main, 7: light, 11: _mix(light, 0xFFFFFF, 0.45)}
    return [_hex(ramp[s]) for s in MANIA_NAME_SLOTS]


if __name__ == "__main__":  # list every extra's accent (and where it came from)
    from extras import EXTRAS, UI_ACCENT
    for e in EXTRAS:
        print(f"{e['art'].name:12} {'hand' if e['art'].name in UI_ACCENT else 'auto'} {accent(e)}")
