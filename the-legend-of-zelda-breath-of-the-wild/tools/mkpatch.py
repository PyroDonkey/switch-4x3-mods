"""Emit the exact-4:3 pchtxt lines and verify every word by disassembly."""
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
import struct

md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

SITES = [0x00E0AD68, 0x01271870, 0x015C2148]   # instructions being replaced
RETS = [s + 4 for s in SITES]
CAVE = 0x2129BA4                                # zeros until 0x212A000 (checked)
LIT = CAVE + 0x24                               # literal pool word

def B(pc, target):
    off = (target - pc) // 4
    assert (target - pc) % 4 == 0 and -(1 << 25) <= off < (1 << 25)
    return 0x14000000 | (off & 0x3FFFFFF)

def LDR_S_LITERAL(rt, pc, target):
    off = target - pc
    assert off % 4 == 0 and abs(off) < (1 << 20)
    return 0x1C000000 | (((off // 4) & 0x7FFFF) << 5) | rt

lines = []
# hooks: one branch per site into the cave
for i, s in enumerate(SITES):
    w = B(s, CAVE + 8 * i)
    lines.append((s, w, f'b -> cave{i + 1}'))
# cave: 3x (ldr s0, lit ; b back) + literal
for i in range(3):
    pc = CAVE + 8 * i
    lines.append((pc, LDR_S_LITERAL(0, pc, LIT), f'cave{i + 1}: ldr s0, lit'))
    lines.append((pc + 4, B(pc + 4, RETS[i]), f'cave{i + 1}: b back'))
lines.append((LIT, 0x3FAAAAAB, 'literal 1.3333334f'))

for off, w, note in lines:
    b = struct.pack('<I', w)
    dis = next(md.disasm(b, off))
    print(f'{off:08X} {b.hex().upper()}  // {note:24s} disasm: {dis.mnemonic} {dis.op_str}')
