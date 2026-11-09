"""Stage (BancMapUnit) edits for the 4:3 mod: same-size float and guarded actor-type edits from the 1.2.1 originals.

usage:
  python build_stage.py <orig_romfs> <out_dir>
      Writes <out_dir>/romfs/BancMapUnit/<course>.bcett.byml.zs for every course in EDITS.
  python build_stage.py --verify <orig_romfs> <mod_romfs>
      Checks the shipped files in <mod_romfs>/BancMapUnit: exactly the declared courses, each differing from its
      original only in the declared float/string edits. Exits 1 on any problem.

<orig_romfs> is the extracted 1.2.1 romfs (needs BancMapUnit/).
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bymlpatch import Byml, read, write
from byml import parse

# (course, actor Hash, Gyaml, key, original xyz, new xyz)
# Course152_Sub4 (W4 Bowser Jr.): KoopaJrSystemWaterMixAreaPlane draws the underwater tint, caustics and light rays.
# It follows the camera in x only and is sized for the stock 17.5-block view height; the 4:3 view is 23.33 tall and
# the fight framing sits ~2.9 blocks higher (about y -5.6 to 17.7), so Scale Y 1.5 (minimum ~1.35) covers both.
EDITS = [
    ('Course152_Sub4', 2115412732, 'KoopaJrSystemWaterMixAreaPlane', 'Scale', (1.0, 1.0, 1.0), (1.0, 1.5, 1.0)),
    # Course411_Course (Break Time! Wonder Token Tunes): in 4:3 with G = 20.6667 (matching stock 16:9 width 27.56),
    # view height expands to 20.67 (top y = 18.58, bottom y = -2.08).
    # 1. Shift top arch and both side pillars together by +1.45 in Y so the corner joints stay flush and the arch
    #    sits at the top of the 4:3 screen (matching 16:9 relative framing).
    # 2. Upper wall (DVCommonMiniMokkinMiddleKabeA01) nudged down slightly (y 14.5 -> 14.05) matching Course417.
    # 3. Shift backdrop / lower wall (DVCommonMiniMokkinMiddleKabeA00) up to y = 6.05 (Scale 1.0) so its top
    #    overlaps cleanly behind the upper scallops, completely sealing the top gap with zero distortion.
    ('Course411_Course', 17065616487753818880, 'MapObjCommonMiniMokkinKazariHashiraTopA00', 'Translate',
     (14.0, 17.094999313354492, -1.5), (14.0, 18.545, -1.5)),
    ('Course411_Course', 2621125777637998454, 'MapObjCommonMiniMokkinAshibaHashiraA00', 'Translate',
     (0.0, 13.0, 0.0), (0.0, 14.45, 0.0)),
    ('Course411_Course', 16950009666873027591, 'MapObjCommonMiniMokkinAshibaHashiraA00', 'Translate',
     (28.0, 13.0, 0.0), (28.0, 14.45, 0.0)),
    ('Course411_Course', 10511750659666636920, 'DVCommonMiniMokkinMiddleKabeA01', 'Translate',
     (14.0, 14.5, -50.0), (14.0, 14.05, -50.0)),
    ('Course411_Course', 7448602804733534664, 'DVCommonMiniMokkinMiddleKabeA00', 'Translate',
     (14.0, 8.0, -50.0), (14.0, 6.05, -50.0)),
    # Course415_Course (Bouncy Tunes): same camera/frame geometry as Course411, but the lower wall starts at y = 7.
    # Preserve the arch/pillar joints with the same +1.45 shift; use the proven wall heights without scaling art.
    ('Course415_Course', 11189840997242436358, 'MapObjCommonMiniMokkinKazariHashiraTopA00', 'Translate',
     (14.0, 17.094999313354492, -1.5), (14.0, 18.545, -1.5)),
    ('Course415_Course', 15973468427708520567, 'MapObjCommonMiniMokkinAshibaHashiraA00', 'Translate',
     (0.0, 13.0, 0.0), (0.0, 14.45, 0.0)),
    ('Course415_Course', 10768018882934825920, 'MapObjCommonMiniMokkinAshibaHashiraA00', 'Translate',
     (28.0, 13.0, 0.0), (28.0, 14.45, 0.0)),
    ('Course415_Course', 6698885844443459845, 'DVCommonMiniMokkinMiddleKabeA01', 'Translate',
     (14.0, 14.5, -50.0), (14.0, 14.05, -50.0)),
    ('Course415_Course', 7422773204426211404, 'DVCommonMiniMokkinMiddleKabeA00', 'Translate',
     (14.0, 7.0, -50.0), (14.0, 6.05, -50.0)),
    # Course417_Course starts with A01 pillars whose visible bases end above the taller view.
    # GYAML_EDITS selects A00 instead; place those pillars at the proven Course411/415 height without scaling art.
    # The arch and walls retain the positions previewed in the previous candidate; keep the left pillar's offsets.
    ('Course417_Course', 5572109748998102819, 'MapObjCommonMiniMokkinKazariHashiraTopA00', 'Translate',
     (14.0, 17.25, -1.5), (14.0, 18.545, -1.5)),
    ('Course417_Course', 2563226780723368258, 'MapObjCommonMiniMokkinAshibaHashiraA01', 'Translate',
     (9.5367431640625e-07, 12.999999046325684, 0.0), (9.5367431640625e-07, 14.449999046325684, 0.0)),
    ('Course417_Course', 4481523648176900651, 'MapObjCommonMiniMokkinAshibaHashiraA01', 'Translate',
     (28.0, 13.0, 0.0), (28.0, 14.45, 0.0)),
    ('Course417_Course', 15951153385148960223, 'DVCommonMiniMokkinMiddleKabeA01', 'Translate',
     (14.0, 14.0, -50.0), (14.0, 14.05, -50.0)),
    ('Course417_Course', 15861247310196865901, 'DVCommonMiniMokkinMiddleKabeA00', 'Translate',
     (14.0, 6.0, -50.0), (14.0, 6.05, -50.0)),
    # Course403_Course (Break Time! Zip-Go-Round): at 4:3 with G = 20.6667 (matching stock 16:9 width 27.56),
    # view height expands to 20.67 (bottom y = -2.08), exposing unrendered black floor at y >= 1057.
    # Widen floor cloud Hash 3184768010431751081 across the full floor and nudge slightly down
    # (Translate Y 0.0 -> -0.4, Scale X 6.0 -> 28.0) so the bottom puff row lobes seal both bottom corners
    # and scalloped edge gaps off-screen, while keeping the top at y = 1.6 flush against the red dash floor.
    # All 9 other base clouds (4 ceiling, 5 side walls) remain stock. 2 float writes (8 bytes).
    ('Course403_Course', 3184768010431751081, 'ObjectCloudArea', 'Translate',
     (12.5, 0.0, 0.0), (14.0, -0.4, 0.0)),
    ('Course403_Course', 3184768010431751081, 'ObjectCloudArea', 'Scale',
     (6.0, 4.0, 1.0), (28.0, 4.0, 1.0)),
    # Course400_Course (Break Time! Pop Up, Hoppo!): at 4:3 with G = 20.6667 (matching stock 16:9 width 27.56),
    # view height expands to 20.67, exposing the stock spawn point (y = 12.0) on screen.
    # Raise EnemyKoropon and its linked PopUpTag by +5.0 in Y (12.0 -> 17.0, 16.5 -> 21.5) so the Hoppo spawns
    # off-screen above the 4:3 frame and drops into view as intended, preserving the 4.5-block relative spacing.
    ('Course400_Course', 17703685394400552912, 'EnemyKoropon', 'Translate',
     (3.0, 12.0, 0.0), (3.0, 17.0, 0.0)),
    ('Course400_Course', 3402723882765168318, 'PopUpTag', 'Translate',
     (2.5, 16.5, 0.0), (2.5, 21.5, 0.0)),
    # Course401_Course (Break Time! Kick It, Outmaway!): with the full-room 4:3 camera, the stock ice-block
    # spawn points are visible above the play area. Raise both ice-block variants by +9.0 in Y so they enter
    # the frame from above without changing their horizontal placement or relative spacing.
    ('Course401_Course', 3763676935, 'ObjectBlockPushIce', 'Translate',
     (24.0, 18.0, 0.0), (24.0, 27.0, 0.0)),
    ('Course401_Course', 1355151212, 'ObjectBlockPushIce', 'Translate',
     (24.0, 18.0, 0.0), (24.0, 27.0, 0.0)),
    ('Course401_Course', 3838668586, 'ObjectBlockPushIce', 'Translate',
     (24.0, 18.0, 0.0), (24.0, 27.0, 0.0)),
    ('Course401_Course', 2125968292, 'ObjectBlockPushIce', 'Translate',
     (24.0, 18.0, 0.0), (24.0, 27.0, 0.0)),
    ('Course401_Course', 3554852052, 'ObjectBlockPushIce', 'Translate',
     (24.0, 18.0, 0.0), (24.0, 27.0, 0.0)),
    ('Course401_Course', 3087609171, 'ObjectBlockPushIce', 'Translate',
     (24.0, 18.0, 0.0), (24.0, 27.0, 0.0)),
    ('Course401_Course', 53176105, 'ObjectBlockPushIce', 'Translate',
     (24.0, 18.0, 0.0), (24.0, 27.0, 0.0)),
    ('Course401_Course', 3181913597, 'ObjectBlockPushIce', 'Translate',
     (24.0, 18.0, 0.0), (24.0, 27.0, 0.0)),
    ('Course401_Course', 1321743696, 'ObjectBlockPushIce4x4', 'Translate',
     (23.0, 19.0, 0.0), (23.0, 28.0, 0.0)),
    ('Course401_Course', 333063829, 'ObjectBlockPushIce4x4', 'Translate',
     (23.0, 19.0, 0.0), (23.0, 28.0, 0.0)),
    ('Course401_Course', 4116886011, 'ObjectBlockPushIce4x4', 'Translate',
     (23.0, 19.0, 0.0), (23.0, 28.0, 0.0)),
    ('Course401_Course', 3391928854, 'ObjectBlockPushIce4x4', 'Translate',
     (23.0, 19.0, 0.0), (23.0, 28.0, 0.0)),
    ('Course401_Course', 2898691502, 'ObjectBlockPushIce4x4', 'Translate',
     (23.0, 19.0, 0.0), (23.0, 28.0, 0.0)),
    ('Course401_Course', 2362422353, 'ObjectBlockPushIce4x4', 'Translate',
     (23.0, 19.0, 0.0), (23.0, 28.0, 0.0)),
    # Course408_Course (Break Time! Floating Wonder Tokens): lock the camera horizontally at X = 64.0
    # while keeping the stock Y centre and height. Y-only spawner shifts (X stays stock):
    # top-right +6.0; bottom pair -1.5 (Y -1.5 -> -3.0) to hide the pop-in at the screen edges.
    ('Course408_Course', 892663682, 'CameraArea', 'Scale',
     (27.5, 15.5, 1.0), (24.6667, 15.5, 1.0)),
    ('Course408_Course', 2021327989, 'CreateTag', 'Translate',
     (79.5, 13.5, 0.0), (79.5, 19.5, 0.0)),
    ('Course408_Course', 1522517719, 'CreateTag', 'Translate',
     (58.5, -1.5, 0.0), (58.5, -3.0, 0.0)),
    ('Course408_Course', 1001471908, 'CreateTag', 'Translate',
     (69.5, -1.5, 0.0), (69.5, -3.0, 0.0)),
    # Course407_Course (Break Time! Watery Wonder Tokens): adjust the carved A01 pillar proportionally
    # so its square top is preserved while covering the taller 4:3 view's top-right void.
    ('Course407_Course', 3373664933504165692, 'DVWaKaiganFarIwaA01', 'Translate',
     (23.5, 48.0, -167.5), (23.5, 49.5, -167.5)),
    ('Course407_Course', 3373664933504165692, 'DVWaKaiganFarIwaA01', 'Scale',
     (0.699999988079071, 0.699999988079071, 0.699999988079071), (0.82, 0.82, 0.82)),
]

# (course, actor hashes, original Gyaml, replacement Gyaml). Both variants have matching static-map/physics
# definitions; use the game's existing A00 art rather than stretching A01 or shipping an actor/model pack.
GYAML_EDITS = [
    ('Course417_Course', (2563226780723368258, 4481523648176900651),
     'MapObjCommonMiniMokkinAshibaHashiraA01', 'MapObjCommonMiniMokkinAshibaHashiraA00'),
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
# (course, rail_hash, point_idx, orig_xyz, new_xyz)
# Course853_Main (Sunbaked Desert Special: Pole Block Allure - Autoscroll rail intermediate vertical centering):
# In 4:3 (height 15.75, width 21.0), the authored autoscroll rail 1776580222928036096 climb (Y = 17 -> 25.5 -> 41)
# lifts the camera far above Mario and the poles (which sit at Y = 4.5..15.5). At pt 3 (X = 63, Y = 41), the camera
# bottom reaches Y = 33.12, causing the Wonder Flower (ItemWonderHole at Y = 25.5) and lower poles to be cut off
# below the screen by 7.62 blocks.
# Lower points 0-3 vertically to an intermediate 50% position between stock and the low-profile tuning:
# - Pt 0: (0.0, 17.0, 0.0) -> (0.0, 14.5, 0.0)   (-2.5)
# - Pt 1: (13.0, 17.0, 0.0) -> (13.0, 14.5, 0.0) (-2.5)
# - Pt 2: (38.0, 25.5, 0.0) -> (38.0, 22.75, 0.0)(-2.75)
# - Pt 3: (63.0, 41.0, 0.0) -> (63.0, 36.0, 0.0)  (-5.0)
# This keeps the Wonder Flower (Y = 25.5) +4.00 blocks above the bottom edge while preserving plenty of upper
# headroom for climbing Snake Pole 1 (Y = 29.5) and Snake Pole 2 (Y = 21.5).
RAIL_EDITS = [
    ('Course853_Main', 1776580222928036096, 0, (0.0, 17.0, 0.0), (0.0, 14.5, 0.0)),
    ('Course853_Main', 1776580222928036096, 1, (13.0, 17.0, 0.0), (13.0, 14.5, 0.0)),
    ('Course853_Main', 1776580222928036096, 2, (38.0, 25.5, 0.0), (38.0, 22.75, 0.0)),
    ('Course853_Main', 1776580222928036096, 3, (63.0, 41.0, 0.0), (63.0, 36.0, 0.0)),
]



def bcett(romfs, course):
    return os.path.join(romfs, 'BancMapUnit', f'{course}.bcett.byml.zs')


def edits_by_course():
    out = {}
    for e in EDITS:
        out.setdefault(e[0], {'actors': [], 'bg': [], 'gyaml': [], 'rails': []})['actors'].append(e)
    for b_edit in BG_EDITS:
        out.setdefault(b_edit[0], {'actors': [], 'bg': [], 'gyaml': [], 'rails': []})['bg'].append(b_edit)
    for g_edit in GYAML_EDITS:
        out.setdefault(g_edit[0], {'actors': [], 'bg': [], 'gyaml': [], 'rails': []})['gyaml'].append(g_edit)
    for r_edit in RAIL_EDITS:
        out.setdefault(r_edit[0], {'actors': [], 'bg': [], 'gyaml': [], 'rails': []})['rails'].append(r_edit)
    return out


def replace_actor_gyaml(d, hashes, original, replacement):
    """Rename a same-size pooled string only when its sole consumers are the selected actor Gyaml fields."""
    assert hashes and len(set(hashes)) == len(hashes), 'duplicate or empty actor selection'
    old, new = original.encode('utf-8'), replacement.encode('utf-8')
    assert old != new and len(old) == len(new), 'Gyaml replacement must be distinct and the same byte length'
    b = Byml(d)
    assert b.strs.count(original) == 1 and replacement not in b.strs, 'unexpected Gyaml string table'
    for h in hashes:
        matches = [a for a in b.actors() if b.hash_of(a) == h]
        assert len(matches) == 1, f'actor hash {h} is missing or duplicated'
        a = matches[0]
        assert a['Gyaml'][0] == 0xA0 and b.actor_value(a, 'Gyaml') == original, f'actor {h}: wrong original Gyaml'

    expected = parse(bytes(d))
    for a in expected['Actors']:
        if a['Hash'] in hashes:
            a['Gyaml'] = replacement

    index = b.strs.index(original)
    strings = b.strs[:]
    strings[index] = replacement
    assert strings == sorted(strings), 'Gyaml replacement would unsort the string table'
    count = len(b.strs)
    assert d[b.strs_off] == 0xC2
    offsets = struct.unpack_from(f'<{count + 1}I', d, b.strs_off + 4)
    table_end = b.strs_off + offsets[-1]
    start = b.strs_off + offsets[index]
    end = start + len(old)
    assert b.strs_off + 4 + 4 * (count + 1) <= start < end < table_end <= len(d), 'invalid string bounds'
    assert d[start:end] == old and d[end] == 0, 'wrong string payload or terminator'
    for i, offset in enumerate(offsets[:-1]):
        if i == index:
            continue
        other_start = b.strs_off + offset
        other_end = d.index(b'\0', other_start) + 1
        assert other_end <= table_end, 'string exceeds table bounds'
        assert max(start, other_start) >= min(end + 1, other_end), 'overlapping string storage'

    allowed = {start + i for i, (a, c) in enumerate(zip(old, new)) if a != c}
    candidate = bytearray(d)
    candidate[start:end] = new
    assert parse(bytes(candidate)) == expected, 'Gyaml replacement affects unintended fields or shared consumers'
    d[start:end] = new
    return allowed


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

    rails_slots = b.array_slots(root['Rails'][2]) if 'Rails' in root else []
    all_rpts = []
    for s in rails_slots:
        rdict = b.hash_entries(s[2])
        if 'Points' in rdict:
            for ps in b.array_slots(rdict['Points'][2]):
                all_rpts.append(b.hash_entries(ps[2]))
    for course, rhash, pidx, orig, new in course_edits.get('rails', []):
        matching_rails = [b.hash_entries(s[2]) for s in rails_slots if b.hash_of(b.hash_entries(s[2])) == rhash]
        assert len(matching_rails) == 1, f'{course} rail {rhash}: {len(matching_rails)} matches'
        rdict = matching_rails[0]
        pts = b.array_slots(rdict['Points'][2])
        p = b.hash_entries(pts[pidx][2])
        node = p['Translate'][2]
        sharers = [pt for pt in all_rpts if pt['Translate'][2] == node]
        assert len(sharers) == 1, f'{course} Rail {rhash} Pt {pidx}: Translate shared by {len(sharers)} points'
        cur = [v for _, v in b.vec3(p, 'Translate')]
        assert cur == list(orig), f'{course} Rail {rhash} Pt {pidx}: {cur}, expected {orig}'
        b.set_vec3(p, 'Translate', new)
        for eslot, _ in b.vec3(p, 'Translate'):
            allowed.update(range(eslot, eslot + 4))

    for course, hashes, original, replacement in course_edits.get('gyaml', []):
        allowed.update(replace_actor_gyaml(d, hashes, original, replacement))
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
            problems.append(f'{course}: {len(diff - allowed)} byte(s) changed outside the declared edits')
        elif bytes(ship) != bytes(ref):
            problems.append(f'{course}: edited values differ from the edit tables')
        elif diff:
            n_total = len(edits.get('actors', [])) + len(edits.get('bg', [])) + len(edits.get('gyaml', [])) + len(edits.get('rails', []))
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
