#!/usr/bin/env python3
"""Build Mania Lock-On's menu patches (mods/ManiaLockOn/patches/): the SONIC MANIA button's data for Origins' menu.

Mania Lock-On (native/lockon/) is the stand-alone mod with the SONIC MANIA button in Origins' main menu. The button
needs two things in the game's menu archives, the same ones NoSwap's own archives carry (tools/build_origins_menu.py):
- in every ui_mainmenu_<language>.pac, the island scene (menu_main_menu_island.swif) with the button's two layout
  patterns (build_origins_menu.edit_launcher, LAUNCHER_LAYOUT);
- in every text_menu_<language>.pac, its text keys (LOCKON_TEXT: the same keys as NoSwap's LAUNCHER_TEXT, Lock-On's
  own wording).
Lock-On ships no archive: only a patch per archive (the bytes that differ from the game's own file, PATCH format
below), so it holds none of the game's files. At startup in the player's game the DLL rebuilds each archive it needs
from the game's own copy (checking that copy's size and CRC-32 first, and the result's after) into its cache/ folder,
and serves it when the game opens the archive and no other mod replaces it (native/lockon/src/MenuFiles.h). When NoSwap
is installed its archives (which carry the same patterns and keys) are the ones served, and the patches go unused.

PATCH format (little endian): "MLOP", u32 version 1, u64 source size, u32 source CRC-32, u64 output size, u32 output
CRC-32, u32 op count, then the ops: u8 0 = copy (u64 source offset, u32 length), u8 1 = data (u32 length, the bytes).

Usage: build_lockon_menu.py [--force]   (ORIGINS_GAME: the game's folder, as build_origins_menu.py). Without --force it
does nothing when every patch is newer than the game's archives and the scripts that make them.
"""
import struct
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import build_origins_menu as bom  # noqa: E402
import cnvrs_text  # noqa: E402
import origins_pac  # noqa: E402
import origins_pacx as pacx  # noqa: E402
import surfride  # noqa: E402

OUT = REPO / "mods" / "ManiaLockOn" / "patches"
# The button's label and description keys (the DLL's LABEL_KEY and "MAINMENU_text_" + its description slot "mania").
# The keys must stay NoSwap's (bom.LAUNCHER_TEXT): with NoSwap installed its archives are served instead.
LOCKON_TEXT = {
    "MAINMENU_island_mania": "SONIC MANIA",
    "MAINMENU_text_mania": "Play Sonic Mania (your own copy of the decompilation)",
    "MAINMENU_text_mania_missing": "Sonic Mania decompilation not found: set its folder in Mania Lock-On's settings",
}
assert set(LOCKON_TEXT) == set(bom.LAUNCHER_TEXT), "Lock-On's text keys must be the ones NoSwap's archives carry"
MAGIC, VERSION = b"MLOP", 1
WINDOW = 32  # the match length the source is indexed by (every WINDOW-aligned offset)


# ---------------------------------------------------------------- the patches
def make_patch(src, out):
    """-> the PATCH bytes turning `src` into `out`: copies of source runs where `out` repeats them, data elsewhere."""
    index = {}
    for k in range(0, len(src) - WINDOW + 1, WINDOW):
        index.setdefault(src[k:k + WINDOW], k)
    ops, data_from, i = [], 0, 0
    while i + WINDOW <= len(out):
        j = index.get(out[i:i + WINDOW])
        if j is None:
            i += 1
            continue
        n = WINDOW  # extend the match forward, 4 KB at a time, then byte by byte
        while i + n + 4096 <= len(out) and j + n + 4096 <= len(src) and out[i + n:i + n + 4096] == src[j + n:j + n + 4096]:
            n += 4096
        while i + n < len(out) and j + n < len(src) and out[i + n] == src[j + n]:
            n += 1
        if data_from < i:
            ops.append((1, out[data_from:i]))
        ops.append((0, j, n))
        i += n
        data_from = i
    if data_from < len(out):
        ops.append((1, out[data_from:]))
    b = bytearray(MAGIC + struct.pack("<IQIQII", VERSION, len(src), zlib.crc32(src), len(out), zlib.crc32(out),
                                      len(ops)))
    for op in ops:
        if op[0] == 0:
            b += struct.pack("<BQI", 0, op[1], op[2])
        else:
            b += struct.pack("<BI", 1, len(op[1])) + op[1]
    return bytes(b)


def apply_patch(src, patch):
    """The DLL's ApplyPatch (native/lockon/src/MenuFiles.h), as a check of make_patch."""
    assert patch[:4] == MAGIC
    version, src_size, src_crc, out_size, out_crc, count = struct.unpack_from("<IQIQII", patch, 4)
    assert version == VERSION and len(src) == src_size and zlib.crc32(src) == src_crc
    at, out = 4 + struct.calcsize("<IQIQII"), bytearray()
    for _ in range(count):
        kind = patch[at]
        if kind == 0:
            off, n = struct.unpack_from("<QI", patch, at + 1)
            assert off + n <= len(src)
            out += src[off:off + n]
            at += 13
        else:
            n = struct.unpack_from("<I", patch, at + 1)[0]
            out += patch[at + 5:at + 5 + n]
            at += 5 + n
    assert at == len(patch) and len(out) == out_size and zlib.crc32(out) == out_crc
    return bytes(out)


