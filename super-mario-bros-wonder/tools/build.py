"""Build a native-looking 4:3 layout set for Super Mario Bros. Wonder from the ORIGINAL layouts.

usage: python -I build.py <tools_dir> <orig_layout_dir> <out_dir>

Writes <out_dir>/romfs/Layout (only archives this build changes; unchanged ones fall back to the game's own copy)
and <out_dir>/build_report.json (holds original values, so keep <out_dir> outside the repo).
"""
import sys, os, struct, re, json, collections, shutil
sys.path.insert(0, sys.argv[1])
from lyt import *
from compression import zstd

ORIG, OUT = sys.argv[2], sys.argv[3]
TOP = set(open(os.path.join(sys.argv[1], 'toplevel.txt')).read().split())

ROOT_SY = 0.75                      # (4/3) / (16/9)
K = 1 / ROOT_SY                     # 4/3
THRESH = 380                        # |y| (root-local) from which a pane counts as edge-anchored
SMALL_H = 400

# won-aar skipped CmnOnUIBlurBg; with the fill pass it gets 0.75 like the rest. Cursor: the game places the menu pointer
# in screen coordinates, so a 0.75 root pulled it toward the screen's middle onto other elements (user-confirmed fix
# 2026-10-29); its art keeps the 4:3 shape through PART_SCALE_Y below.
ROOT_SKIP = {'Cursor'}
# Parts panes given scale y x0.75 to stand in for a skipped root. LCursor N_RB holds the arrow above N_Pos (rotated 45 deg),
# so the squash must sit here, unrotated; on P_Arrow it squashed along the diagonal (arrow came out 28x34.5 px).
PART_SCALE_Y = {'LCursor': {'N_RB'}}
FORCE_SHIFT = {
    'GameDisplay': {'N_OverlapArea01', 'A_ItemStock'},
    'RaceTimer': {'N_All'},
    'AccountSelect': {'N_DeleteSaveData'},
    'CourseIn': {'N_Badge'},
}
UNIT_SHIFT = {}                     # container -> shift as a whole, no descent
NO_SHIFT_SUBTREE = {
    'ControlGuide': {'N_BG', 'N_Contents'},
    'Option': {'N_CapMask', 'N_CapMaskUse', 'N_Contents'},
    'KakashiCollection': {'N_Contents'},
    'CourseOut': {'N_Flash'},
    'Pause': {'N_Right'},           # course info / members / badge column is one stacked block
}
NO_SHIFT_LAYOUT = {'DeleteSaveData', 'GetWonderFlower', 'KakashiGet', 'TalkFlowerCutIn', 'GrandWorldMap', 'Title'}
NO_FILL = {'GrandWorldMap': {'P_GrandWorldMap'}}
# strips inside unshifted blocks whose outer edge sat on the 16:9 edge: grow them out to the 4:3 edge
EXTEND_TO_EDGE = {'KakashiCollection': {'N_TCap', 'P_TCap'}}
TITLE_ART_DECOR = re.compile(r'^(P_Dust\d+|P_Flash\d+|P_FlashSub\d+|P_MarioShadow\w*)$')
TITLE_EDGE = {'T_Version', 'N_PressStart'}
# capture source panes that keep the 1440 fill (the course-in iris is only round with it). The capture then
# holds the frame in its middle 1080 of 1440 rows (180 clamped rows above/below), so the use pane's
# V coordinates are cropped to 0.125..0.875 to draw the frame back 1:1 (no snapshot jump).
CAPTURE_KEEP_FILL = {'WipeCourseIn': ('N_Cap', 'P_CapUse')}

# Capture "use" panes (P_Cap*): the game copies the capture pane's LOCAL size as framebuffer pixels and the use pane
# draws it back. Stretching every use pane x4/3 (to undo the 0.75 root scale) was TESTED against the stock 16:9 game
# and made things WORSE almost everywhere (key glyphs X/L/R/+, the Select a User card, the in-level HUD all came out
# ~1.3-1.4x too tall; docs/DEVELOPMENT.md 16-16d). Only the BadgeShop (Poplin shop) intro, which came from the original
# build and is user-confirmed, keeps it. Add a layout here only after measuring it against stock.
CAP_USE = re.compile(r'^P_(?:Blank)?Cap(?!ture|EasyBG)\w*$')
CAP_USE_LAYOUTS = {'BadgeShop'}

