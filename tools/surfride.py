"""SurfRide .swif (SWIF v6 / 'VERSION 5' layout, Sonic Origins) reader and append-only editor.
Structures follow DeaTh-G's 010 templates (github.com/DeaTh-G/surfboard-templates, SWIFv6.bt + SurfRide/*.h).
All size_t pointers are u64 ABSOLUTE file offsets, 8-aligned; vec3 are 16-aligned (x,y,z,w).
Chunk-local offsets (SWTL TextureListOffset, SWPR ProjectOffset) are relative to the chunk header."""
import struct, sys, json

PTRS = {}  # position -> value of every pointer field read by the last parse()


class R:
    def __init__(s, b, p=0): s.b, s.p = b, p
    def al(s, n): s.p += -s.p % n
    def u8(s): v = s.b[s.p]; s.p += 1; return v
    def u16(s): v = struct.unpack_from('<H', s.b, s.p)[0]; s.p += 2; return v
    def s16(s): v = struct.unpack_from('<h', s.b, s.p)[0]; s.p += 2; return v
    def u32(s): v = struct.unpack_from('<I', s.b, s.p)[0]; s.p += 4; return v
    def i32(s): v = struct.unpack_from('<i', s.b, s.p)[0]; s.p += 4; return v
    def f32(s): v = struct.unpack_from('<f', s.b, s.p)[0]; s.p += 4; return v
    def f64(s): v = struct.unpack_from('<d', s.b, s.p)[0]; s.p += 8; return v
    def ptr(s):
        s.al(8); v = struct.unpack_from('<Q', s.b, s.p)[0]; PTRS[s.p] = v; s.p += 8; return v
    def col(s): v = tuple(s.b[s.p:s.p+4]); s.p += 4; return v
    def v3(s): s.al(16); v = struct.unpack_from('<4f', s.b, s.p); s.p += 16; return v
    def str(s, o): return s.b[o:s.b.index(b'\0', o)].decode() if o else None
    def at(s, o): return R(s.b, o)

def userdata(b, o):
    if not o: return None
    r = R(b, o); n = r.u32(); dp = r.ptr(); out = []
    r = R(b, dp)
    for _ in range(n):
        name = r.str(r.ptr()); t = r.u32(); vp = r.ptr()
        v = None
        if vp:
            v = {0: lambda: b[vp], 1: lambda: struct.unpack_from('<i', b, vp)[0], 3: lambda: struct.unpack_from('<f', b, vp)[0],
                 5: lambda: R(b).str(vp)}.get(t, lambda: struct.unpack_from('<I', b, vp)[0])()
        out.append((name, t, v))
    return out

def texture(r):
    d = dict(at=r.p); d['name'] = r.str(r.ptr()); d['file'] = r.str(r.ptr()); d['id'] = r.u32()
    d['w'] = r.u16(); d['h'] = r.u16(); d['flags'] = r.u32(); n = r.u32(); d['crop_count_at'] = r.p - 4
    cp = r.ptr(); d['crops_at'] = cp; d['ud'] = userdata(r.b, r.ptr())
    c = R(r.b, cp); d['crops'] = [(c.f32(), c.f32(), c.f32(), c.f32()) for _ in range(n)]
    return d

def texlist(r):
    d = dict(at=r.p); d['name'] = r.str(r.ptr()); d['field_08'] = r.u32(); n = r.u32(); tp = r.ptr(); d['ud'] = userdata(r.b, r.ptr())
    t = R(r.b, tp); d['textures_at'] = tp; d['textures'] = [texture(t) for _ in range(n)]
    return d

def camera(r):
    d = {}; d['name'] = r.str(r.ptr()); d['id'] = r.u32(); d['pos'] = r.v3(); d['target'] = r.v3()
    d['f30'] = r.i32(); d['flags'] = r.u32(); d['near'] = r.f32(); d['far'] = r.f32(); r.ptr(); r.ptr()
    return d

def cropref(b, o, n):
    r = R(b, o); return [(r.u16(), r.u16(), r.u16()) for _ in range(n)]

def textdata(b, o):
    r = R(b, o); d = dict(flags=r.u32(), font=r.u32()); d['text'] = r.str(r.ptr()); d['scale'] = (r.f32(), r.f32())
    d['misc'] = [r.s16() for _ in range(6)]; fp = r.ptr(); d['font_ptr'] = fp
    return d

