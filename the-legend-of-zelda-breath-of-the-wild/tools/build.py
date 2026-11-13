"""Build a native-looking 4:3 layout set for BOTW 1.6.0 from the ORIGINAL layouts.

usage: python -I build.py <dump_romfs_dir> <out_dir> [--no-compress]

Writes <out_dir>/Layout/*.sblarc, <out_dir>/Pack/Bootup.pack, Title.pack (only the archives that changed)
and <out_dir>/build_report.json. Every change is a float overwrite in place (no pane/size is added), so only
the Yaz0 stream sizes change; SARC containers are rebuilt with the original order and alignment.
"""
import sys, os, struct, re, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import *
import curated as C

SRC, OUT = sys.argv[1], sys.argv[2]
COMPRESS = '--no-compress' not in sys.argv

CONTAINERS = {'pan1', 'scr1', 'ali1'}


class Writer:
    def __init__(self, buf):
        self.buf = buf
        self.log = []

    def f32(self, off, val, what):
        old = struct.unpack_from('<f', self.buf, off)[0]
        struct.pack_into('<f', self.buf, off, val)
        self.log.append((off, old, val, what))


def grow_fill(W, lname, p, factor, uniform, szh_keys, ty_keys, notes, why='fill'):
    """Grow a pane's height by `factor` (and width if uniform), recentring on its centre and scaling
    any SizeH animation keys. Curated fills only: a TransY animation makes the pane unsafe -> skip."""
    if p.name in ty_keys:
        notes.append(f'WARN {why} {p.name}: TransY animation present, skipped')
        return False
    vo = vert_origin(p)
    W.f32(p.off + Pane.H, p.h * factor, f'{why}-h {lname}/{p.name}')
    if vo:
        grow = (p.h * factor - p.h) / 2 * p.sy
        W.f32(p.off + Pane.TY, p.ty + (grow if vo == 1 else -grow), f'{why}-recentre {lname}/{p.name}')
    if uniform:
        W.f32(p.off + Pane.W, p.w * factor, f'{why}-w {lname}/{p.name}')
    for an, keys in szh_keys.get(p.name, []):
        for k in keys:
            W.f32(k.off + 4, k.value * factor, f'{why}-hanim {lname}/{p.name} {an}')
            W.f32(k.off + 8, k.slope * factor, f'{why}-hanim-slope {lname}/{p.name} {an}')
    return True


def find_capture_source(root, use):
    """The pan1 'Capture' source whose rect equals a FBLayout use pane's rect (same centre and size), growable
    in height: no TransY animation is checked by the caller; children must not hang off its top/bottom edge."""
    for s in root.walk():
        if s.kind != 'pan1' or 'Capture' not in s.name or s is use:
            continue
        if (abs(s.ax - use.ax) <= 2 and abs(s.ay - use.ay) <= 2 and abs(s.aw - use.aw) <= 2 and abs(s.ah - use.ah) <= 2
                and abs(s.h - use.h) <= 2 and not any(parent_vert_origin(c) for c in s.children)):
            return s
    return None
def last_key_shift(W, lname, name, dy, ty_keys, notes, why='lastkey'):
    """Shift the FINAL pose of every TransY curve of `name` (>= 2 keys) by dy and keep the hermite
    start slope linear (slope += dy / frame span). Single-key curves (constant overrides) and the
    static pane position are untouched."""
    n = 0
    for an, keys in ty_keys.get(name, []):
        if len(keys) < 2:
            continue
        kl, kp = keys[-1], keys[-2]
        W.f32(kl.off + 4, kl.value + dy, f'{why} {lname}/{name} {an}')
        df = kl.frame - kp.frame
        if df > 0 and kp.slope is not None:
            W.f32(kp.off + 8, kp.slope + dy / df, f'{why}-slope {lname}/{name} {an}')
        n += 1
    if n:
        notes.append(f'{why} {name:<26} final TransY pose {dy:+.0f} ({n} curve(s))')
    return n


def scale_ty(W, lname, p, factor, ty_keys, notes):
    """Scale a pane's TransY (static value and every key + slope) by factor (centre-origin panes)."""
    W.f32(p.off + Pane.TY, p.ty * factor, f'ty-scale {lname}/{p.name}')
    for an, keys in ty_keys.get(p.name, []):
        for k in keys:
            W.f32(k.off + 4, k.value * factor, f'ty-scale-anim {lname}/{p.name} {an}')
            if k.slope is not None:
                W.f32(k.off + 8, k.slope * factor, f'ty-scale-slope {lname}/{p.name} {an}')
    notes.append(f'ty-scale {p.name:<26} x{factor:.4f}')


# ---------------------------------------------------------------------------------------------------------
# fullframe capture policy (children mode). See curated.CAPTURE_POLICY.
def _visited(p):
    """children_pass visits this pane (same rule as verify.tl)."""
    if p.parent is None or p.name in C.NO_SCALE_NAMES:
        return False
    if p.parent.parent is None:
        return True
    q = p.parent
    return q.name in C.CODE_SCALE_PANES and q.rot == (0.0, 0.0, 0.0) and _visited(q)


def _scaled(p):
    """the pane receives the 0.75 factor on its own ScaleY in children mode"""
    return _visited(p) and p.name not in C.CODE_SCALE_PANES and p.rot == (0.0, 0.0, 0.0)


def n_scaled_chain(p):
    n = 0
    while p is not None and p.parent is not None:
        n += _scaled(p)
        p = p.parent
    return n


