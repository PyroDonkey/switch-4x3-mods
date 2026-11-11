"""Verify a build against the ORIGINAL layouts (independent of build.py's decisions).

usage: python -I verify.py <dump_romfs_dir> <out_dir>
"""
import sys, os, struct, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import *
import curated as C

SRC, OUT = sys.argv[1], sys.argv[2]
rep = json.load(open(os.path.join(OUT, 'build_report.json')))
MODE = rep.get('_meta', {}).get('root_mode', 'root')      # mode the build used
JOBS = [('Layout/BootUp.sblarc', None), ('Layout/Horse.sblarc', None),
        ('Pack/Title.pack', 'Layout/Title.sblarc'), ('Pack/Bootup.pack', 'Layout/Common.sblarc')]
fails, warns = [], []
if MODE != C.ROOT_MODE:
    fails.append(f'build used ROOT_MODE={MODE!r} but verify runs with {C.ROOT_MODE!r} (set BOTW_ROOT_MODE the same)')
CSTAT = collections.Counter()


def top_eligible(ln, lw, lh):
    """Layouts the build treats as top-level and scales (same condition as build.py)."""
    return (lw, lh) == (1280.0, 720.0) and ln not in C.ROOT_SKIP and ln not in C.CURSOR_ROOT_KEEP


def tl(p):
    """children mode (old tree): True when build.children_pass visits pane p (direct child of the root, or child of a
    visited, unrotated, code-rescaled pane)."""
    if p.parent is None or p.name in C.NO_SCALE_NAMES:
        return False
    if p.parent.parent is None:
        return True
    q = p.parent
    return q.name in C.CODE_SCALE_PANES and q.rot == (0.0, 0.0, 0.0) and tl(q)


def kind(p):
    """'scale' | 'pd' (code-rescaled: factor goes to children/SizeH) | None (untouched), for an OLD-tree pane."""
    if not tl(p) or p.rot != (0.0, 0.0, 0.0):
        return None
    return 'pd' if p.name in C.CODE_SCALE_PANES else 'scale'


def norm_children(rt):
    """children mode: annotate() values of the new tree are ROOT_SY x the root-mode equivalent in Y; undo that
    so every geometric check below stays in root-local units exactly as for the root mode."""
    for q in rt.walk():
        if q is rt:
            continue
        q.ay *= K; q.ay_origin *= K; q.ah *= K; q.asy *= K
        if q.parent is not rt:
            q.parent_sy *= K
cont_stats = {}
seen_lk = set()
ALL_REFS = set()
for _o, _i in JOBS:
    _r, _e = load_archive(os.path.join(SRC, _o), _i)
    for _n in _e:
        if _n.endswith('.bflyt'):
            ALL_REFS |= part_refs(_r, _e[_n][0])


def _norm_tree(ln, rt, lw, lh):
    """children mode: bring the new tree's annotate() values back to root-local units (same helper as the other checks)."""
    if MODE == 'children' and top_eligible(ln, lw, lh) and ln not in ALL_REFS:
        norm_children(rt)


def _ty_root_local(a_old, v):
    """children mode: a visited pane's TransY (static or key) carries the factor ROOT_SY (+ the root-edge base term);
    undo it so shifts are compared in the old units. a_old: the pane in the OLD tree."""
    if MODE == 'children' and tl(a_old):
        base = 0.0
        pvo = parent_vert_origin(a_old) if a_old.parent.parent is None else 0
        if pvo:
            base = a_old.parent.h / 2 if pvo == 1 else -a_old.parent.h / 2
        return (v - (ROOT_SY - 1) * base) / ROOT_SY
    return v


def F(m): fails.append(m)
def Wn(m): warns.append(m)


# ---- Sheikah frame helpers ----
def xrange_(p):
    h = p.origin & 3                      # 0 centre, 1 left (anchor = left edge), 2 right (anchor = right edge)
    return (p.ax, p.ax + p.aw) if h == 1 else (p.ax - p.aw, p.ax) if h == 2 else (p.ax - p.aw / 2, p.ax + p.aw / 2)


def yrange_(p):
    return (p.ay - p.ah / 2, p.ay + p.ah / 2)


def ygap(a, b):
    (alo, ahi), (blo, bhi) = yrange_(a), yrange_(b)
    return max(blo - ahi, alo - bhi)


def xoverlap(a, b):
    (alo, ahi), (blo, bhi) = xrange_(a), xrange_(b)
    return min(ahi, bhi) - max(alo, blo)


def continuity(tag, po_list, pn_list):
    """Frame continuity: every pair of drawn leaf panes that touched (vertical gap <= 1.5 px) or overlapped while
    sharing horizontal extent in the ORIGINAL must still touch/overlap in the new tree. Returns number of pairs."""
    leaf = [(a, b) for a, b in zip(po_list, pn_list)
            if a.kind in ('pic1', 'txt1', 'wnd1', 'prt1') and a.ah >= 1 and a.aw >= 1
            and not (a.kind == 'prt1' and a.ah > 300) and a.name not in getattr(C, 'CONT_EXEMPT', ())]   # big prt1 boxes are layout-sized placeholders (Pa_Deco_00)
    n = 0
    for i in range(len(leaf)):
        for j in range(i + 1, len(leaf)):
            a, b = leaf[i][0], leaf[j][0]
            if xoverlap(a, b) <= 2 or ygap(a, b) > 1.5:
                continue
            n += 1
            a2, b2 = leaf[i][1], leaf[j][1]
            if ygap(a2, b2) > 1.5 or xoverlap(a2, b2) <= 2:
                F(f'{tag}: frame continuity broken {a.name} / {b.name} '
                  f'(gap {ygap(a, b):.1f} -> {ygap(a2, b2):.1f})')
    return n


assert abs(C.WINDOW_H - (608 + 2 * DELTA)) < 1e-6, 'WINDOW_H must be the 608 window grown by 2*DELTA'


# 0. game-files policy (docs/game-files-policy.md): every archive in the output must differ from the original, and no
#    archive the build left unchanged may be present (a stale copy from an older build would ship an original file).
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    if not rep[outrel]['writes']:
        F(f'{outrel}: present in the output but the build changed nothing in it (stale or original archive)')
        continue
    if load_archive(n_path, inner)[0] == load_archive(os.path.join(SRC, outrel), inner)[0]:
        F(f'{outrel}: identical to the original archive (must not be shipped)')
for root_dir, _, fnames in os.walk(OUT):
    for fn in fnames:
        rel = os.path.relpath(os.path.join(root_dir, fn), OUT).replace(os.sep, '/')
        if rel not in {o for o, _ in JOBS} and rel != 'build_report.json':
            F(f'{rel}: not a build output (only {sorted(o for o, _ in JOBS)} may be in the output dir)')