# Patterns mapped by an orthographic texture projection (texgen source 3) follow the 16:9 screen, not the 0.75 root,
# so at 4:3 they come out 0.75 as wide as tall. Scale that texture's TexSRT X by ROOT_SY to make them square again.
# User-confirmed: Badge Challenge wipe background (badges were ~0.76 wide/tall). Add materials only after measuring.
PROJECTED_PATTERN = {'WipeBadgeChallenge': {'W_WipeC', 'W_WipeLT'}}

# Course-clear photo: the game fills P_Screenshot with a capture of the 4:3 view, so a 16:9 frame drew it ~1.33x too
# wide (bricks measured 35.5x27 px). Photo panes get width x0.75 (frame border kept, width - 0.25 x photo width).
# User-confirmed 2026-10-29: square on the clear screen, main-menu photo and "View photo" zoom look right.
PHOTO_4x3 = {
    'CourseOut': {'photo': 'P_Screenshot', 'narrow': ('P_Screenshot', 'N_Info', 'P_Fade', 'W_PhotoFrame'),
                  'follow_corner': 'N_Flash'},
    'MainMenu': {'photo': 'P_Screenshot', 'narrow': ('P_Screenshot', 'N_Info', 'W_PhotoFrame'),
                 'small_frame': 'W_PhotoFrameSmall', 'small_scale': 0.25, 'pos': 'N_ScreenshotPos',
                 'pos_anim': 'anim/MainMenu_ViewPhoto.bflan', 'key_label': 'A_ViewPhotoKey'},
}
# TransY keys that must NOT get the edge shift: the "View photo" zoom ends centred (frame 16 = 0), only its rest
# position sits at the edge. Shifting it left the enlarged photo 180 units low.
SHIFT_KEEP_KEY = {('MainMenu', 'N_ScreenshotPos', 'anim/MainMenu_ViewPhoto.bflan', 16.0)}

CONTAINERS = {'pan1', 'scr1', 'ali1'}


def is_nominal_null(p):
    return p.kind == 'pan1' and (p.w, p.h) == (30, 40)


def vert_origin(p):
    return (p.origin >> 2) & 3


def parent_vert_origin(p):
    return (p.origin >> 6) & 3


class Writer:
    def __init__(self, buf):
        self.buf = buf
        self.log = []          # (abs_off, old, new, what)

    def f32(self, off, val, what):
        old = struct.unpack_from('<f', self.buf, off)[0]
        struct.pack_into('<f', self.buf, off, val)
        self.log.append((off, old, val, what))


def materials(raw, s):
    """Return list of (name, first_texture_name or None) for the bflyt at raw[s:]."""
    hlen = struct.unpack_from('<H', raw, s + 6)[0]
    nsec = struct.unpack_from('<H', raw, s + 0x10)[0]
    p = s + hlen
    tex, mats = [], []
    for _ in range(nsec):
        mag = raw[p:p + 4]; size = struct.unpack_from('<I', raw, p + 4)[0]
        if mag == b'txl1':
            n = struct.unpack_from('<H', raw, p + 8)[0]; base = p + 12
            for o in struct.unpack_from('<%dI' % n, raw, base):
                tex.append(raw[base + o:raw.index(b'\0', base + o)].decode())
        elif mag == b'mat1':
            n = struct.unpack_from('<H', raw, p + 8)[0]
            for o in struct.unpack_from('<%dI' % n, raw, p + 12):
                m = p + o
                name = raw[m:m + 28].split(b'\0')[0].decode()
                flags = struct.unpack_from('<I', raw, m + 28)[0]
                t = []
                for j in range(flags & 3):
                    ti = struct.unpack_from('<H', raw, m + 0x2C + 4 * j)[0]
                    t.append(tex[ti] if ti < len(tex) else '?')
                mats.append((name, t))
        p += size
    return mats


