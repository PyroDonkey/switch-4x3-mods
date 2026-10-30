"""Find AArch64 code references (ADRP + LDR/ADD/STR) to data addresses in a flat NSO image.

usage: python xref.py <image.bin> <text_end_hex> <addr_hex> [<addr_hex> ...]
       python xref.py <image.bin> <text_end_hex> --float <value> [--ro-start <hex>]
The second form first finds every 4-byte occurrence of the float (exact and +-1 ulp) after ro-start.
"""
import sys, struct

img = open(sys.argv[1], 'rb').read()
text_end = int(sys.argv[2], 16)
args = sys.argv[3:]

targets = []
if args and args[0] == '--float':
    v = float(args[1])
    ro_start = int(args[args.index('--ro-start') + 1], 16) if '--ro-start' in args else text_end
    base = struct.unpack('<I', struct.pack('<f', v))[0]
    pats = {struct.pack('<I', base + d): d for d in (-2, -1, 0, 1, 2)}
    for pat, d in pats.items():
        i = img.find(pat, ro_start)
        while i != -1:
            if i % 4 == 0:
                targets.append(i)
                print(f'float {v} (ulp {d:+d}) at {i:#x}')
            i = img.find(pat, i + 1)
else:
    targets = [int(a, 16) for a in args]

pages = {}
for t in targets:
    pages.setdefault(t & ~0xFFF, []).append(t)

words = struct.unpack_from(f'<{text_end // 4}I', img, 0)


def sx(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


hits = []
for i, w in enumerate(words):
    if (w & 0x9F000000) != 0x90000000:          # ADRP
        continue
    imm = sx(((w >> 5) & 0x7FFFF) << 2 | ((w >> 29) & 3), 21)
    pc = i * 4
    page = (pc & ~0xFFF) + (imm << 12)
    if page not in pages:
        continue
    rd = w & 31
    for j in range(i + 1, min(i + 12, len(words))):
        w2 = words[j]
        rn = (w2 >> 5) & 31
        if rn != rd:
            continue
        off = None
        op = (w2 >> 22) & 0x3FF
        if (w2 & 0x3B000000) == 0x39000000:     # LDR/STR (immediate, unsigned offset), any size
            size = (w2 >> 30) & 3
            if (w2 >> 26) & 1 and ((w2 >> 23) & 1):  # 128-bit SIMD
                size = 4
            off = ((w2 >> 10) & 0xFFF) << size
            kind = 'ldst'
        elif (w2 & 0x7F800000) == 0x11000000:   # ADD (immediate) 64/32
            sh = (w2 >> 22) & 1
            off = ((w2 >> 10) & 0xFFF) << (12 if sh else 0)
            kind = 'add'
        if off is None:
            continue
        addr = page + off
        for t in pages[page]:
            if addr <= t < addr + 16 or addr == t:
                hits.append((t, pc, j * 4, kind, addr))
        break

for t, pc, use, kind, addr in sorted(hits):
    print(f'target {t:#x}: adrp @{pc:#x}  {kind} @{use:#x} (address {addr:#x})')
print(f'{len(hits)} reference(s)')
