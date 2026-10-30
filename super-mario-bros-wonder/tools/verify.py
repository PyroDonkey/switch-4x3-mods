"""Verify the built layouts against the originals.

usage: python -I verify.py <tools_dir> <orig_layout_dir> <out_dir>/romfs/Layout
"""
import sys, os, json, struct, collections
sys.path.insert(0, sys.argv[1])
from lyt import *
from compression import zstd

scratch, ORIG, OUT = sys.argv[1:4]
TOP = set(open(os.path.join(scratch, 'toplevel.txt')).read().split())
report = json.load(open(os.path.join(OUT, os.pardir, os.pardir, 'build_report.json')))
VISUAL = {'pic1', 'txt1', 'wnd1', 'prt1'}
# edge blocks reviewed by hand: they deliberately move as one unit with their central-looking children
REVIEWED_BLOCKS = {('CourseIn', 'S_CourseName'), ('CourseIn', 'N_Badge'), ('GameDisplay', 'A_ItemStock'),
                   ('MainMenu', 'N_ScreenshotPos'), ('GameDisplayTimer', 'N_BestScore')}
# panes inside deliberately unshifted blocks that may stay off the 4:3 edge
EDGE_EXEMPT = {('Pause', 'L_ConnectionState')}   # top of the Pause right column, which stays one block

orig = {b: raw for b, _, raw, _ in load_layout_dir(ORIG)}
problems, stats = [], collections.Counter()


def bounds(root):
    """Static absolute bounds (root-local units, root scale excluded) for every pane."""
    out = {}
    def rec(p, ax, ay_o, asx, asy, vis):
        for c in p.children:
            csx, csy = asx * c.sx, asy * c.sy
            pvo = (c.origin >> 6) & 3
            base_local = 0.0
            if pvo:
                pv = (p.origin >> 2) & 3 if p.parent is not None else 0
                rc = -p.h / 2 if pv == 1 else p.h / 2 if pv == 2 else 0.0
                base_local = rc + (p.h / 2 if pvo == 1 else -p.h / 2)
            px, py = ax + asx * c.tx, ay_o + asy * (base_local + c.ty)
            hh = abs(c.h * csy); hw = abs(c.w * csx)
            vo = (c.origin >> 2) & 3
            cy = py - hh / 2 if vo == 1 else py + hh / 2 if vo == 2 else py
            cvis = vis and c.sx != 0 and c.sy != 0
            out[c.name] = (c, px, cy, hw, hh, cvis)
            rec(c, px, py, csx, csy, cvis)
    rec(root, 0, 0, 1, 1, True)
    return out


for base, path, raw, ents in load_layout_dir(OUT):
    if base == 'GrandWorldMap':      # hand-edited (tools\hand-edited), not generated
        continue
    o = orig[base]
    stats['archives'] += 1
    if raw == o:
        problems.append(f'{base}: unchanged original shipped (the build should leave it out)')
    # 1) structure: same size, sarc table identical
    assert len(raw) == len(o), base
    assert sarc_entries(raw) == sarc_entries(o), base
    # 2) every differing 4-byte word is a logged write
    logged = {w[0] for w in report[base]['writes']}
    diff_words = {i - (i - 0) % 1 for i in range(len(o)) if raw[i] != o[i]}
    for i in diff_words:
        if not any(off <= i < off + 4 for off in logged):
            problems.append(f'{base}: unlogged byte change at {i:#x}')
    for off, old, new, what in report[base]['writes']:
        got = struct.unpack_from('<f', raw, off)[0]
        if abs(got - new) > 1e-3 * max(1, abs(new)):
            problems.append(f'{base}: write {what} not present')
    stats['writes'] += len(report[base]['writes'])
    # 3) re-parse everything
    for nm, (s, e) in ents.items():
        if nm.endswith('.bflan'):
            parse_flan(raw, s); stats['bflan'] += 1
        elif nm.endswith('.bflyt'):
            lw, lh, root = parse_flyt(raw, s); stats['bflyt'] += 1
            if base not in TOP:
                if (root.sx, root.sy) != (1, 1):
                    problems.append(f'{base}: parts root scale {root.sx},{root.sy}')
                continue
            olw, olh, oroot = parse_flyt(o, s)
            vis_half = lh / 2 / root.sy           # 720 for root.sy 0.75 (CmnOnUIBlurBg: 540)
            nb, ob = bounds(root), bounds(oroot)
            for name, (c, x, y, hw, hh, vis) in nb.items():
                _, ox, oy, ohw, ohh, ovis = ob[name]
                moved = (abs(y - oy) > 0.01 or abs(hh - ohh) > 0.01)
                if not moved:
                    continue
                stats['moved panes (incl. children)'] += 1
                if c.kind in VISUAL and vis:
                    was_in = abs(oy) + ohh / 2 <= lh / 2 + 1
                    now_in = abs(y) + hh / 2 <= vis_half + 1
                    if was_in and not now_in and hh < lh * 0.9:
                        problems.append(f'{base}: {c.kind} {name} pushed off-screen: y {oy:.0f}->{y:.0f} h {hh:.0f}')
            # moved groups must not carry central content (pivot / wrapper regression check)
            shifted = {w[3].split()[1] for w in report[base]['writes'] if w[3].startswith('shift ')}
            for name in shifted:
                if (base, name) in REVIEWED_BLOCKS:
                    continue
                c = nb[name][0]
                for d in c.walk():
                    if d is c or d.kind not in VISUAL:
                        continue
                    _, ox, oy, ohw, ohh, ovis = ob[d.name]
                    if ovis and abs(oy) < 250:
                        problems.append(f'{base}: shifted {name} carries central {d.kind} {d.name} (orig y {oy:.0f})')
            # elements that hugged a 16:9 edge should hug the 4:3 edge
            edge_misses = []
            for name, (c, x, y, hw, hh, vis) in nb.items():
                _, ox, oy, ohw, ohh, ovis = ob[name]
                if c.kind not in VISUAL or not ovis or ohh >= lh * 0.9 or ohw < lw * 0.5 or (base, name) in EDGE_EXEMPT:
                    continue
                for sgn in (1, -1):
                    if abs(sgn * oy + ohh / 2 - lh / 2) <= 5 and abs(sgn * y + hh / 2 - vis_half) > 5:
                        edge_misses.append(f'{base}: {c.kind} {name} touched the 16:9 edge (y {oy:.0f}) but not the 4:3 edge (y {y:.0f})')
            problems.extend(edge_misses)
            # fill coverage
            for line in report[base]['notes']:
                if line.startswith('fill'):
                    n = line.split()[1]
                    c, x, y, hw, hh, vis = nb[n]
                    animated = any(w[3].startswith('fill-anim ' + n + ' ') for w in report[base]['writes'])
                    if (abs(y) > 1 and not animated) or hh / 2 < vis_half - 1:
                        problems.append(f'{base}: fill {n} does not cover screen: y {y:.1f} half-h {hh/2:.1f}')
                    stats['fill panes'] += 1

print(dict(stats))
print(f'{len(problems)} problem(s)')
for p in problems:
    print('  ' + p)
sys.exit(1 if problems else 0)
