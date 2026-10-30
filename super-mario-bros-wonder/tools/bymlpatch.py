"""In-place patcher for scalar values in BYML map-unit files (.bcett.byml.zs).

Only same-size edits (float / int / bool stored inline in a node slot) are supported, so the file layout never changes.

usage:
  python bymlpatch.py <in.zs> <out.zs> <Gyaml> <key> <value> [--nth N] [--top]
      Sets Actors[*] (the Nth with that Gyaml, default 0) -> Dynamic[key] (default) or the actor's own key (--top) to value.
  python bymlpatch.py <in.zs> <out.zs> --hash <Hash> <key> <value>
      Same, selecting the actor by its Hash.
  python bymlpatch.py <in.zs> <out.zs> --hash <Hash> --translate <x> <y> <z>
      Moves an actor (Translate is an array of three inline floats).
"""
import struct, sys
from compression import zstd


def read(path):
    raw = open(path, 'rb').read()
    return bytearray(zstd.decompress(raw)) if path.endswith('.zs') else bytearray(raw)


def write(path, data):
    out = zstd.compress(bytes(data), level=19) if path.endswith('.zs') else bytes(data)
    assert (zstd.decompress(out) if path.endswith('.zs') else out) == bytes(data)
    open(path, 'wb').write(out)


class Byml:
    def __init__(self, d):
        assert d[:2] == b'YB', 'little-endian BYML only'
        self.d = d
        _, self.keys_off, self.strs_off, self.root = struct.unpack_from('<HIII', d, 2)
        self.keys = self._strtable(self.keys_off)
        self.strs = self._strtable(self.strs_off)

    def u24(self, o):
        return int.from_bytes(self.d[o:o + 3], 'little')

    def _strtable(self, off):
        if not off:
            return []
        n = self.u24(off + 1)
        offs = struct.unpack_from(f'<{n + 1}I', self.d, off + 4)
        return [self.d[off + offs[i]:self.d.index(b'\0', off + offs[i])].decode() for i in range(n)]

    def hash_entries(self, off):
        """{key: (type, slot_offset, raw)} of a hash node."""
        assert self.d[off] == 0xC1
        out = {}
        for i in range(self.u24(off + 1)):
            o = off + 4 + 8 * i
            out[self.keys[self.u24(o)]] = (self.d[o + 3], o + 4, struct.unpack_from('<I', self.d, o + 4)[0])
        return out

    def array_slots(self, off):
        assert self.d[off] == 0xC0
        n = self.u24(off + 1)
        vo = off + 4 + ((n + 3) & ~3)
        return [(self.d[off + 4 + i], vo + 4 * i, struct.unpack_from('<I', self.d, vo + 4 * i)[0]) for i in range(n)]

    def actors(self):
        root = self.hash_entries(self.root)
        t, slot, raw = root['Actors']
        for at, aslot, araw in self.array_slots(raw):
            yield self.hash_entries(araw)

    def actor_value(self, a, key):
        return self.d_value(*a[key])

    def d_value(self, t, slot, raw):
        if t == 0xA0: return self.strs[raw]
        if t == 0xD2: return struct.unpack('<f', struct.pack('<I', raw))[0]
        if t == 0xD1: return struct.unpack('<i', struct.pack('<I', raw))[0]
        if t in (0xD3, 0xD0): return raw
        return raw

    def hash_of(self, a):
        t, slot, raw = a['Hash']
        if t == 0xD5:                      # u64 stored out of line
            return struct.unpack_from('<Q', self.d, raw)[0]
        return raw

    def find_actor(self, gyaml=None, hash_=None, nth=0):
        n = 0
        for a in self.actors():
            if gyaml is not None and self.actor_value(a, 'Gyaml') != gyaml:
                continue
            if hash_ is not None and self.hash_of(a) != hash_:
                continue
            if n == nth:
                return a
            n += 1
        raise KeyError(f'actor not found: {gyaml} {hash_} #{nth}')

    def set_scalar(self, entry, value):
        t, slot, raw = entry
        if t == 0xD2:
            struct.pack_into('<f', self.d, slot, float(value))
        elif t in (0xD1, 0xD3):
            struct.pack_into('<i' if t == 0xD1 else '<I', self.d, slot, int(value))
        elif t == 0xD0:
            struct.pack_into('<I', self.d, slot, 1 if value else 0)
        else:
            raise ValueError(f'unsupported inline type {t:#x}')

    def set_translate(self, actor, xyz):
        t, slot, raw = actor['Translate']
        for (et, eslot, _), v in zip(self.array_slots(raw), xyz):
            assert et == 0xD2
            struct.pack_into('<f', self.d, eslot, float(v))


def main(argv):
    src, dst, rest = argv[0], argv[1], argv[2:]
    d = read(src)
    b = Byml(d)
    nth = int(rest[rest.index('--nth') + 1]) if '--nth' in rest else 0
    if rest[0] == '--hash':
        h = int(rest[1])
        a = b.find_actor(hash_=h)
        rest = rest[2:]
    else:
        a = b.find_actor(gyaml=rest[0], nth=nth)
        rest = rest[1:]
    if rest[0] == '--translate':
        b.set_translate(a, [float(x) for x in rest[1:4]])
    else:
        key, value = rest[0], rest[1]
        target = a['Dynamic'] if '--top' not in rest else a
        if '--top' not in rest:
            target = b.hash_entries(a['Dynamic'][2])
        b.set_scalar(target[key], float(value) if '.' in value else int(value))
    write(dst, b.d)
    print('patched', dst)


if __name__ == '__main__':
    main(sys.argv[1:])