for outrel, inner in JOBS:
    if not rep[outrel]['writes']:
        continue
    o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        F(f'{outrel}: output missing'); continue
    n_raw, n_ents = load_archive(n_path, inner)
    # 1. structure
    if len(o_raw) != len(n_raw): F(f'{outrel}: decompressed size differs'); continue
    if {k: (v[0], v[1]) for k, v in o_ents.items()} != {k: (v[0], v[1]) for k, v in n_ents.items()}:
        F(f'{outrel}: SARC table differs')
    # 2. changed bytes == logged writes
    logged = {}
    for off, a, b, what in rep[outrel]['writes']:
        logged[off] = b                       # last write wins
    changed = set()
    diff = [i for i in range(len(o_raw)) if o_raw[i] != n_raw[i]] if len(o_raw) < 4_000_000 else None
    if diff is None:
        import itertools
        diff = []
        # chunked compare
        step = 1 << 20
        for st in range(0, len(o_raw), step):
            a, b = o_raw[st:st + step], n_raw[st:st + step]
            if a != b:
                diff += [st + i for i in range(len(a)) if a[i] != b[i]]
    covered = set()
    for off in logged:
        for i in range(4):
            covered.add(off + i)
    stray = [i for i in diff if i not in covered]
    if stray: F(f'{outrel}: {len(stray)} changed bytes outside logged writes (first {stray[0]:#x})')
    for off, val in logged.items():
        got = struct.unpack_from('<f', n_raw, off)[0]
        if abs(got - val) > 1e-4 * max(1, abs(val)):
            F(f'{outrel}: logged write at {off:#x} not present ({got} != {val})')
    # 3. re-parse everything
    fl = sorted(n for n in n_ents if n.endswith('.bflyt'))
    referenced = ALL_REFS
    for n in n_ents:
        if n.endswith('.bflan'):
            try: parse_flan(n_raw, n_ents[n][0])
            except Exception as ex: F(f'{outrel}: {n} fails to parse: {ex}')
    for n in fl:
        ln = n[5:-6]
        so, _ = o_ents[n]; sn, _ = n_ents[n]
        try:
            lw, lh, ro = parse_flyt(o_raw, so); _, _, rn = parse_flyt(n_raw, sn)
        except Exception as ex:
            F(f'{outrel}: {n} fails to parse: {ex}'); continue
        # 4. parts keep root (1, 1)
        if ln in referenced and (rn.sx, rn.sy) != (ro.sx, ro.sy):
            F(f'{ln}: part root changed')
        if MODE == 'children' and (rn.sx, rn.sy) != (ro.sx, ro.sy):
            F(f'{ln}: children mode must leave RootPane scale untouched, got ({rn.sx},{rn.sy})')
        if (MODE == 'root' and ln not in referenced and ln not in ('Fade_00', 'Thanks_00')
                and ln not in __import__('curated').ROOT_SKIP and ln not in C.CURSOR_ROOT_KEEP and (lw, lh) == (1280.0, 720.0)):
            if abs(rn.sy - ro.sy * ROOT_SY) > 1e-6: F(f'{ln}: top-level root scale {rn.sy}')
        if ln in referenced:
            # 4b. curated part fills / shifts: geometry re-derived from the original
            fills = C.PART_FILL.get(ln, {})
            shifts = C.PART_SHIFT.get(ln, set())
            exact = C.PART_EXACT_H.get(ln, {})
            shift_y = C.PART_SHIFT_Y.get(ln, {})
            ty_scale = C.PART_TY_SCALE.get(ln, {})
            grow_h = C.PART_GROW_H.get(ln, {})
            if fills or shifts or exact or shift_y or ty_scale or grow_h:
                for an in layout_anims(n_ents, ln):
                    for pane, im, tm, tg, ct, keys in parse_flan(n_raw, n_ents[an][0]):
                        if pane == 'RootPane' and not im:
                            F(f'{ln}: {an} animates RootPane')
                annotate(ro); annotate(rn)
                po = {p.path(): p for p in ro.walk()}; pn = {p.path(): p for p in rn.walk()}
                if set(po) != set(pn):
                    F(f'{ln}: part pane set differs'); continue
                no_ = {}; nn_ = {}
                for p in po.values(): no_.setdefault(p.name, p)
                for p in pn.values(): nn_.setdefault(p.name, p)
                for pname, mode in fills.items():
                    a, b = no_.get(pname), nn_.get(pname)
                    if a is None or b is None:
                        F(f'{ln}: curated part pane {pname} missing'); continue
                    factor = (C.PART_FILL_H.get(ln, 2 * HALF_VIS) / a.h) if mode in 'HU' else K
                    if abs(b.h - a.h * factor) > 0.5:
                        F(f'{ln}/{pname}: height {b.h:.1f}, expected {a.h * factor:.1f}')
                    if mode in 'uU' and abs(b.w - a.w * factor) > 0.5:
                        F(f'{ln}/{pname}: width {b.w:.1f}, expected {a.w * factor:.1f}')
                    if abs(b.ay - a.ay) > 1.5:
                        F(f'{ln}/{pname}: fill moved the centre (ay {a.ay:.1f} -> {b.ay:.1f})')
                    if b.ah < 2 * HALF_VIS - 1:
                        F(f'{ln}/{pname}: grown to {b.ah:.0f}, short of {2 * HALF_VIS:.0f}')
                for pname in sorted(shifts):
                    a, b = no_.get(pname), nn_.get(pname)
                    if a is None or b is None:
                        F(f'{ln}: curated part pane {pname} missing'); continue
                    sign = 1 if a.ay > 0 else -1
                    want = sign * DELTA / a.parent_sy
                    if abs((b.ty - a.ty) - want) > 0.5:
                        F(f'{ln}/{pname}: shift {b.ty - a.ty:.1f}, expected {want:.1f}')
                    pairs = [(a, b)]
                    for ca, cb in pairs:
                        if abs(ca.ay) + ca.ah / 2 <= H0 / 2 + 1 and abs(cb.ay) + cb.ah / 2 > HALF_VIS + 1:
                            F(f'{ln}/{pname}/{ca.name}: now extends to {abs(cb.ay) + cb.ah / 2:.0f} (> {HALF_VIS:.0f})')
                        pairs.extend(zip(ca.children, cb.children))
                # exact-height windows
                for pname, hh in exact.items():
                    a, b = no_.get(pname), nn_.get(pname)
                    if a is None or b is None:
                        F(f'{ln}: curated exact pane {pname} missing'); continue
                    if abs(b.h - hh) > 0.5: F(f'{ln}/{pname}: exact height {b.h:.1f}, expected {hh:.1f}')
                    if abs(hh - C.WINDOW_H) > 1e-6: F(f'{ln}/{pname}: exact height {hh} is not the window height')
                    if abs(b.ay - a.ay) > 1.5: F(f'{ln}/{pname}: exact-height pane moved its centre')
                # round 10: fixed height growth (stock + dh, centre kept, width/scale/translation X untouched)
                for pname, dh in grow_h.items():
                    a, b = no_.get(pname), nn_.get(pname)
                    if a is None or b is None:
                        F(f'{ln}: curated grow-h pane {pname} missing'); continue
                    if abs(b.h - (a.h + dh)) > 0.5: F(f'{ln}/{pname}: height {b.h:.1f}, expected {a.h + dh:.1f}')
                    if abs(b.w - a.w) > 0.01 or abs(b.sy - a.sy) > 1e-6 or abs(b.tx - a.tx) > 0.01:
                        F(f'{ln}/{pname}: grow-h changed width/scale/x')
                    if abs(b.ay - a.ay) > 0.5: F(f'{ln}/{pname}: grow-h moved the centre (ay {a.ay:.1f} -> {b.ay:.1f})')
                    if abs(b.w - a.w) > 0.5: F(f'{ln}/{pname}: exact-height pane changed width')
                # explicit signed shifts: static ty, and ONLY the final pose of multi-key TransY curves
                oa = {}; na = {}
                for an in layout_anims(n_ents, ln):
                    for pane, im, tm, tg, ct, keys in parse_flan(o_raw, o_ents[an][0]):
                        if not im and tg == 1: oa[(an, pane)] = keys
                    for pane, im, tm, tg, ct, keys in parse_flan(n_raw, n_ents[an][0]):
                        if not im and tg == 1: na[(an, pane)] = keys
                for pname, dy in shift_y.items():
                    a, b = no_.get(pname), nn_.get(pname)
                    if a is None or b is None:
                        F(f'{ln}: curated shift-y pane {pname} missing'); continue
                    if abs((b.ty - a.ty) - dy) > 0.5: F(f'{ln}/{pname}: shift-y {b.ty - a.ty:.1f}, expected {dy:.1f}')
                    for (an, pn_), ko in oa.items():
                        if pn_ != pname: continue
                        kn = na[(an, pn_)]
                        for idx, (x, y) in enumerate(zip(ko, kn)):
                            last = idx == len(ko) - 1 and len(ko) >= 2
                            want = x.value + dy if last else x.value
                            if abs(y.value - want) > 0.01:
                                F(f'{ln}/{pname}: {an} key {idx} value {y.value:.2f}, expected {want:.2f}')
                for pname, fac in ty_scale.items():
                    a, b = no_.get(pname), nn_.get(pname)
                    if a is None or b is None:
                        F(f'{ln}: curated ty-scale pane {pname} missing'); continue
                    if abs(b.ty - a.ty * fac) > 0.01: F(f'{ln}/{pname}: ty {b.ty:.2f}, expected {a.ty * fac:.2f}')
                    for (an, pn_), ko in oa.items():
                        if pn_ != pname: continue
                        for x, y in zip(ko, na[(an, pn_)]):
                            if abs(y.value - x.value * fac) > 0.01:
                                F(f'{ln}/{pname}: {an} key value {y.value:.2f}, expected {x.value * fac:.2f}')
                # frame continuity inside the part (touching / overlapping pairs must stay so)
                # (PaAppMapSensor_00 mixes two groups that overlap by coincidence - popup shadow vs pill effect
                #  lines - and PaDLCTipsBefore_00's buttons leave the art by design: both excluded)
                if ln in ('PaSeekPadScanningLine_00', 'PaCameraPointer_00', 'PaAppSystemWindow_00',
                          'PaAppMapSensorSetting_00'):
                    cont_stats[ln] = continuity(ln, list(ro.walk()), list(rn.walk()))
            continue
        annotate(ro); annotate(rn)
        po = {p.path(): p for p in ro.walk()}; pn = {p.path(): p for p in rn.walk()}
        if set(po) != set(pn): F(f'{ln}: pane set differs'); continue
        elig = top_eligible(ln, lw, lh)
        # 0. scale integrity (both modes): ScaleX never changes anywhere; ScaleY changes only where the mode says
        for path, a in po.items():
            b = pn[path]
            hf = C.HUD_SCALE if (abs(C.HUD_SCALE - 1.0) > 1e-6 and a.name in C.HUD_PANES.get(ln, {})) else 1.0
            gf = C.HOST_SY_FACTOR.get(ln, {}).get(a.name, 1.0)      # stamina-wheel host compensation (check 21)
            if abs(b.sx - a.sx * hf) > (1e-6 if hf != 1.0 else 0):
                F(f'{ln}/{a.name}: ScaleX changed {a.sx} -> {b.sx}')
            if a is ro:
                continue
            kd = kind(a) if (MODE == 'children' and elig) else None
            if MODE == 'children' and elig and tl(a):
                if kd is None:
                    if b.sy != a.sy: F(f'{ln}/{a.name}: rotated pane must stay unscaled')
                    CSTAT['rotated_visited'] += 1
                elif kd == 'pd':
                    if b.sy != a.sy: F(f'{ln}/{a.name}: code-rescaled pane ScaleY changed {a.sy} -> {b.sy}')
                    CSTAT['pushdown'] += 1
                else:
                    if abs(b.sy - a.sy * ROOT_SY * hf * gf) > 1e-6: F(f'{ln}/{a.name}: ScaleY {b.sy}, expected {a.sy * ROOT_SY * hf * gf}')
                    CSTAT['scaled'] += 1
            elif gf != 1.0:
                if abs(b.sy - a.sy * gf) > 1e-6: F(f'{ln}/{a.name}: stamina host ScaleY {b.sy}, expected {a.sy * gf}')
            elif b.sy != a.sy and a.name not in C.CAPTURE_APPLY_INVARIANT.get(ln, ()):   # check 16 owns these
                F(f'{ln}/{a.name}: ScaleY changed {a.sy} -> {b.sy} (only visited panes may change, and only in children mode)')
        if MODE == 'children' and elig:
            # 10. direct-child animation keys follow the static value; ScaleY keys scale by ROOT_SY
            for an in layout_anims(n_ents, ln):
                olds = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(o_raw, o_ents[an][0]) if not im_}
                news = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(n_raw, n_ents[an][0]) if not im_}
                for (pn_, tg_), ko in olds.items():
                    if tg_ not in (1, 7):
                        continue
                    a = next((q for q in ro.walk() if q.name == pn_ and tl(q)), None)
                    if a is None:
                        continue
                    if tg_ == 1 and pn_ in C.LAST_KEY_SHIFT.get(ln, {}):
                        continue    # final pose moved on purpose (checked by the last-key check below)
                    b = pn[a.path()]
                    kn = news[(pn_, tg_)]
                    if tg_ == 7:
                        want = ROOT_SY if kind(a) == 'scale' else 1.0
                        for x, y in zip(ko, kn):
                            if x.slope is None: continue
                            if abs(y.value - x.value * want) > 1e-4 * max(1, abs(x.value)) or abs(y.slope - x.slope * want) > 1e-4 * max(1, abs(x.slope)):
                                F(f'{ln}/{pn_}: ScaleY keys in {an} not x{want}'); break
                        CSTAT['sy_key_curves'] += 1
                    else:
                        base = 0.0
                        pvo = parent_vert_origin(a) if a.parent is ro else 0
                        if pvo: base = ro.h / 2 if pvo == 1 else -ro.h / 2
                        sh = (b.ty - (ROOT_SY - 1) * base) / ROOT_SY - a.ty
                        okay_add = okay_mul = True
                        for x, y in zip(ko, kn):
                            eq = (y.value - (ROOT_SY - 1) * base) / ROOT_SY
                            if abs(eq - x.value - sh) > 0.02: okay_add = False
                            if abs(eq - x.value * K) > 0.02 * max(1, abs(x.value)): okay_mul = False
                            if x.slope is not None and abs(y.slope / ROOT_SY - x.slope) > 1e-3 * max(1, abs(x.slope)) and abs(y.slope / ROOT_SY - x.slope * K) > 1e-3 * max(1, abs(x.slope)):
                                okay_add = okay_mul = False
                        if not (okay_add or okay_mul):
                            F(f'{ln}/{pn_}: TransY keys in {an} inconsistent with the static value after the x{ROOT_SY} factor')
                        CSTAT['ty_key_curves'] += 1
            norm_children(rn)
        # animation checks
        for an in layout_anims(n_ents, ln):
            for pane, im, tm, tg, ct, keys in parse_flan(n_raw, n_ents[an][0]):
                if pane == 'RootPane' and not im: F(f'{ln}: {an} animates RootPane')
        for path, a in po.items():
            b = pn[path]
            if a is ro: continue
            vis_o = abs(a.ay) - a.ah / 2 < H0 / 2 and a.ah > 0
            # 5. nothing that was on screen ends past the new visible edge
            #    (FORCE_FILL panes are reviewed exceptions: they intentionally overshoot one edge)
            if (vis_o and a.name not in C.OVERSHOOT_OK.get(ln, ())
                    and abs(b.ay) + b.ah / 2 > HALF_VIS + 1 and abs(a.ay) + a.ah / 2 <= H0 / 2 + 1):
                F(f'{ln}/{a.name}: now extends to {abs(b.ay) + b.ah / 2:.0f} (> {HALF_VIS:.0f})')
            # 6. filled panes cover the visible area and are centred
            if b.ah > a.ah + 0.5 and b.kind in ('pic1', 'wnd1', 'scr1', 'pan1'):
                if b.ah < 2 * HALF_VIS - 1 and abs(b.ay) < 5 and a.name not in C.PROP_GROW.get(ln, {}) and a.name not in C.EXACT_H.get(ln, ()):
                    Wn(f'{ln}/{a.name}: grown to {b.ah:.0f}, short of {2 * HALF_VIS:.0f}')
                if abs(b.ay) > 1 and abs(a.ay) <= 1:
                    Wn(f'{ln}/{a.name}: grown but off-centre ({b.ay:.0f})')
            # 8. full-width element that touched the old edge now touches the new one (or was a deliberate keep)
            touched = abs(abs(a.ay) + a.ah / 2 - H0 / 2) <= 1.5 and a.aw >= 0.95 * lw and a.ah < H0 * 0.9
            if touched and abs(abs(b.ay) + b.ah / 2 - HALF_VIS) > 1.5:
                Wn(f'{ln}/{a.name}: full-width strip touched the old edge, now at {abs(b.ay) + b.ah / 2:.0f}')
            # 7. fill pane with a size animation on the grown axis: keys must be scaled by exactly K
            if b.ah > a.ah + 0.5 and a.name not in C.SIZEH_RETARGET.get(ln, {}):   # retargeted panes: check 15
                for an in layout_anims(n_ents, ln):
                    olds = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(o_raw, o_ents[an][0]) if not im_}
                    news = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(n_raw, n_ents[an][0]) if not im_}
                    ko = olds.get((a.name, 9))
                    if ko is None:
                        continue
                    kn = news[(a.name, 9)]
                    want = K * (ROOT_SY if (MODE == 'children' and elig and kind(a) == 'pd') else 1.0)
                    for x, y in zip(ko, kn):
                        if abs(y.value - x.value * want) > 1e-3 * max(1, abs(x.value)) or (x.slope is not None and abs(y.slope - x.slope * want) > 1e-3 * max(1, abs(x.slope))):
                            F(f'{ln}/{a.name}: height keys in {an} not scaled by {want:.4f}')
                            break
        # 6a. top-level exact-height windows and final-pose shifts
        for pname, hh in C.EXACT_H.get(ln, {}).items():
            a = next((p for p in po.values() if p.name == pname), None)
            b = next((p for p in pn.values() if p.name == pname), None)
            if a is None or b is None: F(f'{ln}: exact-height pane {pname} missing'); continue
            # root mode: the pane's own SizeH; children mode: effective (root-local) height, since the factor may sit on ScaleY
            hh_now, hh_want = (b.h, hh) if MODE == 'root' else (b.ah, hh * a.ah / a.h)
            if abs(hh_now - hh_want) > 0.5: F(f'{ln}/{pname}: exact height {hh_now:.1f}, expected {hh_want:.1f}')
            if abs(hh - C.WINDOW_H) > 1e-6: F(f'{ln}/{pname}: exact height {hh} is not the window height')
            if abs(b.ay - a.ay) > 1.5 or abs(b.w - a.w) > 0.5: F(f'{ln}/{pname}: exact-height pane moved / changed width')
        lk = C.LAST_KEY_SHIFT.get(ln, {})
        if lk:
            for an in layout_anims(n_ents, ln):
                olds = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(o_raw, o_ents[an][0]) if not im_}
                news = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(n_raw, n_ents[an][0]) if not im_}
                for pname, dy in lk.items():
                    ko = olds.get((pname, 1))
                    if ko is None or len(ko) < 2: continue
                    seen_lk.add((ln, pname))
                    a_lk = next((p for p in po.values() if p.name == pname), None)
                    for idx, (x, y) in enumerate(zip(ko, news[(pname, 1)])):
                        want = x.value + (dy if idx == len(ko) - 1 else 0)
                        yv = _ty_root_local(a_lk, y.value) if (a_lk is not None and elig) else y.value   # children mode: undo x ROOT_SY
                        if abs(yv - want) > 0.01:
                            F(f'{ln}/{pname}: {an} TransY key {idx} {yv:.2f}, expected {want:.2f}')
        # 6b. curated force fills: grown by exactly K around their centre, covering the 4:3 height
        for pname in C.FORCE_FILL.get(ln, ()):
            a = next((p for p in po.values() if p.name == pname), None)
            b = next((p for p in pn.values() if p.name == pname), None)
            if a is None or b is None:
                F(f'{ln}: force-fill pane {pname} missing'); continue
            if MODE == 'root' and abs(b.h - a.h * K) > 0.5:
                F(f'{ln}/{pname}: force-fill height {b.h:.1f}, expected {a.h * K:.1f}')
            if abs(b.ah - a.ah * K) > 0.5:
                F(f'{ln}/{pname}: force-fill effective height {b.ah:.1f}, expected {a.ah * K:.1f}')
            if abs(b.ay - a.ay) > 1.5:
                F(f'{ln}/{pname}: force-fill moved the centre (ay {a.ay:.1f} -> {b.ay:.1f})')
            if b.ah < 2 * HALF_VIS - 1:
                F(f'{ln}/{pname}: force-fill grown to {b.ah:.0f}, short of {2 * HALF_VIS:.0f}')

