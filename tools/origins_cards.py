"""Origins' character select cards from the installed packages (docs/plan-b-modular-characters.md, phase B).

The select's card pictures and names live in archives Origins loads from NoSwap's raw/ folder: the pictures in
raw/ui/ui_gamestage.pac (the popup's own copy of the scene) and raw/ui/ui_mainmenu.pac, the names in
raw/text/text_menu_<language>.pac. tools/build_origins_menu.py builds those ONCE with SLOTS generic cards; at startup
the DLL writes each offered character's card into a copy of them (NoSwap's cache/ folder) and serves the copies.

A card slot s (1..SLOTS) is:
- a picture: a CELL_W x CELL_H cell of BC7 blocks appended below menu_main_menu_chara_select_chara_sonic.dds, shown by
  the animation pattern(s, lines) (the scene's one generic picture group, its crop index set to the slot's cell);
- two name lines: the text keys name_key(s, 1) and name_key(s, 2), each with room for NAME_UNITS UTF-16 units;
- a sprite credit line (credit_key(s), room for CREDIT_UNITS units): the package's noswap_character.json "credit_short"
  (e.g. "Sprites: Akimaca"), shown in the select's own small text box CREDIT_CAST (added to the popup's scene below the
  zone-name bar) while the card is highlighted: the DLL sets that box's text key to the card's credit key.

Only fixed byte ranges ever change, so the DLL needs no archive code: the chunks holding them are stored as LZ4 blocks
of literals only (lz4_literal: a valid LZ4 block any reader decodes, whose bytes are the data itself after a header
that depends only on the length), and a descriptor (DESCRIPTOR, written by build_origins_menu.py) lists, per archive,
where each literal run sits in the file ("runs": [stream offset, file offset, length]) and where each slot's cell rows
and name texts / lengths are in that stream. plan() below turns cards into (file offset, bytes) writes; the DLL's
MenuCards.h is the same thing in C++ (proved equal by the scratchpad tests).

A package's card (its folder's PICTURE): a BC7 DDS (DX10 header, format 98, one mip), at most CELL_W x CELL_H, sides
multiples of 4, placed bottom-centre in the cell (transparent around it). NoSwap's own packages' cards are their Sonic 1
"Stopped" frame 0 enlarged SCALE times (nearest), its pivot on the cell's centre line and its feet BASELINE pixels above
the cell's bottom (card_dds). Its name lines: the package's "name" split at the first space ("METAL" / "SONIC").
"""
import json
import struct

import numpy as np

SLOTS = 64                  # cards the archives hold (the S3&K save screen pictures' cap too)
CELL_W, CELL_H = 440, 536   # a card cell in DDS pixels (the .swif declares half); 536: Gamma's picture, the tallest
SCALE, BASELINE = 8, 20     # NoSwap's own cards: 8x pixels, feet 20 px above the cell's bottom (as Sonic's picture)
NAME_UNITS = 31             # UTF-16 units per name line (+ a terminator: 64 bytes)
PICTURE = "ui/card_picture.dds"                 # in a package
DESCRIPTOR = "raw/ui/noswap_cards.json"         # in NoSwap's folder
PICTURE_ARCHIVES = ("raw/ui/ui_gamestage.pac", "raw/ui/ui_mainmenu.pac")
FIRST_KIND = 7
BLOCK = 16                  # bytes per BC7 block (4x4 pixels)
DESCRIPTOR_VERSION = 3      # 2: with the main menu's CONTINUE bubble heads ("head", archives' "head_cells");
                            # 3: with the sprite credit lines ("credit", text archives' "credits")
CREDIT_UNITS = 40           # UTF-16 units per credit line (+ a terminator: 82 bytes)
CREDIT_CAST = "sysf_noswap_credit"  # the select scene's credit text box (layer "lay", build_origins_menu.py)

