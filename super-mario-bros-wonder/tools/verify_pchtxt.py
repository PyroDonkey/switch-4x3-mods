"""Disassemble every enabled line of the 1.2.1 pchtxt that touches code (addresses < 0x2138650 or in the caves).

usage: python verify_pchtxt.py [pchtxt]   (default: the mod's exefs\1.2.1.pchtxt)
"""
import os, re, sys
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mod',
                                                           'Native 4x3 Aspect Ratio', 'exefs', '1.2.1.pchtxt')
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
txt = open(path).read()
enabled = txt.split('@enabled')[1].split('@stop')[0]
for line in enabled.splitlines():
    m = re.match(r'^([0-9A-F]{8}) ([0-9A-F]{8})$', line)
    if not m:
        continue
    addr, raw = int(m.group(1), 16), bytes.fromhex(m.group(2))
    if addr >= 0x2139000:                        # .ro / .data: constants, not code
        print(f"{addr:08X} {m.group(2)}  (data, float {__import__('struct').unpack('<f', raw)[0]:.4f})")
        continue
    ins = list(md.disasm(raw, addr))
    print(f"{addr:08X} {m.group(2)}  " + (f"{ins[0].mnemonic} {ins[0].op_str}" if ins else "(data)"))