# 9. curated parts: every prt1 use site must keep the geometry the part edit assumed.
#    Scale must stay (1, 1); shifted parts must sit at the layout origin; filled panes must cover
#    the 4:3 height at every use site (combined centre = prt1 origin + part-local pane centre;
#    X is not checked: the mod never changes horizontal geometry).
part_roots = {}
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    n_raw, n_ents = load_archive(n_path, inner)
    for part in set(C.PART_FILL) | set(C.PART_SHIFT) | set(C.PART_EXACT_H) | set(C.PART_SHIFT_Y) | set(C.PART_TY_SCALE):
        nm = 'blyt/' + part + '.bflyt'
        if nm in n_ents and part not in part_roots:
            _, _, rt = parse_flyt(n_raw, n_ents[nm][0])
            annotate(rt)
            part_roots[part] = {p.name: p for p in rt.walk()}
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    n_raw, n_ents = load_archive(n_path, inner)
    for n in n_ents:
        if not n.endswith('.bflyt'):
            continue
        _, _, rt = parse_flyt(n_raw, n_ents[n][0])
        secs = [p for mag, p, s in flyt_tags(n_raw, n_ents[n][0], {b'prt1'})]
        panes = [q for q in rt.walk() if q.kind == 'prt1']
        if len(secs) != len(panes):
            Wn(f'{n}: prt1 section/pane count mismatch, use-site check skipped')
            continue
        annotate(rt)
        if MODE == 'children' and top_eligible(n[5:-6], *parse_flyt(n_raw, n_ents[n][0])[:2]) and n[5:-6] not in ALL_REFS:
            norm_children(rt)
        for p, q in zip(secs, panes):
            part = prt1_name(n_raw, p)
            if part not in part_roots:
                continue
            if abs(q.asx - 1) > 1e-4 or abs(q.asy - 1) > 1e-4:
                F(f'{part}: used by {n[5:-6]}/{q.name} at scale ({q.asx:.3f},{q.asy:.3f}); part edit assumes (1, 1)')
            if part in C.PART_SHIFT and (abs(q.ax) > 1 or abs(q.ay_origin) > 1):
                F(f'{part}: shifted part used by {n[5:-6]}/{q.name} off-origin ({q.ax:.1f},{q.ay_origin:.1f})')
            for pname in C.PART_SHIFT_Y.get(part, ()):
                pp = part_roots[part].get(pname)
                if pp is None: continue
                cy = q.ay_origin + pp.ay
                if abs(cy) + pp.ah / 2 > HALF_VIS + 1:
                    F(f'{part}/{pname}: after shift-y it extends to {abs(cy) + pp.ah / 2:.0f} in {n[5:-6]}')
            for pname in C.PART_FILL.get(part, ()):
                pp = part_roots[part].get(pname)
                if pp is None:
                    continue
                cy = q.ay_origin + pp.ay
                short = HALF_VIS - (pp.ah / 2 - abs(cy))
                if short > 64:
                    F(f'{part}/{pname}: {short:.0f}px short at one edge in {n[5:-6]}')
                elif short > 24:
                    Wn(f'{part}/{pname}: {short:.0f}px short at one edge in {n[5:-6]}')

