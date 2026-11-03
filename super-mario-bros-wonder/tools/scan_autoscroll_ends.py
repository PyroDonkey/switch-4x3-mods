"""Scan autoscroll end stops from extracted RomFS BancMapUnit and StageParam files.

Reads an extracted romfs directory given as an argument (e.g. <workspace>/extracted/romfs-1.2.1)
and prints the autoscroll end stops table as Python literals for gen_zoom_v2.py.
Only areas with intermediate pauses >= 120 frames are included in the table.
"""
import os, sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Allow importing byml from current or script directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import byml

AUTOSCROLL_STAGES = [
    "Course002_Main", "Course008_Sub2", "Course010_Main", "Course016_Sub2",
    "Course019_Main", "Course022_Main", "Course023_Main", "Course049_Sub3",
    "Course061_Sub2", "Course062_Sub1", "Course064_Sub1", "Course100_Main",
    "Course101_Main", "Course102_Main", "Course102_Sub1", "Course290_Main",
    "Course407_Course", "Course460_Course", "Course853_Main", "Course854_Main",
    "Course857_Main", "Course858_Main"
]

HALF_W_16_9 = 27.5556 / 2.0


def scan_autoscroll_ends(romfs_dir):
    banc_dir = os.path.join(romfs_dir, "BancMapUnit")
    stage_param_dir = os.path.join(romfs_dir, "Stage", "StageParam")

    if not os.path.isdir(banc_dir):
        sys.exit(f"ERROR: BancMapUnit directory not found under {romfs_dir}")

    # Load course labels from StageParam if present
    course_labels = {}
    if os.path.isdir(stage_param_dir):
        for f in os.listdir(stage_param_dir):
            if f.endswith('.bgyml'):
                try:
                    b = byml.load(os.path.join(stage_param_dir, f))
                    lbl = b.get('Label', '')
                    if lbl:
                        base = f.split('.')[0]
                        course_labels[base] = lbl
                except Exception:
                    pass

    all_stage_data = []

    for st in AUTOSCROLL_STAGES:
        p = os.path.join(banc_dir, f"{st}.bcett.byml.zs")
        if not os.path.exists(p):
            sys.exit(f"ERROR: Stage file missing: {p}")
        data = byml.load(p)
        root_hash = data.get('RootAreaHash')
        rails = data.get('Rails', [])
        actor_to_rails = data.get('ActorToRailLinks', [])
        rail_by_hash = {r.get('Hash'): r for r in rails}
        as_actors = [a for a in data.get('Actors', [])
                     if a.get('Gyaml') in ('AutoScrollControlSignalFrame', 'SoundRhythmAutoScrollControlSignalFrame')]
        if not as_actors:
            continue

        a = as_actors[0]
        links = [l for l in actor_to_rails if l.get('Src') == a.get('Hash')]
        if not links:
            sys.exit(f"ERROR: No rail link found for autoscroll actor in {st}")
        rail = rail_by_hash.get(links[0].get('Dst'))
        if not rail:
            sys.exit(f"ERROR: Referenced rail not found in {st}")

        pts = rail.get('Points', [])
        if not pts:
            sys.exit(f"ERROR: Rail has no points in {st}")

        final_pt_x = pts[-1]['Translate'][0]
        final_pt_y = pts[-1]['Translate'][1]

        # Key is independent of G: rail final point X + 16:9 view half-width (27.5556 / 2)
        end_key = final_pt_x + HALF_W_16_9

        lbl = course_labels.get(st, '')

        # Survey ALL ways the scroll can stand still for >= 120 frames before the last point:
        # across the autoscroll rail and autoscroll actor parameters in the area
        stage_pauses = []

        # 1. WaitFrame on autoscroll rail points
        for i, pt in enumerate(pts):
            wf = pt.get('Dynamic', {}).get('WaitFrame', 0)
            is_end = (i == len(pts) - 1) or (abs(pt['Translate'][0] - final_pt_x) < 0.05 and abs(pt['Translate'][1] - final_pt_y) < 0.05)
            if wf >= 120 and not is_end:
                stage_pauses.append({
                    'stage': st,
                    'kind': f'WaitFrame ({wf}f)',
                    'pt': i,
                    'x': pt['Translate'][0],
                    'stop_key': pt['Translate'][0] + HALF_W_16_9,
                    'margin': abs(pt['Translate'][0] - final_pt_x)
                })

        # 2. Plateaus (consecutive identical points on autoscroll rail)
        for i in range(len(pts) - 1):
            p1 = pts[i]['Translate']
            p2 = pts[i+1]['Translate']
            if abs(p1[0] - p2[0]) < 0.01 and abs(p1[1] - p2[1]) < 0.01:
                is_end = (i + 1 == len(pts) - 1) or (abs(p1[0] - final_pt_x) < 0.05 and abs(p1[1] - final_pt_y) < 0.05)
                if not is_end:
                    d1 = pts[i].get('Dynamic', {})
                    d2 = pts[i+1].get('Dynamic', {})
                    dur = 0
                    if 'PassingFrame' in d2 and 'PassingFrame' in d1:
                        dur = d2['PassingFrame'] - d1['PassingFrame']
                    elif 'SectionFrame' in d1:
                        dur = d1['SectionFrame']
                    if dur >= 120:
                        stage_pauses.append({
                            'stage': st,
                            'kind': f'Plateau pts {i}->{i+1} ({dur:.0f}f)',
                            'pt': i,
                            'x': p1[0],
                            'stop_key': p1[0] + HALF_W_16_9,
                            'margin': abs(p1[0] - final_pt_x)
                        })

        # 3. PulledWaitFrame / start delay on AutoScroll actor
        pwf = a.get('Dynamic', {}).get('PulledWaitFrame', 0)
        if pwf >= 120:
            start_x = pts[0]['Translate'][0]
            stage_pauses.append({
                'stage': st,
                'kind': f'PulledWaitFrame ({pwf}f)',
                'pt': 0,
                'x': start_x,
                'stop_key': start_x + HALF_W_16_9,
                'margin': abs(start_x - final_pt_x)
            })

        all_stage_data.append({
            'stage': st,
            'root_hash': root_hash,
            'end_key': end_key,
            'label': lbl,
            'final_pt_x': final_pt_x,
            'pauses': stage_pauses
        })

    # Filter to ONLY areas with intermediate pauses >= 120 frames
    needed_entries = [d for d in all_stage_data if len(d['pauses']) > 0]
    return needed_entries, all_stage_data


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: python scan_autoscroll_ends.py <extracted_romfs_path>")

    needed, all_data = scan_autoscroll_ends(sys.argv[1])

    print("# Autoscroll end stops: (RootAreaHash, end key). Key = rail final point X + 16:9 view half-width (27.5556 / 2).")
    print("# Only areas with intermediate pauses >= 120 frames are included. Terminated by hash 0.")
    print("AUTOSCROLL_ENDS = [")
    for d in needed:
        comment = f"# {d['stage']}"
        if d['label']:
            comment += f" ({d['label']})"
        print(f"    ({d['root_hash']}, {d['final_pt_x']:.2f} + 27.5556 / 2),".ljust(47) + f"{comment}")
    print("]")

    print("\n# Margin check for included areas (threshold > 0.05 blocks):")
    for d in needed:
        min_margin = min(p['margin'] for p in d['pauses'])
        print(f"# {d['stage']:18s}: min margin = {min_margin:8.4f} blocks")
        assert min_margin > 0.05, f"Conflict in {d['stage']}: margin {min_margin} <= 0.05!"
