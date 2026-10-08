"""Full read/write of Sonic Origins' split .pac archives (PACx v4.03 outer + PACx v4.02 root and blocks).

Complements origins_pac.py (which only handles small, unsplit archives). Layout (see also that file):

Outer (PACx403): 0x30-byte header (0x0C file size, 0x10 root offset, 0x14/0x18 root compressed and
uncompressed size, 0x24 size of the root chunk table, padded to 8), the root chunk table at 0x30, then the
dependency BLOCKS (".pac.000", ".pac.001", ...), each 16-aligned, then the root, then padding to 16.
Every block and the root are split in 64 KB pieces, each compressed alone as an LZ4 block.

Root (PACx402): header, then the node trees, the dependency section, data entries, string table, file data
and offset table (sizes at 0x10..0x24 in that order; 0x0C = total size). The dependency section:
u64 block count, u64 -> entries; entry 0x20 = u64 -> name, u32 compressed size, u32 size, u32 offset of
the block in the outer file, u32 chunk count, u64 -> chunk table ({u32 compressed, u32 size} per chunk).
Files stored in a block are listed in the root with flags 1 and data pointer 0; the block (itself a
PACx402 archive, without dependency section) holds their data.

Offset table: positions of every pointer in the archive, as deltas >> 2 in 1, 2 or 4 bytes (top bits
01 / 10 / 11), padded with zeros to 8. With it any bytes can be inserted and every pointer fixed up
(insert()).

Names are radix trees of fragments (HedgeLib's PACx v4 layout, github.com/Radfordhound/HedgeLib):
node 0x28 = u64 -> name fragment, u64 -> data, u64 -> child indices, i32 parent, i32 global index,
i32 data index, u16 child count, u8 has data, u8 full path size; tree header = u32 node count,
u32 data node count, u64 -> nodes, u64 -> data node indices.
"""
import struct

from origins_pac import lz4_compress, lz4_decompress

CHUNK = 0x10000
HEADER = 0x30
SECTIONS = ("trees", "deps", "entries", "strings", "data", "offsets")


def align(n, a):
    return n + (-n % a)


# ---------------------------------------------------------------- PACx402
def sections(b):
    """-> {name: (start, size)} of a PACx402 archive"""
    sizes = struct.unpack_from("<6I", b, 0x10)
    out, at = {}, HEADER
    for name, size in zip(SECTIONS, sizes):
        out[name] = (at, size)
        at += size
    return out


def read_offsets(b):
    at, size = sections(b)["offsets"]
    table, pos, out, i = b[at:at + size], 0, [], 0
    while i < len(table) and table[i]:
        t = table[i] >> 6
        if t == 1:
            v = table[i] & 0x3F; i += 1
        elif t == 2:
            v = (table[i] & 0x3F) << 8 | table[i + 1]; i += 2
        else:
            v = (table[i] & 0x3F) << 24 | table[i + 1] << 16 | table[i + 2] << 8 | table[i + 3]; i += 4
        pos += v << 2
        out.append(pos)
    return out


def encode_offsets(positions):
    out, prev = bytearray(), 0
    for p in sorted(positions):
        d = (p - prev) >> 2
        assert (p - prev) % 4 == 0 and (p > prev or not out), "offsets must be distinct multiples of 4"
        if d < 0x40:
            out.append(0x40 | d)
        elif d < 0x4000:
            out += bytes([0x80 | d >> 8, d & 0xFF])
        else:
            assert d < 0x40000000
            out += bytes([0xC0 | d >> 24, d >> 16 & 0xFF, d >> 8 & 0xFF, d & 0xFF])
        prev = p
    return bytes(out) + b"\0" * (-len(out) % 8)


def insert(b, at, n, section):
    """PACx402 `b` with `n` zero bytes inserted at `at`, growing `section` (a SECTIONS name) by n:
    every pointer stored at or after `at` moves, and every pointer to `at` or beyond is increased."""
    assert section != "offsets" and n >= 0
    secs = sections(b)
    s_at, s_size = secs[section]
    assert s_at <= at <= s_at + s_size, "insertion point outside the section"
    positions = read_offsets(b)
    off_at = secs["offsets"][0]
    out = bytearray(b[:at]) + bytes(n) + bytearray(b[at:off_at])
    moved = []
    for p in positions:
        q = p + n if p >= at else p
        v = struct.unpack_from("<Q", out, q)[0]
        if v >= at:
            struct.pack_into("<Q", out, q, v + n)
        moved.append(q)
    table = encode_offsets(moved)
    out += table
    k = SECTIONS.index(section)
    struct.pack_into("<I", out, 0x10 + 4 * k, s_size + n)
    struct.pack_into("<I", out, 0x24, len(table))
    struct.pack_into("<I", out, 0x0C, len(out))
    return bytes(out)