# 10. HUD review extensions (sec/hud): (a) recurse through prt1 parts: nothing on screen in the original may end past the
#     new visible edge once the part's own (shifted) contents are placed under the final prt1 position;
#     (b) every TransY key of a shifted pane moved by exactly the pane's shift (independent of build.py);
#     (c) HUD layouts: unshifted bottom/top blocks whose far edge was within 40 of the old edge are reported.
HUD_LAYOUTS = ['MainScreen_00', 'MainScreenMS_00', 'MainScreen3D_00', 'MainDungeon_00', 'MainHorse_00', 'MainHardMode_00',
               'Rupee_00', 'KeyNum_00', 'KologNum_00', 'MamoNum_00', 'Time_00', 'AkashiNum_00', 'EnergyMeterDLC_00',
               'WolfLinkHeartGauge_00', 'MainScreenHeartIchigekiDLC_00', 'DLCSinJuAkashiNum_00']
_o_raw, _o_ents = load_archive(os.path.join(SRC, 'Pack/Bootup.pack'), 'Layout/Common.sblarc')
_n_raw, _n_ents = load_archive(os.path.join(OUT, 'Pack/Bootup.pack'), 'Layout/Common.sblarc')


def _prts(raw, s):
    return {p: prt1_name(raw, p) for m, p, sz in flyt_tags(raw, s, {b'prt1'})}


def _extents(ln, bo, bn, path, out, depth=0):
    nm = 'blyt/' + ln + '.bflyt'
    if nm not in _o_ents or depth > 4:
        return
    _lw, _lh, a_root = parse_flyt(_o_raw, _o_ents[nm][0]); _, _, b_root = parse_flyt(_n_raw, _n_ents[nm][0])
    annotate(a_root); annotate(b_root)
    if depth == 0:
        _norm_tree(ln, b_root, _lw, _lh)
    pr = _prts(_o_raw, _o_ents[nm][0])
    for a, b in zip(a_root.walk(), b_root.walk()):
        if a is a_root:
            continue
        if a.kind == 'prt1':
            _extents(pr.get(a.off), bo + a.ay_origin, bn + b.ay_origin, path + '/' + a.name, out, depth + 1)
        elif a.kind in ('pic1', 'txt1', 'wnd1') and a.ah > 0:
            out.append((abs(bo + a.ay) + a.ah / 2, abs(bn + b.ay) + b.ah / 2, path + '/' + a.name, a.name))


for _ln in HUD_LAYOUTS:
    if 'blyt/' + _ln + '.bflyt' not in _o_ents:
        continue
    _out = []
    _extents(_ln, 0.0, 0.0, _ln, _out)
    for o_, n_, p_, nm_ in _out:
        if n_ > HALF_VIS + 1 and o_ <= H0 / 2 + 1 and nm_ not in C.OVERSHOOT_OK.get(_ln, ()) and 'ColdBG' not in nm_:
            F(f'{p_}: far edge {o_:.0f} -> {n_:.0f} (> {HALF_VIS:.0f}) through part contents')
        if o_ <= H0 / 2 + 1 and 0 < n_ - o_ < 119 and 'Scanning' not in p_:
            Wn(f'{p_}: moved by {n_ - o_:.0f}, not the full {DELTA:.0f} (partial shift / fill)')
    # (b) TransY key consistency
    nm = 'blyt/' + _ln + '.bflyt'
    _lw, _lh, ra = parse_flyt(_o_raw, _o_ents[nm][0]); _, _, rb = parse_flyt(_n_raw, _n_ents[nm][0])
    _apo = {}
    _dty_a = {}
    dty = {}
    for a, b in zip(ra.walk(), rb.walk()):
        if a is ra:
            continue
        _apo.setdefault(a.name, a)
        d_ = _ty_root_local(a, b.ty) - a.ty
        if abs(d_) > 1e-3:
            dty[a.name] = d_
    for an in layout_anims(_o_ents, _ln):
        ko = parse_flan(_o_raw, _o_ents[an][0]); kn = parse_flan(_n_raw, _n_ents[an][0])
        for (p_, im_, tm_, tg_, ct_, ks_), (_, _, _, _, _, kk_) in zip(ko, kn):
            if im_ or tg_ != 1 or p_ not in dty or p_ in C.OVERSHOOT_OK.get(_ln, ()):
                continue
            for x_, y_ in zip(ks_, kk_):
                yv_ = _ty_root_local(_apo[p_], y_.value) if p_ in _apo else y_.value
                if abs((yv_ - x_.value) - dty[p_]) > 0.5 and abs(yv_ - x_.value * K) > 0.5:
                    F(f'{_ln}/{p_}: TransY key in {an} moved {yv_ - x_.value:.1f}, pane moved {dty[p_]:.1f}')
                    break
    # (c) unshifted blocks near the old edge
    annotate(ra); annotate(rb)
    _norm_tree(_ln, rb, _lw, _lh)
    for a, b in zip(ra.walk(), rb.walk()):
        if a is ra or a.kind not in ('pic1', 'txt1', 'wnd1', 'prt1') or a.ah <= 0 or a.ah >= EDGE_MAXH:
            continue
        if abs(b.ay - a.ay) < 1e-3 and abs(a.ay) + a.ah / 2 >= THRESH - 40 and abs(a.ay) + a.ah / 2 <= H0 / 2 and abs(a.ay) > 100:
            Wn(f'{_ln}/{a.name}: unshifted, far edge {abs(a.ay) + a.ah / 2:.0f} (old edge 360, threshold {THRESH:.0f})')


# ---- P. pause-menu / pivot / proportional-growth checks (additive) ---------------------------------------
PAUSE_SET = lambda ln: ln.startswith('PauseMenu') or ln in ('MessageTipsPauseMenu_00', 'SeekPadMenuBG_00')
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
    n_raw, n_ents = load_archive(n_path, inner)
    for n in sorted(o_ents):
        if not n.endswith('.bflyt') or n not in n_ents:
            continue
        ln = n[5:-6]
        lw, lh, ro = parse_flyt(o_raw, o_ents[n][0]); _, _, rn = parse_flyt(n_raw, n_ents[n][0])
        if ln in ALL_REFS or (lw, lh) != (1280.0, 720.0):
            continue
        annotate(ro); annotate(rn)
        _norm_tree(ln, rn, lw, lh)
        po = list(ro.walk()); pn = list(rn.walk())
        if len(po) != len(pn):
            continue
        by_o = {p.name: p for p in po}; by_n = {p.name: p for p in pn}
        # P1. nothing is moved TOWARDS the centre by the edge pass (a child counter-translating out of a shifted
        #     container: the container moved outward, the child ended up closer to the centre than it was).
        #     Hard failure for the pause set, warning elsewhere (other sections own those layouts).
        for a, b in zip(po, pn):
            if a is ro or abs(b.ah - a.ah) > 0.5 or a.name in C.FORCE_SIGN.get(ln, {}):   # FORCE_SIGN: direction chosen on purpose (hud)
                continue
            dy = b.ay - a.ay
            if abs(a.ay) > 5 and abs(dy) > 0.5 and a.ay * dy < 0:
                msg = f'{ln}/{a.name}: moved towards the centre (y {a.ay:.0f} -> {b.ay:.0f}); container shifted outward but child counter-translates'
                (F if PAUSE_SET(ln) else Wn)(msg)
        # P2. curated NO_SHIFT_SUBTREE / PIVOT_SPLIT contracts
        for nm in C.NO_SHIFT_SUBTREE.get(ln, ()):
            r0 = by_o.get(nm)
            if r0 is None:
                F(f'{ln}: NO_SHIFT_SUBTREE pane {nm} missing'); continue
            for a in r0.walk():
                b = by_n[a.name]
                if abs(b.ay - a.ay) > 0.5 or abs(b.ah - a.ah) > 0.5:
                    F(f'{ln}/{a.name}: inside NO_SHIFT_SUBTREE {nm} but moved ({a.ay:.0f} -> {b.ay:.0f})')
        for nm in C.PIVOT_SPLIT.get(ln, ()):
            a, b = by_o.get(nm), by_n.get(nm)
            if a is None:
                F(f'{ln}: PIVOT_SPLIT pane {nm} missing'); continue
            if abs(_ty_root_local(a, b.ty) - a.ty) > 1e-3:
                F(f'{ln}/{nm}: PIVOT_SPLIT container was shifted whole')
            for ka, kb in zip(a.children, b.children):
                want = (1 if ka.ay > 0 else -1) * DELTA
                if abs(ka.ay) >= THRESH and abs((kb.ay - ka.ay) - want) > 0.5:
                    F(f'{ln}/{ka.name}: PIVOT_SPLIT child moved {kb.ay - ka.ay:.1f}, expected {want:.1f}')
        # P4. proportional growth: height exactly xK, width/centre untouched, inside the 4:3 height
        for nm in C.PROP_GROW.get(ln, ()):
            a, b = by_o.get(nm), by_n.get(nm)
            if a is None:
                F(f'{ln}: PROP_GROW pane {nm} missing'); continue
            if abs(b.h - a.h * K) > 0.5: F(f'{ln}/{nm}: prop-grow height {b.h:.1f}, expected {a.h * K:.1f}')
            if abs(b.w - a.w) > 0.5: F(f'{ln}/{nm}: prop-grow changed width')
            if abs(b.ay - a.ay) > 1.5: F(f'{ln}/{nm}: prop-grow moved the centre')
            if abs(b.ay) + b.ah / 2 > HALF_VIS + 1 and nm not in C.OVERSHOOT_OK.get(ln, ()):
                F(f'{ln}/{nm}: prop-grow extends to {abs(b.ay) + b.ah / 2:.0f} (> {HALF_VIS:.0f})')
        # P5. pause set: every pane except the reviewed FORCE_FILL backdrops ends inside the 4:3 height
        if PAUSE_SET(ln):
            for b in pn:
                if b is rn or b.name in C.OVERSHOOT_OK.get(ln, ()) or b.kind == 'pan1' and (b.w, b.h) == (30, 40):
                    continue
                if abs(b.ay) + b.ah / 2 > HALF_VIS + 1:
                    F(f'{ln}/{b.name}: pause pane ends at {abs(b.ay) + b.ah / 2:.0f} (> {HALF_VIS:.0f})')