def imagecast(b, o):
    r = R(b, o); d = dict(at=o, flags=r.u32(), size=(r.f32(), r.f32()), pivot=(r.f32(), r.f32()), vcol=[r.col() for _ in range(4)])
    d['crop0'] = r.s16(); d['crop1'] = r.s16(); n0 = r.s16(); n1 = r.s16()
    p0 = r.ptr(); p1 = r.ptr(); fp = r.ptr(); d['f38'] = r.ptr(); d['effect'] = r.ptr()
    d['cropref0'] = cropref(b, p0, n0); d['cropref1'] = cropref(b, p1, n1); d['cropref0_at'] = p0
    d['text'] = textdata(b, fp) if fp else None
    return d

def slicecast(b, o):
    r = R(b, o); d = dict(at=o, flags=r.u32(), size=(r.f32(), r.f32()), pivot=(r.f32(), r.f32()), vcol=[r.col() for _ in range(4)])
    d['fixed'] = (r.f32(), r.f32()); sh, sv, hf, vf, n0, n1 = [r.s16() for _ in range(6)]
    p0 = r.ptr(); p1 = r.ptr(); r.ptr()
    d['slices'] = (sh, sv); d['cropref0'] = cropref(b, p0, n0); d['cropref1'] = cropref(b, p1, n1)
    return d

KEYVAL = {0x10: 'f', 0x20: 'i', 0x30: 'b', 0x40: 'i', 0x50: 'col', 0x60: 'I', 0x70: 'd', 0x80: 'b'}
CURVE = ['Tx','Ty','Tz','Rx','Ry','Rz','Sx','Sy','Sz','MaterialColor','Display','Width','Height','VtxColTL','VtxColTR','VtxColBL','VtxColBR',
         'CropIndex0','CropIndex1','Unknown19','IlluminationColor',
         'MatR','MatG','MatB','MatA'] + [f'Vtx{c}{k}' for c in ('TL','TR','BL','BR') for k in 'RGBA'] + ['IllumR','IllumG','IllumB','IllumA']

def keyframes(b, o, n, flags):
    r = R(b, o); out = []
    for _ in range(n):
        fr = r.i32(); k = KEYVAL.get(flags & 0xF0)
        if k == 'f': v = r.f32()
        elif k in ('i',): v = r.i32()
        elif k == 'I': v = r.u32()
        elif k == 'b': v = r.u8()
        elif k == 'col': v = r.col()
        elif k == 'd': v = r.f64()
        else: v = None
        interp = flags & 3; extra = ()
        if interp >= 2:
            r.al(4); extra = (r.f32(), r.f32())
        if interp == 3: extra += (r.i32(),)
        out.append((fr, v) + extra)
        r.al(4)
    return out

def animation(r):
    d = dict(at=r.p); d['name'] = r.str(r.ptr()); d['id'] = r.u32(); n = r.i32(); d['end'] = r.u32(); mp = r.ptr(); d['ud'] = userdata(r.b, r.ptr()); d['loop'] = r.u8()
    r.al(8)
    d['motions_at'] = mp; m = R(r.b, mp); ms = []
    for _ in range(n):
        cid = m.u16(); tc = m.s16(); tp = m.ptr(); t = R(r.b, tp); tr = []
        for _ in range(tc):
            ty = t.u16(); kc = t.s16(); fl = t.u32(); ff = t.u32(); lf = t.u32(); kp = t.ptr()
            tr.append(dict(type=CURVE[ty] if ty < len(CURVE) else ty, flags=fl, first=ff, last=lf, keys=keyframes(r.b, kp, kc, fl)))
        ms.append(dict(cast=cid, tracks=tr))
    d['motions'] = ms
    return d

def trs(r, is3d):
    base = dict(mat=r.col(), illum=r.col(), display=r.u8()); r.p += 3
    if is3d:
        base['t'] = r.v3(); base['r'] = (r.u32(), r.u32(), r.u32()); base['s'] = r.v3()
    else:
        base['t'] = (r.f32(), r.f32()); base['rz'] = r.u32(); base['s'] = (r.f32(), r.f32())
    return base