# The main menu's CONTINUE bubble heads (menu_main_menu_icon_chara_s.dds in raw/ui/ui_mainmenu.pac, drawn by the casts
# pattern_chara_1 / _2 of menu_main_menu_island.swif in every raw/ui/ui_mainmenu_<language>.pac): a HEAD_W x HEAD_H cell
# per card slot below the game's four heads, crop HEAD_FIRST_CROP + slot - 1 of both casts. A package's head
# (HEAD_PICTURE): a BC7 DDS at most a cell's size, sides multiples of 4, placed in the middle of the cell. NoSwap's own
# packages' heads are their 16x16 life icon enlarged HEAD_SCALE times (nearest: pixel-exact).
HEAD_W, HEAD_H = 120, 96
HEAD_SCALE = 4
HEAD_FIRST_CROP = 4
HEAD_PICTURE = "ui/menu_head.dds"


def pattern(slot, lines):
    """The picture animation of card slot `slot` (1..SLOTS): the second name line shown when lines == 2."""
    return f"PRM_noswap_{slot}" + ("_2" if lines == 2 else "")


def name_key(slot, line):
    return f"MAINMENU_character_name_noswap{slot}_{line}"


def credit_key(slot):
    return f"MAINMENU_character_credit_noswap{slot}"


def name_lines(name):
    """A character's name as the card's two lines: split at the first space ("METAL SONIC" -> "METAL", "SONIC")."""
    first, _, rest = name.partition(" ")
    return first, rest


def slot_for(kinds):
    """{kind: slot} for the offered kinds (in kind order), as the DLL assigns them: kind - 6 when that slot exists and is
    free (so the first 21 characters keep the cards the archives ship with), else the lowest free slot; none past SLOTS."""
    out, used = {}, set()
    for k in sorted(kinds):
        if k - 6 <= SLOTS:
            out[k] = k - 6
            used.add(k - 6)
    for k in sorted(kinds):
        if k not in out:
            free = next((s for s in range(1, SLOTS + 1) if s not in used), None)
            if free is not None:
                out[k] = free
                used.add(free)
    return out


# ---------------------------------------------------------------- the card picture
def place(rgba, frame, scale=SCALE, cell_h=CELL_H):
    """The frame enlarged `scale` times (nearest) in a CELL_W x cell_h cell: its pivot on the centre line, its bottom
    BASELINE pixels above the cell's bottom, like Sonic's idle picture."""
    big = rgba.repeat(scale, 0).repeat(scale, 1)
    left = CELL_W // 2 + frame["px"] * scale
    top = cell_h - BASELINE - frame["h"] * scale
    assert left >= 0 and left + big.shape[1] <= CELL_W and top >= 0, "picture doesn't fit its cell"
    assert left % 4 == 0 and top % 4 == 0, "picture not on 4x4 blocks"
    cell = np.zeros((cell_h, CELL_W, 4), np.uint8)
    cell[top:top + big.shape[0], left:left + big.shape[1]] = big
    return cell


def card_rgba(rgba, frame, scale=SCALE):
    """The card picture (RGBA) of a frame: the bottom of its cell, from the frame's top (to 4 px) down. scale: a
    multiple of 4 (a tall character's frame at 8x is taller than the cell: character.json "card" {"scale": 4})."""
    cell = place(rgba, frame, scale)
    h = frame["h"] * scale + BASELINE
    h += -h % 4
    return cell[CELL_H - h:]


