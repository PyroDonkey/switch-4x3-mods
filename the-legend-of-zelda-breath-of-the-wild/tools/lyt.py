"""SARC / Yaz0 / BFLYT / BFLAN reader for BOTW (Switch) that records byte offsets for in-place patching.

Ported from the SMBW reference tools. BOTW differences: Yaz0 (.sblarc) archives, layouts authored at 1280x720,
one big archive (Common.sblarc) holding hundreds of layouts + animations.
"""
import struct, re

LE_BOM = bytes([255, 254])


# ---------------------------------------------------------------- Yaz0
def yaz0_decompress(b):
    assert b[:4] == b'Yaz0'
    n = struct.unpack_from('>I', b, 4)[0]
    out = bytearray(n)
    o = 0
    p = 16
    L = len(b)
    while o < n:
        c = b[p]; p += 1
        for i in range(8):
            if o >= n:
                break
            if c & (0x80 >> i):
                out[o] = b[p]; p += 1; o += 1
            else:
                x = (b[p] << 8) | b[p + 1]; p += 2
                d = (x & 0xFFF) + 1
                l = x >> 12
                if l == 0:
                    l = b[p] + 18; p += 1
                else:
                    l += 2
                s = o - d
                if d >= l:
                    out[o:o + l] = out[s:s + l]
                else:
                    for k in range(l):
                        out[o + k] = out[s + k]
                o += l
    return bytes(out)


def yaz0_compress(data, level=None):
    """Greedy LZ77 Yaz0 encoder (hash-chain). Output is valid Yaz0; size differs from Nintendo's encoder."""
    n = len(data)
    out = bytearray(b'Yaz0' + struct.pack('>I', n) + b'\0' * 8)
    head = {}
    prev = [-1] * n
    i = 0
    grp = bytearray()
    flags = 0
    nb = 0

    def insert(pos):
        if pos + 2 < n:
            k = data[pos:pos + 3]
            prev[pos] = head.get(k, -1)
            head[k] = pos

    while i < n:
        best_l, best_d = 0, 0
        if i + 2 < n:
            k = data[i:i + 3]
            cand = head.get(k, -1)
            tries = 0
            maxl = min(0x111, n - i)
            while cand >= 0 and i - cand <= 0x1000 and tries < 32:
                l = 3
                while l < maxl and data[cand + l] == data[i + l]:
                    l += 1
                if l > best_l:
                    best_l, best_d = l, i - cand
                    if l == maxl:
                        break
                cand = prev[cand]
                tries += 1
        if best_l >= 3:
            d = best_d - 1
            if best_l < 18:
                grp += bytes([((best_l - 2) << 4) | (d >> 8), d & 0xFF])
            else:
                grp += bytes([d >> 8, d & 0xFF, best_l - 18])
            for k in range(best_l):
                insert(i + k)
            i += best_l
        else:
            flags |= 0x80 >> nb
            grp.append(data[i])
            insert(i)
            i += 1
        nb += 1
        if nb == 8:
            out.append(flags); out += grp
            flags = 0; nb = 0; grp = bytearray()
    if nb:
        out.append(flags); out += grp
    return bytes(out)


# ---------------------------------------------------------------- SARC
def sarc_entries(data):
    """Return {name: (abs_start, abs_end)} for every file in a SARC."""
    assert data[:4] == b'SARC', data[:4]
    e = '<' if data[6:8] == LE_BOM else '>'
    hlen = struct.unpack_from(e + 'H', data, 4)[0]
    data_off = struct.unpack_from(e + 'I', data, 0x0C)[0]
    p = hlen
    assert data[p:p + 4] == b'SFAT'
    count = struct.unpack_from(e + 'H', data, p + 6)[0]
    q = p + 12 + count * 16
    assert data[q:q + 4] == b'SFNT'
    names_base = q + 8
    out = {}
    for i in range(count):
        h, attr, s, en = struct.unpack_from(e + 'IIII', data, p + 12 + i * 16)
        no = (attr & 0xFFFF) * 4
        nm = data[names_base + no: data.index(b'\0', names_base + no)].decode()
        out[nm] = (data_off + s, data_off + en)
    return out


PANE_MAGIC = {b'pan1', b'pic1', b'txt1', b'wnd1', b'bnd1', b'prt1', b'scr1', b'ali1'}


class Pane:
    def __init__(self, kind, name, off, tx, ty, sx, sy, w, h, rot, origin):
        self.kind, self.name, self.off = kind, name, off
        self.tx, self.ty, self.sx, self.sy, self.w, self.h = tx, ty, sx, sy, w, h
        self.rot, self.origin = rot, origin
        self.children, self.parent = [], None
        self.usd = b''

    TX, TY, SX, SY, W, H = 44, 48, 68, 72, 76, 80

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def path(self):
        p, n = [], self
        while n:
            p.append(n.name); n = n.parent
        return '/'.join(reversed(p))