# ---------------------------------------------------------------- the archives
def build_scene(game):
    """A ui_mainmenu_<language>.pac with only the button's layout patterns added to its island scene."""
    outer = pacx.Outer(game)
    s = pacx.find(outer.root, bom.HEAD_SCENE, "swif")
    swif = outer.root[s["data"]:s["data"] + s["size"]]
    outer.root = pacx.replace_file(outer.root, bom.HEAD_SCENE, "swif", bom.edit_launcher(swif))
    data = outer.build()
    # the check: the same blocks and files as the game's, the scene's layer with the game's animations + the two patterns
    g, o = pacx.Outer(game), pacx.Outer(data)
    assert o.build() == data and o.blocks == g.blocks, "a block changed"
    assert [e["name"] for e in pacx.entries(o.root)] == [e["name"] for e in pacx.entries(g.root)]
    for e in pacx.entries(g.root):
        if e["data"] and not (e["name"] == bom.HEAD_SCENE and e["ext"] == "swif"):
            f = pacx.find(o.root, e["name"], e["ext"])
            assert o.root[f["data"]:f["data"] + f["size"]] == g.root[e["data"]:e["data"] + e["size"]], e["name"]
    f = pacx.find(o.root, bom.HEAD_SCENE, "swif")
    gs = pacx.find(g.root, bom.HEAD_SCENE, "swif")
    bom.check_launcher(surfride.check(o.root[f["data"]:f["data"] + f["size"]]),
                       surfride.parse(g.root[gs["data"]:gs["data"] + gs["size"]]))
    return data


def build_text(game):
    """A text_menu_<language>.pac with only the button's text keys added."""
    header, inner = origins_pac.read_outer(game)
    doc = cnvrs_text.parse(origins_pac.last_file(inner))
    if cnvrs_text.build(doc) != origins_pac.last_file(inner):
        sys.exit("can't reproduce the game's text file, not touching it")
    keys = {e["key"] for e in doc["entries"]}
    for key, text in LOCKON_TEXT.items():
        if key in keys:
            sys.exit(f"{key} already exists in the game's text")
        doc["entries"].append({"key": key, "text": text})
    ids = [cnvrs_text.key_hash(e["key"]) for e in doc["entries"]]
    if len(set(ids)) != len(ids):
        sys.exit("two text keys with the same hash")
    data = origins_pac.write_outer(header, origins_pac.replace_last_file(inner, cnvrs_text.build(doc)))
    texts = {e["key"]: e["text"] for e in cnvrs_text.parse(origins_pac.last_file(origins_pac.read_outer(data)[1]))
             ["entries"]}
    assert all(texts[k] == v for k, v in LOCKON_TEXT.items())
    return data


def up_to_date(jobs):
    inputs = [Path(__file__), Path(bom.__file__), Path(surfride.__file__), Path(pacx.__file__),
              Path(origins_pac.__file__), Path(cnvrs_text.__file__)]
    inputs += [bom.RAW_IN / rel[len("raw/"):] for rel, _ in jobs]
    outputs = [OUT / (rel + ".mlp") for rel, _ in jobs]
    if not all(o.exists() for o in outputs):
        return False
    return min(o.stat().st_mtime for o in outputs) > max(i.stat().st_mtime for i in inputs)


def main():
    jobs = [(f"raw/ui/{p.name}", build_scene) for p in sorted((bom.RAW_IN / "ui").glob("ui_mainmenu_*.pac"))
            if not p.stem.startswith("ui_mainmenu_pkg_")]
    jobs += [(f"raw/text/{p.name}", build_text) for p in sorted((bom.RAW_IN / "text").glob("text_menu_*.pac"))]
    if not jobs:
        sys.exit(f"no menu archives in {bom.RAW_IN} (ORIGINS_GAME)")
    if "--force" not in sys.argv[1:] and up_to_date(jobs):
        print(f"mods/ManiaLockOn/patches: {len(jobs)} archive patches up to date")
        return
    wanted = set()
    total = 0
    for rel, build in jobs:
        game = (bom.RAW_IN / rel[len("raw/"):]).read_bytes()
        data = build(game)
        patch = make_patch(game, data)
        assert apply_patch(game, patch) == data
        dest = OUT / (rel + ".mlp")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or dest.read_bytes() != patch:
            dest.write_bytes(patch)
        else:
            dest.touch()  # (up to date)
        wanted.add(dest)
        total += len(patch)
    for old in OUT.rglob("*.mlp"):  # (archives the game no longer has)
        if old not in wanted:
            old.unlink()
    print(f"mods/ManiaLockOn/patches: {len(jobs)} archive patches ({sum(1 for r, _ in jobs if r.startswith('raw/ui'))} "
          f"scenes, {sum(1 for r, _ in jobs if r.startswith('raw/text'))} texts), {total:,} bytes")


if __name__ == "__main__":
    main()