# 10. screen-capture source/use consistency (FBLayout textures). A SOURCE is a pan1 whose name contains
#     'Capture'; a USE is a pic1 with an FBLayout* texture. Whatever the game does with the copied rectangle
#     (scaled layout units or raw local pixels), a use pane drawn at another size than its source distorts
#     and blurs the capture, and a pair that sat on the same rect must keep moving together.
#   a. a use pane's w/h may change only together with an identical stock-equal-rect source (grow_source policy)
#   b. a source whose size changed needs every stock-equal-rect use pane to end at exactly the same size
#   c. stock-equal-rect source/use pairs keep the same net vertical displacement
n_pairs = 0
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
    n_raw, n_ents = load_archive(n_path, inner)
    for n in sorted(o_ents):
        if not n.endswith('.bflyt') or n not in n_ents:
            continue
        ln = n[5:-6]
        lw, lh, ro = parse_flyt(o_raw, o_ents[n][0]); _, _, rn = parse_flyt(n_raw, n_ents[n][0])
        annotate(ro); annotate(rn)
        _norm_tree(ln, rn, lw, lh)
        mats = materials(o_raw, o_ents[n][0])
        pn_ = {p.path(): p for p in rn.walk()}
        srcs = [p for p in ro.walk() if p.kind == 'pan1' and 'Capture' in p.name and 'Pos' not in p.name]
        uses = []
        for p in ro.walk():
            if p.kind != 'pic1':
                continue
            mi = struct.unpack_from('<H', o_raw, p.off + 100)[0]
            tex = mats[mi][1] if mi < len(mats) else []
            if any(t.startswith('FBLayout') for t in tex):
                uses.append(p)
        # children mode: SizeH / ScaleY carry the factor, so sizes are compared as effective (root-local, normalised) sizes
        sw = (lambda p: p.w) if MODE == 'root' else (lambda p: p.aw)
        sh = (lambda p: p.h) if MODE == 'root' else (lambda p: p.ah)
        def same_rect(a, b):
            return (a is not b and abs(a.ax - b.ax) <= 2 and abs(a.ay - b.ay) <= 2 and abs(a.aw - b.aw) <= 2
                    and abs(a.ah - b.ah) <= 2 and abs(a.w - b.w) <= 2 and abs(a.h - b.h) <= 2)
        for u in ([x for x in uses if x.name not in C.SIZEH_RETARGET.get(ln, {})] if MODE == 'root' else []):   # children mode: check 11 (fullframe policy) replaces this
            un = pn_[u.path()]
            size_changed = abs(sw(un) - sw(u)) > 0.5 or abs(sh(un) - sh(u)) > 0.5
            mates = [s_ for s_ in srcs if same_rect(s_, u)]
            if size_changed:
                ok = any(abs(sw(pn_[m.path()]) - sw(un)) <= 0.5 and abs(sh(pn_[m.path()]) - sh(un)) <= 0.5 for m in mates)
                if not ok:
                    F(f'{ln}/{u.name}: capture use pane resized {sw(u):.0f}x{sh(u):.0f} -> {sw(un):.0f}x{sh(un):.0f} '
                      f'without an identically resized source (stretched/blurred capture)')
            for m in mates:
                mn = pn_[m.path()]
                n_pairs += 1
                if (abs(sw(mn) - sw(m)) > 0.5 or abs(sh(mn) - sh(m)) > 0.5) and (
                        abs(sw(mn) - sw(un)) > 0.5 or abs(sh(mn) - sh(un)) > 0.5):
                    F(f'{ln}/{m.name}->{u.name}: source resized to {sw(mn):.0f}x{sh(mn):.0f}, use pane is {sw(un):.0f}x{sh(un):.0f}')
                if abs((mn.ay - m.ay) - (un.ay - u.ay)) > 1.5:
                    F(f'{ln}/{m.name}->{u.name}: source moved {mn.ay - m.ay:+.0f}, use pane {un.ay - u.ay:+.0f} '
                      f'(pair sat on the same rect in the original)')
print(f'capture source/use pairs checked: {n_pairs}')

for ln_, pn_ in {(l, p_) for l, d in C.LAST_KEY_SHIFT.items() for p_ in d} - seen_lk:
    F(f'{ln_}/{pn_}: curated last-key pane had no multi-key TransY curve to check')

# 11. fullframe capture geometry (children mode). Independent of build.py: pairs are re-derived from the STOCK
#     layout. Engine model (see curated.CAPTURE_POLICY): the copied rect has the source pane's LOCAL size at its
#     global centre; the use pane draws the whole texture, so it is undistorted only when its projected height
#     (local h x product of the scales in its chain; panes the game code rescales by name count as 1) equals the
#     stock projected height AND the source keeps its stock local size.
def _proj_chain(p):
    f = 1.0
    while p is not None and p.parent is not None:
        f *= 1.0 if p.name in C.CODE_SCALE_PANES else p.sy
        p = p.parent
    return f


def _fb_uses(raw, s, root):
    mats = materials(raw, s)
    for u in root.walk():
        if u.kind != 'pic1':
            continue
        mi = struct.unpack_from('<H', raw, u.off + 100)[0]
        tex = mats[mi][1] if mi < len(mats) else []
        if any(t.startswith('FBLayout') for t in tex):
            yield u


n_fb = 0
if MODE == 'children' and C.CAPTURE_POLICY == 'fullframe':
    for outrel, inner in JOBS:
        n_path = os.path.join(OUT, outrel)
        if not os.path.exists(n_path):
            continue
        o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
        n_raw, n_ents = load_archive(n_path, inner)
        for n in sorted(o_ents):
            if not n.endswith('.bflyt'):
                continue
            ln = n[5:-6]
            lw, lh, ro = parse_flyt(o_raw, o_ents[n][0])
            _, _, rn = parse_flyt(n_raw, n_ents[n][0])
            lo, lnw = list(ro.walk()), list(rn.walk())
            if len(lo) != len(lnw):
                continue
            annotate(ro)
            # part capture panes: projected size at every host use site
            for part, pnames in C.PART_CAPTURE_USE.items():
                if (part in ALL_REFS and ln != part and top_eligible(ln, lw, lh) and ln not in ALL_REFS):
                    nm = 'blyt/' + part + '.bflyt'
                    if nm not in o_ents:
                        continue
                    _, _, po = parse_flyt(o_raw, o_ents[nm][0]); _, _, pn = parse_flyt(n_raw, n_ents[nm][0])
                    pmo = {q.name: q for q in po.walk()}; pmn = {q.name: q for q in pn.walk()}
                    secs = [p for mag, p, z in flyt_tags(o_raw, o_ents[n][0], {b'prt1'})]
                    prts = [q for q in lo if q.kind == 'prt1']
                    prtn = [q for q in lnw if q.kind == 'prt1']
                    for sp, qo, qn in zip(secs, prts, prtn):
                        if prt1_name(o_raw, sp) != part:
                            continue
                        for pname in pnames:
                            a, b = pmo.get(pname), pmn.get(pname)
                            if a is None or b is None:
                                continue
                            n_fb += 1
                            ps, pb = a.h * _proj_chain(qo), b.h * _proj_chain(qn)
                            if abs(ps - pb) > 1.0:
                                F(f'{ln}/{qo.name}->{part}/{pname}: part capture use projects {pb:.1f}, stock {ps:.1f}')
            if not top_eligible(ln, lw, lh) or ln in ALL_REFS or ln in C.CAPTURE_SKIP_LAYOUTS or ln in C.CURSOR_ROOT_KEEP:
                continue
            nmap = {id(a): b for a, b in zip(lo, lnw)}
            for u in _fb_uses(o_raw, o_ents[n][0], ro):
                if u.name.startswith(C.CAPTURE_SKIP_PREFIX):
                    continue
                cands = [q for q in lo if q.kind == 'pan1' and 'Capture' in q.name and 'Pos' not in q.name
                         and abs(q.ax - u.ax) <= 2 and abs(q.ay - u.ay) <= 2 and abs(q.aw - u.aw) <= 2
                         and abs(q.ah - u.ah) <= 2 and abs(q.w - u.w) <= 2 and abs(q.h - u.h) <= 2]
                if not cands or any((b'CaptureBGColor' in q.usd and q.name not in C.CAPTURE_BG_FULLFRAME.get(ln, ()))
                                    or b'CaptureApplyScale' in q.usd for q in cands):
                    continue
                n_fb += 1
                un = nmap[id(u)]
                ps, pb = u.h * _proj_chain(u), un.h * _proj_chain(un)
                if abs(ps - pb) > 1.0:
                    F(f'{ln}/{u.name}: capture use projects {pb:.1f}, stock {ps:.1f} (source rect {cands[0].h:.0f}) '
                      f'-> distorted / partial capture')
                if abs(un.w - u.w) > 0.5:
                    F(f'{ln}/{u.name}: capture use width changed {u.w:.0f} -> {un.w:.0f}')
                if u.h >= 0.95 * H0 and abs(u.ay) < 10 and pb < H0 - 1.0:
                    F(f'{ln}/{u.name}: full-frame capture use projects only {pb:.1f} of {H0:.0f} (bars)')
                for q in cands:
                    qn = nmap[id(q)]
                    if abs(qn.h - q.h) > 0.5 or abs(qn.w - q.w) > 0.5:
                        F(f'{ln}/{q.name}: capture source size changed {q.w:.0f}x{q.h:.0f} -> {qn.w:.0f}x{qn.h:.0f}')
print(f'check 11: {n_fb} framebuffer-capture use panes checked against the stock projected size')

# 12. selector layouts in CURSOR_ROOT_KEEP stay byte-identical to stock (layout, animations).
n_cur = 0
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
    n_raw, n_ents = load_archive(n_path, inner)
    for ln in C.CURSOR_ROOT_KEEP:
        for nm in o_ents:
            if nm == 'blyt/' + ln + '.bflyt' or nm.startswith('anim/' + ln + '_'):
                n_cur += 1
                if nm not in n_ents or o_raw[o_ents[nm][0]:o_ents[nm][1]] != n_raw[n_ents[nm][0]:n_ents[nm][1]]:
                    F(f'{nm}: must be byte-identical to stock (CURSOR_ROOT_KEEP) but differs')
print(f'check 12: {n_cur} CURSOR_ROOT_KEEP files compared byte-for-byte')


