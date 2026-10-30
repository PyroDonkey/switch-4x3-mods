import struct, sys, os, glob
from compression import zstd

def sarc_files(data):
    assert data[:4] == b'SARC', data[:4]
    e = '<' if data[6:8] == bytes([255,254]) else '>'
    hlen = struct.unpack_from(e + 'H', data, 4)[0]
    data_off = struct.unpack_from(e + 'I', data, 0x0C)[0]
    p = hlen
    assert data[p:p+4] == b'SFAT'
    sh, count, key = struct.unpack_from(e + 'HHI', data, p + 4)
    nodes = []
    for i in range(count):
        h, attr, s, en = struct.unpack_from(e + 'IIII', data, p + 12 + i * 16)
        nodes.append((attr, s, en))
    q = p + 12 + count * 16
    assert data[q:q+4] == b'SFNT'
    names_base = q + 8
    out = {}
    for attr, s, en in nodes:
        if attr >> 24:
            no = (attr & 0xFFFF) * 4
            nm = data[names_base + no: data.index(b'\0', names_base + no)].decode()
        else:
            nm = '?'
        out[nm] = data[data_off + s: data_off + en]
    return out

PANES = {b'pan1', b'pic1', b'txt1', b'wnd1', b'bnd1', b'prt1', b'scr1', b'ali1'}

def parse_flyt(d):
    assert d[:4] == b'FLYT'
    e = '<' if d[4:6] == bytes([255,254]) else '>'
    hlen = struct.unpack_from(e + 'H', d, 6)[0]
    nsec = struct.unpack_from(e + 'H', d, 0x10)[0]
    p = hlen
    res = []
    depth = 0
    for _ in range(nsec):
        mag = d[p:p+4]; size = struct.unpack_from(e + 'I', d, p + 4)[0]
        if mag == b'lyt1':
            centered, = struct.unpack_from('B', d, p + 8)
            w, h = struct.unpack_from(e + 'ff', d, p + 12)
            res.append(('LAYOUT', depth, w, h))
        elif mag == b'pas1':
            depth += 1
        elif mag == b'pae1':
            depth -= 1
        elif mag in PANES:
            flags, origin, alpha, ps = struct.unpack_from('4B', d, p + 8)
            name = d[p+12:p+36].split(b'\0')[0].decode(errors='replace')
            tx, ty, tz = struct.unpack_from(e + 'fff', d, p + 44)
            sx, sy = struct.unpack_from(e + 'ff', d, p + 68)
            w, h = struct.unpack_from(e + 'ff', d, p + 76)
            res.append((mag.decode(), depth, name, origin, tx, ty, sx, sy, w, h))
        p += size
    return res

def main():
    root = sys.argv[1]
    only = sys.argv[2:]
    for f in sorted(glob.glob(os.path.join(root, '*.blarc.zs'))):
        base = os.path.basename(f).split('.')[0]
        if only and base not in only:
            continue
        raw = zstd.decompress(open(f, 'rb').read())
        files = sarc_files(raw)
        for nm, d in sorted(files.items()):
            if not nm.endswith('.bflyt'):
                continue
            print(f'=== {base} :: {nm}')
            for r in parse_flyt(d):
                if r[0] == 'LAYOUT':
                    print(f'  LAYOUT {r[2]:g}x{r[3]:g}')
                else:
                    mag, dep, name, origin, tx, ty, sx, sy, w, h = r
                    print(f"  {'  '*dep}{mag} {name:<24} org={origin:02x} T=({tx:g},{ty:g}) S=({sx:g},{sy:g}) size=({w:g},{h:g})")

main()