def fb_pairs(lname, raw, s, root):
    """(use, [sources]) pairs of framebuffer-copy captures in a top-level layout, on the STOCK tree (annotate(root)
    must have run): use = pic1 with an FBLayout texture, source = pan1 'Capture' pane on the same rect. Text-glow
    captures (CaptureBGColor), CaptureApplyScale sources, map windows and code-sized slide seams are not framebuffer
    copies of the plain kind and are left alone."""
    if C.CAPTURE_POLICY != 'fullframe' or C.ROOT_MODE != 'children' or lname in C.CAPTURE_SKIP_LAYOUTS:
        return []
    mats = materials(raw, s)
    out = []
    for u in root.walk():
        if u.kind != 'pic1' or u.name.startswith(C.CAPTURE_SKIP_PREFIX):
            continue
        mi = struct.unpack_from('<H', raw, u.off + 100)[0]
        tex = mats[mi][1] if mi < len(mats) else []
        if not any(t.startswith('FBLayout') for t in tex):
            continue
        cands = [q for q in root.walk() if q.kind == 'pan1' and 'Capture' in q.name and 'Pos' not in q.name
                 and abs(q.ax - u.ax) <= 2 and abs(q.ay - u.ay) <= 2 and abs(q.aw - u.aw) <= 2
                 and abs(q.ah - u.ah) <= 2 and abs(q.w - u.w) <= 2 and abs(q.h - u.h) <= 2]
        if not cands or any((b'CaptureBGColor' in q.usd and q.name not in C.CAPTURE_BG_FULLFRAME.get(lname, ()))
                            or b'CaptureApplyScale' in q.usd for q in cands):
            continue
        out.append((u, cands))
    return out


def retarget_h(W, lname, p, target, szh_keys_cur, notes, why):
    """set a pane's height to `target` (centre kept for edge-origin panes, SizeH keys scaled by the same ratio)."""
    cur = struct.unpack_from('<f', W.buf, p.off + Pane.H)[0]
    if abs(target - cur) < 0.01:
        return False
    r = target / cur
    W.f32(p.off + Pane.H, target, f'{why}-h {lname}/{p.name}')
    vo = vert_origin(p)
    if vo:
        sy_eff = p.sy * (ROOT_SY if _scaled(p) else 1.0)
        grow = (target - cur) / 2 * sy_eff
        W.f32(p.off + Pane.TY, struct.unpack_from('<f', W.buf, p.off + Pane.TY)[0] + (grow if vo == 1 else -grow),
              f'{why}-recentre {lname}/{p.name}')
    for an, keys in szh_keys_cur.get(p.name, []):
        for k in keys:
            W.f32(k.off + 4, struct.unpack_from('<f', W.buf, k.off + 4)[0] * r, f'{why}-hanim {lname}/{p.name} {an}')
            W.f32(k.off + 8, struct.unpack_from('<f', W.buf, k.off + 8)[0] * r, f'{why}-hanim-slope {lname}/{p.name} {an}')
    notes.append(f'{why} {p.name:<24} h {cur:.0f} -> {target:.0f}')
    return True


def capture_pass(lname, raw, ents, buf, W):
    s, e = ents['blyt/' + lname + '.bflyt']
    lw, lh, root = parse_flyt(raw, s)
    annotate(root)
    notes = []
    pairs = fb_pairs(lname, raw, s, root)
    if not pairs:
        return notes
    szh = collections.defaultdict(list)
    for an in layout_anims(ents, lname):
        for pane, is_mat, tmag, target, ctype, ks in parse_flan(raw, ents[an][0]):
            if not is_mat and target == 9:
                szh[pane].append((an, ks))
    for u, cs in pairs:
        n = n_scaled_chain(u)
        retarget_h(W, lname, u, u.h / (ROOT_SY ** n), szh, notes, f'capture-use(n={n}, src {cs[0].name})')
    return notes


def host_scale_counts(raw, ents, part):
    """{n} over every use site of `part` in this archive's top-level layouts: n = 0.75-scaled panes in the prt1's chain."""
    counts = set()
    for nm in ents:
        if not nm.endswith('.bflyt'):
            continue
        ln = nm[5:-6]
        if ln == part or ln in C.ROOT_SKIP:
            continue
        s = ents[nm][0]
        lw, lh, root = parse_flyt(raw, s)
        if (lw, lh) != (1280.0, 720.0):
            continue
        panes = [q for q in root.walk() if q.kind == 'prt1']
        secs = [p for m, p, z in flyt_tags(raw, s, {b'prt1'})]
        if len(panes) != len(secs):
            continue
        for q, p in zip(panes, secs):
            if prt1_name(raw, p) == part:
                counts.add(n_scaled_chain(q))
    return counts


