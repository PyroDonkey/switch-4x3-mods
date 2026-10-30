"""Decompress a Switch NSO (e.g. exefs/main) into a flat memory image.

usage: python -I nso_to_bin.py <main> <out.bin>
The image is laid out at memory offsets (text at 0), so a .pchtxt address with
`@flag offset_shift 0x100` maps to image offset (address - 0x100).
"""
import sys, struct
import lz4.block

src, dst = sys.argv[1], sys.argv[2]
d = open(src, 'rb').read()
assert d[:4] == b'NSO0', 'not an NSO'
flags = struct.unpack_from('<I', d, 0x0C)[0]
segs = []
for i, base in enumerate((0x10, 0x20, 0x30)):           # text, ro, data
    file_off, mem_off, size = struct.unpack_from('<III', d, base)
    segs.append((file_off, mem_off, size))
comp = struct.unpack_from('<III', d, 0x60)
bss = struct.unpack_from('<I', d, 0x3C)[0]
module_id = d[0x40:0x60].hex()

end = max(m + s for _, m, s in segs)
img = bytearray(end + bss)
for i, ((fo, mo, size), csize) in enumerate(zip(segs, comp)):
    raw = d[fo:fo + csize]
    data = lz4.block.decompress(raw, uncompressed_size=size) if flags & (1 << i) else raw[:size]
    assert len(data) == size, (i, len(data), size)
    img[mo:mo + size] = data
open(dst, 'wb').write(img)
names = ('text', 'ro', 'data')
print('module id', module_id)
for n, (fo, mo, size) in zip(names, segs):
    print(f'{n:5} mem 0x{mo:08X}-0x{mo + size:08X}')
print(f'bss   {bss:#x} bytes; image {len(img):#x} bytes -> {dst}')