# 13. round-2 curated geometry (independent of build.py): EDGE_GROW, UNIFORM_GROW (+ Title wallpaper coverage),
#     Fade_00 corner items, tip text font squash. Values are compared in root-local units (children mode normalised).
n13 = 0
SKY = {'P_MainV_00', 'P_MainV_02', 'P_MainVE_00', 'P_MainVOE_00'}                 # must cover the whole 4:3 height
FORE = {'P_MainV_01', 'P_MainV_03', 'P_MainVE_01', 'P_MainVOE_01'}                # foregrounds: bottom must reach the edge
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
    n_raw, n_ents = load_archive(n_path, inner)
    for n in sorted(o_ents):
        if not n.endswith('.bflyt'):
            continue
        ln = n[5:-6]
        want = (set(C.EDGE_GROW.get(ln, ())) | set(C.UNIFORM_GROW.get(ln, ())) | set(C.UNIFORM_TY_GROW.get(ln, ()))
                | ({'T_DummyText_00'} if ln == 'Fade_00' else set()))
        if not want and ln not in C.TXT_FONT_Y_LAYOUTS:
            continue
        lw, lh, ro = parse_flyt(o_raw, o_ents[n][0]); _, _, rn = parse_flyt(n_raw, n_ents[n][0])
        annotate(ro); annotate(rn)
        _norm_tree(ln, rn, lw, lh)
        po = {p.path(): p for p in ro.walk()}
        pn = {p.path(): p for p in rn.walk()}
        for path, a in po.items():
            b = pn[path]
            if a.name in C.EDGE_GROW.get(ln, {}):
                n13 += 1
                amt = C.EDGE_GROW[ln][a.name]
                if abs(b.ah - (a.ah + amt)) > 0.6:
                    F(f'{ln}/{a.name}: edge-grow height {b.ah:.1f}, expected {a.ah + amt:.1f}')
                if abs(b.ay - a.ay) > 1.0:
                    F(f'{ln}/{a.name}: edge-grow moved the centre {a.ay:.1f} -> {b.ay:.1f}')
                top_o, bot_o = a.ay + a.ah / 2, a.ay - a.ah / 2
                top_n, bot_n = b.ay + b.ah / 2, b.ay - b.ah / 2
                if abs((top_n - top_o) - amt / 2) > 1.0 or abs((bot_o - bot_n) - amt / 2) > 1.0:
                    F(f'{ln}/{a.name}: edge distances changed by ({top_n - top_o:.1f}, {bot_o - bot_n:.1f}), expected {amt / 2:.0f} each')
            if a.name in C.UNIFORM_GROW.get(ln, ()) or a.name in C.UNIFORM_TY_GROW.get(ln, ()):
                n13 += 1
                if abs(b.ah - a.ah * K) > 0.6 or abs(b.aw - a.aw * K) > 0.6:
                    F(f'{ln}/{a.name}: uniform grow {b.aw:.0f}x{b.ah:.0f}, expected {a.aw * K:.0f}x{a.ah * K:.0f}')
                want_ay = a.ay * K if a.name in C.LEAF_TY.get(ln, ()) else a.ay
                if abs(b.ay - want_ay) > 1.0:
                    F(f'{ln}/{a.name}: uniform grow centre {b.ay:.1f}, expected {want_ay:.1f}')
                if ln == 'Title_00':
                    top_n, bot_n = b.ay + b.ah / 2, b.ay - b.ah / 2
                    if a.name in SKY and (top_n < HALF_VIS - 1 or bot_n > -HALF_VIS + 1):
                        F(f'{ln}/{a.name}: wallpaper sky covers y [{bot_n:.0f}, {top_n:.0f}], not the full +-{HALF_VIS:.0f}')
                    if a.name in FORE and bot_n > -HALF_VIS + 1:
                        F(f'{ln}/{a.name}: wallpaper foreground ends at y {bot_n:.0f}, above the bottom edge')
            if ln == 'Fade_00' and a.name == 'T_DummyText_00':
                n13 += 1
                if abs((b.ay - a.ay) - DELTA) > 1.0:
                    F(f'{ln}/{a.name}: top-left text moved {b.ay - a.ay:.1f}, expected +{DELTA:.0f}')
            if ln in C.TXT_FONT_Y_LAYOUTS and a.kind == 'txt1' and a.name in C.CODE_SCALE_PANES and tl(a) and MODE == 'children':
                n13 += 1
                fo = [struct.unpack_from('<f', o_raw, a.off + k)[0] for k in (112, 116, 124)]
                fn = [struct.unpack_from('<f', n_raw, b.off + k)[0] for k in (112, 116, 124)]
                if abs(fn[0] - fo[0]) > 1e-4 or abs(fn[1] - fo[1] * ROOT_SY) > 1e-3 or abs(fn[2] - fo[2] * ROOT_SY) > 1e-3:
                    F(f'{ln}/{a.name}: tip text font (X, Y, lineSpace) {fn} vs stock {fo}: expected Y and lineSpace x{ROOT_SY}')
print(f'check 13: {n13} round-2 curated panes checked')

# 14. parts whose edge panes were shifted for round 2 (PaFadeBar_00): shifted -DELTA / +DELTA in local units
for part in ('PaFadeBar_00',):
    for outrel, inner in JOBS:
        n_path = os.path.join(OUT, outrel)
        if not os.path.exists(n_path):
            continue
        o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
        n_raw, n_ents = load_archive(n_path, inner)
        nm = 'blyt/' + part + '.bflyt'
        if nm not in o_ents:
            continue
        _, _, po = parse_flyt(o_raw, o_ents[nm][0]); _, _, pn = parse_flyt(n_raw, n_ents[nm][0])
        annotate(po); annotate(pn)
        mo = {q.name: q for q in po.walk()}; mn = {q.name: q for q in pn.walk()}
        for pname in C.PART_SHIFT[part]:
            if pname not in mo:
                F(f'{part}/{pname}: missing'); continue
            d = mn[pname].ay - mo[pname].ay
            if abs(abs(d) - DELTA) > 1.0 or (d > 0) != (mo[pname].ay > 0):
                F(f'{part}/{pname}: moved {d:.1f}, expected {DELTA:.0f} towards its own edge')

# 15. round 3: Title wallpaper (TransY keys x K, live/capture twins identical), glow source/uses, Sheikah map scissor.
n15 = 0
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
    n_raw, n_ents = load_archive(n_path, inner)
    for ln in sorted(set(C.LEAF_TY) | set(C.CAPTURE_BG_FULLFRAME) | set(C.SIZEH_RETARGET)):
        nm = 'blyt/' + ln + '.bflyt'
        if nm not in o_ents:
            continue
        lw, lh, ro = parse_flyt(o_raw, o_ents[nm][0]); _, _, rn = parse_flyt(n_raw, n_ents[nm][0])
        po = {p.name: p for p in ro.walk()}; pn = {p.name: p for p in rn.walk()}
        # TransY keys of leaf panes are exactly x K (static value too); TransX untouched
        for an in layout_anims(n_ents, ln):
            olds = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(o_raw, o_ents[an][0]) if not im_}
            news = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(n_raw, n_ents[an][0]) if not im_}
            for (pname, tgt), ko in olds.items():
                kn = news[(pname, tgt)]
                if pname in C.LEAF_TY.get(ln, ()) and tgt in (0, 1):
                    n15 += 1
                    want = K if tgt == 1 else 1.0
                    for x, y in zip(ko, kn):
                        if abs(y.value - x.value * want) > 1e-3 * max(1, abs(x.value)) or (
                                x.slope is not None and abs(y.slope - x.slope * want) > 1e-3 * max(1, abs(x.slope))):
                            F(f'{ln}/{pname}: {an} target {tgt} keys not x{want:.3f}')
                            break
                if ln in C.SIZEH_RETARGET and pname in C.SIZEH_RETARGET[ln] and tgt == 9:
                    n15 += 1
                    for i, (x, y) in enumerate(zip(ko, kn)):
                        want_v = C.SIZEH_RETARGET[ln][pname] if abs(x.value - H0) < 0.5 else x.value
                        if abs(y.value - want_v) > 0.01:
                            F(f'{ln}/{pname}: {an} SizeH key {i} {y.value:.1f}, expected {want_v:.1f}')
        for pname in C.LEAF_TY.get(ln, ()):
            a, b = po.get(pname), pn.get(pname)
            if a is None or b is None:
                F(f'{ln}/{pname}: leaf-ty pane missing'); continue
            n15 += 1
            if abs(b.ty - a.ty * K) > 0.01:
                F(f'{ln}/{pname}: static ty {b.ty:.2f}, expected {a.ty * K:.2f}')
            if abs(b.tx - a.tx) > 0.01:
                F(f'{ln}/{pname}: tx changed ({a.tx:.1f} -> {b.tx:.1f}); only ty may change')
        if ln == 'Title_00' and MODE == 'children':
            for x, y in C.TITLE_TWINS:
                a, b = pn.get(x), pn.get(y)
                n15 += 1
                if a is None or b is None or abs(a.h - b.h) > 0.01 or abs(a.w - b.w) > 0.01 or abs(a.ty - b.ty) > 0.01 or abs(a.tx - b.tx) > 0.01:
                    F(f'{ln}: live pane {x} and capture twin {y} differ in size/position')
            src = pn.get('N_Capture_00'); so = po.get('N_Capture_00')
            n15 += 1
            if src is None or abs(src.h - so.h) > 0.01 or abs(src.w - so.w) > 0.01:
                F(f'{ln}/N_Capture_00: glow source must keep its stock local size {so.w:.0f}x{so.h:.0f}')
            for p in src.children:
                n15 += 1
                if abs(p.sy - 0.75) > 1e-4:
                    F(f'{ln}/N_Capture_00/{p.name}: glow child must carry the 0.75 pushdown, sy={p.sy}')
            for name, q in pn.items():
                if name.startswith('P_Light_') or (name.startswith('P_Blur_') and name != 'P_Blur_08'):
                    n15 += 1
                    if abs(q.h - 960.0) > 0.01:
                        F(f'{ln}/{name}: glow use local height {q.h:.0f}, expected 960 (projects 720 under the 0.75 chain)')
        for pname, tgt in C.SIZEH_RETARGET.get(ln, {}).items():
            a, b = po.get(pname), pn.get(pname)
            n15 += 1
            if a is None or b is None or abs(b.h - tgt) > 0.01:
                F(f'{ln}/{pname}: static SizeH {None if b is None else b.h}, expected {tgt}')
        if ln == 'AppMap_00':
            # round 10: each map capture source has the same size as its use (static and every SizeH key), as in stock
            for sname, uname in C.MAP_CAPTURE_PAIRS.items():
                s_, u_ = pn.get(sname), pn.get(uname)
                n15 += 1
                if s_ is None or u_ is None or abs(s_.h - u_.h) > 0.01 or abs(s_.w - u_.w) > 0.01:
                    F(f'{ln}/{sname}: map capture source size differs from its use {uname}')
            for an in layout_anims(n_ents, ln):
                kk = {p_: ks for p_, im_, tm_, t_, ct_, ks in parse_flan(n_raw, n_ents[an][0]) if not im_ and t_ == 9}
                for sname, uname in C.MAP_CAPTURE_PAIRS.items():
                    if (sname in kk) != (uname in kk):
                        F(f'{ln}/{sname}: SizeH animated on only one of source/use {uname} in {an}')
                    elif sname in kk and [round(k.value, 3) for k in kk[sname]] != [round(k.value, 3) for k in kk[uname]]:
                        F(f'{ln}/{sname}: SizeH keys differ from its use {uname} in {an}')
