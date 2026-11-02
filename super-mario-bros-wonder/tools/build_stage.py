"""Stage (BancMapUnit) edits for the 4:3 mod: same-size float edits on single actors, built from the 1.2.1 originals.

usage:
  python build_stage.py <orig_romfs> <out_dir>
      Writes <out_dir>/romfs/BancMapUnit/<course>.bcett.byml.zs for every course in EDITS.
  python build_stage.py --verify <orig_romfs> <mod_romfs>
      Checks the shipped files in <mod_romfs>/BancMapUnit: exactly the EDITS courses, each differing from its
      original only in the edited floats. Exits 1 on any problem.

<orig_romfs> is the extracted 1.2.1 romfs (needs BancMapUnit/).
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bymlpatch import Byml, read, write

# (course, actor Hash, Gyaml, key, original xyz, new xyz)
# Course152_Sub4 (W4 Bowser Jr.): KoopaJrSystemWaterMixAreaPlane draws the underwater tint, caustics and light rays.
# It follows the camera in x only and is sized for the stock 17.5-block view height; the 4:3 view is 23.33 tall and
# the fight framing sits ~2.9 blocks higher (about y -5.6 to 17.7), so Scale Y 1.5 (minimum ~1.35) covers both.
EDITS = [
    ('Course152_Sub4', 2115412732, 'KoopaJrSystemWaterMixAreaPlane', 'Scale', (1.0, 1.0, 1.0), (1.0, 1.5, 1.0)),
]

# (course, unit_idx, wall_idx, point_idx, orig_xyz, new_xyz)
# In Course152_Sub4 (W4 Bowser Jr.), the arena walls (Unit 1 Wall 1 & Wall 2) and corridor (Wall 0) bottom out at
# y = -7.0. In 4:3 with the fight camera pinned at y = 3.25, the view reaches y = -8.42, exposing black void boxes
# in the bottom-left and bottom-right corners below the walls. Extending the bottom points to y = -10.0 pulls the
# wall geometry past the bottom of the screen.
BG_EDITS = [
    ('Course152_Sub4', 1, 0, 0, (-8.0, -7.0, 0.0), (-8.0, -10.0, 0.0)),
    ('Course152_Sub4', 1, 0, 7, (23.0, -7.0, 0.0), (23.0, -10.0, 0.0)),
    ('Course152_Sub4', 1, 1, 0, (39.0, -7.0, 0.0), (39.0, -10.0, 0.0)),
    ('Course152_Sub4', 1, 1, 5, (50.0, -7.0, 0.0), (50.0, -10.0, 0.0)),
    ('Course152_Sub4', 1, 2, 0, (79.0, -7.0, 0.0), (79.0, -10.0, 0.0)),
    ('Course152_Sub4', 1, 2, 21, (92.0, -7.0, 0.0), (92.0, -10.0, 0.0)),
]


def bcett(romfs, course):
    return os.path.join(romfs, 'BancMapUnit', f'{course}.bcett.byml.zs')


def edits_by_course():
    out = {}
    for e in EDITS:
        out.setdefault(e[0], {'actors': [], 'bg': []})['actors'].append(e)
    for b_edit in BG_EDITS:
        out.setdefault(b_edit[0], {'actors': [], 'bg': []})['bg'].append(b_edit)
    return out


def apply(d, course_edits):
    """Applies actor and BgUnit edits to decompressed BYML d in place; returns the set of byte offsets allowed to change."""
    b = Byml(d)
    allowed = set()
    for course, h, gyaml, key, orig, new in course_edits.get('actors', []):
        a = b.find_actor(hash_=h)
        assert b.actor_value(a, 'Gyaml') == gyaml, (course, h, b.actor_value(a, 'Gyaml'))
        node = a[key][2]
        sharers = [o for o in b.actors() if key in o and o[key][2] == node]
        assert len(sharers) == 1, f'{course} {h}: {key} array shared by {len(sharers)} actors'
        cur = [v for _, v in b.vec3(a, key)]
        assert cur == list(orig), f'{course} {h}: {key} is {cur}, expected {orig}'
        b.set_vec3(a, key, new)
        for eslot, _ in b.vec3(a, key):
            allowed.update(range(eslot, eslot + 4))

    root = b.hash_entries(b.root)
    slots = b.array_slots(root['BgUnits'][2]) if 'BgUnits' in root else []
    for course, uidx, widx, pidx, orig, new in course_edits.get('bg', []):
        unit = b.hash_entries(slots[uidx][2])
        walls = b.array_slots(unit['Walls'][2])
        wall = b.hash_entries(walls[widx][2])
        er = b.hash_entries(wall['ExternalRail'][2])
        pts = b.array_slots(er['Points'][2])
        p = b.hash_entries(pts[pidx][2])
        node = p['Translate'][2]
        all_pts = []
        for u in slots:
            unit_dict = b.hash_entries(u[2])
            if 'Walls' in unit_dict:
                for _, _, wraw in b.array_slots(unit_dict['Walls'][2]):
                    wall_dict = b.hash_entries(wraw)
                    if 'ExternalRail' in wall_dict:
                        er_dict = b.hash_entries(wall_dict['ExternalRail'][2])
                        if 'Points' in er_dict:
                            for _, _, praw in b.array_slots(er_dict['Points'][2]):
                                all_pts.append(b.hash_entries(praw))
        sharers = [pt for pt in all_pts if pt['Translate'][2] == node]
        assert len(sharers) == 1, f'{course} Unit {uidx} Wall {widx} Pt {pidx}: Translate shared by {len(sharers)} points'
        cur = [v for _, v in b.vec3(p, 'Translate')]
        assert cur == list(orig), f'{course} Unit {uidx} Wall {widx} Pt {pidx}: {cur}, expected {orig}'
        b.set_vec3(p, 'Translate', new)
        for eslot, _ in b.vec3(p, 'Translate'):
            allowed.update(range(eslot, eslot + 4))

    return allowed


def build(orig_romfs, out_dir):
    dst_dir = os.path.join(out_dir, 'romfs', 'BancMapUnit')
    os.makedirs(dst_dir, exist_ok=True)
    for course, edits in edits_by_course().items():
        src = bcett(orig_romfs, course)
        d = read(src)
        apply(d, edits)
        assert bytes(d) != bytes(read(src)), f'{course}: no change'
        write(bcett(os.path.join(out_dir, 'romfs'), course), d)
        print('wrote', bcett(os.path.join(out_dir, 'romfs'), course))


def verify(orig_romfs, mod_romfs):
    problems = []
    want = edits_by_course()
    shipped_dir = os.path.join(mod_romfs, 'BancMapUnit')
    shipped = sorted(os.listdir(shipped_dir)) if os.path.isdir(shipped_dir) else []
    expected = sorted(f'{c}.bcett.byml.zs' for c in want)
    if shipped != expected:
        problems.append(f'BancMapUnit ships {shipped}, expected {expected}')
    for course, edits in want.items():
        path = bcett(mod_romfs, course)
        if not os.path.exists(path):
            continue
        orig = read(bcett(orig_romfs, course))
        ship = read(path)
        ref = bytearray(orig)
        allowed = apply(ref, edits)
        if len(ship) != len(orig):
            problems.append(f'{course}: size {len(ship)} != original {len(orig)}')
            continue
        diff = {i for i in range(len(orig)) if orig[i] != ship[i]}
        if not diff:
            problems.append(f'{course}: identical to the original')
        if diff - allowed:
            problems.append(f'{course}: {len(diff - allowed)} byte(s) changed outside the edited floats')
        elif bytes(ship) != bytes(ref):
            problems.append(f'{course}: edited values differ from EDITS')
        elif diff:
            n_total = len(edits.get('actors', [])) + len(edits.get('bg', []))
            print(f'{course}: {len(diff)} byte(s) differ, all inside {n_total} edit(s)')
    for p in problems:
        print('PROBLEM:', p)
    print(f'{len(problems)} problem(s)')
    return not problems


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[:1] == ['--verify'] and len(args) == 3:
        sys.exit(0 if verify(args[1], args[2]) else 1)
    elif len(args) == 2:
        build(args[0], args[1])
    else:
        sys.exit(__doc__)