CASTTYPE = {0: 'null', 1: 'image', 2: 'slice', 3: 'reference'}

def layer(b, o, seen):
    r = R(b, o); d = dict(at=o); d['name'] = r.str(r.ptr()); d['id'] = r.u32(); d['flags'] = r.u32(); n = r.u32()
    np_ = r.ptr(); cp = r.ptr(); an = r.u32(); ap = r.ptr(); d['cur_anim'] = r.u32(); d['ud'] = userdata(b, r.ptr())
    d['end'] = r.p
    casts = []; c = R(b, np_)
    for _ in range(n):
        e = dict(at=c.p); e['name'] = c.str(c.ptr()); e['id'] = c.u32(); e['flags'] = c.u32(); dp = c.ptr()
        e['child'] = c.s16(); e['sibling'] = c.s16(); e['ud'] = userdata(b, c.ptr())
        e['type'] = CASTTYPE.get(e['flags'] & 0xF, e['flags'] & 0xF)
        if dp:
            if e['type'] == 'image': e['image'] = imagecast(b, dp)
            elif e['type'] == 'slice': e['slice'] = slicecast(b, dp)
            elif e['type'] == 'reference':
                rr = R(b, dp); lp = rr.ptr(); e['ref'] = dict(layer_ptr=lp, f04=rr.i32(), anim_id=rr.i32(), anim_frame=rr.i32(), f10=rr.i32())
                if lp not in seen:
                    seen[lp] = None; seen[lp] = layer(b, lp, seen)
                e['ref']['layer'] = seen[lp]['name']
        casts.append(e)
    d['casts'] = casts; d['nodes_at'] = np_; d['cells_at'] = cp
    t = R(b, cp); is3d = (d['flags'] & 0xF) == 1
    for e in casts: e['trs'] = trs(t, is3d)
    d['anims_at'] = ap
    a = R(b, ap); d['anims'] = [animation(a) for _ in range(an)]
    return d

def scene(r, seen):
    d = dict(at=r.p); d['name'] = r.str(r.ptr()); d['id'] = r.u32(); d['flags'] = r.u32(); d['f10'] = r.u32(); ln = r.u32(); lp = r.ptr()
    cc = r.s16(); r.s16(); cp = r.ptr()
    rc = R(r.b, cp); d['cameras'] = [camera(rc) for _ in range(cc)]
    d['bg'] = r.col(); d['res'] = (r.f32(), r.f32()); d['ud'] = userdata(r.b, r.ptr())
    d['layers'] = []
    for k in range(ln):
        # layer struct size: walk with a probe to find it
        lo = lp + k * LAYER_SIZE
        if lo not in seen: seen[lo] = layer(r.b, lo, seen)
        d['layers'].append(seen[lo])
    return d

LAYER_SIZE = 0x48   # name8 id4 flags4 count4 pad4 nodes8 cells8 animcount4 pad4 anims8 curanim4 pad4 ud8

def parse(b):
    PTRS.clear()
    sig, sz, nch, nxt, listsz, offoff, rev = struct.unpack_from('<4sIIIIII', b, 0)
    out = dict(info=dict(chunks=nch, next=nxt, listsize=listsz, offset_chunk=offoff, rev=hex(rev)))
    p = nxt
    seen = {}
    for _ in range(nch):
        while b[p:p+4] not in (b'SWTL', b'SWPR'): p += 4
        s, csz = struct.unpack_from('<4sI', b, p)
        if s == b'SWTL':
            to, tc = struct.unpack_from('<II', b, p + 8)
            r = R(b, p + to); out['texlists_chunk'] = [texlist(r) for _ in range(tc)]
        else:
            po = struct.unpack_from('<I', b, p + 8)[0]
            r = R(b, p + po); pr = dict(at=p + po); pr['name'] = r.str(r.ptr()); sc = r.s16(); r.s16(); tl = r.s16(); fc = r.s16()
            sp = r.ptr(); tp = r.ptr(); fp = r.ptr(); pr['camera'] = camera(r); pr['start'] = r.u32(); pr['end'] = r.u32(); pr['fps'] = r.f32()
            pr['ud'] = userdata(b, r.ptr())
            rs = R(b, sp); pr['scenes'] = []
            for _ in range(sc):
                pr['scenes'].append(scene(rs, seen)); rs.p = rs.p  # scene struct size discovered below
                rs.al(8)
            t = R(b, tp); pr['texlists'] = [texlist(t) for _ in range(tl)]
            pr['fonts_ptr'] = fp; pr['font_count'] = fc
            out['project'] = pr
            out['all_layers'] = seen
        p += 8 + csz
        p += -p % 16
    oc = offoff
    s, csz, cnt = struct.unpack_from('<4sII', b, oc)
    out['offsets'] = list(struct.unpack_from('<%dI' % cnt, b, oc + 16))
    out['ptr_fields'] = dict(PTRS)
    return out