def build_part(lname, raw, ents, buf, W, root):
    """Curated fills/shifts for a referenced part layout. Root stays (1, 1); safety for the fill
    geometry (all prt1 uses at scale (1, 1), part content centred on screen) is enforced in verify.py."""
    fills = C.PART_FILL.get(lname, {})
    shifts = C.PART_SHIFT.get(lname, set())
    exact = C.PART_EXACT_H.get(lname, {})
    shift_y = C.PART_SHIFT_Y.get(lname, {})
    ty_scale = C.PART_TY_SCALE.get(lname, {})
    cap_use = C.PART_CAPTURE_USE.get(lname, []) if (C.CAPTURE_POLICY == 'fullframe' and C.ROOT_MODE == 'children') else []
    squash = C.PART_SQUASH_Y.get(lname, set())
    grow_h = C.PART_GROW_H.get(lname, {})
    part_sy = C.PART_SY.get(lname, set()) if C.ROOT_MODE == 'children' else set()
    if not (fills or shifts or exact or shift_y or ty_scale or cap_use or squash or grow_h or part_sy):
        return []
    notes = []
    annotate(root)
    ty_keys = collections.defaultdict(list)
    szh_keys = collections.defaultdict(list)
    sy_keys = collections.defaultdict(list)
    for an in layout_anims(ents, lname):
        for pane, is_mat, tmag, target, ctype, keys in parse_flan(raw, ents[an][0]):
            if is_mat:
                continue
            if target == 1:
                ty_keys[pane].append((an, keys))
            elif target == 7:
                sy_keys[pane].append((an, keys))
            elif target == 9:
                szh_keys[pane].append((an, keys))
    # round 9: squash direct RootPane children of the part by ROOT_SY about the part centre (ScaleY and TransY,
    # static + keys). Only centre-attached, unrotated panes; anything else is reported and left alone.
    for p in root.children:
        if p.name not in squash:
            continue
        if parent_vert_origin(p) or p.rot != (0.0, 0.0, 0.0):
            notes.append(f'WARN part-squash {p.name}: edge-attached or rotated, left alone')
            continue
        W.f32(p.off + Pane.SY, p.sy * ROOT_SY, f'part-squash-sy {lname}/{p.name}')
        W.f32(p.off + Pane.TY, p.ty * ROOT_SY, f'part-squash-ty {lname}/{p.name}')
        for kd, what in ((ty_keys, 'ty'), (sy_keys, 'sy')):
            for an, keys in kd.get(p.name, []):
                for k in keys:
                    if k.slope is None:
                        notes.append(f'WARN part-squash {p.name}: step curve in {an}, left alone')
                        continue
                    W.f32(k.off + 4, k.value * ROOT_SY, f'part-squash-{what}-anim {lname}/{p.name} {an}')
                    W.f32(k.off + 8, k.slope * ROOT_SY, f'part-squash-{what}-slope {lname}/{p.name} {an}')
        notes.append(f'part-squash {p.name:<26} ScaleY {p.sy:.3f} -> {p.sy * ROOT_SY:.3f}, TransY {p.ty:.1f} -> {p.ty * ROOT_SY:.1f}')
    missing = squash - {p.name for p in root.children}
    if missing:
        notes.append(f'WARN part-squash panes not direct RootPane children: {sorted(missing)}')
    done = set()
    if cap_use:
        ns = host_scale_counts(raw, ents, lname)
        if len(ns) != 1:
            notes.append(f'WARN part capture {lname}: use sites disagree / not found (n={sorted(ns)}), panes left alone')
        else:
            n = ns.pop()
            for p in root.walk():
                if p.name in cap_use:
                    retarget_h(W, lname, p, p.h / (ROOT_SY ** n), szh_keys, notes, f'part-capture-use(n={n})')
        done.update(cap_use)
    for p in root.walk():
        if p.name in fills:
            mode = fills[p.name]
            factor = (C.PART_FILL_H.get(lname, 2 * HALF_VIS) / p.h) if mode in 'HU' else K
            if grow_fill(W, lname, p, factor, mode in 'uU', szh_keys, ty_keys, notes, 'part-fill'):
                done.add(p.name)
                notes.append(f'part-fill {p.name:<26} h {p.h:.0f} -> {p.h * factor:.0f}  ({mode})')
        elif p.name in shifts:
            sign = 1 if p.ay > 0 else -1
            d_local = sign * DELTA / p.parent_sy
            W.f32(p.off + Pane.TY, p.ty + d_local, f'part-shift {lname}/{p.name}')
            for an, keys in ty_keys.get(p.name, []):
                for k in keys:
                    W.f32(k.off + 4, k.value + d_local, f'part-shift-anim {lname}/{p.name} {an}')
            done.add(p.name)
            notes.append(f'part-shift {p.name:<26} y {p.ay:7.1f} -> {p.ay + sign * DELTA:7.1f}')
    # exact-height windows (grown around their own centre to a fixed height)
    for p in root.walk():
        if p.name in exact:
            if grow_fill(W, lname, p, exact[p.name] / p.h, False, szh_keys, ty_keys, notes, 'part-exact'):
                done.add(p.name)
                notes.append(f'part-exact {p.name:<26} h {p.h:.0f} -> {exact[p.name]:.0f}')
    # explicit signed TransY shifts (parts whose use sites sit off the layout origin); the final pose of any
    # multi-key TransY curve moves with the pane, constant single-key overrides are left alone
    for p in root.walk():
        if p.name in shift_y:
            dy = shift_y[p.name]
            W.f32(p.off + Pane.TY, p.ty + dy / p.parent_sy, f'part-shift-y {lname}/{p.name}')
            last_key_shift(W, lname, p.name, dy / p.parent_sy, ty_keys, notes, 'part-shift-y-key')
            done.add(p.name)
            notes.append(f'part-shift-y {p.name:<26} y {p.ay:7.1f} -> {p.ay + dy:7.1f}')
    for p in root.walk():
        if p.name in ty_scale:
            scale_ty(W, lname, p, ty_scale[p.name], ty_keys, notes)
            done.add(p.name)
    # round 10: fixed height growth around the pane's own centre (no SizeH / TransY animation allowed)
    for p in root.walk():
        if p.name in grow_h:
            if p.name in szh_keys or p.name in ty_keys:
                notes.append(f'WARN part-grow-h {p.name}: SizeH/TransY animated, left alone')
                continue
            if grow_fill(W, lname, p, (p.h + grow_h[p.name]) / p.h, False, szh_keys, ty_keys, notes, 'part-grow-h'):
                done.add(p.name)
                notes.append(f'part-grow-h {p.name:<26} h {p.h:.0f} -> {p.h + grow_h[p.name]:.0f}')
    for p in root.walk():                      # stamina wheel: the 0.75 squash lives inside the part (see curated.PART_SY)
        if p.name in part_sy:
            W.f32(p.off + Pane.SY, p.sy * ROOT_SY, f'part-sy {lname}/{p.name}')
            W.f32(p.off + Pane.TY, p.ty * ROOT_SY, f'part-sy-ty {lname}/{p.name}')
            done.add(p.name)
            notes.append(f'part-sy {p.name:<26} ScaleY {p.sy:.2f} -> {p.sy * ROOT_SY:.3f}')
    for n in (list(fills) + sorted(shifts) + list(exact) + list(shift_y) + list(ty_scale) + list(grow_h)
              + sorted(part_sy)):  # cap_use warns itself
        if n not in done:
            notes.append(f'WARN curated part pane {n} not found/handled')
    return notes


