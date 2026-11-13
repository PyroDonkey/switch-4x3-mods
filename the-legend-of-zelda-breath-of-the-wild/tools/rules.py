"""Shared geometry helpers for the BOTW native-4:3 build (layouts are 1280x720)."""
import struct
from lyt import *

H0 = 720.0
RATIO = 4 / 3
ROOT_SY = RATIO / (16 / 9)          # 0.75
K = 1 / ROOT_SY                     # 1.3333
HALF_VIS = H0 / 2 * K               # 480
DELTA = HALF_VIS - H0 / 2           # 120
THRESH = 0.7 * H0 / 2               # 252
SMALL_H = 0.37 * H0                 # 266.4
EDGE_MAXH = 0.8 * H0                # 576


def vert_origin(p):
    return (p.origin >> 2) & 3


def parent_vert_origin(p):
    return (p.origin >> 6) & 3


def is_nominal_null(p):
    return p.kind == 'pan1' and (p.w, p.h) == (30, 40)


def annotate(root):
    """Absolute centre/size in root-local units (rotation ignored)."""
    root.ax = root.ay = root.ay_origin = 0.0
    root.asx = root.asy = 1.0
    root.parent_sy = 1.0

    def rec(p):
        for c in p.children:
            c.asx, c.asy = p.asx * c.sx, p.asy * c.sy
            pvo = parent_vert_origin(c)
            base_local = 0.0
            if pvo:
                pv = vert_origin(p) if p is not root else 0
                rc = -p.h / 2 if pv == 1 else p.h / 2 if pv == 2 else 0.0
                base_local = rc + (p.h / 2 if pvo == 1 else -p.h / 2)
            px, py = p.ax + p.asx * c.tx, p.ay_origin + p.asy * (base_local + c.ty)
            vo = vert_origin(c)
            hh = c.h * c.asy
            c.ay_origin = py
            c.ay = py - hh / 2 if vo == 1 else py + hh / 2 if vo == 2 else py
            c.ax = px
            c.ah, c.aw = abs(hh), abs(c.w * c.asx)
            c.parent_sy = p.asy
            rec(c)
    root.ah, root.aw = root.h, root.w
    rec(root)


def materials(raw, s):
    """List of (name, [texture names]) for the bflyt at raw[s:]."""
    hlen = struct.unpack_from('<H', raw, s + 6)[0]
    nsec = struct.unpack_from('<H', raw, s + 0x10)[0]
    p = s + hlen
    tex, mats = [], []
    for _ in range(nsec):
        mag = raw[p:p + 4]
        size = struct.unpack_from('<I', raw, p + 4)[0]
        if mag == b'txl1':
            n = struct.unpack_from('<H', raw, p + 8)[0]
            base = p + 12
            for o in struct.unpack_from('<%dI' % n, raw, base):
                tex.append(raw[base + o:raw.index(b'\0', base + o)].decode())
        elif mag == b'mat1':
            n = struct.unpack_from('<H', raw, p + 8)[0]
            for o in struct.unpack_from('<%dI' % n, raw, p + 12):
                m = p + o
                name = raw[m:m + 28].split(b'\0')[0].decode()
                flags = struct.unpack_from('<I', raw, m + 28)[0]
                t = []
                for j in range(flags & 3):
                    ti = struct.unpack_from('<H', raw, m + 0x2C + 4 * j)[0]
                    t.append(tex[ti] if ti < len(tex) else '?')
                mats.append((name, t))
        p += size
    return mats


def prt1_name(d, p):
    """Layout name referenced by the prt1 section at offset p (magic at p).
    prt1 = 84-byte pane base, u32 entry count at +84, two f32 at +88/+92,
    40-byte entries from +96, then the referenced layout name (null-terminated)."""
    cnt = struct.unpack_from('<I', d, p + 84)[0]
    no = p + 96 + 40 * cnt
    return d[no:d.index(b'\0', no)].decode(errors='replace')


def layout_anims(ents, layout_name):
    """bflan entries belonging to a layout: anim/<Layout>_<Anim>.bflan"""
    pre = 'anim/' + layout_name + '_'
    return [n for n in ents if n.startswith(pre) and n.endswith('.bflan')]