def material_offsets(raw, s):
    """Return {material name: absolute offset} for the bflyt at raw[s:]."""
    hlen = struct.unpack_from('<H', raw, s + 6)[0]
    nsec = struct.unpack_from('<H', raw, s + 0x10)[0]
    p = s + hlen
    for _ in range(nsec):
        mag = raw[p:p + 4]; size = struct.unpack_from('<I', raw, p + 4)[0]
        if mag == b'mat1':
            n = struct.unpack_from('<H', raw, p + 8)[0]
            return {raw[p + o:p + o + 28].split(b'\0')[0].decode().strip(): p + o     # e.g. 'W_WipeC ' has a trailing space
                    for o in struct.unpack_from('<%dI' % n, raw, p + 12)}
        p += size
    return {}


def annotate(root):
    """Absolute centre/size in root-local units (rotation ignored; asserted absent where it matters)."""
    root.ax = root.ay = root.ay_origin = 0.0
    root.asx = root.asy = 1.0
    def rec(p):
        for c in p.children:
            c.asx, c.asy = p.asx * c.sx, p.asy * c.sy
            pvo = parent_vert_origin(c)
            base_local = 0.0
            if pvo:   # attached to parent's top/bottom edge (relative to parent's rect, not its origin)
                pv = vert_origin(p) if p is not root else 0
                rc = -p.h / 2 if pv == 1 else p.h / 2 if pv == 2 else 0.0
                base_local = rc + (p.h / 2 if pvo == 1 else -p.h / 2)
            px, py = p.ax + p.asx * c.tx, p.ay_origin + p.asy * (base_local + c.ty)
            vo = vert_origin(c)
            hh = c.h * c.asy
            c.ay_origin = py
            c.ay = py - hh / 2 if vo == 1 else py + hh / 2 if vo == 2 else py
            c.ax = px
            c.ah, c.aw = abs(hh), abs(c.w * c.asx)
            c.parent_sy = p.asy
            rec(c)
    rec(root)