def _build_layout(lname, raw, ents, buf, W, top, referenced):
    """Apply the rules to one bflyt. Returns notes."""
    s, e = ents['blyt/' + lname + '.bflyt']
    lw, lh, root = parse_flyt(raw, s)
    notes = []
    if lname in referenced:
        return build_part(lname, raw, ents, buf, W, root)  # part: root stays (1, 1), prt1 stands in for it
    if (lw, lh) != (1280.0, 720.0):
        notes.append(f'skip layout size {lw}x{lh}')
        return notes
    if lname not in C.ROOT_SKIP and lname not in C.CURSOR_ROOT_KEEP and C.ROOT_MODE == 'root':
        W.f32(root.off + Pane.SY, root.sy * ROOT_SY, 'root.sy')
    if lname in C.NO_SHIFT_LAYOUT_ALL:
        return notes
    annotate(root)
    mats = materials(raw, s)

    # TransY / size curves by pane name (this layout's own animations)
    ty_keys = collections.defaultdict(list)
    szh_keys = collections.defaultdict(list)
    for an in layout_anims(ents, lname):
        for pane, is_mat, tmag, target, ctype, keys in parse_flan(raw, ents[an][0]):
            if is_mat:
                continue
            if target == 1:
                assert ctype == 2, (lname, an, pane, ctype)
                ty_keys[pane].append((an, keys))
            elif target == 9:
                szh_keys[pane].append((an, keys))

    handled = set()
    sign_of = lambda p: 1 if p.ay > 0 else -1

    # ---- capture panes that keep the fill ----
    # (none by default: source panes keep their 1280x720 size, only the use panes fill)

    def shift_pane(p, sign, why):
        d_local = sign * DELTA / p.parent_sy
        W.f32(p.off + Pane.TY, p.ty + d_local, f'shift {lname}/{p.name} ({why})')
        for an, keys in ty_keys.get(p.name, []):
            for k in keys:
                W.f32(k.off + 4, k.value + d_local, f'shift-anim {lname}/{p.name} {an}')
        notes.append(f'shift {p.name:<26} y {p.ay:7.1f} -> {p.ay + sign * DELTA:7.1f}  ({why})')
        handled.add(p.name)

    no_fill = C.NO_FILL.get(lname, set())
    # ---- fill pass ----
    fill = set()
    grown_src = set()
    for p in root.walk():
        if p is root or p.name in no_fill:
            continue
        edge_parent = p.kind == 'pan1' and any(parent_vert_origin(c) for c in p.children)
        if not (p.kind in ('pic1', 'wnd1', 'scr1') or edge_parent):
            continue
        if not (H0 * 0.95 <= p.ah < H0 * K - 1):
            continue
        animated_ty = p.name in ty_keys
        if abs(p.ay) > 10 and not (animated_ty and p.aw >= lw * 0.95):
            continue
        if parent_vert_origin(p) != 0:
            notes.append(f'WARN fill {p.name}: attached to parent edge, skipped')
            continue
        vo = vert_origin(p)
        uniform = False
        tex = None
        capture = False
        if p.kind == 'pic1':
            mi = struct.unpack_from('<H', buf, p.off + 100)[0]
            tex = mats[mi][1] if mi < len(mats) else ['?']
            capture = any(t.startswith('FBLayout') for t in tex)
            uniform = (bool(tex) and not capture and p.aw >= lw * 0.95 and p.name not in C.NO_UNIFORM.get(lname, ())
                       and p.name not in szh_keys)
        if capture:
            # FBLayout use pane: it must keep the size of its capture source (see curated.CAPTURE_POLICY).
            src = find_capture_source(root, p) if C.CAPTURE_POLICY == 'grow_source' else None
            if src is None or src.name in ty_keys:
                notes.append(f'capture-keep {p.name:<22} {p.w:.0f}x{p.h:.0f} unchanged (source {src.name if src else "none/policy"} kept)')
                continue
            if src.path() not in grown_src:
                if grow_fill(W, lname, src, K, False, szh_keys, ty_keys, notes, 'capture-src'):
                    grown_src.add(src.path())
                    fill.add(src.name)
                    notes.append(f'capture-src {src.name:<22} h {src.h:.0f} -> {src.h * K:.0f}')
                else:
                    continue
        W.f32(p.off + Pane.H, p.h * K, f'fill-h {lname}/{p.name}')
        if vo:
            grow = (p.h * K - p.h) / 2 * p.sy
            W.f32(p.off + Pane.TY, p.ty + (grow if vo == 1 else -grow), f'fill-recentre {lname}/{p.name}')
        if uniform:
            W.f32(p.off + Pane.W, p.w * K, f'fill-w {lname}/{p.name}')
        for an, keys in szh_keys.get(p.name, []):
            for k in keys:
                W.f32(k.off + 4, k.value * K, f'fill-hanim {lname}/{p.name} {an}')
                W.f32(k.off + 8, k.slope * K, f'fill-hanim-slope {lname}/{p.name} {an}')
        if animated_ty:
            W.f32(p.off + Pane.TY, p.ty * K, f'fill-ty {lname}/{p.name}')
            for an, keys in ty_keys[p.name]:
                for k in keys:
                    W.f32(k.off + 4, k.value * K, f'fill-anim {lname}/{p.name} {an}')
                    W.f32(k.off + 8, k.slope * K, f'fill-anim-slope {lname}/{p.name} {an}')
        fill.add(p.name)
        notes.append(f"fill  {p.name:<26} {'uniform' if uniform else 'height '}  tex={tex}")

    # ---- curated force fills: off-centre full-screen backdrops the generic rule skips ----
    ff_done = set()
    for p in root.walk():
        mode = C.FORCE_FILL.get(lname, {}).get(p.name)
        if mode and grow_fill(W, lname, p, K, mode == 'u', szh_keys, ty_keys, notes, 'force-fill'):
            ff_done.add(p.name)
            fill.add(p.name)
            notes.append(f'force-fill {p.name:<26} h {p.h:.0f} -> {p.h * K:.0f}')
    for n in C.FORCE_FILL.get(lname, {}):
        if n not in ff_done:
            notes.append(f'WARN curated force-fill pane {n} not handled')

    # ---- curated proportional growth: screen-proportional decoration (frames/vignettes) that is NOT a full-screen
    # backdrop. Height x K keeps its stock distance from the screen edges in framebuffer pixels. Not required to
    # cover the 4:3 height (verify.py check P4 enforces exactness, centre and the 480 limit).
    pg_done = set()
    for p in root.walk():
        if C.PROP_GROW.get(lname, {}).get(p.name) and grow_fill(W, lname, p, K, False, szh_keys, ty_keys, notes, 'prop-grow'):
            pg_done.add(p.name)
            fill.add(p.name)
            notes.append(f'prop-grow {p.name:<26} h {p.h:.0f} -> {p.h * K:.0f}')
    for n in C.PROP_GROW.get(lname, {}):
        if n not in pg_done:
            notes.append(f'WARN curated prop-grow pane {n} not handled')
    # ---- uniform growth of textured art (aspect kept) and edge-anchored decoration (height += 2*DELTA) ----
    for p in root.walk():
        if p.name in C.UNIFORM_GROW.get(lname, ()):
            if grow_fill(W, lname, p, K, True, szh_keys, ty_keys, notes, 'uniform-grow'):
                fill.add(p.name)
                notes.append(f'uniform-grow {p.name:<24} {p.w:.0f}x{p.h:.0f} -> {p.w * K:.0f}x{p.h * K:.0f}')
        amt = C.EDGE_GROW.get(lname, {}).get(p.name)
        if amt:
            if grow_fill(W, lname, p, (p.h + amt / p.asy) / p.h, False, szh_keys, ty_keys, notes, 'edge-grow'):
                fill.add(p.name)
                notes.append(f'edge-grow {p.name:<24} h {p.h:.0f} -> {p.h + amt / p.asy:.0f}')
    # ---- round 3: wallpaper cut-outs grown uniformly with their TransY scaled (own writer: TransY keys allowed) ----
    for p in root.walk():
        if p.name in C.UNIFORM_TY_GROW.get(lname, ()):
            if vert_origin(p) or p.name in szh_keys:
                notes.append(f'WARN uniform-ty-grow {p.name}: edge origin / SizeH keys, skipped')
                continue
            W.f32(p.off + Pane.H, p.h * K, f'uniform-ty-grow-h {lname}/{p.name}')
            W.f32(p.off + Pane.W, p.w * K, f'uniform-ty-grow-w {lname}/{p.name}')
            notes.append(f'uniform-ty-grow {p.name:<22} {p.w:.0f}x{p.h:.0f} -> {p.w * K:.0f}x{p.h * K:.0f}')
        if p.name in C.LEAF_TY.get(lname, ()):
            scale_ty(W, lname, p, K, ty_keys, notes)
            fill.add(p.name)
    # ---- exact-height windows (match the Sheikah scanning window, 608 + 2*DELTA) ----
    ex = C.EXACT_H.get(lname, {})
    for p in root.walk():
        if p.name in ex and grow_fill(W, lname, p, ex[p.name] / p.h, False, szh_keys, ty_keys, notes, 'exact-h'):
            fill.add(p.name)
            handled.add(p.name)
            notes.append(f'exact-h {p.name:<26} h {p.h:.0f} -> {ex[p.name]:.0f}')
    for n in ex:
        if n not in handled:
            notes.append(f'WARN curated exact-h pane {n} not handled')

    # ---- final-pose shifts of corner-anchored animation targets (mini-map poses) ----
    for p in root.walk():
        dy = C.LAST_KEY_SHIFT.get(lname, {}).get(p.name)
        if dy is not None:
            if not last_key_shift(W, lname, p.name, dy / p.parent_sy, ty_keys, notes):
                notes.append(f'WARN curated last-key pane {p.name}: no multi-key TransY curve')

    # ---- extend edge strips ----
    for p in root.walk():
        if p.name in C.EXTEND_TO_EDGE.get(lname, ()):
            sign = sign_of(p)
            W.f32(p.off + Pane.H, p.h + DELTA / p.asy, f'extend-h {lname}/{p.name}')
            W.f32(p.off + Pane.TY, p.ty + sign * DELTA / 2 / p.parent_sy, f'extend-ty {lname}/{p.name}')
            notes.append(f'extend {p.name}')

    # ---- edge shift pass ----
    if lname in C.NO_SHIFT_LAYOUT or lname.startswith('Pa') and not lname.startswith('Pause') and lname not in C.PA_SHIFT:
        return notes
    force = C.FORCE_SHIFT.get(lname, set())
    skip = C.NO_SHIFT_SUBTREE.get(lname, set())

    def is_edge(c):
        h_eff = 0 if is_nominal_null(c) else c.ah
        return h_eff < EDGE_MAXH and (abs(c.ay) >= THRESH or abs(c.ay_origin) >= THRESH
                                      or (h_eff <= SMALL_H and abs(c.ay) + h_eff / 2 >= THRESH))

    def consider(c, why):
        sign = C.FORCE_SIGN.get(lname, {}).get(c.name) or sign_of(c)
        pivot = c.kind == 'pan1' and why != 'forced' and (c.name in C.PIVOT_SPLIT.get(lname, ()) or any(
            not is_edge(k) and k.name not in fill and k.ty * sign * c.asy <= -0.28 * H0 for k in c.children))
        if pivot:
            notes.append(f'split {c.name:<26} (pivot: child counter-translates to central content)')
            for k in c.children:
                if k.name in skip or k.name in fill:
                    continue
                if is_edge(k):
                    consider(k, 'edge')
            return
        shift_pane(c, sign, why)

    def visit(p):
        kids = [c for c in p.children if c.name not in skip]
        # stacked-column clusters: siblings in the same column touching an edge member move with it
        edge_members = [c for c in kids if c.name not in fill and c.ty != 0 and is_edge(c)]
        cluster = set()
        for em in edge_members:
            for c in kids:
                if c is em or c.name in fill or c.ty == 0 or c in edge_members:
                    continue
                if (abs(em.ax) >= 300 and abs(c.tx - em.tx) <= 1 and c.kind == em.kind and (c.ay > 0) == (em.ay > 0)
                        and abs(c.ay - em.ay) <= 4 * max(c.ah, 40) and c.ah < EDGE_MAXH):
                    cluster.add(c.name)
        for c in kids:
            if c.name in fill:
                if c.kind in CONTAINERS and c.children and c.ty == 0 and c.rot == (0, 0, 0):
                    visit(c)
                continue
            if c.ty != 0 or c.name in force:
                if c.name in force:
                    consider(c, 'forced')
                elif is_edge(c):
                    consider(c, 'edge')
                elif c.name in cluster:
                    consider(c, 'cluster')
                continue
            if c.kind in CONTAINERS and c.children and c.sy == 1 and c.rot == (0, 0, 0):
                visit(c)

    visit(root)
    # forced panes the container walk could not reach (e.g. parented under a pic1): shift directly unless an
    # ancestor was already shifted (that would move them twice)
    anc = {}
    def mark(p, chain):
        anc[p.path()] = chain
        for c in p.children:
            mark(c, chain + [p])
    mark(root, [])
    for p in root.walk():
        if p.name in force and p.name not in handled and p is not root:
            if any(a.name in handled for a in anc[p.path()]):
                continue
            if any(a.ty != 0 or a.sy != 1 or a.rot != (0, 0, 0) for a in anc[p.path()] if a is not root):
                continue
            consider(p, 'forced')
    for n in force:
        if n not in handled:
            notes.append(f'WARN curated pane {n} not handled')
    return notes


