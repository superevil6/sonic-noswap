#!/usr/bin/env python3
"""Extract files from an RSDKv5 data pack (Sonic Mania's Data.rsdk), by name.

The pack lists files by the MD5 of their lowercased path; encrypted ones are XORed with keys from the MD5 of the
uppercased path and of the decimal file size (the RSDKv5 decompilation's RSDK::OpenDataFile, GenerateELoadKeys and
DecryptBytes, Core/Reader.cpp, ported). File names come from a list (RSDKv5Extract's rsdk_files_list.txt).

    python3 tools/rsdk5_extract.py Data.rsdk names.txt out/ [path prefix filter ...]
e.g. ... "Data/Sprites/Players/" "Data/Palettes/" extracts only those.
"""
import hashlib
import struct
import sys
from pathlib import Path


def read_index(data):
    if data[:4] != b"RSDK":
        sys.exit("not an RSDK data pack")
    count = struct.unpack_from("<H", data, 6)[0]
    files, at = {}, 8
    for _ in range(count):
        digest = data[at:at + 16]
        offset, size = struct.unpack_from("<II", data, at + 16)
        files[digest] = (offset, size & 0x7FFFFFFF, bool(size & 0x80000000))
        at += 24
    return files


def swapped(d):
    """The digest with each 4-byte group reversed (the engine's uint32 view of it)."""
    return b"".join(d[i:i + 4][::-1] for i in range(0, 16, 4))


def keys(name, size):
    a = swapped(hashlib.md5(name.upper().encode()).digest())
    b = swapped(hashlib.md5(str(size).encode()).digest())
    return a, b


def decrypt(buf, name, size):
    ka, kb = keys(name, size)
    key_no, pos_a, pos_b, swap = (size // 4) & 0x7F, 0, 8, False
    out = bytearray(buf)
    for i in range(len(out)):
        v = out[i] ^ key_no ^ kb[pos_b]
        if swap:
            v = ((v << 4) + (v >> 4)) & 0xFF
        out[i] = v ^ ka[pos_a]
        pos_a += 1
        pos_b += 1
        if pos_a <= 15:
            if pos_b > 12:
                pos_b = 0
                swap = not swap
        elif pos_b <= 8:
            pos_a = 0
            swap = not swap
        else:
            key_no = (key_no + 2) & 0x7F
            if swap:
                swap = False
                pos_a, pos_b = key_no % 7, (key_no % 12) + 2
            else:
                swap = True
                pos_a, pos_b = (key_no % 12) + 3, key_no % 7
    return bytes(out)


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    pack, names, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    prefixes = [p.lower() for p in sys.argv[4:]]
    data = pack.read_bytes()
    index = read_index(data)
    found = 0
    for name in names.read_text(errors="replace").splitlines():
        name = name.strip()
        if not name or (prefixes and not any(name.lower().startswith(p) for p in prefixes)):
            continue
        d = hashlib.md5(name.lower().encode()).digest()
        entry = index.get(d) or index.get(swapped(d))
        if not entry:
            continue
        offset, size, enc = entry
        blob = data[offset:offset + size]
        if enc:
            blob = decrypt(blob, name, size)
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        found += 1
    print(f"{found} files extracted ({len(index)} in the pack)")


if __name__ == "__main__":
    main()
