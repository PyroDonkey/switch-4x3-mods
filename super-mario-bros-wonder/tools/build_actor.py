"""Actor pack edits for the 4:3 mod: same-size parameter edits from the 1.2.1 originals.

usage:
  python build_actor.py <orig_romfs> <out_dir>
      Writes <out_dir>/romfs/Pack/Actor/FinalCourseDemoKoopaJr.pack.zs
  python build_actor.py --verify <orig_romfs> <mod_romfs>
      Checks that the shipped pack differs from stock only by the declared parameter edit.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compression import zstd
import byml

PACK_REL = os.path.join('Pack', 'Actor', 'FinalCourseDemoKoopaJr.pack.zs')
SUBFILE = 'GameParameter/FinalCourseDemoKoopaJr/FinalCourseDemoKoopaJr.game__actor__gparam__FinalCourseDemoKoopaJr.bgyml'
PARAM = 'KoopaJrJumpFrame'
OLD_VAL = 45.0
NEW_VAL = 70.0


def extract_sarc_files(data):
    magic, hdr_sz, bom, f_sz, data_off, ver = struct.unpack_from('<4sHHIHH', data, 0)
    assert magic == b'SARC', 'not SARC'
    sfat_hdr_sz, node_cnt = struct.unpack_from('<4sHHI', data, hdr_sz)[1:3]
    sfnt_off = hdr_sz + sfat_hdr_sz + node_cnt * 16
    sfnt_str_base = sfnt_off + 8

    files = {}
    for i in range(node_cnt):
        node_off = hdr_sz + sfat_hdr_sz + i * 16
        h, name_info, start, end = struct.unpack_from('<IIII', data, node_off)
        name_off = (name_info & 0xFFFFFF) * 4
        str_end = data.find(b'\x00', sfnt_str_base + name_off)
        name = data[sfnt_str_base + name_off : str_end].decode('latin1')
        files[name] = (data_off + start, data_off + end)
    return files


def locate_param_offset(sarc_bytes):
    files = extract_sarc_files(sarc_bytes)
    assert SUBFILE in files, f'{SUBFILE} not in SARC'
    start, end = files[SUBFILE]
    subdata = sarc_bytes[start:end]
    parsed = byml.parse(subdata)
    assert parsed.get(PARAM) == OLD_VAL, f'expected {PARAM}={OLD_VAL}, got {parsed.get(PARAM)}'
    idx = subdata.find(struct.pack('<f', OLD_VAL))
    assert idx != -1, f'float {OLD_VAL} not found in {SUBFILE}'
    return start + idx


def build(orig_romfs, out_dir):
    src = os.path.join(orig_romfs, PACK_REL)
    raw = zstd.decompress(open(src, 'rb').read())
    off = locate_param_offset(raw)

    patched = bytearray(raw)
    struct.pack_into('<f', patched, off, NEW_VAL)

    diff = [i for i in range(len(raw)) if raw[i] != patched[i]]
    assert len(diff) in (1, 2, 4), f'unexpected diff size: {len(diff)}'

    comp = zstd.compress(bytes(patched), level=19)
    assert zstd.decompress(comp) == bytes(patched)

    dst = os.path.join(out_dir, 'romfs', PACK_REL) if not out_dir.endswith('romfs') else os.path.join(out_dir, PACK_REL)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'wb') as f:
        f.write(comp)
    print(f'wrote {dst} (1 edit: {PARAM} {OLD_VAL} -> {NEW_VAL})')


def verify(orig_romfs, mod_romfs):
    problems = []
    src = os.path.join(orig_romfs, PACK_REL)
    dst = os.path.join(mod_romfs, PACK_REL) if mod_romfs.endswith('romfs') else os.path.join(mod_romfs, 'romfs', PACK_REL)
    if not os.path.isfile(dst):
        problems.append(f'missing {dst}')
        return problems

    orig_raw = zstd.decompress(open(src, 'rb').read())
    ship_raw = zstd.decompress(open(dst, 'rb').read())

    if len(orig_raw) != len(ship_raw):
        problems.append(f'{PACK_REL}: uncompressed size {len(ship_raw)} != stock {len(orig_raw)}')
        return problems

    diff = [i for i in range(len(orig_raw)) if orig_raw[i] != ship_raw[i]]
    expected_off = locate_param_offset(orig_raw)
    allowed = set(range(expected_off, expected_off + 4))

    if set(diff) - allowed:
        problems.append(f'{PACK_REL}: {len(set(diff) - allowed)} byte(s) changed outside declared edit')
    elif not diff:
        problems.append(f'{PACK_REL}: identical to stock original')
    else:
        # Check parsed value in mod
        files = extract_sarc_files(ship_raw)
        start, end = files[SUBFILE]
        parsed = byml.parse(ship_raw[start:end])
        if parsed.get(PARAM) != NEW_VAL:
            problems.append(f'{PACK_REL}: {PARAM} is {parsed.get(PARAM)}, expected {NEW_VAL}')
        else:
            print(f'{PACK_REL}: {len(diff)} byte(s) differ ({PARAM} {OLD_VAL} -> {NEW_VAL})')

    return problems


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[:1] == ['--verify'] and len(args) == 3:
        probs = verify(args[1], args[2])
        for p in probs:
            print('PROBLEM:', p)
        print(f'{len(probs)} problem(s)')
        sys.exit(0 if not probs else 1)
    elif len(args) == 2:
        build(args[0], args[1])
    else:
        sys.exit(__doc__)