STATS = collections.Counter()


def children_pass(lname, raw, ents, buf, W):
    """ROOT_MODE 'children': give every DIRECT child of RootPane the factor ROOT_SY on TransY and ScaleY
    (static values read from the buffer, i.e. AFTER the fill/shift rules ran, plus every TransY / ScaleY
    key and slope of this layout's own animations).  Panes the game code rescales (C.CODE_SCALE_PANES)
    keep their own ScaleY; the factor goes to their children and to their SizeH instead.
    Direct children attached to the root's top/bottom edge (origin bits 6-7) need
    ty' = F*ty + (F-1)*base because the attach base is the (unscaled) root edge."""
    s, e = ents['blyt/' + lname + '.bflyt']
    lw, lh, root = parse_flyt(raw, s)
    notes = []
    F = ROOT_SY
    keys = collections.defaultdict(lambda: collections.defaultdict(list))   # pane -> target -> [(anim, keys)]
    for an in layout_anims(ents, lname):
        for pane, is_mat, tmag, target, ctype, ks in parse_flan(raw, ents[an][0]):
            if is_mat or target not in (1, 7, 9):
                continue
            keys[pane][target].append((an, ctype, ks))

    def rd(off):
        return struct.unpack_from('<f', buf, off)[0]

    _sr = parse_flyt(raw, s)[2]
    annotate(_sr)
    keep_src = {q.off for u, cs in fb_pairs(lname, raw, s, _sr) for q in cs}     # framebuffer-copy sources keep their stock size

    def scale_keys(p, target, factor, why, base=0.0):
        """v' = factor*v + base*(factor-1)  (base = 0 except root-edge-attached direct children)."""
        add = base * (factor - 1.0)
        n = 0
        for an, ctype, ks in keys.get(p.name, {}).get(target, ()):
            if ctype != 2:
                notes.append(f'WARN {why} {p.name}: non-hermite key curve in {an}, skipped')
                STATS['skipped_step_curves'] += 1
                continue
            for k in ks:
                W.f32(k.off + 4, rd(k.off + 4) * factor + add, f'children-{why}-key {lname}/{p.name} {an}')
                W.f32(k.off + 8, rd(k.off + 8) * factor, f'children-{why}-slope {lname}/{p.name} {an}')
                n += 1
        return n

    def apply(p, depth, parent):
        if p.name in C.NO_SCALE_SUBTREES.get(lname, ()):
            notes.append(f'children {p.name}: whole subtree left at stock (NO_SCALE_SUBTREES)')
            STATS['no_scale_subtree'] += 1
            return
        rotated = p.rot != (0.0, 0.0, 0.0)
        # attach to parent's top/bottom edge (only the root edge case has an unscaled base)
        pvo = parent_vert_origin(p)
        base = 0.0
        if depth == 0 and pvo:
            base = p.parent_h / 2 if pvo == 1 else -p.parent_h / 2
            STATS['root_edge_attached'] += 1
        # translation Y (every pane we touch)
        cur_ty = rd(p.off + Pane.TY)
        W.f32(p.off + Pane.TY, F * cur_ty + (F - 1.0) * base, f'children-ty {lname}/{p.name}')
        STATS['ty'] += 1
        STATS['ty_keys'] += scale_keys(p, 1, F, 'ty', base)
        if rotated:
            # position is exact; the shape (and its subtree) cannot take a non-uniform scale through a rotation
            notes.append(f'WARN children {p.name}: rotated {p.rot}, only TransY scaled, shape/children left unsquashed')
            STATS['rotated_pos_only'] += 1
            return
        if p.name in C.CODE_SCALE_PANES:
            # game code rewrites this pane's scale: factor goes on SizeH (keeps attach geometry) and children
            if p.off in keep_src:
                notes.append(f'children capture-source {p.name}: SizeH kept at stock {rd(p.off + Pane.H):.0f}')
                STATS['capture_src_kept'] += 1
            else:
                cur_h = rd(p.off + Pane.H)
                W.f32(p.off + Pane.H, cur_h * F, f'children-sizeh {lname}/{p.name}')
                STATS['sizeh_keys'] += scale_keys(p, 9, F, 'sizeh')
                if p.kind == 'txt1' and lname in C.TXT_FONT_Y_LAYOUTS:
                    for fo, what in ((116, 'fontSizeY'), (124, 'lineSpace')):
                        W.f32(p.off + fo, rd(p.off + fo) * F, f'children-{what} {lname}/{p.name}')
                    notes.append(f'children txt1 {p.name}: fontSizeY and lineSpace x{F}')
            STATS['pushdown'] += 1
            notes.append(f'children pushdown {p.name} ({p.kind}) -> {len(p.children)} children')
            for c in p.children:
                apply(c, depth + 1, p)
        else:
            cur_sy = rd(p.off + Pane.SY)
            W.f32(p.off + Pane.SY, cur_sy * F, f'children-sy {lname}/{p.name}')
            STATS['sy'] += 1
            STATS['sy_keys'] += scale_keys(p, 7, F, 'sy')

    for c in root.children:
        c.parent_h = root.h
        apply(c, 0, root)
    # a pane that was pushed down contributes its children as depth>0: they never use the root base
    return notes


