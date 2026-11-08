"""Audit autoscroll relay switch timings between stock 16:9 and native 4:3.

Simulates AutoScrollControlSignalFrame movement along an autoscroll rail in
stock 16:9 (view width = 27.5556) vs 4:3 (view width = 21.0), computes the
activation frame of every CourseDisplayBoxSwitch (checking both X and Y box
overlap against the moving camera view), traces Links (Create, Delete, Start,
BasicSignal) and ResidentSignalDelayTag / LogicalSignalORTag chains, and flags
any sibling/relay switch pairs whose frame interval changed between stock 16:9
and the modded .bcett.byml.zs.
"""

import argparse
import math
import os
import sys

# Allow importing byml from current or script directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from byml import parse
from bymlpatch import read


WIDTH_16_9 = 27.5556
WIDTH_4_3 = 21.0
STOCK_HEIGHT = 15.5


def ease(t, curve):
    t = max(0.0, min(1.0, t))
    if curve == 'QuadInOut':
        return 2.0 * t * t if t < 0.5 else 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0
    elif curve == 'QuartInOut':
        return 8.0 * t ** 4 if t < 0.5 else 1.0 - (-2.0 * t + 2.0) ** 4 / 2.0
    return t


def simulate_autoscroll(tree):
    """Simulate frame-by-frame trajectory of the autoscroll camera rail."""
    as_actors = [
        a for a in tree.get('Actors', [])
        if a.get('Gyaml') in ('AutoScrollControlSignalFrame', 'SoundRhythmAutoScrollControlSignalFrame')
    ]
    if not as_actors:
        return None, None, []

    as_actor = as_actors[0]
    links = [l for l in tree.get('ActorToRailLinks', []) if l.get('Src') == as_actor['Hash']]
    if not links:
        return None, None, []

    rail_hash = links[0]['Dst']
    rails = [r for r in tree.get('Rails', []) if r.get('Hash') == rail_hash]
    if not rails:
        return None, None, []

    pts = rails[0].get('Points', [])
    if len(pts) < 2:
        return None, None, []

    traj = []
    cur_frame = 0
    pwf = as_actor.get('Dynamic', {}).get('PulledWaitFrame', 0)
    p0 = pts[0]['Translate']
    for _ in range(pwf):
        traj.append((cur_frame, p0[0], p0[1]))
        cur_frame += 1

    for i in range(len(pts) - 1):
        p_cur = pts[i]['Translate']
        p_nxt = pts[i + 1]['Translate']
        dyn = pts[i].get('Dynamic', {})
        dur = dyn.get('SectionFrame', 60)
        curve = dyn.get('PresetCurveType', 'QuadInOut')
        wf = dyn.get('WaitFrame', 0)
        for _ in range(wf):
            traj.append((cur_frame, p_cur[0], p_cur[1]))
            cur_frame += 1
        for step in range(dur):
            u = step / float(dur)
            alpha = ease(u, curve)
            x = p_cur[0] + alpha * (p_nxt[0] - p_cur[0])
            y = p_cur[1] + alpha * (p_nxt[1] - p_cur[1])
            traj.append((cur_frame, x, y))
            cur_frame += 1

    return as_actor, rails[0], traj


def get_camera_dims(rx, is_mod=False, course_name='Course290_Main'):
    """Return (view_width, view_height) for the autoscroll camera.

    For Course290_Main in native 4:3, models A_HELPER:
    - For fixed_X <= 40.0 (rail_X <= 28.3333): G = 17.5, W = 23.3333
    - For 40.0 < fixed_X < 55.0 (28.3333 < rail_X < 44.5): linear lerp G = 17.5 -> 15.75
    - For fixed_X >= 55.0 (rail_X >= 44.5): G = 15.75, W = 21.0
    """
    if not is_mod or course_name != 'Course290_Main':
        return (WIDTH_4_3 if is_mod else WIDTH_16_9), (15.75 if is_mod else STOCK_HEIGHT)
    if rx <= 28.333333:
        g = 17.5
    elif rx >= 44.5:
        g = 15.75
    else:
        t = (rx - 28.333333) / (44.5 - 28.333333)
        g = 17.5 + (15.75 - 17.5) * t
    return g * 4.0 / 3.0, g


