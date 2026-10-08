#!/usr/bin/env python3
"""Read and write Retro Engine v5 sprite animation files (.bin, "SPR" format), as used by S3&K in Origins.

Layout: "SPR\\0", u32 total frame count, u8 sheet count + sheet paths, u8 hitbox count + hitbox names,
u16 animation count, then per animation: name, u16 frame count, s16 speed, u8 loop index, u8 rotation
style, and per frame: u8 sheet, s16 duration, u16 unicode char, s16 x, y, w, h, pivot x, pivot y, and
one (left, top, right, bottom) s16 box per hitbox name. Strings are u8 length (including a trailing NUL).
"""
import struct
import sys
from pathlib import Path


def read_bin(path):
    d = Path(path).read_bytes()
    if d[:4] != b"SPR\0":
        sys.exit(f"{path}: not a v5 sprite animation")
    p = 4

    def take(fmt):
        nonlocal p
        v = struct.unpack_from("<" + fmt, d, p)
        p += struct.calcsize("<" + fmt)
        return v if len(v) > 1 else v[0]

    def string():
        nonlocal p
        n = d[p]
        s = d[p + 1:p + 1 + n].rstrip(b"\0").decode()
        p += 1 + n
        return s

    total = take("I")
    sheets = [string() for _ in range(take("B"))]
    hitboxes = [string() for _ in range(take("B"))]
    anims = []
    for _ in range(take("H")):
        name = string()
        count, speed, loop, rot = take("H"), take("h"), take("B"), take("B")
        frames = []
        for _ in range(count):
            sheet, duration, char = take("B"), take("h"), take("H")
            x, y, w, h, px, py = take("hhhhhh")
            boxes = [take("hhhh") for _ in hitboxes]
            frames.append(dict(sheet=sheet, duration=duration, char=char, x=x, y=y, w=w, h=h, px=px, py=py, boxes=boxes))
        anims.append(dict(name=name, speed=speed, loop=loop, rot=rot, frames=frames))
    if p != len(d):
        sys.exit(f"{path}: {len(d) - p} trailing bytes")
    return dict(total=total, sheets=sheets, hitboxes=hitboxes, anims=anims)


def write_bin(path, ani):
    out = bytearray(b"SPR\0")

    def string(s):
        b = s.encode() + b"\0"
        out.append(len(b))
        out.extend(b)

    out += struct.pack("<I", sum(len(a["frames"]) for a in ani["anims"]))
    out.append(len(ani["sheets"]))
    for s in ani["sheets"]:
        string(s)
    out.append(len(ani["hitboxes"]))
    for s in ani["hitboxes"]:
        string(s)
    out += struct.pack("<H", len(ani["anims"]))
    for a in ani["anims"]:
        string(a["name"])
        out += struct.pack("<HhBB", len(a["frames"]), a["speed"], a["loop"], a["rot"])
        for f in a["frames"]:
            out += struct.pack("<BhHhhhhhh", f["sheet"], f["duration"], f["char"], f["x"], f["y"], f["w"], f["h"], f["px"], f["py"])
            for box in f["boxes"]:
                out += struct.pack("<hhhh", *box)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(bytes(out))


if __name__ == "__main__":
    a = read_bin(sys.argv[1])
    print("sheets", a["sheets"], "hitboxes", a["hitboxes"], "frames", a["total"])
    for i, x in enumerate(a["anims"]):
        f = x["frames"]
        print(i, x["name"], len(f), x["speed"], x["loop"], x["rot"], (f[0]["w"], f[0]["h"], f[0]["px"], f[0]["py"], f[0]["duration"]) if f else "")