def hud_scale_pass(lname, raw, ents, buf, W):
    """Round 8 prototype: enlarge selected HUD groups by C.HUD_SCALE about a fixed anchor (see curated.HUD_PANES)."""
    spec = C.HUD_PANES.get(lname)
    if not spec or abs(C.HUD_SCALE - 1.0) < 1e-6:
        return []
    S = C.HUD_SCALE
    s, e = ents['blyt/' + lname + '.bflyt']
    lw, lh, root = parse_flyt(raw, s)
    byname = {}
    for p in root.walk():
        byname.setdefault(p.name, p)
    notes = []
    for name, (ax, ay) in spec.items():
        p = byname.get(name)
        if p is None:
            notes.append(f'WARN hud-scale pane {name} not found')
            continue
        rd = lambda off: struct.unpack_from('<f', buf, off)[0]
        for off, a, lab in ((Pane.SX, None, 'sx'), (Pane.SY, None, 'sy')):
            W.f32(p.off + off, rd(p.off + off) * S, f'hud-{lab} {lname}/{name}')
        for off, a, lab in ((Pane.TX, ax, 'tx'), (Pane.TY, ay, 'ty')):
            W.f32(p.off + off, a + S * (rd(p.off + off) - a), f'hud-{lab} {lname}/{name}')
        notes.append(f'hud-scale {name} x{S:.4f} about ({ax:.0f},{ay:.0f})')
    # animation keys of the scaled panes: TransX/TransY about the anchor, ScaleX/ScaleY by S (values already carry the 0.75 pass)
    anchors = {n: a for n, a in spec.items()}
    for an in layout_anims(ents, lname):
        for pane, is_mat, tmag, target, ctype, ks in parse_flan(raw, ents[an][0]):
            if is_mat or pane not in anchors or target not in (0, 1, 6, 7):
                continue
            if ctype != 2:
                notes.append(f'WARN hud-scale {pane}: non-hermite key curve in {an}, skipped')
                continue
            ax, ay = anchors[pane]
            for k in ks:
                v = struct.unpack_from('<f', buf, k.off + 4)[0]
                sl = struct.unpack_from('<f', buf, k.off + 8)[0]
                if target in (0, 1):
                    a0 = ax if target == 0 else ay
                    v = a0 + S * (v - a0)
                else:
                    v = v * S
                W.f32(k.off + 4, v, f'hud-key{target} {lname}/{pane} {an}')
                W.f32(k.off + 8, sl * S, f'hud-slope{target} {lname}/{pane} {an}')
    return notes