def build_archive(base, raw):
    buf = bytearray(raw)
    W = Writer(buf)
    ents = sarc_entries(raw)
    top = base in TOP
    notes = []

    # FLPA TransY curves by pane name across all bflan in archive
    ty_keys = collections.defaultdict(list)
    for nm, (s, e) in ents.items():
        if nm.endswith('.bflan'):
            for pane, is_mat, tmag, target, ctype, keys in parse_flan(raw, s):
                if tmag == 'FLPA' and not is_mat and target == 1:
                    assert ctype == 2, (base, nm, pane, ctype)
                    ty_keys[pane].append((nm, keys))

    layouts = [(nm, se) for nm, se in ents.items() if nm.endswith('.bflyt')]
    for nm, (s, e) in layouts:
        lw, lh, root = parse_flyt(raw, s)
        if base in CAP_USE_LAYOUTS:
            for p in root.walk():
                if p.kind == 'pic1' and CAP_USE.match(p.name) and p.h < 1000:
                    W.f32(p.off + Pane.H, p.h * K, f'capture-use height {p.name}')
                    notes.append(f'capuse {p.name:<23} height {p.h:g} -> {p.h * K:.1f} (1:1 pixels under root 0.75)')
        for p in root.walk():
            if p.name in PART_SCALE_Y.get(base, ()):
                assert p.rot == (0.0, 0.0, 0.0), (base, p.name)
                W.f32(p.off + Pane.SY, p.sy * ROOT_SY, f'part-scale-y {p.name}')
                notes.append(f'scale {p.name:<24} y x{ROOT_SY:g} (stands in for the skipped root)')
        if not top:
            continue                      # parts layouts: leave original (root scale 1,1) otherwise
        assert len(layouts) == 1, base
        H, Wd = lh, lw
        half_vis = H / 2 * K              # 720
        delta_edge = half_vis - H / 2     # 180
        if base not in ROOT_SKIP:
            W.f32(root.off + Pane.SY, root.sy * ROOT_SY, 'root.sy')
        annotate(root)
        mats = materials(raw, s)
        handled = set()

        # ---- course-clear photo shown at 4:3 ----
        if base in PHOTO_4x3:
            ph = PHOTO_4x3[base]
            P = {p.name: p for p in root.walk()}
            dw = P[ph['photo']].w * (1 - ROOT_SY)
            for n in ph['narrow']:
                W.f32(P[n].off + Pane.W, P[n].w - dw, f'photo-4x3 width {n}')
            if 'follow_corner' in ph:
                n = ph['follow_corner']
                W.f32(P[n].off + Pane.TX, P[n].tx - dw / 2, f'photo-4x3 corner {n}')
            if 'small_frame' in ph:
                dws = dw * ph['small_scale']
                n = ph['small_frame']
                W.f32(P[n].off + Pane.W, P[n].w - dws, f'photo-4x3 width {n}')
                # keep the small photo's left margin and the key label's place next to it
                pos = P[ph['pos']]
                nx = pos.tx - dws / 2
                W.f32(pos.off + Pane.TX, nx, f'photo-4x3 x {pos.name}')
                s_an, _ = ents[ph['pos_anim']]
                for pane, is_mat, tmag, target, ctype, keys in parse_flan(raw, s_an):
                    if pane == pos.name and tmag == 'FLPA' and not is_mat and target == 0:
                        for k in keys:
                            if k.frame == 0:
                                W.f32(k.off + 4, nx, f'photo-4x3 x-anim {pos.name}')
                lab = P[ph['key_label']]
                W.f32(lab.off + Pane.TX, lab.tx + dws / 2, f'photo-4x3 x {lab.name}')
            notes.append(f'photo {ph["photo"]:<24} 4:3 photo frame (width -{dw:g})')

        # ---- screen-projected patterns ----
        for mname in PROJECTED_PATTERN.get(base, ()):
            m = material_offsets(raw, s)[mname]
            flags = struct.unpack_from('<I', raw, m + 28)[0]
            ntex, nsrt, ngen = flags & 3, (flags >> 2) & 3, (flags >> 4) & 3
            srt0 = m + 0x2C + 4 * ntex                      # TexSRT entries: tx, ty, rot, sx, sy
            gen0 = srt0 + 20 * nsrt                         # TexCoordGen entries, 16 bytes, source at +1
            for i in range(min(nsrt, ngen)):
                if raw[gen0 + 16 * i + 1] == 3:
                    sx_off = srt0 + 20 * i + 12
                    W.f32(sx_off, struct.unpack_from('<f', raw, sx_off)[0] * ROOT_SY, f'projected-pattern sx {mname}')
                    notes.append(f'proj  {mname:<24} TexSRT[{i}] scale X x{ROOT_SY:g} (ortho-projected pattern)')

        # ---- capture panes that keep the fill ----
        if base in CAPTURE_KEEP_FILL:
            cap_name, use_name = CAPTURE_KEEP_FILL[base]
            cap = next(p for p in root.walk() if p.name == cap_name)
            use = next(p for p in root.walk() if p.name == use_name)
            assert cap.kind == 'pan1' and use.kind == 'pic1' and cap.h == use.h == H, (base, cap.h, use.h)
            W.f32(cap.off + Pane.H, cap.h * K, f'capture-keep-fill {cap.name}')
            ntc = buf[use.off + 102]
            for t in range(ntc):
                for corner in range(4):
                    vo = use.off + 104 + 32 * t + 8 * corner + 4
                    v = struct.unpack_from('<f', buf, vo)[0]
                    W.f32(vo, 0.5 + (v - 0.5) * ROOT_SY, f'capture-uv-crop {use.name}')
            notes.append(f'keep  {cap.name:<24} capture fill; {use.name} V cropped to the frame rows')

        def shift_pane(p, sign, why):
            d_local = sign * delta_edge / p.parent_sy
            W.f32(p.off + Pane.TY, p.ty + d_local, f'shift {p.name} ({why})')
            for an, keys in ty_keys.get(p.name, []):
                for k in keys:
                    if (base, p.name, an, k.frame) in SHIFT_KEEP_KEY:
                        continue
                    W.f32(k.off + 4, k.value + d_local, f'shift-anim {p.name} {an}')
            notes.append(f'shift {p.name:<24} y {p.ay:8.1f} -> {p.ay + sign * delta_edge:8.1f}  ({why})')
            handled.add(p.name)

        # ---- fill pass (anywhere in tree) ----
        fill = set()
        for p in root.walk():
            if p is root or p.name in NO_FILL.get(base, ()):
                continue
            # capture source panes (N_Cap*, N_Capture) are NOT filled: the game copies the pane's local size
            # as framebuffer pixels, ignoring the root 0.75, so 1080 already grabs the whole frame (1440 read
            # 180 rows past each edge -> clamped streaks, image squeezed into a 16:9 band). Their use panes fill.
            edge_parent = p.kind == 'pan1' and any(parent_vert_origin(c) for c in p.children)
            if not (p.kind in ('pic1', 'wnd1', 'scr1') or edge_parent):
                continue
            if not (H * 0.95 <= p.ah < H * K - 1):
                continue
            animated_ty = p.name in ty_keys
            if abs(p.ay) > 10 and not (animated_ty and p.aw >= Wd * 0.95):
                continue
            assert parent_vert_origin(p) == 0, (base, p.name, p.origin)
            vo = vert_origin(p)
            assert vo == 0 or not (p.name in ty_keys), (base, p.name)
            uniform = False
            if p.kind == 'pic1':
                mi = struct.unpack_from('<H', buf, p.off + 100)[0]
                mname, tex = mats[mi]
                uniform = bool(tex) and not any(t.startswith('CmnDummy') for t in tex) and p.aw >= Wd * 0.95
            else:
                tex = None
            W.f32(p.off + Pane.H, p.h * K, f'fill-h {p.name}')
            if vo:   # keep the rect centred: top origin grows downward, bottom origin upward
                grow = (p.h * K - p.h) / 2 * p.sy
                W.f32(p.off + Pane.TY, p.ty + (grow if vo == 1 else -grow), f'fill-recentre {p.name}')
            if uniform:
                W.f32(p.off + Pane.W, p.w * K, f'fill-w {p.name}')
            if animated_ty:
                W.f32(p.off + Pane.TY, p.ty * K, f'fill-ty {p.name}')
                for an, keys in ty_keys[p.name]:
                    for k in keys:
                        W.f32(k.off + 4, k.value * K, f'fill-anim {p.name} {an}')
                        W.f32(k.off + 8, k.slope * K, f'fill-anim-slope {p.name} {an}')
            fill.add(p.name)
            notes.append(f"fill  {p.name:<24} {'uniform' if uniform else 'height '}  tex={tex}")

        # ---- extend edge strips ----
        for p in root.walk():
            if p.name in EXTEND_TO_EDGE.get(base, ()):
                assert vert_origin(p) == 0 and p.name not in ty_keys, (base, p.name)
                sign = 1 if p.ay > 0 else -1
                assert abs(abs(p.ay) + p.ah / 2 - H / 2) <= 5, (base, p.name)
                W.f32(p.off + Pane.H, p.h + delta_edge / p.asy, f'extend-h {p.name}')
                W.f32(p.off + Pane.TY, p.ty + sign * delta_edge / 2 / p.parent_sy, f'extend-ty {p.name}')
                notes.append(f'extend {p.name:<23} outer edge {sign * H / 2:.0f} -> {sign * half_vis:.0f}')

        # ---- Title special ----
        if base == 'Title':
            for p in root.walk():
                if TITLE_ART_DECOR.match(p.name):
                    assert vert_origin(p) == 0
                    nx, ny = p.ax * K, p.ay_origin * K
                    par = p.parent
                    W.f32(p.off + Pane.TX, (nx - par.ax) / par.asx, f'title-decor {p.name}')
                    W.f32(p.off + Pane.TY, (ny - par.ay_origin) / par.asy, f'title-decor {p.name}')
                    assert p.name not in ty_keys
                    W.f32(p.off + Pane.W, p.w * K, f'title-decor-size {p.name}')
                    W.f32(p.off + Pane.H, p.h * K, f'title-decor-size {p.name}')
                    notes.append(f'decor {p.name:<24} ({p.ax:.0f},{p.ay:.0f}) -> ({nx:.0f},{ny:.0f})')
                elif p.name in TITLE_EDGE:
                    shift_pane(p, 1 if p.ay > 0 else -1, 'title edge')

        # ---- edge shift pass ----
        if base not in NO_SHIFT_LAYOUT:
            force = FORCE_SHIFT.get(base, set())
            units = UNIT_SHIFT.get(base, {})
            skip = NO_SHIFT_SUBTREE.get(base, set())

            def is_edge(c):
                h_eff = 0 if is_nominal_null(c) else c.ah
                return h_eff < 0.8 * H and (abs(c.ay) >= THRESH or abs(c.ay_origin) >= THRESH
                                            or (h_eff <= SMALL_H and abs(c.ay) + h_eff / 2 >= THRESH))

            def consider(c, why):
                """c is edge-anchored (or forced): shift it, or split it if it mixes edge and central children."""
                # pivot/wrapper pattern (e.g. BadgeShop N_Anchor (-960,-540) -> N_Contents (960,540)): a child
                # counter-translates back towards the centre, so the container is not an edge element itself
                sign = 1 if c.ay > 0 else -1
                pivot = c.kind == 'pan1' and why != 'forced' and any(
                    not is_edge(k) and k.name not in fill and k.ty * sign * c.asy <= -300 for k in c.children)
                if pivot:
                    notes.append(f'split {c.name:<24} (pivot: a child counter-translates to central content)')
                    for k in c.children:
                        if k.name in skip or k.name in fill:
                            continue
                        if is_edge(k):
                            consider(k, 'edge')
                    return
                shift_pane(c, 1 if c.ay > 0 else -1, why)

            def visit(p):
                for c in p.children:
                    if c.name in skip:
                        continue
                    if c.name in fill:
                        if c.kind in CONTAINERS and c.children and c.ty == 0 and c.rot == (0, 0, 0):
                            visit(c)
                        continue
                    if c.name in units:
                        shift_pane(c, units[c.name], 'unit'); continue
                    if c.ty != 0 or c.name in force:
                        if c.name in force:
                            consider(c, 'forced')
                        elif is_edge(c):
                            consider(c, 'edge')
                        continue
                    if c.kind in CONTAINERS and c.children and c.sy == 1 and c.rot == (0, 0, 0):
                        visit(c)
            visit(root)
        # report force/unit names that were never found
        for n in FORCE_SHIFT.get(base, set()) | set(UNIT_SHIFT.get(base, {})):
            if n not in handled:
                raise SystemExit(f'{base}: curated pane {n} not handled')
    return buf, W.log, notes


