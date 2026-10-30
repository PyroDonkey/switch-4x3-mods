"""Minimal BYML (v2-v7, little or big endian) reader. Handles .byml/.bgyml and zstd-compressed .zs files.

usage: python byml.py <file> [--grep <text>]    prints the tree as indented YAML-ish text
"""
import sys, struct

try:
    from compression import zstd
except ImportError:
    zstd = None


def load(path):
    data = open(path, 'rb').read()
    if path.endswith('.zs'):
        data = zstd.decompress(data)
    return parse(data)


def parse(d):
    if d[:2] == b'YB':
        e = '<'
    elif d[:2] == b'BY':
        e = '>'
    else:
        raise ValueError('not BYML')
    ver, keys_off, strs_off, root_off = struct.unpack_from(e + 'HIII', d, 2)

    def u24(o):
        b = d[o:o + 3]
        return int.from_bytes(b, 'little' if e == '<' else 'big')

    def strtable(off):
        if off == 0:
            return []
        assert d[off] == 0xC2
        n = u24(off + 1)
        offs = struct.unpack_from(e + f'{n + 1}I', d, off + 4)
        return [d[off + offs[i]:d.index(b'\0', off + offs[i])].decode('utf-8', 'replace') for i in range(n)]

    keys, strs = strtable(keys_off), strtable(strs_off)

    def value(t, raw, at):
        if t == 0xA0: return strs[raw]
        if t == 0xD0: return bool(raw)
        if t == 0xD1: return struct.unpack(e + 'i', struct.pack(e + 'I', raw))[0]
        if t == 0xD2: return struct.unpack(e + 'f', struct.pack(e + 'I', raw))[0]
        if t == 0xD3: return raw
        if t in (0xD4, 0xD5, 0xD6):
            v = d[raw:raw + 8]
            return struct.unpack(e + {0xD4: 'q', 0xD5: 'Q', 0xD6: 'd'}[t], v)[0]
        if t == 0xFF: return None
        if t in (0xC0, 0xC1, 0x20, 0x21): return node(raw)
        if t == 0xA1:
            n = struct.unpack_from(e + 'I', d, raw)[0]
            return d[raw + 4:raw + 4 + n]
        return f'<type {t:#x} {raw:#x}>'

    def node(off):
        t = d[off]
        n = u24(off + 1)
        if t == 0xC0:                      # array
            types = d[off + 4:off + 4 + n]
            vo = off + 4 + ((n + 3) & ~3)
            return [value(types[i], struct.unpack_from(e + 'I', d, vo + 4 * i)[0], vo + 4 * i) for i in range(n)]
        if t == 0xC1:                      # hash (dictionary)
            out = {}
            for i in range(n):
                o = off + 4 + 8 * i
                k = u24(o)
                vt = d[o + 3]
                raw = struct.unpack_from(e + 'I', d, o + 4)[0]
                out[keys[k]] = value(vt, raw, o + 4)
            return out
        raise ValueError(f'node type {t:#x} at {off:#x}')

    return node(root_off) if root_off else None


def dump(v, ind=0, out=None):
    out = out if out is not None else []
    pad = '  ' * ind
    if isinstance(v, dict):
        for k, x in v.items():
            if isinstance(x, (dict, list)) and x:
                out.append(f'{pad}{k}:'); dump(x, ind + 1, out)
            else:
                out.append(f'{pad}{k}: {x!r}')
    elif isinstance(v, list):
        for x in v:
            if isinstance(x, (dict, list)) and x:
                out.append(f'{pad}-'); dump(x, ind + 1, out)
            else:
                out.append(f'{pad}- {x!r}')
    return out


if __name__ == '__main__':
    lines = dump(load(sys.argv[1]))
    if '--grep' in sys.argv:
        pat = sys.argv[sys.argv.index('--grep') + 1].lower()
        lines = [f'{i + 1}: {l}' for i, l in enumerate(lines) if pat in l.lower()]
    print('\n'.join(lines))
