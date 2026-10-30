"""Minimal SARC / BFLYT / BFLAN reader that records byte offsets for in-place patching."""
import struct, os, glob
from compression import zstd

LE_BOM = bytes([255, 254])


def sarc_entries(data):
    """Return {name: (abs_start, abs_end)} for every file in a SARC."""
    assert data[:4] == b'SARC'
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

    # byte offsets (relative to section start) of fields
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
    """Parse a BFLYT located at d[base:]. Returns (layout_w, layout_h, root Pane)."""
    assert d[base:base + 4] == b'FLYT'
    e = '<' if d[base + 4:base + 6] == LE_BOM else '>'
    assert e == '<'
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
        elif mag == b'grp1' and root is not None and not stack:
            pass
        p += size
    return lw, lh, root


class AnimKey:
    def __init__(self, off, frame, value, slope):
        self.off, self.frame, self.value, self.slope = off, frame, value, slope


def parse_flan(d, base=0):
    """Return list of (pane_name, is_material, tag_magic, target, curve_type, [AnimKey]).
    AnimKey.off is the absolute byte offset of the key's frame field."""
    assert d[base:base + 4] == b'FLAN'
    hlen = struct.unpack_from('<H', d, base + 6)[0]
    version = struct.unpack_from('<I', d, base + 8)[0]
    nsec = struct.unpack_from('<H', d, base + 0x10)[0]
    p = base + hlen
    out = []
    for _ in range(nsec):
        mag = d[p:p + 4]
        size = struct.unpack_from('<I', d, p + 4)[0]
        if mag == b'pai1':
            frame_size, flags = struct.unpack_from('<HB', d, p + 8)
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
                            else:  # step: frame f32, value u16
                                ko = koff + 8 * j
                                fr = struct.unpack_from('<f', d, ko)[0]
                                val = struct.unpack_from('<H', d, ko + 4)[0]
                                sl = None
                            keys.append(AnimKey(ko, fr, val, sl))
                        out.append((name, is_mat, tmag, target, ctype, keys))
        p += size
    return out


def load_layout_dir(layout_dir):
    """Yield (archive_base_name, path, raw_sarc_bytes, entries)."""
    for f in sorted(glob.glob(os.path.join(layout_dir, '*.blarc.zs'))):
        raw = zstd.decompress(open(f, 'rb').read())
        yield os.path.basename(f).split('.')[0], f, raw, sarc_entries(raw)
