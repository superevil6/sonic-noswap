"""Exact BC7 encoding of solid-colour 4x4 blocks, and BC7 DDS helpers.

Only what the menu art needs: pixel art upscaled by a multiple of 4, so every 4x4 block is one colour
(or fully transparent). Each block is written in BC7 mode 5 (one subset, RGB endpoints of 7 bits, separate
8-bit alpha endpoints, 2-bit indices) with every pixel on colour index 1 (weight 21/64): every 8-bit
channel value is reachable exactly that way (mode 6 can't: its shared p-bits make e.g. (0,x,x,255)
impossible). Alpha is exact since both alpha endpoints are the alpha itself.
"""
import struct
from functools import lru_cache

import numpy as np

WEIGHTS2 = [0, 21, 43, 64]


def _interp(e0, e1, w):
    return ((64 - w) * e0 + w * e1 + 32) >> 6


def _expand7(a):
    return (a << 1) | (a >> 6)


@lru_cache(maxsize=None)
def _colour_table():
    """value -> (a, b) 7-bit endpoints that give exactly that value at colour index 1 (weight 21)"""
    out = {}
    for a in range(128):
        for b in range(128):
            out.setdefault(_interp(_expand7(a), _expand7(b), WEIGHTS2[1]), (a, b))
    assert len(out) == 256
    return out


@lru_cache(maxsize=None)
def encode_solid(rgba):
    """16-byte BC7 mode-5 block whose 16 pixels all decode to exactly `rgba`: colour endpoints chosen
    so index 1 interpolates to each exact 8-bit channel value, alpha endpoints both = alpha (8-bit)."""
    t = _colour_table()
    bits, n = 0, 0

    def put(v, width):
        nonlocal bits, n
        bits |= (v & ((1 << width) - 1)) << n
        n += width

    put(1 << 5, 6)  # mode 5: five 0 bits then a 1
    put(0, 2)  # no channel rotation
    for c in rgba[:3]:
        a, b = t[c]
        put(a, 7)
        put(b, 7)
    put(rgba[3], 8)
    put(rgba[3], 8)
    put(1, 1)  # colour index, anchor (1 bit)
    for _ in range(15):
        put(1, 2)
    put(0, 1)  # alpha index, anchor
    for _ in range(15):
        put(0, 2)
    assert n == 128
    return bits.to_bytes(16, "little")


def decode_solid(block):
    """RGBA of pixel 0 of a mode-5 block from encode_solid (used as a self-check)."""
    v = int.from_bytes(block, "little")
    assert v & 0x3F == 0x20, "not mode 5"
    p = 8
    rgb = []
    for _ in range(3):
        a = (v >> p) & 0x7F; b = (v >> (p + 7)) & 0x7F; p += 14
        rgb.append((a, b))
    a0 = (v >> p) & 0xFF; a1 = (v >> (p + 8)) & 0xFF; p += 16
    ci = (v >> p) & 1; p += 31
    ai = (v >> p) & 1
    col = tuple(_interp(_expand7(a), _expand7(b), WEIGHTS2[ci]) for a, b in rgb)
    return col + (_interp(a0, a1, WEIGHTS2[ai]),)


def encode_image(rgba):
    """BC7 data for an HxWx4 uint8 array (H, W multiples of 4) whose every 4x4 block is one colour.
    Fully transparent pixels count as (0,0,0,0). Raises if a block isn't solid."""
    a = np.array(rgba, dtype=np.uint8, copy=True)
    h, w = a.shape[:2]
    assert h % 4 == 0 and w % 4 == 0
    a[a[..., 3] == 0] = 0
    blocks = a.reshape(h // 4, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(h // 4, w // 4, 16, 4)
    first = blocks[:, :, :1, :]
    bad = np.argwhere((blocks != first).any(axis=(2, 3)))
    if len(bad):
        by, bx = bad[0]
        raise ValueError(f"4x4 block at pixel ({bx * 4},{by * 4}) is not one colour; {len(bad)} such blocks")
    out = bytearray()
    for row in first[:, :, 0, :]:
        for c in row:
            key = tuple(int(x) for x in c)
            blk = encode_solid(key)
            assert decode_solid(blk) == key
            out += blk
    return bytes(out)


# ---------------------------------------------------------------- DDS (DX10 header, BC7)
DDS_HEADER = 4 + 124 + 20


def dds_info(dds):
    assert dds[:4] == b"DDS " and dds[84:88] == b"DX10"
    h, w = struct.unpack_from("<II", dds, 12)
    fmt = struct.unpack_from("<I", dds, 128)[0]
    mips = struct.unpack_from("<I", dds, 28)[0]
    return w, h, fmt, mips


def dds_append_rows(dds, bc7_rows, extra_height):
    """A single-mip BC7 DDS with `extra_height` pixel rows (BC7 data `bc7_rows`) added at the bottom."""
    w, h, fmt, mips = dds_info(dds)
    assert fmt == 98 and mips == 1, "expected a single-mip BC7_UNORM texture"
    assert len(dds) == DDS_HEADER + (w // 4) * (h // 4) * 16
    assert len(bc7_rows) == (w // 4) * (extra_height // 4) * 16
    out = bytearray(dds) + bc7_rows
    struct.pack_into("<I", out, 12, h + extra_height)
    struct.pack_into("<I", out, 20, len(out) - DDS_HEADER)  # pitchOrLinearSize = main image size
    return bytes(out)