def cstr(b, o):
    return b[o:b.index(b"\0", o)].decode()


def _tree(b, at):
    count, _, nodes, _ = struct.unpack_from("<IIQQ", b, at)
    out = []
    for i in range(count):
        name, data, _, parent, _, _, _, has_data, _ = struct.unpack_from("<QQQiiiHBB", b, nodes + 0x28 * i)
        out.append((cstr(b, name) if name else "", data, parent, has_data))
    res = []
    for name, data, parent, has_data in out:
        if has_data:
            full, j = "", parent
            while j >= 0:
                full = out[j][0] + full
                j = out[j][2]
            res.append((full, data))
    return res


def entries(b):
    """-> [dict(name, ext, entry, data, size, flags)] for every file of a PACx402 archive"""
    out = []
    for _, tree in _tree(b, HEADER):
        for name, e in _tree(b, tree):
            _, size, _, data, _, ext, flags = struct.unpack_from("<IIQQQQQ", b, e)
            out.append(dict(name=name, ext=cstr(b, ext), entry=e, data=data, size=size, flags=flags))
    return out


def find(b, name, ext):
    hits = [e for e in entries(b) if e["name"] == name and e["ext"] == ext]
    assert len(hits) == 1, f"{name}.{ext}: {len(hits)} entries"
    return hits[0]


def deps(b):
    """-> [dict(name, csize, usize, offset, count, table, entry)] of the root's dependency blocks"""
    at, size = sections(b)["deps"]
    if not size:
        return []
    n, ptr = struct.unpack_from("<QQ", b, at)
    out = []
    for i in range(n):
        e = ptr + 0x20 * i
        name, c, u, o, cnt, t = struct.unpack_from("<QIIIIQ", b, e)
        out.append(dict(name=cstr(b, name), csize=c, usize=u, offset=o, count=cnt, table=t, entry=e))
    return out


def replace_file(b, name, ext, data):
    """PACx402 `b` with that file's data replaced (the file must be stored here, flags 0). The data is
    padded to 16 like the originals; later files move."""
    e = find(b, name, ext)
    assert e["flags"] == 0 and e["data"], "file isn't stored in this archive"
    old, new = align(e["size"], 16), align(len(data), 16)
    data_at, data_size = sections(b)["data"]
    assert e["data"] + old <= data_at + data_size
    if new > old:
        b = insert(b, e["data"] + old, new - old, "data")
    else:
        assert new == old, "shrinking a file isn't supported"
    out = bytearray(b)
    out[e["data"]:e["data"] + new] = data + bytes(new - len(data))
    struct.pack_into("<I", out, e["entry"] + 4, len(data))
    return bytes(out)


def set_size(b, name, ext, size):
    """Update the size recorded for a file (e.g. the root's entry of a file stored in a block)."""
    e = find(b, name, ext)
    out = bytearray(b)
    struct.pack_into("<I", out, e["entry"] + 4, size)
    return bytes(out)


# ---------------------------------------------------------------- PACx403 outer
def _chunks(buf, at, table):
    """[(compressed bytes, uncompressed bytes)] for a chunk table [(csize, usize)] starting at `at`"""
    out = []
    for c, u in table:
        raw = buf[at:at + c]
        out.append((raw, lz4_decompress(raw, u) if c != u else raw))
        at += c
    return out