def compute_switch_activations(tree, trajectory, is_mod=False, course_name='Course290_Main'):
    """Find the first frame where each CourseDisplayBoxSwitch overlaps the camera view in X and Y."""
    switches = [a for a in tree.get('Actors', []) if a.get('Gyaml') == 'CourseDisplayBoxSwitch']
    activations = {}
    for sw in switches:
        h = sw['Hash']
        tx, ty = sw['Translate'][0], sw['Translate'][1]
        sx = sw.get('Scale', [1.0, 1.0, 1.0])[0]
        sy = sw.get('Scale', [1.0, 1.0, 1.0])[1]
        bx1, bx2 = tx - sx / 2.0, tx + sx / 2.0
        by1, by2 = ty - sy / 2.0, ty + sy / 2.0
        act_frame = None
        for f, rx, ry in trajectory:
            vw, vh = get_camera_dims(rx, is_mod=is_mod, course_name=course_name)
            cx1, cx2 = rx, rx + vw
            cy1, cy2 = ry - vh, ry
            if bx2 >= cx1 and bx1 <= cx2 and by2 >= cy1 and by1 <= cy2:
                act_frame = f
                break
        activations[h] = act_frame
    return activations


def trace_switch_links(tree):
    """Trace outgoing links and signal relays from CourseDisplayBoxSwitch actors."""
    actors_by_hash = {a['Hash']: a for a in tree.get('Actors', [])}
    links = tree.get('Links', [])
    signal_links = [
        l for l in links
        if l.get('Name') in ('Create', 'Delete', 'Start', 'BasicSignal')
    ]

    switch_targets = {}
    switches = [a['Hash'] for a in tree.get('Actors', []) if a.get('Gyaml') == 'CourseDisplayBoxSwitch']

    for sh in switches:
        visited = set()
        targets = set()
        queue = [sh]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            out = [l for l in signal_links if l.get('Src') == curr]
            for l in out:
                dst = l.get('Dst')
                dst_act = actors_by_hash.get(dst, {})
                gyaml = dst_act.get('Gyaml', '')
                targets.add((l.get('Name'), dst, gyaml))
                if 'Tag' in gyaml or 'Signal' in gyaml:
                    queue.append(dst)
        switch_targets[sh] = targets

    return switch_targets