print(f'check 15: {n15} round-3 curated items checked')

# 16. CaptureApplyScale sources must give the same copy rect with the engine flag on AND off (see curated.CAPTURE_APPLY_INVARIANT),
#     and plain host-following sources keep SizeH (static and keys) x ROOT_SY.
n16 = 0
if MODE == 'children':
    for outrel, inner in JOBS:
        n_path = os.path.join(OUT, outrel)
        if not os.path.exists(n_path):
            continue
        o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
        n_raw, n_ents = load_archive(n_path, inner)
        for n in sorted(o_ents):
            if not n.endswith('.bflyt'):
                continue
            ln = n[5:-6]
            lw, lh, ro = parse_flyt(o_raw, o_ents[n][0])
            if not top_eligible(ln, lw, lh) or ln in ALL_REFS:
                continue
            _, _, rn = parse_flyt(n_raw, n_ents[n][0])
            lo, lnw = list(ro.walk()), list(rn.walk())
            if len(lo) != len(lnw):
                continue
            for a, b in zip(lo, lnw):
                if a.kind == 'pan1' and b'CaptureApplyScale' in a.usd:
                    n16 += 1
                    chain = _proj_chain(b.parent) if b.parent is not None else 1.0
                    rect_off = b.h
                    rect_on = b.h * chain * b.sy   # the game code never rewrites these two panes' scale (MainShortCut setup 0x11910c0)
                    want = a.h * ROOT_SY
                    if abs(rect_off - want) > 0.5 or abs(rect_on - want) > 0.5:
                        F(f'{ln}/{a.name}: ApplyScale source copy rect {rect_off:.1f} (flag off) / {rect_on:.1f} (flag on), expected {want:.1f} for both')
                    if abs(b.w - a.w) > 0.01 or abs(b.tx - a.tx) > 0.01 or abs(b.ty - a.ty) > 0.01:
                        F(f'{ln}/{a.name}: ApplyScale source width/translation changed')
                if a.name in C.SRC_H_SCALE.get(ln, ()):
                    n16 += 1
                    if abs(b.h - a.h * ROOT_SY) > 0.01:
                        F(f'{ln}/{a.name}: SizeH {b.h:.2f}, expected {a.h * ROOT_SY:.2f}')
        for ln, names in C.SRC_H_SCALE.items():
            nm = 'blyt/' + ln + '.bflyt'
            if nm not in o_ents:
                continue
            for an in layout_anims(n_ents, ln):
                olds = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(o_raw, o_ents[an][0]) if not im_}
                news = {(p_, t_): ks for p_, im_, tm_, t_, ct_, ks in parse_flan(n_raw, n_ents[an][0]) if not im_}
                for pname in names:
                    ko = olds.get((pname, 9))
                    if ko is None:
                        continue
                    n16 += 1
                    for x, y in zip(ko, news[(pname, 9)]):
                        if abs(y.value - x.value * ROOT_SY) > 1e-3 * max(1, abs(x.value)):
                            F(f'{ln}/{pname}: {an} SizeH key {y.value:.2f}, expected {x.value * ROOT_SY:.2f}')
                            break
print(f'check 16: {n16} ApplyScale / host-following capture sources checked')

# 17. followers (e.g. the arc end caps of the system message pill) must have moved exactly like their anchor pane.
n17 = 0
for outrel, inner in JOBS:
    n_path = os.path.join(OUT, outrel)
    if not os.path.exists(n_path):
        continue
    o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
    n_raw, n_ents = load_archive(n_path, inner)
    for ln, (anchor, followers) in C.SHIFT_FOLLOW.items():
        nm = 'blyt/' + ln + '.bflyt'
        if nm not in o_ents:
            continue
        _, _, ro = parse_flyt(o_raw, o_ents[nm][0])
        _, _, rn = parse_flyt(n_raw, n_ents[nm][0])
        annotate(ro)
        annotate(rn)
        if MODE == 'children':
            norm_children(rn)
        po = {p.name: p for p in ro.walk()}
        pn = {p.name: p for p in rn.walk()}
        d_anchor = pn[anchor].ay - po[anchor].ay
        for f in followers:
            n17 += 1
            d = pn[f].ay - po[f].ay
            if abs(d - d_anchor) > 1.0:
                F(f'{ln}/{f}: moved {d:.1f} but its anchor {anchor} moved {d_anchor:.1f}')
print(f'check 17: {n17} anchor/follower pairs checked')

# 18. the Pause-menu page containers keep ScaleY 1 (the game's list code reads it; 0.75 here displaces Memories rows #6+).
n18 = 0
if MODE == 'children':
    for outrel, inner in JOBS:
        n_path = os.path.join(OUT, outrel)
        if not os.path.exists(n_path):
            continue
        n_raw, n_ents = load_archive(n_path, inner)
        for ln in ('PauseMenu_00', 'PauseMenuBG_00'):
            nm = 'blyt/' + ln + '.bflyt'
            if nm not in n_ents:
                continue
            _, _, rn = parse_flyt(n_raw, n_ents[nm][0])
            for c in rn.children:
                if c.name in ('N_Slide_00', 'N_Slide_01', 'N_Slide_02'):
                    n18 += 1
                    if abs(c.sy - 1.0) > 1e-4:
                        F(f'{ln}/{c.name}: ScaleY {c.sy:.4f}, must stay 1 (Memories list rows #6+ break otherwise)')
if MODE == 'children' and n18 != 6:
    F(f'check 18: expected 6 Pause-menu page containers (3 in PauseMenu_00, 3 in PauseMenuBG_00), found {n18}')
print(f'check 18: {n18} Pause-menu page containers checked')

# 19. PauseMenu_00/N_InOutQuest_02 (Adventure Log page, holds Pa_Quest_00) and its subtree stay at stock scale/translation/size
#     (any 0.75 there makes Memories rows #6+ draw on top of #5, round 7).
n19 = 0
if MODE == 'children':
    for outrel, inner in JOBS:
        n_path = os.path.join(OUT, outrel)
        if not os.path.exists(n_path):
            continue
        o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
        n_raw, n_ents = load_archive(n_path, inner)
        nm = 'blyt/PauseMenu_00.bflyt'
        if nm not in n_ents:
            continue
        _, _, ro = parse_flyt(o_raw, o_ents[nm][0])
        _, _, rn = parse_flyt(n_raw, n_ents[nm][0])
        po = {q.name: q for q in ro.walk()}
        pn = {q.name: q for q in rn.walk()}
        for top in C.NO_SCALE_SUBTREES.get('PauseMenu_00', ()):
            if top not in po or top not in pn:
                F(f'check 19: PauseMenu_00/{top} not found')
                continue
            for qo in po[top].walk():
                qn = pn.get(qo.name)
                n19 += 1
                if qn is None or any(abs(getattr(qn, f) - getattr(qo, f)) > 1e-4 for f in ('sx', 'sy', 'tx', 'ty', 'w', 'h')):
                    F(f'check 19: PauseMenu_00/{qo.name} differs from stock (must stay stock, Memories rows break otherwise)')
if MODE == 'children' and n19 == 0:
    F('check 19: no N_InOutQuest_02 subtree panes found')
print(f'check 19: {n19} Adventure Log page panes checked against stock')
# 20. round-8 HUD enlargement (only when HUD_SCALE != 1): compared against the HUD_SCALE=1 build of the same sources
#     (BOTW_HUD_BASE=<its output dir>): each HUD pane is scaled by HUD_SCALE about its anchor (static values and animation keys).
n20 = 0
if MODE == 'children' and abs(C.HUD_SCALE - 1.0) > 1e-6:
    base = os.environ.get('BOTW_HUD_BASE')
    if not base:
        F('check 20: set BOTW_HUD_BASE to the HUD_SCALE=1 build output dir')
    else:
        b_raw, b_ents = load_archive(os.path.join(base, 'Pack/Bootup.pack'), 'Layout/Common.sblarc')
        n_raw, n_ents = load_archive(os.path.join(OUT, 'Pack/Bootup.pack'), 'Layout/Common.sblarc')
        S = C.HUD_SCALE
        for ln, spec in C.HUD_PANES.items():
            nm = 'blyt/' + ln + '.bflyt'
            _, _, rb = parse_flyt(b_raw, b_ents[nm][0]); _, _, rn = parse_flyt(n_raw, n_ents[nm][0])
            pb = {q.name: q for q in rb.walk()}; pn = {q.name: q for q in rn.walk()}
            for name, (ax, ay) in spec.items():
                if name not in pb:
                    F(f'check 20: {ln}/{name} not found'); continue
                a, b = pb[name], pn[name]
                n20 += 1
                want = {'sx': a.sx * S, 'sy': a.sy * S, 'tx': ax + S * (a.tx - ax), 'ty': ay + S * (a.ty - ay)}
                for k, w in want.items():
                    if abs(getattr(b, k) - w) > 1e-3:
                        F(f'check 20: {ln}/{name} {k} {getattr(b, k):.4f}, expected {w:.4f}')
            ob = {}
            for an in layout_anims(b_ents, ln):
                for pane, is_mat, tmag, target, ctype, ks in parse_flan(b_raw, b_ents[an][0]):
                    if not is_mat and pane in spec and target in (0, 1, 6, 7) and ctype == 2:
                        ob[(an, pane, target)] = ks
            for an in layout_anims(n_ents, ln):
                for pane, is_mat, tmag, target, ctype, ks in parse_flan(n_raw, n_ents[an][0]):
                    if (an, pane, target) not in ob:
                        continue
                    ax, ay = spec[pane]
                    for ko, kn in zip(ob[(an, pane, target)], ks):
                        a0 = ax if target == 0 else ay
                        wv = a0 + S * (ko.value - a0) if target in (0, 1) else ko.value * S
                        n20 += 1
                        if abs(kn.value - wv) > 1e-3 or abs(kn.slope - ko.slope * S) > 1e-3:
                            F(f'check 20: {ln}/{pane} key target {target} in {an}: {kn.value:.3f}/{kn.slope:.3f}, expected {wv:.3f}/{ko.slope * S:.3f}')
