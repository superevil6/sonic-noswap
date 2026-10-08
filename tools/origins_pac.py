"""Read and write Sonic Origins' .pac archives (PACx v4.03 outer + PACx v4.02 inner).

Outer (PACx403): 0x30-byte header (signature, version "403", 'L', uid, file size, root offset, root compressed
and uncompressed sizes, flags ...), a chunk table at 0x30 (u32 count, then {u32 compressed, u32 uncompressed}
per chunk; its size padded to 8 is at 0x24, and the root starts on the next 16-byte boundary), then the root: the inner archive, split into chunks
of at most 64 KB, each LZ4-block compressed.

Inner (PACx402): 0x30-byte header (sizes of the trees, dependency table, data entries, string table, file
data and offset table, in that order), followed by those sections. Data entries are 0x30 bytes:
u32 uid, u32 size, u64 0, u64 -> data, u64 0, u64 -> extension, u64 flags.

Only what NoSwap needs is supported: small archives whose whole content is the root (no split data), and
replacing the data of the archive's last file (so nothing after it has to move).
"""
import struct

CHUNK = 0x10000


# ---------------------------------------------------------------- LZ4 block format
def lz4_decompress(src, size):
    out, i = bytearray(), 0
    while i < len(src):
        token = src[i]; i += 1
        n = token >> 4
        if n == 15:
            while True:
                b = src[i]; i += 1; n += b
                if b != 255:
                    break
        out += src[i:i + n]; i += n
        if i >= len(src):
            break
        offset = src[i] | src[i + 1] << 8; i += 2
        m = token & 15
        if m == 15:
            while True:
                b = src[i]; i += 1; m += b
                if b != 255:
                    break
        start = len(out) - offset
        for k in range(m + 4):
            out.append(out[start + k])
    assert len(out) == size, "LZ4: wrong size"
    return bytes(out)


def _length(n):
    out = bytearray()
    while n >= 255:
        out.append(255); n -= 255
    out.append(n)
    return out


def lz4_compress(src):
    """Greedy LZ4 block compression (one match candidate per 4-byte hash). The block format's end rules:
    the last 5 bytes are literals, and no match starts within the last 12 bytes."""
    n, out, table = len(src), bytearray(), {}
    anchor = i = 0
    limit = n - 12
    while i < limit:
        key = src[i:i + 4]
        cand = table.get(key)
        table[key] = i
        if cand is None or i - cand > 0xFFFF:
            i += 1
            continue
        m = 4
        while i + m < n - 5 and src[cand + m] == src[i + m]:
            m += 1
        lit = i - anchor
        out.append((min(lit, 15) << 4) | min(m - 4, 15))
        if lit >= 15:
            out += _length(lit - 15)
        out += src[anchor:i]
        out += struct.pack("<H", i - cand)
        if m - 4 >= 15:
            out += _length(m - 4 - 15)
        i += m
        anchor = i
    lit = n - anchor
    out.append(min(lit, 15) << 4)
    if lit >= 15:
        out += _length(lit - 15)
    out += src[anchor:]
    return bytes(out)


# ---------------------------------------------------------------- outer archive
def read_outer(data):
    """-> (header bytes 0x00-0x2F, inner archive bytes)"""
    sig, ver, endian, uid, size, root_at, root_c, root_u = struct.unpack_from("<4s3scIIIII", data, 0)
    assert sig == b"PACx" and ver == b"403" and endian == b"L", "not a PACx403 archive"
    assert root_at + root_c <= size <= root_at + root_c + 16 and root_at <= 0x30 + 0x10 * 64, \
        "archive has data outside its root (not supported)"
    count = struct.unpack_from("<I", data, 0x30)[0]
    chunks = [struct.unpack_from("<II", data, 0x34 + 8 * k) for k in range(count)]
    inner, p = bytearray(), root_at
    for c, u in chunks:
        inner += lz4_decompress(data[p:p + c], u) if c != u else data[p:p + c]
        p += c
    assert len(inner) == root_u
    return data[:0x30], bytes(inner)


def write_outer(header, inner, literal=False):
    """The outer archive around `inner`. literal: every chunk as an LZ4 block of literals only (origins_cards.lz4_literal),
    so that its bytes can be overwritten in the file in place."""
    parts = [inner[k:k + CHUNK] for k in range(0, len(inner), CHUNK)]
    if literal:
        from origins_cards import lz4_literal
        packed = [lz4_literal(p) for p in parts]
    else:
        packed = [lz4_compress(p) for p in parts]
    table = struct.pack("<I", len(parts)) + b"".join(struct.pack("<II", len(c), len(u)) for c, u in zip(packed, parts))
    table += b"\0" * (-len(table) % 8)  # the header records the table padded to 8
    root_at = 0x30 + len(table) + (-(0x30 + len(table)) % 16)  # the root starts on a 16-byte boundary
    root = b"".join(packed)
    total = root_at + len(root)
    total += -total % 16
    out = bytearray(header)
    struct.pack_into("<IIII", out, 0x0C, total, root_at, len(root), len(inner))
    struct.pack_into("<I", out, 0x24, len(table))
    out += table
    out += b"\0" * (root_at - len(out))
    out += root
    out += b"\0" * (total - len(out))
    return bytes(out)


# ---------------------------------------------------------------- inner archive
def inner_files(inner):
    """-> list of (entry offset, data offset, size) for the inner archive's data entries"""
    sig, ver, endian, uid, size, trees, deps, entries, strings, files, offsets = \
        struct.unpack_from("<4s3scIIIIIIII", inner, 0)
    assert sig == b"PACx" and ver == b"402", "not a PACx402 archive"
    at = 0x30 + trees + deps
    out = []
    for k in range(entries // 0x30):
        e = at + 0x30 * k
        out.append((e, struct.unpack_from("<Q", inner, e + 0x10)[0], struct.unpack_from("<I", inner, e + 4)[0]))
    return out


def replace_last_file(inner, new_data):
    """The inner archive with its last file's data replaced (padded like the original)."""
    files = inner_files(inner)
    entry, at, size = max(files, key=lambda f: f[1])
    header = struct.unpack_from("<4s3scIIIIIIII", inner, 0)
    trees, deps, entries, strings, file_size, offsets = header[5:11]
    files_start = 0x30 + trees + deps + entries + strings
    files_end = files_start + file_size
    assert at + size <= files_end < at + size + 16, "last file isn't at the end of the file data"
    align = 16 if files_end - (at + size) >= 8 else 8  # as the original was padded
    padded = new_data + b"\0" * (-len(new_data) % align)
    out = bytearray(inner[:at]) + padded + inner[files_end:]
    struct.pack_into("<I", out, entry + 4, len(new_data))
    new_file_size = file_size - (files_end - at) + len(padded)
    struct.pack_into("<I", out, 0x0C, len(out))
    struct.pack_into("<I", out, 0x20, new_file_size)
    return bytes(out)


def last_file(inner):
    entry, at, size = max(inner_files(inner), key=lambda f: f[1])
    return inner[at:at + size]