def check(b):
    """Parse `b` and check the pointer model: SOF0 lists exactly the non-null pointer fields, and every
    pointer lands inside the chunk data. -> the parse result."""
    P = parse(b)
    nonnull = {p for p, v in P['ptr_fields'].items() if v}
    offs = set(P['offsets'])
    assert len(offs) == len(P['offsets']), 'duplicate SOF0 entries'
    missing = nonnull - offs
    assert not missing, f'pointer fields missing from SOF0: {sorted(missing)[:10]}'
    end = P['info']['offset_chunk']
    for p in offs:
        v = struct.unpack_from('<Q', b, p)[0]
        assert 0 < v < end, f'pointer at {p:#x} -> {v:#x} outside the data'
    return P


# ---------------------------------------------------------------- append-only editor
class Editor:
    """Edits a .swif by appending new structures after the last chunk (before SOF0) and repointing
    existing fields at them; nothing already there moves, so no pointer needs relocating. Old structures
    that are no longer referenced stay (dead but valid, still listed in SOF0)."""

    def __init__(self, b):
        sig, _, nch, first, listsize, offchunk, _ = struct.unpack_from('<4sIIIIII', b, 0)
        assert sig == b'SWIF'
        self.first = first
        n = struct.unpack_from('<I', b, offchunk + 8)[0]
        self.offsets = list(struct.unpack_from('<%dI' % n, b, offchunk + 16))
        self.b = bytearray(b[:offchunk])
        send = offchunk + 16 + 4 * n
        self.end_chunk = bytes(b[send + (-send % 16):])
        assert self.end_chunk[:4] == b'SEND'
        # the last chunk (the one that ends at SOF0) grows with the appended data
        p = first
        while True:
            sig, size = struct.unpack_from('<4sI', b, p)
            nxt = p + 8 + size
            if nxt >= offchunk:
                break
            p = nxt + (-nxt % 16)
        self.last_chunk = p
        self.orig_len = offchunk

    def alloc(self, data, align=16):
        self.b += bytes(-len(self.b) % align)
        at = len(self.b)
        self.b += data
        return at

    def string(self, s):
        return self.alloc(s.encode() + b'\0', 8)

    def set_ptr(self, pos, value):
        assert pos % 8 == 0
        struct.pack_into('<Q', self.b, pos, value)
        if value and pos not in self.offsets:
            self.offsets.append(pos)

    def pack(self, fmt, pos, *v):
        struct.pack_into(fmt, self.b, pos, *v)

    def build(self):
        b = self.b + bytes(-len(self.b) % 16)
        off = len(b)
        struct.pack_into('<I', b, self.last_chunk + 4, off - self.last_chunk - 8)
        struct.pack_into('<I', b, 0x10, off - self.first)
        struct.pack_into('<I', b, 0x14, off)
        body = struct.pack('<II', len(self.offsets), 0) + struct.pack('<%dI' % len(self.offsets), *self.offsets)
        # The game's files: SEND follows at the next 16-byte boundary, but the recorded size always
        # rounds up to the NEXT boundary ((end + 16) & ~15), so it overlaps SEND when the list ends aligned.
        end = 8 + len(body)
        size = ((end + 16) & ~15) - 8
        b += b'SOF0' + struct.pack('<I', size) + body + bytes(-end % 16)
        return bytes(b + self.end_chunk)

if __name__ == '__main__':
    b = open(sys.argv[1], 'rb').read()
    P = check(b)
    P.pop('ptr_fields')
    print(json.dumps(P, indent=1, default=str))
