"""Disassemble every enabled line of the 1.2.1 pchtxt and verify code patch invariants.

Verifies:
- All enabled instructions disassemble cleanly without syntax errors
- All hooks target their expected code caves
- Original instructions are preserved in each code cave
- All code caves and tables are disjoint (no overlap) and within [0x02138650, 0x02139000)
- Cave A stores the current area RootAreaHash in mailbox 0x037D1F04
- Per-area zoom table preserves every arena/fixed-room override and ends before cave H
- Cave Y (stock vertical camera centre) gates on Course152_Sub4 (RootAreaHash 1778226157), pins the Y
  limits with the fight zoom (stock half-height >= 8.5) and returns to 0x006C66EC
- Cave K (CameraBoundBox2f Y bounds) gates on Course152_Sub4 (RootAreaHash 1778226157), replaces minY/maxY
  with stock -5.50 / 12.00 so Bowser Jr.'s swim AI navigation targets points above the floor and returns to 0x01781B74

usage: python verify_pchtxt.py [pchtxt]   (default: the mod's exefs/1.2.1.pchtxt)
"""
import os, re, struct, sys
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM


def verify_patch(path):
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    txt = open(path).read()
    if '@enabled' not in txt or '@stop' not in txt:
        sys.exit('ERROR: pchtxt missing @enabled or @stop block')

    enabled = txt.split('@enabled')[1].split('@stop')[0]
    lines = []
    patch = {}
    duplicates = []
    for line in enabled.splitlines():
        m = re.match(r'^([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})$', line.strip())
        if not m:
            continue
        addr = int(m.group(1), 16)
        raw = bytes.fromhex(m.group(2))
        word = struct.unpack('<I', raw)[0]
        if addr in patch:
            duplicates.append(addr)
        patch[addr] = word
        lines.append((addr, word, raw))

    assert not duplicates, f"Duplicate addresses found in patch: {[hex(a) for a in duplicates]}"

    # Identify known data addresses in caves
    DATA_HASHES = {0x02138D84: 1778226157, 0x02138DB4: 1778226157,
                   0x02138E00: 607466214, 0x02138E0C: 101336182,
                   0x02138E18: 1778226157, 0x02138E24: 1019598315,
                   0x02138E30: 1607468536, 0x02138E3C: 3684305666,
                   0x02138E48: 2579434623, 0x02138E54: 177084102}
    DATA_FLOATS = {0x02138788, 0x021388E0, 0x021388E4, 0x021388E8, 0x021388EC, 0x021388F0,
                   0x02138AE0, 0x02138AE4, 0x02138D34, 0x02138DB8, 0x02138DBC,
                   0x02138E04, 0x02138E10, 0x02138E1C, 0x02138E28, 0x02138E34, 0x02138E40, 0x02138E4C, 0x02138E58}
    DATA_ZEROS = {0x02138E08, 0x02138E14, 0x02138E20, 0x02138E2C,
                  0x02138E38, 0x02138E44, 0x02138E50, 0x02138E5C, 0x02138E60, 0x02138E64, 0x02138E68}

    # Print disassembly / data listing
    for addr, word, raw in lines:
        if addr >= 0x02139000:
            print(f"{addr:08X} {raw.hex().upper()}  (ro/data float {struct.unpack('<f', raw)[0]:.6g})")
        elif addr in DATA_HASHES:
            print(f"{addr:08X} {raw.hex().upper()}  (cave data: hash {word})")
        elif addr in DATA_FLOATS:
            print(f"{addr:08X} {raw.hex().upper()}  (cave data: float {struct.unpack('<f', raw)[0]:.6g})")
        elif addr in DATA_ZEROS:
            print(f"{addr:08X} {raw.hex().upper()}  (cave data: 0)")
        else:
            ins = list(md.disasm(raw, addr))
            print(f"{addr:08X} {raw.hex().upper()}  " + (f"{ins[0].mnemonic:8s} {ins[0].op_str}" if ins else "(unknown)"))

    # Helper: branch target decoder
    def b_target(pc, w):
        if (w & 0xFC000000) != 0x14000000:
            return None
        imm26 = w & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        return pc + (imm26 << 2)

    # 1. Check all hooks branch to expected caves
    EXPECTED_HOOKS = {
        0x00136A80: 0x02138780,  # loader one-screen fix
        0x002E2B30: 0x02138900,  # view height -> Cave B
        0x005E428C: 0x02138C00,  # pipe box initializer -> Cave E
        0x006C6358: 0x02138D00,  # controller view height -> Cave F1
        0x006C6364: 0x02138D20,  # controller view width -> Cave F2
        0x006C66DC: 0x02138800,  # camera controller clamp -> Cave A
        0x006C66E8: 0x02138D40,  # controller Y limits -> Cave Y
        0x006C6FD0: 0x02138A00,  # fixed-pos camera -> Cave G
        0x006C7BEC: 0x02138F00,  # StopScroll side-lock override -> Cave H
        0x00833B00: 0x02138B00,  # pipe box per-frame update -> Cave D
        0x01781B70: 0x02138D88,  # GetCameraBoundBox2f -> Cave K
    }
    for hook_addr, expected_target in EXPECTED_HOOKS.items():
        assert hook_addr in patch, f"Missing hook at 0x{hook_addr:08X}"
        target = b_target(hook_addr, patch[hook_addr])
        assert target == expected_target, (f"Hook at 0x{hook_addr:08X} targets 0x{target:08X}, "
                                          f"expected 0x{expected_target:08X}")

    # 2. Check original instructions preserved in caves
    ORIG_PRESERVED = [
        (0x021388B4, "fsub", "s2, s7, s4", "Cave A original from 0x006C66DC"),
        (0x02138900, "fmov", "s1, #15.5",  "Cave B original from 0x002E2B30"),
        (0x02138B00, "ldp",  "x8, x9",     "Cave D original from 0x00833B00"),
        (0x02138C00, "ldp",  "x8, x9",     "Cave E original from 0x005E428C"),
        (0x02138D00, "fmov", "s9, #15.5",  "Cave F1 original from 0x006C6358"),
        (0x02138D20, "ldr",  "s8",         "Cave F2 original from 0x006C6364"),
        (0x02138D40, "ldr",  "s13, [sp, #0x68]", "Cave Y original from 0x006C66E8"),
        (0x02138D88, "ldp",  "x8, x9",     "Cave K original from 0x01781B70"),
    ]
    for addr, exp_mnem, exp_op_sub, desc in ORIG_PRESERVED:
        assert addr in patch, f"Missing {desc} at 0x{addr:08X}"
        ins = list(md.disasm(struct.pack('<I', patch[addr]), addr))
        assert ins and ins[0].mnemonic == exp_mnem and exp_op_sub in ins[0].op_str, (
            f"Preserved instruction check failed at 0x{addr:08X} ({desc}): got {ins[0].mnemonic if ins else 'none'} "
            f"{ins[0].op_str if ins else ''}, expected {exp_mnem} with '{exp_op_sub}'"
        )

    # 3. Check cave boundaries and non-overlap
    cave_addrs = sorted(a for a in patch if 0x02138650 <= a < 0x02139000)
    assert min(cave_addrs) >= 0x02138650, f"Cave below .text end: 0x{min(cave_addrs):08X}"
    assert max(cave_addrs) < 0x02139000, f"Cave exceeds .text boundary: 0x{max(cave_addrs):08X}"

    assert 0x02138D34 in patch, "Cave F2 end literal missing"
    assert not any(0x02138D38 <= a < 0x02138D40 for a in patch), "gap between caves F2 and Y is not empty"
    assert max(a for a in cave_addrs if a < 0x02138E00) == 0x02138DBC, "Cave K does not end at its maxy literal"
    assert min(a for a in cave_addrs if a > 0x02138DBC) == 0x02138E00, "TABLE does not start at 0x02138E00"

    # Per-area table: check values independently of the generator, including the terminator and cave H boundary.
    expected_areas = [
        (607466214, 21.0),            # Course150_Sub4
        (101336182, 20.6666667),      # Course151_Sub2
        (1778226157, 20.6666667),     # Course152_Sub4
        (1019598315, 20.6666667),     # Course153_Sub3
        (1607468536, 20.6666667),     # Course411_Course
        (3684305666, 20.6666667),     # Course415_Course
        (2579434623, 20.6666667),     # Course417_Course
        (177084102, 20.6666667),      # Course403_Course
    ]
    for i, (area_hash, height) in enumerate(expected_areas):
        addr = 0x02138E00 + 12 * i
        assert patch.get(addr) == area_hash, f"Area table hash at 0x{addr:08X} != {area_hash}"
        assert patch.get(addr + 4) == struct.unpack('<I', struct.pack('<f', height))[0], f"Area {area_hash}: wrong G"
        assert patch.get(addr + 8) == 0, f"Area {area_hash}: delta must be zero"
    end = 0x02138E00 + 12 * len(expected_areas)
    assert all(patch.get(end + off) == 0 for off in (0, 4, 8)), "Area table terminator missing"
    assert end + 12 <= 0x02138F00, "Area table overlaps cave H"
    assert {a for a in patch if 0x02138E00 <= a < 0x02138F00} == set(range(0x02138E00, end + 12, 4)), "Unexpected area table words"

    # Cave Y: gated on Course152_Sub4, both exits return to 0x006C66EC; with the fight zoom it pins upper = lower
    def dis(a):
        i = list(md.disasm(struct.pack('<I', patch[a]), a))[0]
        return i.mnemonic, i.op_str
    assert patch[0x02138D84] == 1778226157, f"Cave Y hash != 1778226157: {patch[0x02138D84]}"
    assert b_target(0x02138D80, patch[0x02138D80]) == 0x006C66EC, "Cave Y return != 0x006C66EC"
    mn, op = dis(0x02138D58)
    assert mn == 'b.ne' and int(op.lstrip('#'), 16) == 0x02138D80, f"Cave Y gate check failed: {mn} {op}"
    assert dis(0x02138D68) == ('fmov', 's31, #8.50000000'), f"Cave Y pin threshold: {dis(0x02138D68)}"
    assert dis(0x02138D6C) == ('fcmp', 's16, s31'), f"Cave Y pin compare: {dis(0x02138D6C)}"
    assert dis(0x02138D7C) == ('fcsel', 's2, s0, s2, ge'), f"Cave Y pin select: {dis(0x02138D7C)}"

    # Cave K: gated on Course152_Sub4, replaces minY with -5.50 and maxY with 12.00, returns to 0x01781B74
    assert patch[0x02138DB4] == 1778226157, f"Cave K hash != 1778226157: {patch[0x02138DB4]}"
    assert b_target(0x02138DB0, patch[0x02138DB0]) == 0x01781B74, "Cave K return != 0x01781B74"
    mn_k, op_k = dis(0x02138D9C)
    assert mn_k == 'b.ne' and int(op_k.lstrip('#'), 16) == 0x02138DB0, f"Cave K gate check failed: {mn_k} {op_k}"
    assert dis(0x02138DA4)[0] == 'bfi' and 'x8' in dis(0x02138DA4)[1] and '#0x20, #0x20' in dis(0x02138DA4)[1], f"Cave K bfi x8 failed: {dis(0x02138DA4)}"
    assert dis(0x02138DAC)[0] == 'bfi' and 'x9' in dis(0x02138DAC)[1] and '#0x20, #0x20' in dis(0x02138DAC)[1], f"Cave K bfi x9 failed: {dis(0x02138DAC)}"
    assert patch[0x02138DB8] == 0xC0B00000, f"Cave K minY != -5.50: {patch[0x02138DB8]}"
    assert patch[0x02138DBC] == 0x41400000, f"Cave K maxY != 12.00: {patch[0x02138DBC]}"

    # 4. Check Cave A writes area hash to mailbox 0x037D1F04
    # Instruction 2 at 0x02138808: str wzr, [x17, #0xf04] (init mailbox)
    # Instruction 21 at 0x02138854: str w15, [x17, #0xf04] (store current area hash)
    ins_init = list(md.disasm(struct.pack('<I', patch[0x02138808]), 0x02138808))[0]
    ins_store = list(md.disasm(struct.pack('<I', patch[0x02138854]), 0x02138854))[0]
    assert ins_init.mnemonic == 'str' and '0xf04' in ins_init.op_str and 'wzr' in ins_init.op_str, (
        f"Cave A mailbox init check failed: {ins_init.mnemonic} {ins_init.op_str}"
    )
    assert ins_store.mnemonic == 'str' and '0xf04' in ins_store.op_str and 'w15' in ins_store.op_str, (
        f"Cave A mailbox store check failed: {ins_store.mnemonic} {ins_store.op_str}"
    )

    print(f"\nverify_pchtxt: OK ({len(lines)} patch lines, {len(EXPECTED_HOOKS)} hooks, "
          f"all invariants verified, 0 errors)")


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'mod', 'Native 4x3 Aspect Ratio', 'exefs', '1.2.1.pchtxt'
    )
    verify_patch(p)