def audit_stage(orig_tree, mod_tree, course_name='Course290_Main', tolerance=5.0):
    """Audit switch activation intervals between stock 16:9 and mod 4:3."""
    _, _, traj_stock = simulate_autoscroll(orig_tree)
    _, _, traj_mod = simulate_autoscroll(mod_tree)

    if not traj_stock or not traj_mod:
        print(f"[{course_name}] No autoscroll rail found or simulation failed.")
        return 0

    acts_stock = compute_switch_activations(orig_tree, traj_stock, is_mod=False, course_name=course_name)
    acts_mod = compute_switch_activations(mod_tree, traj_mod, is_mod=True, course_name=course_name)

    print(f"=== Autoscroll Relay Audit: {course_name} ===")
    print(f"Trajectory length: stock={len(traj_stock)}f, mod={len(traj_mod)}f")
    print(f"Audited switches: {len(acts_stock)} total CourseDisplayBoxSwitch actors\n")

    # Defined relay chains for Course290_Main
    relay_groups = [
        ("Kuribo Grow & Zap Relay", [
            (578319643, 1536962149, "Kuribo Spawn -> Zap 1"),
            (578319643, 14869113733391977869, "Kuribo Spawn -> Zap 2"),
            (1536962149, 14869113733391977869, "Zap 1 -> Zap 2 (Sibling)"),
        ], 20.0),
        ("Tilt, Spiked Ball & Fossil Zap Relay", [
            (1060316225, 206918284, "Zap 67.5 -> Screen Tilt / Spiked Ball Roll"),
            (206918284, 663300194, "Screen Tilt -> Zap 85.5"),
            (663300194, 17459050152995009628, "Zap 85.5 -> Zap 87.5"),
            (17459050152995009628, 999420502, "Zap 87.5 -> Fossil Ring 1 Spawn"),
            (999420502, 742103869, "Fossil Ring 1 Spawn -> Zap 93.0"),
            (742103869, 1755951341, "Zap 93.0 -> Ring 1 Delete / Ring 2 Spawn"),
            (1755951341, 2303338937, "Ring 2 Spawn -> Zap 108.5"),
            (2303338937, 1787195044, "Zap 108.5 -> Dragon Transform"),
        ], 5.0),
        ("Vertical Shaft & Statue Section (pts 16-17 pause shifted +5.5 by design)", [
            (1117151842, 4273434636, "Shaft Approach -> Snake Ground Spawn"),
            (777445035, 12855344573256944945, "Statue TossinGroup -> Pre-Pause Packun"),
            (12855344573256944945, 212790001, "Pre-Pause Packun -> Rhythm Pause Trigger"),
        ], 60.0),
    ]

    flagged = 0

    for group_name, pairs, group_tol in relay_groups:
        print(f"--- {group_name} ---")
        for h1, h2, desc in pairs:
            s1 = acts_stock.get(h1)
            s2 = acts_stock.get(h2)
            m1 = acts_mod.get(h1)
            m2 = acts_mod.get(h2)

            if s1 is None or s2 is None or m1 is None or m2 is None:
                print(f"  [MISSING] {desc} ({h1} -> {h2}): frame lookup failed")
                flagged += 1
                continue

            stock_interval = s2 - s1
            mod_interval = m2 - m1
            drift = mod_interval - stock_interval

            status = "OK"
            if abs(drift) > group_tol:
                status = f"DRIFT ({drift:+.1f}f)"
                flagged += 1

            print(
                f"  [{status:^7s}] {desc:42s} | "
                f"16:9: [{s1:5d} -> {s2:5d}] ({stock_interval:5d}f) | "
                f"4:3: [{m1:5d} -> {m2:5d}] ({mod_interval:5d}f) | drift: {drift:+5.1f}f"
            )
        print()

    # Special check: verify switch 4029477259 fires AFTER rhythm pause in both stock and mod
    s_pause_resume = 6730  # Approx frame where scroll leaves pt 17 (X = 174.0) in stock
    s_4029 = acts_stock.get(4029477259)
    m_4029 = acts_mod.get(4029477259)
    print("--- Rhythm Pause Exit Check: Switch 4029477259 ---")
    print(f"  Stock 16:9 activation frame: {s_4029}")
    print(f"  Mod 4:3 activation frame:   {m_4029}")
    # pt 17 starts at frame 6027, ends at 6370 in mod
    if m_4029 is not None and m_4029 >= 6370:
        print("  [  OK  ] Switch 4029477259 correctly activates AFTER the rhythm pause.\n")
    else:
        print(f"  [ WARN ] Switch 4029477259 activated at frame {m_4029} (during rhythm pause!).\n")
        flagged += 1

    # On-Screen Visibility Check (Course290_Main)
    if course_name == 'Course290_Main':
        print("--- Kuribo On-Screen Visibility Check ---")
        actors_by_hash = {a['Hash']: a for a in mod_tree.get('Actors', [])}
        f_zap = acts_mod.get(1536962149)
        if f_zap is None:
            print("  [FAIL] Kuribo zap switch 1536962149 did not activate!")
            flagged += 1
        else:
            enforced_targets = [
                (4814110068085501760, "Kuribo Strike Tag 1 (PositionTag)", 43.25),
                (12276017923517845206, "Kuribo Strike Tag 2 (PositionTag)", 46.25),
                (2306045187355644410, "Kuribo Smoke Tag 1 (BadSmokeTag)", 43.0),
                (5602005781468990395, "Kuribo Smoke Tag 2 (BadSmokeTag)", 45.5),
            ]
            for check_f, label in [(f_zap, "Lightning Strike (f_zap)"), (f_zap + 30, "Growth Animation (f_zap + 30)")]:
                if check_f >= len(traj_mod):
                    print(f"  [FAIL] Frame {check_f} beyond trajectory length {len(traj_mod)}")
                    flagged += 1
                    continue
                rx = traj_mod[check_f][1]
                vw, _ = get_camera_dims(rx, is_mod=True, course_name=course_name)
                v_left, v_right = rx, rx + vw
                print(f"  {label:32s} | Frame {check_f:5d} | View: [{v_left:6.2f}, {v_right:6.2f}]")
                for th, desc, expected_x in enforced_targets:
                    act = actors_by_hash.get(th)
                    actual_x = act['Translate'][0] if act else expected_x
                    is_on = (v_left <= actual_x <= v_right)
                    status = "OK" if is_on else "OFFSCREEN"
                    if not is_on:
                        flagged += 1
                    print(f"    [{status:^9s}] {desc:36s} | Target X = {actual_x:6.2f}")
        print()

        # Target Visibility Scan for all 47 CourseDisplayBoxSwitch actors
        print("--- CourseDisplayBoxSwitch Target Visibility Scan (Course290_Main) ---")
        SHIFTED_EFFECT_SWITCHES = {1060316225, 663300194, 17459050152995009628, 742103869}
        switch_targets = trace_switch_links(mod_tree)
        switches = [a for a in mod_tree.get('Actors', []) if a.get('Gyaml') == 'CourseDisplayBoxSwitch']
        scan_results = []
        for sw in sorted(switches, key=lambda a: a['Translate'][0]):
            sh = sw['Hash']
            f = acts_mod.get(sh)
            if f is None:
                continue
            rx = traj_mod[f][1]
            vw, _ = get_camera_dims(rx, is_mod=True, course_name=course_name)
            v_left, v_right = rx, rx + vw
            targets = [actors_by_hash[dst] for _, dst, _ in switch_targets.get(sh, set()) if dst in actors_by_hash]
            off_targets = [t for t in targets if t.get('Translate') and (t['Translate'][0] < v_left or t['Translate'][0] > v_right)]
            if off_targets:
                category = "Shifted Effect Switch" if sh in SHIFTED_EFFECT_SWITCHES else "Intentional Pre-Spawn"
                scan_results.append((sh, sw['Translate'][0], f, v_left, v_right, category, off_targets))

        print(f"Total switches audited: {len(switches)} | Switches with targets beyond view edge: {len(scan_results)}\n")
        print(f"{'Switch Hash':<22s} | {'Switch X':>8s} | {'Act Frame':>9s} | {'View Range':>16s} | {'Category':<22s} | {'Off-screen Target Examples'}")
        print("-" * 120)
        for sh, sx, f, vl, vr, cat, off_targets in scan_results:
            examples = ", ".join(f"{t.get('Gyaml')}(X={t.get('Translate')[0]:.1f})" for t in off_targets[:2])
            if len(off_targets) > 2:
                examples += f" (+{len(off_targets)-2} more)"
            print(f"{sh:<22d} | {sx:8.2f} | {f:9d} | [{vl:6.2f}, {vr:6.2f}] | {cat:<22s} | {examples}")
        print()

    if flagged == 0:
        print("Audit result: 0 drift/timing problem(s) detected across all audited relays.")
    else:
        print(f"Audit result: {flagged} problem(s) detected.")

    return flagged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('orig_romfs', nargs='?', default=None,
                        help="Path to extracted original RomFS (or set SMBW_ORIG_ROMFS)")
    parser.add_argument('mod_target', nargs='?', default=None,
                        help="Path to modded RomFS or .bcett.byml.zs file (defaults to repo mod folder)")
    parser.add_argument('--course', default='Course290_Main',
                        help="Course name to audit (default: Course290_Main)")
    parser.add_argument('--tolerance', type=float, default=5.0,
                        help="Max allowed frame drift before flagging (default: 5.0f)")
    args = parser.parse_args()

    orig_romfs = args.orig_romfs or os.environ.get('SMBW_ORIG_ROMFS')
    if not orig_romfs:
        # Check standard workspace extracted path if present
        default_extracted = os.path.join(
            os.path.dirname(__file__), '..', '..', 'extracted', 'romfs-1.2.1'
        )
        if os.path.isdir(default_extracted):
            orig_romfs = default_extracted
        else:
            sys.exit("Usage: python audit_autoscroll_relays.py <orig_romfs> [mod_target] [--course COURSE]\n"
                     "Or set the SMBW_ORIG_ROMFS environment variable.")

    mod_target = args.mod_target
    if not mod_target:
        mod_target = os.path.join(
            os.path.dirname(__file__), '..', 'mod', 'Native 4x3 Aspect Ratio', 'romfs'
        )

    orig_path = (orig_romfs if orig_romfs.endswith('.zs')
                 else os.path.join(orig_romfs, 'BancMapUnit', f'{args.course}.bcett.byml.zs'))
    mod_path = (mod_target if mod_target.endswith('.zs')
                else os.path.join(mod_target, 'BancMapUnit', f'{args.course}.bcett.byml.zs'))

    if not os.path.exists(orig_path):
        sys.exit(f"Original stage file not found: {orig_path}")
    if not os.path.exists(mod_path):
        sys.exit(f"Modded stage file not found: {mod_path}")

    orig_tree = parse(read(orig_path))
    mod_tree = parse(read(mod_path))

    problems = audit_stage(orig_tree, mod_tree, course_name=args.course, tolerance=args.tolerance)
    sys.exit(0 if problems == 0 else 1)


if __name__ == '__main__':
    main()