def main():
    os.makedirs(os.path.join(OUT, 'romfs', 'Layout'), exist_ok=True)
    report, unchanged = {}, []
    for base, path, raw, ents in load_layout_dir(ORIG):
        buf, log, notes = build_archive(base, raw)
        assert len(buf) == len(raw)
        if bytes(buf) == raw:           # ship only what the mod overrides; never an original game file
            unchanged.append(base)
            continue
        comp = zstd.compress(bytes(buf), level=19)
        assert zstd.decompress(comp) == bytes(buf)
        with open(os.path.join(OUT, 'romfs', 'Layout', os.path.basename(path)), 'wb') as f:
            f.write(comp)
        report[base] = {'writes': [(o, a, b, w) for o, a, b, w in log], 'notes': notes}
    # layouts edited by hand (not derivable from the originals) are copied over the generated ones
    hand = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hand-edited')
    for f in os.listdir(hand) if os.path.isdir(hand) else []:
        shutil.copyfile(os.path.join(hand, f), os.path.join(OUT, 'romfs', 'Layout', f))
        print(f'hand-edited layout kept: {f}')
    json.dump(report, open(os.path.join(OUT, 'build_report.json'), 'w'), indent=1)
    print(f'{len(report)} archives written, {len(unchanged)} unchanged and left out')
    for base in sorted(report):
        if report[base]['notes']:
            print(f'== {base}')
            for n in report[base]['notes']:
                print('   ' + n)


main()
