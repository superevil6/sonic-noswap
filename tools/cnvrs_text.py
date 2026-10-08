"""Read and write Hedgehog Engine "cnvrs-text" files (Sonic Origins' localised text, inside text_*.pac).

A cnvrs-text is a BINA 2.1 container. Its data:
- root: u8 version (6), u8 languages (1), u16 entry count, u32 0, u64 -> entries, u64 -> language name, u64 0
- entries (0x30 each, sorted by id): u64 id, u64 -> key, u64 -> attributes, u64 -> UTF-16 text, u64 length, u64 0
- the texts (UTF-16 + terminator, each padded to 8), then the attribute blocks (0x20 each: u64 -> key, 3 x 0),
  both in the file's own "source" order
- a string table (the language name and the keys, each once), then the offset table (where the pointers are)

An entry's id is hash(key): h = h * 127 + byte, modulo 2^32. The game looks keys up by id.
Rebuilding an unchanged file reproduces it byte for byte (checked by build_origins_menu.py).
"""
import struct


def key_hash(key):
    h = 0
    for c in key.encode():
        h = (h * 127 + c) & 0xFFFFFFFF
    return h


def parse(data):
    """-> {"language", "version", "entries": [{"key", "text"}] in source order}"""
    assert data[:8] == b"BINA210L", "not a BINA 2.1 file"
    x = data[0x40:]

    def cstr(o):
        return x[o:x.index(b"\0", o)].decode()

    def utf16(o, n):
        return x[o:o + 2 * n].decode("utf-16-le")

    version, languages, count = struct.unpack_from("<BBH", x, 0)
    entries_at, lang_at = struct.unpack_from("<QQ", x, 8)
    raw = [struct.unpack_from("<QQQQQQ", x, entries_at + 0x30 * i) for i in range(count)]
    for e in raw:
        assert e[0] == key_hash(cstr(e[1])), "unexpected key hash"
        assert struct.unpack_from("<QQQQ", x, e[2])[1:] == (0, 0, 0), "unexpected attributes"
    raw.sort(key=lambda e: e[3])  # source order = order of the texts
    return {"version": version, "languages": languages, "language": cstr(lang_at),
            "entries": [{"key": cstr(e[1]), "text": utf16(e[3], e[4])} for e in raw]}


def encode_offsets(positions):
    """BINA offset table: each step from the previous pointer (4-byte units) in 1, 2 or 4 bytes."""
    out, last = bytearray(), 0
    for p in sorted(positions):
        d = (p - last) >> 2
        if d < 0x40:
            out.append(0x40 | d)
        elif d < 0x4000:
            out += struct.pack(">H", 0x8000 | d)
        else:
            out += struct.pack(">I", 0xC0000000 | d)
        last = p
    while len(out) % 4:
        out.append(0)
    return bytes(out)


def build(doc):
    entries = doc["entries"]
    count = len(entries)
    pad8 = lambda b: b + b"\0" * (-len(b) % 8)

    root_size, entry_size = 0x20, 0x30
    text_at = root_size + entry_size * count
    texts, text_offsets = bytearray(), []
    for e in entries:
        text_offsets.append(text_at + len(texts))
        texts += pad8(e["text"].encode("utf-16-le") + b"\0\0")
    attr_at = text_at + len(texts)
    str_at = attr_at + 0x20 * count

    # string table: each string once, in the order the pointers to them appear in the data
    strings, string_at = bytearray(), {}

    def ref(s):
        if s not in string_at:
            string_at[s] = str_at + len(strings)
            strings.extend(s.encode() + b"\0")
        return string_at[s]

    pointers = []
    body = bytearray(str_at)
    struct.pack_into("<BBHIQQQ", body, 0, doc["version"], doc["languages"], count, 0, root_size,
                     ref(doc["language"]), 0)
    pointers += [8, 16]
    order = sorted(range(count), key=lambda i: key_hash(entries[i]["key"]))
    for slot, i in enumerate(order):
        e, at = entries[i], root_size + entry_size * slot
        struct.pack_into("<QQQQQQ", body, at, key_hash(e["key"]), ref(e["key"]), attr_at + 0x20 * i,
                         text_offsets[i], len(e["text"].encode("utf-16-le")) // 2, 0)
        pointers += [at + 8, at + 16, at + 24]
    body[text_at:attr_at] = texts
    for i, e in enumerate(entries):
        struct.pack_into("<QQQQ", body, attr_at + 0x20 * i, ref(e["key"]), 0, 0, 0)
        pointers.append(attr_at + 0x20 * i)
    while len(strings) % 4:
        strings.append(0)
    offsets = encode_offsets(pointers)

    data = bytes(body) + bytes(strings) + offsets
    node_size = 0x18 + 0x18 + len(data)
    header = b"BINA210L" + struct.pack("<IHH", 0x10 + node_size, 1, 0)
    node = b"DATA" + struct.pack("<IIIIHH", node_size, str_at, len(strings), len(offsets), 0x18, 0)
    return header + node + b"\0" * 0x18 + data


def entry_positions(data):
    """-> {key: (text position, length field position)} in the file `data` (a cnvrs-text): where each entry's UTF-16 text
    starts and where its u64 length (in UTF-16 units) is stored."""
    x = 0x40
    count = struct.unpack_from("<H", data, x + 2)[0]
    entries_at = struct.unpack_from("<Q", data, x + 8)[0]
    out = {}
    for i in range(count):
        e = x + entries_at + 0x30 * i
        key_at, text_at = struct.unpack_from("<Q", data, e + 8)[0], struct.unpack_from("<Q", data, e + 24)[0]
        key = data[x + key_at:data.index(b"\0", x + key_at)].decode()
        out[key] = (x + text_at, e + 0x20)
    return out