class Outer:
    """A split .pac: .root (PACx402 bytes) and .blocks[name] (PACx402 bytes). Remembers the original
    compressed chunks so unchanged 64 KB pieces are written back byte for byte."""

    def __init__(self, data):
        sig, ver, endian = struct.unpack_from("<4s3sc", data, 0)
        assert sig == b"PACx" and ver == b"403" and endian == b"L", "not a PACx403 archive"
        self.header = bytes(data[:HEADER])
        root_at, root_c, root_u = struct.unpack_from("<III", data, 0x10)
        count = struct.unpack_from("<I", data, 0x30)[0]
        table = [struct.unpack_from("<II", data, 0x34 + 8 * k) for k in range(count)]
        self.orig = {}  # name -> [(compressed, uncompressed)]
        self.orig[None] = _chunks(data, root_at, table)
        self.root = b"".join(u for _, u in self.orig[None])
        assert len(self.root) == root_u
        self.blocks = {}
        for d in deps(self.root):
            t = [struct.unpack_from("<II", self.root, d["table"] + 8 * k) for k in range(d["count"])]
            self.orig[d["name"]] = _chunks(data, d["offset"], t)
            self.blocks[d["name"]] = b"".join(u for _, u in self.orig[d["name"]])
            assert len(self.blocks[d["name"]]) == d["usize"]

    def _compress(self, name, buf, literal=()):
        """[(compressed, uncompressed)] reusing the original compressed piece where a chunk is unchanged. A chunk
        overlapping one of the `literal` ranges [(start, end)] is stored as an LZ4 block of literals only (its bytes
        as they are, after a header that depends only on its length: origins_cards.lz4_literal), so that those bytes
        can later be overwritten in the file in place."""
        from origins_cards import lz4_literal
        old = self.orig.get(name, [])
        out = []
        for k in range(0, len(buf), CHUNK):
            piece = buf[k:k + CHUNK]
            i = k // CHUNK
            if any(s < k + len(piece) and k < e for s, e in literal):
                out.append((lz4_literal(piece), piece))
            elif i < len(old) and old[i][1] == piece:
                out.append(old[i])
            else:
                out.append((lz4_compress(piece), piece))
        return out

    def build(self, literal=None):
        """-> the outer file bytes. Grows the root's chunk tables where a block needs more chunks. `literal`: {block
        name (None: the root): [(start, end)]} byte ranges to keep in literal-only chunks (_compress)."""
        literal = literal or {}
        root = self.root
        self.layout = {}  # name (None: the root) -> (file offset, [(compressed, uncompressed)]) of what build() wrote
        packed = {}
        for d in deps(root):
            packed[d["name"]] = self._compress(d["name"], self.blocks[d["name"]], literal.get(d["name"], ()))
        for name, chunks in packed.items():  # make room in the root's chunk tables
            d = next(x for x in deps(root) if x["name"] == name)
            extra = len(chunks) - d["count"]
            assert extra >= 0, "a block shrank below its chunk count (not supported)"
            if extra:
                root = insert(root, d["table"] + 8 * d["count"], align(8 * extra, 16), "deps")
        root_count = -(-len(root) // CHUNK)
        table_size = align(4 + 8 * root_count, 8)  # the header records it padded to 8
        at = align(HEADER + table_size, 16)         # the blocks start on a 16-byte boundary
        out_blocks = []
        rb = bytearray(root)
        for d in deps(root):
            chunks = packed[d["name"]]
            blob = b"".join(c for c, _ in chunks)
            struct.pack_into("<IIII", rb, d["entry"] + 8, len(blob), len(self.blocks[d["name"]]), at, len(chunks))
            for k, (c, u) in enumerate(chunks):
                struct.pack_into("<II", rb, d["table"] + 8 * k, len(c), len(u))
            out_blocks.append((at, blob))
            self.layout[d["name"]] = (at, chunks)
            at = align(at + len(blob), 16)
        root = bytes(rb)
        root_chunks = self._compress(None, root, literal.get(None, ()))
        assert len(root_chunks) == root_count
        root_blob = b"".join(c for c, _ in root_chunks)
        root_at = at
        self.layout[None] = (root_at, root_chunks)
        total = align(root_at + len(root_blob), 16)
        out = bytearray(total)
        out[:HEADER] = self.header
        struct.pack_into("<IIII", out, 0x0C, total, root_at, len(root_blob), len(root))
        struct.pack_into("<I", out, 0x24, table_size)
        struct.pack_into("<I", out, 0x30, root_count)
        for k, (c, u) in enumerate(root_chunks):
            struct.pack_into("<II", out, 0x34 + 8 * k, len(c), len(u))
        for at_, blob in out_blocks:
            out[at_:at_ + len(blob)] = blob
        out[root_at:root_at + len(root_blob)] = root_blob
        return bytes(out)