def dds_bc7(w, h, data):
    """A BC7_UNORM DDS (DX10 header, one mip), laid out as the game's own menu textures."""
    assert len(data) == (w // 4) * (h // 4) * BLOCK
    head = bytearray(148)
    head[:4] = b"DDS "
    struct.pack_into("<7I", head, 4, 124, 0x000A1007, h, w, len(data), 1, 1)
    struct.pack_into("<2I4s", head, 76, 32, 4, b"DX10")
    struct.pack_into("<I", head, 108, 0x1000)
    struct.pack_into("<5I", head, 128, 98, 3, 0, 1, 0)
    return bytes(head) + data


def card_dds(rgba, frame, scale=SCALE):
    import bc7
    pic = card_rgba(rgba, frame, scale)
    return dds_bc7(pic.shape[1], pic.shape[0], bc7.encode_image(pic))


def read_card(dds, max_w=CELL_W, max_h=CELL_H):
    """-> (width, height, BC7 blocks) of a package's card picture (or head: max HEAD_W x HEAD_H); raises ValueError if
    it isn't one."""
    if len(dds) < 148 or dds[:4] != b"DDS " or dds[84:88] != b"DX10":
        raise ValueError("not a DDS file with a DX10 header")
    h, w = struct.unpack_from("<II", dds, 12)
    fmt, mips = struct.unpack_from("<I", dds, 128)[0], struct.unpack_from("<I", dds, 28)[0]
    if fmt != 98 or mips > 1:
        raise ValueError(f"format {fmt}, {mips} mips: expected BC7_UNORM (98), one mip")
    if not (0 < w <= max_w and 0 < h <= max_h and w % 4 == 0 and h % 4 == 0):
        raise ValueError(f"{w}x{h}: must be at most {max_w}x{max_h}, sides multiples of 4")
    n = (w // 4) * (h // 4) * BLOCK
    if len(dds) != 148 + n:
        raise ValueError(f"{len(dds)} bytes, expected {148 + n}")
    return w, h, bytes(dds[148:])


def head_dds(icon):
    """A package's CONTINUE bubble head (HEAD_PICTURE) from its life icon (RGBA, transparent (0, 0, 0, 0) around it):
    enlarged HEAD_SCALE times (nearest), as a BC7 DDS."""
    import bc7
    big = np.asarray(icon).repeat(HEAD_SCALE, 0).repeat(HEAD_SCALE, 1)
    h, w = big.shape[:2]
    assert w <= HEAD_W and h <= HEAD_H and w % 4 == 0 and h % 4 == 0, f"{w}x{h} head doesn't fit a head cell"
    return dds_bc7(w, h, bc7.encode_image(big))


def read_head(dds):
    return read_card(dds, HEAD_W, HEAD_H)


# ---------------------------------------------------------------- LZ4 literal-only blocks
def literal_header(n):
    """The LZ4 block header of a block holding `n` bytes as literals only (one sequence, no match)."""
    if n < 15:
        return bytes([n << 4])
    n -= 15
    return bytes([0xF0]) + b"\xff" * (n // 255) + bytes([n % 255])


def lz4_literal(data):
    return literal_header(len(data)) + bytes(data)


def literal_runs(chunks, file_at, stream_at=0):
    """[(stream offset, file offset, length)] for the literal-only chunks among `chunks` [(compressed, uncompressed)]
    stored one after another from file offset `file_at`."""
    out, u = [], stream_at
    for c, raw in chunks:
        hdr = literal_header(len(raw))
        if len(c) == len(hdr) + len(raw) and c[:len(hdr)] == hdr:
            out.append((u, file_at + len(hdr), len(raw)))
        file_at += len(c)
        u += len(raw)
    return out


# ---------------------------------------------------------------- the patch step (the DLL's, in Python)
BLANK = None  # the transparent BC7 block (bc7.encode_solid((0, 0, 0, 0))), filled in on first use


def blank_block():
    global BLANK
    if BLANK is None:
        import bc7
        BLANK = bc7.encode_solid((0, 0, 0, 0))
    return BLANK


def utf16_line(text, room=NAME_UNITS):
    """(bytes of a text line's room (NAME_UNITS, or CREDIT_UNITS for a credit): UTF-16 text then zeros, its length in
    units)"""
    units = text.encode("utf-16-le")[:2 * room]
    return units + bytes(2 * (room + 1) - len(units)), len(units) // 2


def cell_rows(card, cell_w=CELL_W, cell_h=CELL_H, middle=False):
    """The cell_h / 4 block rows (bytes) of a slot's cell holding `card` ((w, h, blocks) or None: blank): bottom-centre
    (a card picture), or in the middle (`middle`: a head)."""
    blank = blank_block()
    bw, bh = cell_w // 4, cell_h // 4
    rows = [bytearray(blank * bw) for _ in range(bh)]
    if card:
        w, h, blocks = card
        cw, ch = w // 4, h // 4
        x0, y0 = (bw - cw) // 2, (bh - ch) // 2 if middle else bh - ch
        for r in range(ch):
            rows[y0 + r][BLOCK * x0:BLOCK * (x0 + cw)] = blocks[BLOCK * cw * r:BLOCK * cw * (r + 1)]
    return [bytes(r) for r in rows]


def to_file(runs, at, data):
    """[(file offset, bytes)] writing `data` at stream offset `at` through the literal runs; raises if a byte isn't in one."""
    out, end = [], at + len(data)
    for u, f, n in runs:
        lo, hi = max(at, u), min(end, u + n)
        if lo < hi:
            out.append((f + lo - u, data[lo - at:hi - at]))
    if sum(len(b) for _, b in out) != len(data):
        raise ValueError(f"stream bytes {at:#x}..{end:#x} aren't all in literal runs")
    return out


def plan(archive, cards):
    """The writes [(file offset, bytes)] that put `cards` {slot: dict(picture=(w, h, blocks) | None, lines=(l1, l2),
    head=(w, h, blocks) | None, credit="..." (optional))} into one archive described by `archive` (an entry of the descriptor's "archives"); every
    other slot is made blank."""
    out = []
    runs = archive["runs"]
    if "cells" in archive:
        pitch = archive["pitch"]
        for s in range(1, SLOTS + 1):
            c = cards.get(s)
            for r, row in enumerate(cell_rows(c and c.get("picture"))):
                out += to_file(runs, archive["cells"][s - 1] + r * pitch, row)
    if "head_cells" in archive:
        pitch = archive["head_pitch"]
        for s in range(1, SLOTS + 1):
            c = cards.get(s)
            for r, row in enumerate(cell_rows(c and c.get("head"), HEAD_W, HEAD_H, middle=True)):
                out += to_file(runs, archive["head_cells"][s - 1] + r * pitch, row)
    if "names" in archive:
        for s in range(1, SLOTS + 1):
            c = cards.get(s)
            for line in (1, 2):
                text_at, length_at = archive["names"][2 * (s - 1) + line - 1]
                room, n = utf16_line(c["lines"][line - 1] if c else "")
                out += to_file(runs, text_at, room)
                out += to_file(runs, length_at, struct.pack("<Q", n))
    if "credits" in archive:
        for s in range(1, SLOTS + 1):
            c = cards.get(s)
            text_at, length_at = archive["credits"][s - 1]
            room, n = utf16_line(c.get("credit", "") if c else "", CREDIT_UNITS)
            out += to_file(runs, text_at, room)
            out += to_file(runs, length_at, struct.pack("<Q", n))
    return out


def check_runs(data, archive):
    """The archive file is the one described: its size, and every literal run's LZ4 header in place."""
    if len(data) != archive["size"]:
        raise ValueError(f"{archive['path']}: {len(data)} bytes, the descriptor says {archive['size']}")
    for u, f, n in archive["runs"]:
        hdr = literal_header(n)
        if data[f - len(hdr):f] != hdr:
            raise ValueError(f"{archive['path']}: no literal block header before file offset {f:#x}")


def apply(data, archive, cards):
    """The archive `data` with `cards` written in (a new bytes object)."""
    check_runs(data, archive)
    out = bytearray(data)
    for f, b in plan(archive, cards):
        out[f:f + len(b)] = b
    return bytes(out)


def load_descriptor(path):
    return json.loads(path.read_text())