print(f'check 20: {n20} HUD panes/keys checked')
# 21. stamina wheel: the part panes in PART_SY carry ScaleY/TransY x ROOT_SY (the code-written host scale cannot), and the
#     net Y squash of every wheel host chain is ROOT_SY (host ScaleY x parent chain x part pane / stock part pane).
n21 = 0
if MODE == 'children' and C.PART_SY:
    s_raw, s_ents = load_archive(os.path.join(SRC, 'Pack/Bootup.pack'), 'Layout/Common.sblarc')
    o_raw, o_ents = load_archive(os.path.join(OUT, 'Pack/Bootup.pack'), 'Layout/Common.sblarc')
    for part, names in C.PART_SY.items():
        a0, b0 = s_ents['blyt/' + part + '.bflyt'][0], o_ents['blyt/' + part + '.bflyt'][0]
        sa = {p.name: p for p in parse_flyt(s_raw, a0)[2].walk()}
        sb = {p.name: p for p in parse_flyt(o_raw, b0)[2].walk()}
        for nm in names:
            if abs(sb[nm].sy - sa[nm].sy * ROOT_SY) > 1e-6: F(f'check 21: {part}/{nm} ScaleY {sb[nm].sy}, expected {sa[nm].sy * ROOT_SY}')
            if abs(sb[nm].ty - sa[nm].ty * ROOT_SY) > 1e-6: F(f'check 21: {part}/{nm} TransY {sb[nm].ty}')
            n21 += 1
        for nm in sa:                                    # nothing else in the part may change its scale
            if nm not in names and sb[nm].sy != sa[nm].sy: F(f'check 21: {part}/{nm} ScaleY changed unexpectedly')
    for ln, hosts in C.HOST_SY_FACTOR.items():
        sa = {p.name: p for p in parse_flyt(s_raw, s_ents['blyt/' + ln + '.bflyt'][0])[2].walk()}
        sb = {p.name: p for p in parse_flyt(o_raw, o_ents['blyt/' + ln + '.bflyt'][0])[2].walk()}
        for h in hosts:
            chain_a = chain_b = 1.0
            q = sa[h]
            while q: chain_a *= q.sy; q = q.parent
            q = sb[h]
            while q: chain_b *= q.sy; q = q.parent
            if abs(chain_b - chain_a * ROOT_SY) > 1e-5 and abs(chain_b - chain_a * 1.0) > 1e-5:
                F(f'check 21: {ln}/{h} host chain ScaleY {chain_b:.4f} vs stock {chain_a:.4f}')
            n21 += 1
print(f'check 21: {n21} stamina-wheel panes/chains checked')
# 22. round-9 Adventure Log squash (PART_SQUASH_Y): each listed pane is a direct RootPane child of its part
#     with ScaleY and TransY exactly x0.75 of stock (animation keys too); every other pane of that part is stock; the part
#     is used by exactly one layout (PaChallengeListBtn_00 fills the 5 row slots of PaPageChallenge5_00).
n22 = 0
if C.PART_SQUASH_Y:
    o_raw, o_ents = load_archive(os.path.join(SRC, 'Pack/Bootup.pack'), 'Layout/Common.sblarc')
    n_raw, n_ents = load_archive(os.path.join(OUT, 'Pack/Bootup.pack'), 'Layout/Common.sblarc')
    for part, names in C.PART_SQUASH_Y.items():
        nm = 'blyt/' + part + '.bflyt'
        _, _, ro = parse_flyt(o_raw, o_ents[nm][0]); _, _, rn = parse_flyt(n_raw, n_ents[nm][0])
        po_, pn_ = list(ro.walk()), list(rn.walk())
        if [p.name for p in po_] != [p.name for p in pn_]:
            F(f'check 22: {part} pane list changed'); continue
        if names - {p.name for p in ro.children}:
            F(f'check 22: {part}: {sorted(names - {p.name for p in ro.children})} are not direct RootPane children')
        for a, b in zip(po_, pn_):
            n22 += 1
            sq = a.parent is ro and a.name in names
            want = {'sx': a.sx, 'sy': a.sy * (ROOT_SY if sq else 1), 'tx': a.tx, 'ty': a.ty * (ROOT_SY if sq else 1),
                    'w': a.w, 'h': a.h}
            for k, w in want.items():
                if abs(getattr(b, k) - w) > 1e-4:
                    F(f'check 22: {part}/{a.name} {k} {getattr(b, k):.4f}, expected {w:.4f}')
        ok_ = {}
        for an in layout_anims(o_ents, part):
            for pane, is_mat, tmag, target, ctype, ks in parse_flan(o_raw, o_ents[an][0]):
                if not is_mat and target in (1, 7):
                    ok_[(an, pane, target)] = ks
        for an in layout_anims(n_ents, part):
            for pane, is_mat, tmag, target, ctype, ks in parse_flan(n_raw, n_ents[an][0]):
                if (an, pane, target) not in ok_:
                    continue
                f = ROOT_SY if pane in names else 1.0
                for ko, kn in zip(ok_[(an, pane, target)], ks):
                    n22 += 1
                    if abs(kn.value - ko.value * f) > 1e-4:
                        F(f'check 22: {part}/{pane} key target {target} in {an}: {kn.value:.4f}, expected {ko.value * f:.4f}')
        users = sorted(n[5:-6] for n in n_ents if n.endswith('.bflyt')
                       and any(prt1_name(n_raw, p) == part for mag, p, s in flyt_tags(n_raw, n_ents[n][0], {b'prt1'})))
        if len(users) != 1:
            F(f'check 22: {part} is used by {users}, the squash assumes exactly one layout (the Adventure Log page chain)')
if MODE == 'children' and n22 == 0:
    F('check 22: no PART_SQUASH_Y panes checked')
print(f'check 22: {n22} squashed-part panes/keys checked')
print('continuity pairs checked:', cont_stats)
print('mode:', MODE, dict(CSTAT))
# 10. bnd1 / cursor-like panes must stay glued to their visual partners.
#     For every bnd1 and every pane named *Cursor*/*Select*/*Focus*/*Hit*/*Sel* (all layouts, parts included):
#       a) its own world centre moved exactly like its parent's (no private shift, no private growth),
#       b) it moved like every visual sibling (pic1/wnd1/txt1/prt1) under the same parent, unless that sibling
#          is a deliberately grown fill pane (then only the centre must match),
#       c) its absolute Y scale changed by exactly the root factor of its layout (0.75, or 1.0 for
#          ROOT_SKIP / CURSOR_ROOT_KEEP / parts), never anything else.
import re as _re
_PAT = _re.compile(r'cursor|select|focus|(^|_)hit(_|\d|$)|(^|_)sel(_|\d|$)', _re.I)
_n10 = 0
for outrel, inner in JOBS:
    if not rep[outrel]['writes']:
        continue
    o_raw, o_ents = load_archive(os.path.join(SRC, outrel), inner)
    n_raw, n_ents = load_archive(os.path.join(OUT, outrel), inner)
    for n in sorted(o_ents):
        if not n.endswith('.bflyt'):
            continue
        ln = n[5:-6]
        _, _, ro = parse_flyt(o_raw, o_ents[n][0]); _, _, rn = parse_flyt(n_raw, n_ents[n][0])
        annotate(ro); annotate(rn)
        if MODE == 'children' and ln not in ALL_REFS and top_eligible(ln, ro.w, ro.h):
            norm_children(rn)
        po_, pn_ = list(ro.walk()), list(rn.walk())
        if len(po_) != len(pn_):
            continue
        is_part = ln in ALL_REFS
        want_ratio = 1.0 if (is_part or ln in C.ROOT_SKIP or ln in C.CURSOR_ROOT_KEEP
                             or (ro.w, ro.h) != (1280.0, 720.0) or ln in ('Fade_00', 'Thanks_00')) else ROOT_SY
        oi = {id(p): i for i, p in enumerate(po_)}
        for a, b in zip(po_, pn_):
            if a is ro or not (a.kind == 'bnd1' or _PAT.search(a.name)):
                continue
            _n10 += 1
            tag = f'{ln}/{a.path()}'
            wa, wb = a.asy * ro.sy, b.asy * rn.sy      # annotate() excludes the root's own scale
            if MODE == 'root' and wa and abs(wb / wa - want_ratio) > 1e-4:
                F(f'{tag}: abs Y scale ratio {wb / wa:.4f}, expected {want_ratio}')
            if a.kind == 'bnd1' and (abs(b.h - a.h) > 1e-3 or abs(b.w - a.w) > 1e-3):
                F(f'{tag}: bnd1 resized ({a.w}x{a.h} -> {b.w}x{b.h})')
            par_a, par_b = a.parent, b.parent
            if par_a is None:
                continue
            da = b.ay - a.ay
            if par_a is not ro and abs(da - (par_b.ay - par_a.ay)) > 1.0 and abs(par_b.h - par_a.h) < 1e-3:
                F(f'{tag}: moved {da:.1f} but parent {par_a.name} moved {par_b.ay - par_a.ay:.1f}')
            for sa, sb in zip(par_a.children, par_b.children):
                if sa is a or sa.kind not in ('pic1', 'wnd1', 'txt1', 'prt1'):
                    continue
                ds = sb.ay - sa.ay
                grown = abs(sb.h - sa.h) > 0.5
                if abs(ds - da) > 1.0 and not grown:
                    F(f'{tag}: separated from sibling {sa.name} (hit/cursor {da:.1f}, sibling {ds:.1f})')
                elif abs(ds - da) > 1.0 and grown and abs(sb.ay - sa.ay) > 1.0:
                    F(f'{tag}: grown sibling {sa.name} also moved its centre ({ds:.1f}) while hit/cursor moved {da:.1f}')
print(f'check 10: {_n10} bnd1/cursor-like panes compared against partners')

print(f'FAILS: {len(fails)}')
for m in fails[:80]: print('  FAIL', m)
print(f'WARNINGS: {len(warns)}')
for m in warns[:80]: print('  warn', m)
sys.exit(1 if fails else 0)


