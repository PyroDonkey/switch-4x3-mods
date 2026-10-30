import sys, collections
sys.path.insert(0, sys.argv[1])
from lyt import *

layout_dir = sys.argv[2]
CONTAINERS = {'pan1', 'scr1', 'ali1'}
VISUAL = {'pic1', 'wnd1', 'txt1', 'prt1'}
FLPA = {0: 'TX', 1: 'TY', 6: 'SX', 7: 'SY', 8: 'W', 9: 'H'}

stats = collections.Counter()
TOP = set(open(sys.argv[1] + "/toplevel.txt").read().split())
for base, path, raw, ents in load_layout_dir(layout_dir):
    if base not in TOP: continue
    anims = collections.defaultdict(set)
    for nm, (s, e) in ents.items():
        if nm.endswith('.bflan'):
            try:
                for pane, is_mat, tmag, target, ctype, keys in parse_flan(raw, s):
                    if tmag == 'FLPA' and not is_mat:
                        anims[pane].add(FLPA.get(target, str(target)))
            except Exception as ex:
                print('  !! bflan parse failed', base, nm, ex)
    for nm, (s, e) in ents.items():
        if not nm.endswith('.bflyt'):
            continue
        lw, lh, root = parse_flyt(raw, s)
        print(f'=== {base} :: {nm}  {lw:g}x{lh:g} root S=({root.sx:g},{root.sy:g})')

        def visit(p, depth):
            # p is a container whose own ty == 0; decide for each child
            for c in p.children:
                an = ','.join(sorted(anims.get(c.name, ())))
                full = c.w >= lw * 0.95 and c.h >= lh * 0.95
                tag = []
                if full: tag.append('FULL')
                if an: tag.append('anim:' + an)
                desc = f"{'  '*depth}{c.kind} {c.name:<26} T=({c.tx:g},{c.ty:g}) S=({c.sx:g},{c.sy:g}) size=({c.w:g},{c.h:g}) {' '.join(tag)}"
                if c.ty != 0:
                    print('  POS ' + desc); stats['pos'] += 1
                    if 'TY' in an: stats['pos_animTY'] += 1
                elif c.kind in CONTAINERS and c.children and c.sy == 1 and c.rot == (0, 0, 0):
                    print('  ... ' + desc)
                    visit(c, depth + 1)
                else:
                    if full or c.kind in VISUAL and c.children:
                        print('  STOP' + desc)
        visit(root, 0)
print(stats)
