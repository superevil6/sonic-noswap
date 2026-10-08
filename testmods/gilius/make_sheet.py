#!/usr/bin/env python3
"""Gilius_sheet.png, the working sheet character.json reads: Ragey's Gilius.png (transparent) on a #ff00ff ground, and
under it, pasted pixel for pixel (crops only, the faithful-art rule), the Earthquake pieces from Bad Moon's
Gilius_Magic_GA2.png (its #0008ff ground made #ff00ff; the "GILIUS MAGIC BY BAD MOON" tag and its wizard are left out).
Run it again after either source changes."""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
BG = (255, 0, 255)
MAGIC_BG = (0, 8, 255)
# piece: (box on Gilius_Magic_GA2.png, where it goes on the working sheet)
PIECES = {
    "ROCK_BIG": ((166, 14, 62, 64), (3, 1160)), "ROCK_SMALL": ((100, 36, 31, 32), (70, 1160)),
    "GSPIKE_R": ((247, 189, 64, 23), (106, 1160)), "WSPIKE_R": ((247, 140, 64, 30), (175, 1160)),
    "DUST_B_R": ((247, 87, 64, 31), (244, 1160)), "DUST_M_R": ((247, 53, 64, 13), (313, 1160)),
    "DUST_S_R": ((255, 15, 48, 7), (3, 1230)), "GSPIKE_L": ((11, 188, 32, 22), (56, 1230)),
    "WSPIKE_L": ((11, 140, 32, 30), (93, 1230)), "DUST_B_L": ((3, 97, 48, 31), (130, 1230)),
    "DUST_M_L": ((3, 66, 48, 13), (183, 1230)), "DUST_S_L": ((3, 34, 48, 7), (236, 1230)),
}
HEIGHT = 1270


def main():
    src = Image.open(HERE / "Gilius.png").convert("RGBA")
    out = Image.new("RGB", (src.width, HEIGHT), BG)
    ground = Image.new("RGBA", src.size, BG + (255,))
    ground.alpha_composite(src)
    out.paste(ground.convert("RGB"), (0, 0))
    magic = Image.open(HERE / "Gilius_Magic_GA2.png").convert("RGB")
    for name, ((x, y, w, h), at) in PIECES.items():
        piece = magic.crop((x, y, x + w, y + h))
        px = piece.load()
        for i in range(w):
            for j in range(h):
                if px[i, j] == MAGIC_BG:
                    px[i, j] = BG
        out.paste(piece, at)
    out.save(HERE / "Gilius_sheet.png")
    print("wrote Gilius_sheet.png", out.size)


if __name__ == "__main__":
    main()
