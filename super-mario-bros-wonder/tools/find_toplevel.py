"""List top-level layouts (never referenced by a prt1 pane) and write them to <tools_dir>/toplevel.txt.

usage: python -I find_toplevel.py <tools_dir> <layout_dir>
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from lyt import *

data = list(load_layout_dir(sys.argv[2]))
names = {b for b, _, _, _ in data}
used = set()
for b, _, raw, ents in data:
    for nm, (s, e) in ents.items():
        if nm.endswith('.bflyt'):
            lw, lh, root = parse_flyt(raw, s)
            for p in root.walk():
                if p.kind == 'prt1':
                    for t in re.findall(rb'[A-Za-z0-9_]+', p.raw[84:]):
                        if t.decode() in names:
                            used.add(t.decode())
top = sorted(names - used)
print(f'parts: {len(used)}  top-level: {len(top)}')
with open(os.path.join(sys.argv[1], 'toplevel.txt'), 'w') as f:
    f.write('\n'.join(top))