def parse_flyt(d, base=0):
    """Parse a BFLYT at d[base:]. Returns (layout_w, layout_h, root Pane)."""
    assert d[base:base + 4] == b'FLYT'
    assert d[base + 4:base + 6] == LE_BOM
    hlen = struct.unpack_from('<H', d, base + 6)[0]
    nsec = struct.unpack_from('<H', d, base + 0x10)[0]
    p = base + hlen
    lw = lh = None
    root = None
    stack = []
    last = None
    for _ in range(nsec):
        mag = d[p:p + 4]
        size = struct.unpack_from('<I', d, p + 4)[0]
        if mag == b'lyt1':
            lw, lh = struct.unpack_from('<ff', d, p + 12)
        elif mag == b'pas1':
            stack.append(last)
        elif mag == b'pae1':
            stack.pop()
        elif mag == b'usd1' and last is not None:
            last.usd = d[p:p + size]       # user data of the pane just parsed (e.g. CaptureOn / CaptureApplyScale)
        elif mag in PANE_MAGIC:
            origin = d[p + 9]
            name = d[p + 12:p + 36].split(b'\0')[0].decode(errors='replace')
            tx, ty, tz = struct.unpack_from('<fff', d, p + 44)
            rot = struct.unpack_from('<fff', d, p + 56)
            sx, sy = struct.unpack_from('<ff', d, p + 68)
            w, h = struct.unpack_from('<ff', d, p + 76)
            pn = Pane(mag.decode(), name, p, tx, ty, sx, sy, w, h, rot, origin)
            pn.raw = d[p:p + size]
            if stack and stack[-1] is not None:
                pn.parent = stack[-1]
                stack[-1].children.append(pn)
            elif root is None:
                root = pn
            last = pn
        p += size
    return lw, lh, root


class AnimKey:
    def __init__(self, off, frame, value, slope):
        self.off, self.frame, self.value, self.slope = off, frame, value, slope


def parse_flan(d, base=0):
    """Return list of (pane_name, is_material, tag_magic, target, curve_type, [AnimKey]) for FLPA tags.
    AnimKey.off is the absolute byte offset of the key's frame field."""
    assert d[base:base + 4] == b'FLAN'
    hlen = struct.unpack_from('<H', d, base + 6)[0]
    nsec = struct.unpack_from('<H', d, base + 0x10)[0]
    p = base + hlen
    out = []
    for _ in range(nsec):
        mag = d[p:p + 4]
        size = struct.unpack_from('<I', d, p + 4)[0]
        if mag == b'pai1':
            ntex, nent, ent_off = struct.unpack_from('<HHI', d, p + 12)
            for i in range(nent):
                eo = p + struct.unpack_from('<I', d, p + ent_off + 4 * i)[0]
                name = d[eo:eo + 28].split(b'\0')[0].decode(errors='replace')
                ntag, is_mat = d[eo + 28], d[eo + 29]
                for t in range(ntag):
                    to = eo + struct.unpack_from('<I', d, eo + 32 + 4 * t)[0]
                    tmag = d[to:to + 4].decode(errors='replace')
                    if tmag != 'FLPA':
                        continue
                    nte = d[to + 4]
                    for k in range(nte):
                        teo = to + struct.unpack_from('<I', d, to + 8 + 4 * k)[0]
                        idx, target, ctype = d[teo], d[teo + 1], d[teo + 2]
                        nkeys = struct.unpack_from('<H', d, teo + 4)[0]
                        koff = teo + struct.unpack_from('<I', d, teo + 8)[0]
                        keys = []
                        for j in range(nkeys):
                            if ctype == 2:  # hermite: frame, value, slope
                                ko = koff + 12 * j
                                fr, val, sl = struct.unpack_from('<fff', d, ko)
                            else:           # step: frame f32, value u16
                                ko = koff + 8 * j
                                fr = struct.unpack_from('<f', d, ko)[0]
                                val = struct.unpack_from('<H', d, ko + 4)[0]
                                sl = None
                            keys.append(AnimKey(ko, fr, val, sl))
                        out.append((name, is_mat, tmag, target, ctype, keys))
        p += size
    return out


def flyt_tags(d, base, want):
    """Yield (section_offset, size) for every section whose magic is in `want`."""
    hlen = struct.unpack_from('<H', d, base + 6)[0]
    nsec = struct.unpack_from('<H', d, base + 0x10)[0]
    p = base + hlen
    for _ in range(nsec):
        mag = d[p:p + 4]
        size = struct.unpack_from('<I', d, p + 4)[0]
        if mag in want:
            yield mag, p, size
        p += size


def part_refs(d, base):
    """Names of layouts referenced by prt1 panes of the bflyt at d[base:] (best effort: scan identifier strings)."""
    out = set()
    for mag, p, size in flyt_tags(d, base, {b'prt1'}):
        for t in re.findall(rb'[A-Za-z0-9_]{3,}', d[p + 84:p + size]):
            out.add(t.decode())
    return out


def load_archive(path, inner=None):
    """Load a (possibly Yaz0) SARC from a file, or from entry `inner` of a pack. Returns (raw_sarc_bytes, entries)."""
    b = open(path, 'rb').read()
    if inner:
        t = sarc_entries(b)
        s, e = t[inner]
        b = b[s:e]
    if b[:4] == b'Yaz0':
        b = yaz0_decompress(b)
    return b, sarc_entries(b)
