"""Writing sprite sheets the way the games' own are stored.

The originals are plain GIFs: rows in order (not interlaced), a full 256-colour palette and no
transparency block (the engine treats index 0 as transparent anyway). Pillow interlaces GIFs by
default, and an interlaced Special/Objects.gif broke the Sonic 1 special stage's rotated maze blocks
(they drew garbage) while its normally drawn sprites looked fine.

Origins' GIF loader (all four games) also stops at the first 0x3B byte (the GIF trailer, ";") even
inside the palette: a colour with a 0x3B in it made the whole sheet load as nothing (Gamma's 33333B,
2026-09-26). Such a byte is nudged to 0x3C, one step in one channel; the games draw with their own
palettes (the scripts' and the DLL's colours are untouched), so nothing on screen changes.

The header is written as the games' own sheets have it: "GIF89a" with the logical screen's colour
resolution bits set (flags 0xF7 for a 256-colour table). Pillow writes "GIF87a" with those bits clear
(0x87), and Sonic 1 loaded such a 512-wide sheet (the ending's) as nothing, while the same pixels with the
game's header drew fine (2026-09-26). Only these header bytes change; the image data is Pillow's.
"""
import os

TRAILER = 0x3B
COLOUR_RESOLUTION = 0x70  # the logical screen descriptor's colour resolution bits (8 bits per primary)


def save_sheet(img, path):
    os.makedirs(os.path.dirname(os.fspath(path)) or ".", exist_ok=True)  # (a fresh work tree: the Creator Kit's)
    pal = img.getpalette()
    if pal and TRAILER in pal:
        img = img.copy()
        img.putpalette([TRAILER + 1 if v == TRAILER else v for v in pal])
    img.save(path, interlace=False, optimize=False)  # optimize would renumber palette slots
    with open(path, "r+b") as f:  # the games' header style (see above)
        head = bytearray(f.read(11))
        if head[:6] != b"GIF87a" and head[:6] != b"GIF89a":
            raise ValueError(f"{path}: not a GIF")
        head[:6] = b"GIF89a"
        head[10] |= COLOUR_RESOLUTION
        f.seek(0)
        f.write(head)