def capture_apply_pass(lname, raw, ents, buf, W):
    spec, hs = C.CAPTURE_APPLY_INVARIANT.get(lname, ()), C.SRC_H_SCALE.get(lname, ())
    if not (spec or hs) or C.ROOT_MODE != 'children':
        return []
    s, e = ents['blyt/' + lname + '.bflyt']
    root = parse_flyt(raw, s)[2]
    annotate(root)
    notes = []
    rd = lambda off: struct.unpack_from('<f', buf, off)[0]
    keys = collections.defaultdict(list)
    for an in layout_anims(ents, lname):
        for pane, is_mat, tmag, target, ctype, ks in parse_flan(raw, ents[an][0]):
            if not is_mat:
                keys[(pane, target)].append((an, ks))
    for p in root.walk():
        if p.name in spec:
            if any(pn == p.name for (pn, t) in keys):
                notes.append(f'WARN capture-apply {p.name}: has animation keys, skipped')
                continue
            n = n_scaled_chain(p.parent)
            W.f32(p.off + Pane.H, p.h * ROOT_SY, f'capture-apply-h {lname}/{p.name}')
            W.f32(p.off + Pane.SY, p.sy / ROOT_SY ** n, f'capture-apply-sy {lname}/{p.name}')
            notes.append(f'capture-apply {p.name}: h {p.h:.0f} -> {p.h * ROOT_SY:.1f}, ScaleY {p.sy:g} -> {p.sy / ROOT_SY ** n:.4f} (n={n})')
        if p.name in hs:
            W.f32(p.off + Pane.H, p.h * ROOT_SY, f'src-h-scale {lname}/{p.name}')
            for an, ks in keys.get((p.name, 9), ()):
                for k in ks:
                    W.f32(k.off + 4, rd(k.off + 4) * ROOT_SY, f'src-h-scale-key {lname}/{p.name} {an}')
                    if k.slope is not None:
                        W.f32(k.off + 8, rd(k.off + 8) * ROOT_SY, f'src-h-scale-slope {lname}/{p.name} {an}')
            notes.append(f'src-h-scale {p.name}: SizeH and SizeH keys x{ROOT_SY}')
    return notes


def sizeh_retarget_pass(lname, raw, ents, buf, W):
    spec = C.SIZEH_RETARGET.get(lname)
    if not spec:
        return []
    s, e = ents['blyt/' + lname + '.bflyt']
    root = parse_flyt(raw, s)[2]
    notes = []
    rd = lambda off: struct.unpack_from('<f', buf, off)[0]
    for p in root.walk():
        if p.name in spec and abs(rd(p.off + Pane.H) - H0) < 0.5:
            W.f32(p.off + Pane.H, spec[p.name], f'sizeh-retarget {lname}/{p.name}')
            notes.append(f'sizeh-retarget {p.name:<22} static h {H0:.0f} -> {spec[p.name]:.0f}')
    for an in layout_anims(ents, lname):
        for pane, is_mat, tmag, target, ctype, ks in parse_flan(raw, ents[an][0]):
            if is_mat or target != 9 or pane not in spec:
                continue
            for k in ks:
                v = rd(k.off + 4)
                if abs(v - H0) < 0.5:
                    W.f32(k.off + 4, spec[pane], f'sizeh-retarget-key {lname}/{pane} {an}')
                    if k.slope is not None:
                        W.f32(k.off + 8, rd(k.off + 8) * spec[pane] / v, f'sizeh-retarget-slope {lname}/{pane} {an}')
                    notes.append(f'sizeh-retarget key {pane} {an} {v:.0f} -> {spec[pane]:.0f}')
    return notes


def host_sy_pass(lname, raw, ents, buf, W):
    """Stamina-wheel hosts: ScaleY x factor (see curated.HOST_SY_FACTOR). Static value read from the buffer."""
    want = C.HOST_SY_FACTOR.get(lname)
    if not want:
        return []
    s, e = ents['blyt/' + lname + '.bflyt']
    lw, lh, root = parse_flyt(raw, s)
    notes = []
    for p in root.walk():
        if p.name in want:
            cur = struct.unpack_from('<f', buf, p.off + Pane.SY)[0]
            W.f32(p.off + Pane.SY, cur * want[p.name], f'host-sy {lname}/{p.name}')
            notes.append(f'host-sy {p.name:<24} ScaleY {cur:.3f} -> {cur * want[p.name]:.3f}')
    return notes


def build_layout(lname, raw, ents, buf, W, top, referenced):
    if lname in C.CURSOR_ROOT_KEEP and lname not in referenced:
        return ['kept byte-identical to stock (CURSOR_ROOT_KEEP)']
    notes = _build_layout(lname, raw, ents, buf, W, top, referenced)
    if C.ROOT_MODE != 'children' or lname in referenced or lname in C.ROOT_SKIP:
        if lname not in referenced:
            notes = notes + sizeh_retarget_pass(lname, raw, ents, buf, W)   # root scale 0.75 clips the map scissor too
        return notes
    s, e = ents['blyt/' + lname + '.bflyt']
    lw, lh, root = parse_flyt(raw, s)
    if (lw, lh) != (1280.0, 720.0):
        return notes
    notes = notes + children_pass(lname, raw, ents, buf, W)
    notes = notes + host_sy_pass(lname, raw, ents, buf, W)
    notes = notes + capture_pass(lname, raw, ents, buf, W)
    notes = notes + capture_apply_pass(lname, raw, ents, buf, W)
    notes = notes + hud_scale_pass(lname, raw, ents, buf, W)
    return notes + sizeh_retarget_pass(lname, raw, ents, buf, W)



def pack_sarc(orig, new_files):
    """Rebuild a SARC with the same entry order/hashes; new_files {name: bytes} replace entries.
    Alignment of every entry is preserved as the lowest-set-bit of its original relative offset (capped)."""
    e = '<' if orig[6:8] == LE_BOM else '>'
    hlen = struct.unpack_from(e + 'H', orig, 4)[0]
    data_off = struct.unpack_from(e + 'I', orig, 0x0C)[0]
    cnt = struct.unpack_from(e + 'H', orig, hlen + 6)[0]
    nodes = [list(struct.unpack_from(e + 'IIII', orig, hlen + 12 + 16 * i)) for i in range(cnt)]
    ents = sarc_entries(orig)
    by_off = {}
    for nm, (s, en) in ents.items():
        by_off[s - data_off] = nm
    order = sorted(by_off)
    out = bytearray()
    new_nodes = {}
    for rel in order:
        nm = by_off[rel]
        s, en = ents[nm]
        blob = new_files.get(nm, orig[s:en])
        align = min(rel & -rel, 0x2000) if rel else 0x2000
        if rel == 0 and nm in ents:
            align = 0x2000 if data_off % 0x2000 == 0 else 0x1000
        # keep the first file at relative 0; later files keep their original alignment
        pad = (-len(out)) % max(align, 1)
        out += b'\0' * pad
        new_nodes[nm] = (len(out), len(out) + len(blob))
        out += blob
    # patch node table
    head = bytearray(orig[:data_off])
    for i in range(cnt):
        h, attr, s, en = nodes[i]
        name_off = (attr & 0xFFFF) * 4
        nm = None
        for n2, (so, eo) in ents.items():
            if so - data_off == s:
                nm = n2; break
        ns, ne = new_nodes[nm]
        struct.pack_into(e + 'II', head, hlen + 12 + 16 * i + 8, ns, ne)
    total = len(head) + len(out)
    struct.pack_into(e + 'I', head, 8, total)
    return bytes(head) + bytes(out)


def main():
    os.makedirs(os.path.join(OUT, 'Layout'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'Pack'), exist_ok=True)
    jobs = [  # (output rel path, source file, inner entry or None)
        ('Layout/BootUp.sblarc', 'Layout/BootUp.sblarc', None),
        ('Layout/Horse.sblarc', 'Layout/Horse.sblarc', None),
        ('Pack/Title.pack', 'Pack/Title.pack', 'Layout/Title.sblarc'),
        ('Pack/Bootup.pack', 'Pack/Bootup.pack', 'Layout/Common.sblarc'),
    ]
    loaded = {}
    referenced = set()
    for outrel, src, inner in jobs:
        raw, ents = load_archive(os.path.join(SRC, src), inner)
        loaded[outrel] = (raw, ents)
        for n in ents:
            if n.endswith('.bflyt'):
                referenced |= part_refs(raw, ents[n][0])
    report = {}
    for outrel, src, inner in jobs:
        raw, ents = loaded[outrel]
        buf = bytearray(raw)
        W = Writer(buf)
        names = sorted(n[5:-6] for n in ents if n.endswith('.bflyt'))
        # referenced only counts parts of THIS archive's layouts being used elsewhere
        notes_all = {}
        for ln in names:
            notes = build_layout(ln, raw, ents, buf, W, True, referenced)
            if notes:
                notes_all[ln] = notes
        assert len(buf) == len(raw)
        report[outrel] = {'writes': [(o, a, b, w) for o, a, b, w in W.log], 'notes': notes_all}
        print(f'== {outrel}: {len(W.log)} float writes in {len(notes_all)} layouts')
        if not W.log:
            continue
        comp = yaz0_compress(bytes(buf)) if COMPRESS else None
        if comp is None:
            continue
        assert yaz0_decompress(comp) == bytes(buf)
        if inner:
            pack_raw = open(os.path.join(SRC, src), 'rb').read()
            newpack = pack_sarc(pack_raw, {inner: comp})
            # round-trip check on the container
            old_e = sarc_entries(pack_raw); new_e = sarc_entries(newpack)
            assert set(old_e) == set(new_e)
            for n in old_e:
                if n != inner:
                    assert pack_raw[old_e[n][0]:old_e[n][1]] == newpack[new_e[n][0]:new_e[n][1]], n
            assert newpack[new_e[inner][0]:new_e[inner][1]] == comp
            open(os.path.join(OUT, outrel), 'wb').write(newpack)
        else:
            open(os.path.join(OUT, outrel), 'wb').write(comp)
    report['_meta'] = {'root_mode': C.ROOT_MODE, 'children_stats': dict(STATS)}
    print('root mode:', C.ROOT_MODE, dict(STATS))
    json.dump(report, open(os.path.join(OUT, 'build_report.json'), 'w'), indent=1)
    for k, v in report.items():
        if k == '_meta':
            continue
        for ln, notes in v['notes'].items():
            print(f'-- {k}: {ln}')
            for n in notes:
                print('     ' + n)


main()
