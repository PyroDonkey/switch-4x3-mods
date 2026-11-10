"""Stage (BancMapUnit) and Event (EventFlow) edits for the 4:3 mod: same-size float and guarded actor-type edits from the 1.2.1 originals.

usage:
  python build_stage.py <orig_romfs> <out_dir>
      Writes <out_dir>/romfs/BancMapUnit/<course>.bcett.byml.zs for every course in EDITS and
      <out_dir>/romfs/Event/EventFlow/<flow>.bfevfl.zs for every flow in EVENT_EDITS.
  python build_stage.py --verify <orig_romfs> <mod_romfs>
      Checks the shipped files in <mod_romfs>: exactly the declared courses/events, each differing from its
      original only in the declared edits. Exits 1 on any problem.

<orig_romfs> is the extracted 1.2.1 romfs (needs BancMapUnit/ and Event/EventFlow/).
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
    # Course290_Main (Bowser's Rage Stage - Kuribo grow & zap relay retuning for on-screen visibility & strike alignment):
    # Under opening camera G = 18.5 (view width 24.67), retune zap switches 1536962149 and 14869113733391977869 to X = 43.77
    # so they fire at rail X = 18.63 (frame 1040, view [18.63, 43.30]), framing all strike and smoke tags on-screen.
    # Retune spawn switch 578319643 to X = 36.48 so it activates at frame 657, preserving
    # the exact stock 383-frame relay interval (frame 1040 - 657 = 383f, drift 0.0f).
    # With 200f spawn delay (frame 857), Kuribos walk 183f before lightning strikes at frame 1040.
    # Calibrated against stock and Eden play-test: Goombas walk faster/further than nominal 1/32 blk/frame (reaching X ~ 38.3 & 42.3).
    # Align strike PositionTags and BadSmokeTags to where the Goombas actually are in Eden:
    # Goomba 1 at X = 38.28125 (tag 38.28125, smoke 38.03125); Goomba 2 at X = 42.28125 (tag 42.28125, smoke 41.53125).
    # Growth fires 30f later at frame 1070, fully on-screen in view [20.28, 44.95].
    ('Course290_Main', 578319643, 'CourseDisplayBoxSwitch', 'Translate',
     (38.5, 20.537498474121094, 0.0), (36.48, 20.537498474121094, 0.0)),
    ('Course290_Main', 1536962149, 'CourseDisplayBoxSwitch', 'Translate',
     (44.0, 34.051910400390625, 0.0), (43.77, 34.051910400390625, 0.0)),
    ('Course290_Main', 14869113733391977869, 'CourseDisplayBoxSwitch', 'Translate',
     (44.0, 33.16312026977539, 0.0), (43.77, 33.16312026977539, 0.0)),
    ('Course290_Main', 4814110068085501760, 'PositionTag', 'Translate',
     (43.25, 24.0, 0.0), (38.28125, 24.0, 0.0)),
    ('Course290_Main', 12276017923517845206, 'PositionTag', 'Translate',
     (46.25, 28.0, 0.0), (42.28125, 28.0, 0.0)),
    ('Course290_Main', 2306045187355644410, 'LastBossWonderBadSmokeTag', 'Translate',
     (43.0, 35.5, 0.0), (38.03125, 35.5, 0.0)),
    ('Course290_Main', 5602005781468990395, 'LastBossWonderBadSmokeTag', 'Translate',
     (45.5, 35.5, 0.0), (41.53125, 35.5, 0.0)),
    # Shift Goomba spawns left by 3.5 blocks (Task D3) to align walking Goombas to bolt strikes at tags 38.28125 & 42.28125:
    ('Course290_Main', 2542738868, 'KuriboWillGrowIntoGiant', 'Translate',
     (46.0, 23.0, 0.0), (42.5, 23.0, 0.0)),
    ('Course290_Main', 1405933960, 'KuriboWillGrowIntoGiant', 'Translate',
     (50.0, 28.5, 0.0), (46.5, 28.5, 0.0)),
    # Course290_Main (Bowser's Rage Stage - Tilt, rolling spiked ball, fossil rings & dragon relay):
    # With the intro zoom G = 18.5 hold extended to fixed_X in [100.0, 112.0] (rail_X in [87.67, 101.50]), the 4:3
    # camera width is 24.67 (2.89 blocks narrower than stock 16:9 27.56, rather than 6.56 blocks narrower at G = 15.75).
    # Shift triggers firing during the G = 18.5 hold (1060316225, 206918284, 663300194, 17459050152995009628, 999420502,
    # 742103869, 1755951341) left by -2.89 blocks in X.
    # Shift triggers firing during the return lerp according to view width at activation:
    # - 1787195044 (dragon transform, frame 3031, W = 23.99) shifted by -3.57 blocks (X: 136.0 -> 132.43).
    # - 2303338937 (fossil palette, frame 3282, W = 23.27) shifted by -4.29 blocks (X: 121.0 -> 116.71).
    # This preserves 0-drift relative timing across the entire rolling obstacle and zap obstacle course.
    ('Course290_Main', 1060316225, 'CourseDisplayBoxSwitch', 'Translate',
     (73.5, 34.513580322265625, 0.0), (70.61111450195312, 34.513580322265625, 0.0)),
    ('Course290_Main', 206918284, 'CourseDisplayBoxSwitch', 'Translate',
     (81.5, 20.342161178588867, 0.0), (78.61111450195312, 20.342161178588867, 0.0)),
    ('Course290_Main', 663300194, 'CourseDisplayBoxSwitch', 'Translate',
     (88.5, 35.5, 0.0), (85.61111450195312, 35.5, 0.0)),
    ('Course290_Main', 17459050152995009628, 'CourseDisplayBoxSwitch', 'Translate',
     (89.5, 35.5, 0.0), (86.61111450195312, 35.5, 0.0)),
    ('Course290_Main', 999420502, 'CourseDisplayBoxSwitch', 'Translate',
     (90.5, 21.96936798095703, 0.0), (87.61111450195312, 21.96936798095703, 0.0)),
    ('Course290_Main', 742103869, 'CourseDisplayBoxSwitch', 'Translate',
     (98.52086639404297, 35.10392761230469, 0.0), (95.6319808959961, 35.10392761230469, 0.0)),
    ('Course290_Main', 1755951341, 'CourseDisplayBoxSwitch', 'Translate',
     (106.0, 19.168628692626953, 0.0), (103.11111450195312, 19.168628692626953, 0.0)),
    ('Course290_Main', 2303338937, 'CourseDisplayBoxSwitch', 'Translate',
     (121.0, 34.49203872680664, 0.0), (116.70992279052734, 34.49203872680664, 0.0)),
    ('Course290_Main', 1787195044, 'CourseDisplayBoxSwitch', 'Translate',
     (136.0, 26.0, 0.0), (132.43197631835938, 26.0, 0.0)),
    # Course290_Main (Bowser's Rage Stage - Vertical shaft ground & guide coins):
    # Switch 4273434636 (stock min_x = 146.50, missed by 4:3 right edge at 146.0) fires to spawn the bottom
    # horizontal snake-block ground (ObjectBlockSnakePole 34729090 at Y = 27.5..31.5) and guide coins before
    # the vertical shaft climb. Switches 1117151842, 3717095890, and 1344248650 spawn intermediate snake poles.
    ('Course290_Main', 1117151842, 'CourseDisplayBoxSwitch', 'Translate',
     (146.0, 32.5, 0.0), (139.44, 32.5, 0.0)),
    ('Course290_Main', 4273434636, 'CourseDisplayBoxSwitch', 'Translate',
     (152.5449676513672, 25.0, 0.0), (145.9849676513672, 25.0, 0.0)),
    ('Course290_Main', 3717095890, 'CourseDisplayBoxSwitch', 'Translate',
     (155.3033447265625, 47.0, 0.0), (148.7433447265625, 47.0, 0.0)),
    ('Course290_Main', 1344248650, 'CourseDisplayBoxSwitch', 'Translate',
     (155.8292236328125, 58.66417694091797, 0.0), (149.2692236328125, 58.66417694091797, 0.0)),
    # Course290_Main (Bowser's Rage Stage - Bowser statue section): SetAutoScrollPos left-aligns the 21.0-wide
    # 4:3 view to the autoscroll rail, cutting 6.56 blocks off the right edge vs stock 16:9 (27.56). Shift the
    # statue-section CourseDisplayBoxSwitch triggers left by 6.56 blocks in X so EnemyTossinGroup spawns during
    # the slow approach (pt 13->14, rail X 147.94) before the scroll reaches the statue at X = 156.5, and the
    # post-statue pause/Packun switch (12855344573256944945) enters the 4:3 view (max X 195.0) at rail X = 174.0.
    # Note: switch 4029477259 is intentionally kept at stock X = 206.00457763671875 (min_x = 202.82) so it fires
    # after the rhythm pause (pt 17 -> pt 18) instead of prematurely during the pause.
    ('Course290_Main', 777445035, 'CourseDisplayBoxSwitch', 'Translate',
     (198.0, 52.0, 0.0), (191.44, 52.0, 0.0)),
    ('Course290_Main', 212790001, 'CourseDisplayBoxSwitch', 'Translate',
     (223.04513549804688, 51.73638153076172, 0.0), (216.48513549804688, 51.73638153076172, 0.0)),
    ('Course290_Main', 12855344573256944945, 'CourseDisplayBoxSwitch', 'Translate',
     (199.5, 52.0, 0.0), (192.94, 52.0, 0.0)),
    # Course290_Main (Bowser's Rage Stage - Post-statue rhythm pause singing plants & pipes):
    # In 4:3 (width 21.0), with the rhythm pause plateau at rail X = 179.0, the camera frames X = [179.0, 200.0].
    # Shift the 3 left rising pipes (SoundRhythmObjectUpDownDokan) and 3 singing Piranha Plants (EnemySoundRunRunPackun)
    # right by +2.0 blocks (X = 178, 180, 182 -> 180, 182, 184) to pull them away from the left screen edge and frame
    # both the left singing group and the right Spike thrower (X = 199.0) simultaneously with 1.0 block margin.
    ('Course290_Main', 14018291091925094241, 'SoundRhythmObjectUpDownDokan', 'Translate',
     (178.0, 39.0, 0.0), (180.0, 39.0, 0.0)),
    ('Course290_Main', 18409431755698402034, 'SoundRhythmObjectUpDownDokan', 'Translate',
     (180.0, 39.0, 0.0), (182.0, 39.0, 0.0)),
    ('Course290_Main', 4568669752595535956, 'SoundRhythmObjectUpDownDokan', 'Translate',
     (182.0, 39.0, 0.0), (184.0, 39.0, 0.0)),
    ('Course290_Main', 1451404568616177091, 'EnemySoundRunRunPackun', 'Translate',
     (178.0, 47.0, 0.0), (180.0, 47.0, 0.0)),
    ('Course290_Main', 16407013882060977642, 'EnemySoundRunRunPackun', 'Translate',
     (180.0, 47.0, 0.0), (182.0, 47.0, 0.0)),
    ('Course290_Main', 1044554605811720563, 'EnemySoundRunRunPackun', 'Translate',
     (182.0, 47.0, 0.0), (184.0, 47.0, 0.0)),
    # Course290_Main (Bowser's Rage Stage - Fist & fossil section smoke coverage):
    # With G = 18.5 (view height 18.5, vertical range [18.00, 36.50]), expand the vertical coverage of the
    # background smoke planes by shifting bottom smoke actors down by -1.5 in Y and top smoke actors up by +1.5 in Y
    # so the smoke edges stay offscreen across both the opening fist and fossil sections.
    ('Course290_Main', 15192233820085708065, 'DVCommonTorideKemuriB', 'Translate',
     (5.3074798583984375, 19.16788673400879, -60.0), (5.3074798583984375, 17.66788673400879, -60.0)),
    ('Course290_Main', 1591783371223145825, 'DVCommonTorideKemuriB', 'Translate',
     (27.5, 18.5, -60.0), (27.5, 17.0, -60.0)),
    ('Course290_Main', 5984094973414626142, 'DVCommonTorideKemuriA', 'Translate',
     (-3.859537124633789, 36.74950408935547, -61.515625), (-3.859537124633789, 38.24950408935547, -61.515625)),
    ('Course290_Main', 10892834247364923251, 'DVCommonTorideKemuriA', 'Translate',
     (19.93733787536621, 36.85106658935547, -86.515625), (19.93733787536621, 38.35106658935547, -86.515625)),
    ('Course290_Main', 13067625065345285749, 'DVCommonTorideKemuriA', 'Translate',
     (56.0, 35.5, -60.0), (56.0, 37.0, -60.0)),
    ('Course290_Main', 7396728262115999967, 'DVCommonTorideKemuriB', 'Translate',
     (78.09263610839844, 20.79288673400879, -60.0), (78.09263610839844, 19.29288673400879, -60.0)),
    ('Course290_Main', 10206074945194904884, 'DVCommonTorideKemuriA', 'Translate',
     (99.5, 32.5, -60.0), (99.5, 34.0, -60.0)),
    # World001 (Pipe-Rock Plateau map), subregion 22 (underground area: sign, ? block, courses 9 and 10, KO arena):
    # the camera is fixed on WorldMapCameraLookAtTag obj479 at x 87.25 and never follows Mario. At that depth the
    # view is ~48 px per unit at ~1060 rows: 16:9 shows x ~67.6-106.9, 4:3 only ~72.5-102.0, so the hidden warp
    # pipe obj513 (x 103, to the lost-Toad room) and Mario's silhouette beside it (~104.5) were off the right edge.
    # Look-at x +4.0 -> 91.25 shows ~76.5-106.0: pipe and Mario on screen, entry pipe obj29 (opening ~78.5) kept.
    # Confirmed in Eden 2026-11-09.
    ('World001', 2929358336, 'WorldMapCameraLookAtTag', 'Translate',
     (87.25, -11.0, 24.5), (91.25, -11.0, 24.5)),
    # Course022_Main (W2 Outmaway Valley), Wonder autoscroll (rail x 445.25 -> 693.0, the rail point is the view's
    # left edge): the rolling snow hill knocks the goal pole down and carries it round, and the finish Wonder Seed
    # (obj8927, GravityOn at x 693.5) drops when CourseDisplayBoxSwitch obj8878 enters the view, timed to land on
    # the pole's tip. The 4:3 view is 21.0 wide (G 15.75) against 27.5556, so the box entered 6.5556 blocks of
    # scroll late and the seed missed the pole and fell out of the course. Moving each display-box switch of the
    # section left by 6.5556 makes it fire at the stock scroll position; the other two create the Mini Lucky
    # Coins bound to the rolling hill.
    ('Course022_Main', 3802668973, 'CourseDisplayBoxSwitch', 'Translate',
     (715.5, 9.0, 0.0), (708.9444, 9.0, 0.0)),
    ('Course022_Main', 14721847139351791685, 'CourseDisplayBoxSwitch', 'Translate',
     (574.5, 14.5, 0.0), (567.9444, 14.5, 0.0)),
    ('Course022_Main', 16130168003287809964, 'CourseDisplayBoxSwitch', 'Translate',
     (596.5, 13.5, 0.0), (589.9444, 13.5, 0.0)),
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
    # Course290_Main (Bowser's Rage Stage - Post-statue rhythm pause pipe gap):
    # Shift Wall 2 right boundary (pts 2-3) and Wall 5 left boundary (pts 0-1) right by +2.0 blocks in X so the gap
    # beneath the rising rhythm pipes moves from X = [177, 183] to [179, 185].
    ('Course290_Main', 0, 2, 2, (177.0, 47.0, 0.0), (179.0, 47.0, 0.0)),
    ('Course290_Main', 0, 2, 3, (177.0, 8.0, 0.0), (179.0, 8.0, 0.0)),
    ('Course290_Main', 0, 5, 0, (183.0, 42.0, 0.0), (185.0, 42.0, 0.0)),
    ('Course290_Main', 0, 5, 1, (183.0, 47.0, 0.0), (185.0, 47.0, 0.0)),
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
# Pt 12 (final stop): rail X is the view's LEFT edge (docs/DEVELOPMENT.md section 22, SetAutoScrollPos adds the current
# half-width), so the stock stop (226.75) frames [226.75, 247.75] in 4:3 versus [226.75, 254.31] in 16:9. The finale
# cannon ObjectBalloonKillerHodaiLeft (X = 251.5, body 251..252, IsFirstInCamera) was therefore 3.75 blocks past the
# 4:3 right edge and never started firing. The camera-margin value it tests is not stored in its AI graph, so the stop
# is taken from an Eden capture of a build with the cannon at X = 248.5 (body 248..249): there the cannon sat 0.335
# blocks inside the right edge (view [228.34, 249.34], measured from screenshots calibrated on the pole end block at
# 240.5) and had fired. The stock cannon body ends at 252.0, so stop X = 252.0 + 0.335 - 21.0 = 231.335 frames
# [231.335, 252.335]: whole cannon and Wall 5 (247..252) in view, pole end (X = 240.5) and Wonder Seed
# (240.5, 144.24) in view. The pole's first 0.8 blocks (ball at X 230.5) fall off the left edge: pole start to
# cannon centre is exactly 21.0, the 4:3 width, so both cannot be fully framed with the stock cannon.
# Y = 147.0 is untouched (rail Y is the view's top edge, so the pole at 133.5 and the cannon at 134.0 stay in frame).
RAIL_EDITS = [
    ('Course853_Main', 1776580222928036096, 0, (0.0, 17.0, 0.0), (0.0, 14.5, 0.0)),
    ('Course853_Main', 1776580222928036096, 1, (13.0, 17.0, 0.0), (13.0, 14.5, 0.0)),
    ('Course853_Main', 1776580222928036096, 2, (38.0, 25.5, 0.0), (38.0, 22.75, 0.0)),
    ('Course853_Main', 1776580222928036096, 3, (63.0, 41.0, 0.0), (63.0, 36.0, 0.0)),
    ('Course853_Main', 1776580222928036096, 12, (226.75, 147.0, 0.0), (231.335, 147.0, 0.0)),
    # In Course290_Main, AutoScrollControlSignalFrame (4286093022) on Rail 185828596 passes rail_X + current_half_width
    # to SetAutoScrollPos, left-aligning the 21.0-wide 4:3 view to rail_X and cutting 6.56 blocks off the right edge vs
    # stock 16:9 (27.56):
    # - Dragon & vertical shaft section (pts 8-11): pt 6 is kept at stock 92.0 to maintain the fossil relay timing.
    #   Shift pt 8 right to frame Wall 1 [113, 122] without pushing the player off Wall 0 (ends at X = 104), and shift
    #   pts 9-11 right by +3.28 so the 840-frame vertical shaft climb (CameraArea 3010860670, X = [124.75, 152.25])
    #   is centered at X = 138.78.
    # - Post-statue rhythm pause (pts 16-17): shift the rhythm pause plateau from 174.0 to 179.0 to frame
    #   X = [179.0, 200.0] in 4:3, fitting all 3 shifted singing plants/pipes ([179.0, 185.0]) and the Spike thrower
    #   (15920962010745316511 at X = 199.0) + right pipe (9780181108041827457 at X = 199.0) simultaneously with
    #   1.0 block of margin from both actor centers (180.0 and 199.0) to the screen edges.
    ('Course290_Main', 185828596, 8, (101.0, 35.0, 0.0), (102.0, 35.0, 0.0)),
    ('Course290_Main', 185828596, 9, (112.0, 35.0, 0.0), (115.28, 35.0, 0.0)),
    ('Course290_Main', 185828596, 10, (125.0, 35.0, 0.0), (128.28, 35.0, 0.0)),
    ('Course290_Main', 185828596, 11, (125.0, 60.0, 0.0), (128.28, 60.0, 0.0)),
    ('Course290_Main', 185828596, 16, (174.0, 60.0, 0.0), (179.0, 60.0, 0.0)),
    ('Course290_Main', 185828596, 17, (174.0, 60.0, 0.0), (179.0, 60.0, 0.0)),
]



# (course, unit_idx, belt_idx, point_idx, orig_xyz, new_xyz)
# In Course290_Main, BgUnits[0] has matching conveyor belt collision rails (BeltRails) that define the top surface
# of Wall 2 and Wall 5. Both Walls and BeltRails must be shifted together to keep the visual geometry and collision aligned.
BELT_EDITS = [
    ('Course290_Main', 0, 2, 2, (177.0, 47.0, 0.0), (179.0, 47.0, 0.0)),
    ('Course290_Main', 0, 2, 3, (177.0, 8.0, 0.0), (179.0, 8.0, 0.0)),
    ('Course290_Main', 0, 5, 0, (183.0, 42.0, 0.0), (185.0, 42.0, 0.0)),
    ('Course290_Main', 0, 5, 1, (183.0, 47.0, 0.0), (185.0, 47.0, 0.0)),
]




# (flow, event_name, param_name, byte_offset, orig_val, new_val)
# CourseDemo_PreFinalBattle (Course290 intro cutscene):
# Event50 is the final cutscene camera pose before gameplay handoff.
# Raise TargetYpos 27.5 -> 28.75 to match gameplay camera resting height (19.5 + 9.25 = 28.75)
# and hide Bowser Jr. parked at y ~19.5..20.1 behind the bottom letterbox bar (covers up to y 20.20).
EVENT_EDITS = [
    ('CourseDemo_PreFinalBattle', 'Event26', 'TargetYpos', 0x2A80, 27.5, 28.75),
    ('CourseDemo_PreFinalBattle', 'Event50', 'TargetYpos', 0x2D90, 27.5, 28.75),
]


def bfevfl(romfs, flow):
    return os.path.join(romfs, 'Event', 'EventFlow', f'{flow}.bfevfl.zs')


def bcett(romfs, course):
    return os.path.join(romfs, 'BancMapUnit', f'{course}.bcett.byml.zs')


def edits_by_flow():
    out = {}
    for e in EVENT_EDITS:
        out.setdefault(e[0], []).append(e[1:])
    return out


def edits_by_course():
    out = {}
    for e in EDITS:
        out.setdefault(e[0], {'actors': [], 'bg': [], 'belts': [], 'gyaml': [], 'rails': []})['actors'].append(e)
    for b_edit in BG_EDITS:
        out.setdefault(b_edit[0], {'actors': [], 'bg': [], 'belts': [], 'gyaml': [], 'rails': []})['bg'].append(b_edit)
    for belt_edit in BELT_EDITS:
        out.setdefault(belt_edit[0], {'actors': [], 'bg': [], 'belts': [], 'gyaml': [], 'rails': []})['belts'].append(belt_edit)
    for g_edit in GYAML_EDITS:
        out.setdefault(g_edit[0], {'actors': [], 'bg': [], 'belts': [], 'gyaml': [], 'rails': []})['gyaml'].append(g_edit)
    for r_edit in RAIL_EDITS:
        out.setdefault(r_edit[0], {'actors': [], 'bg': [], 'belts': [], 'gyaml': [], 'rails': []})['rails'].append(r_edit)
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

    for course, uidx, bidx, pidx, orig, new in course_edits.get('belts', []):
        unit = b.hash_entries(slots[uidx][2])
        belts = b.array_slots(unit['BeltRails'][2])
        belt = b.hash_entries(belts[bidx][2])
        pts = b.array_slots(belt['Points'][2])
        p = b.hash_entries(pts[pidx][2])
        node = p['Translate'][2]
        all_bpts = []
        for u in slots:
            unit_dict = b.hash_entries(u[2])
            if 'BeltRails' in unit_dict:
                for _, _, braw in b.array_slots(unit_dict['BeltRails'][2]):
                    belt_dict = b.hash_entries(braw)
                    if 'Points' in belt_dict:
                        for _, _, praw in b.array_slots(belt_dict['Points'][2]):
                            all_bpts.append(b.hash_entries(praw))
        sharers = [pt for pt in all_bpts if pt['Translate'][2] == node]
        assert len(sharers) == 1, f'{course} Unit {uidx} BeltRail {bidx} Pt {pidx}: Translate shared by {len(sharers)} points'
        cur = [v for _, v in b.vec3(p, 'Translate')]
        assert cur == list(orig), f'{course} Unit {uidx} BeltRail {bidx} Pt {pidx}: {cur}, expected {orig}'
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
    for flow, edits in edits_by_flow().items():
        dst_event_dir = os.path.join(out_dir, 'romfs', 'Event', 'EventFlow')
        os.makedirs(dst_event_dir, exist_ok=True)
        src = bfevfl(orig_romfs, flow)
        d = read(src)
        for ev_name, param, offset, orig_val, new_val in edits:
            assert struct.unpack_from('<f', d, offset)[0] == orig_val, f'{flow} {ev_name} {param}: expected {orig_val}'
            struct.pack_into('<f', d, offset, new_val)
            assert struct.unpack_from('<f', d, offset)[0] == new_val, f'{flow} {ev_name} {param}: expected {new_val}'
        out_path = bfevfl(os.path.join(out_dir, 'romfs'), flow)
        write(out_path, d)
        print('wrote', out_path)


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
            n_total = (len(edits.get('actors', [])) + len(edits.get('bg', [])) +
                       len(edits.get('belts', [])) +
                       len(edits.get('gyaml', [])) + len(edits.get('rails', [])))
            print(f'{course}: {len(diff)} byte(s) differ, all inside {n_total} edit(s)')
    for flow, edits in edits_by_flow().items():
        path = bfevfl(mod_romfs, flow)
        if not os.path.exists(path):
            problems.append(f'missing {path}')
            continue
        orig = read(bfevfl(orig_romfs, flow))
        ship = read(path)
        if len(ship) != len(orig):
            problems.append(f'{flow}: size {len(ship)} != original {len(orig)}')
            continue
        allowed = set()
        for ev_name, param, offset, orig_val, new_val in edits:
            if struct.unpack_from('<f', ship, offset)[0] != new_val:
                problems.append(f'{flow}: edited value {struct.unpack_from("<f", ship, offset)[0]} != {new_val}')
            allowed.update(range(offset, offset + 4))
        diff = {i for i in range(len(orig)) if orig[i] != ship[i]}
        if not diff:
            problems.append(f'{flow}: identical to the original')
        elif diff - allowed:
            problems.append(f'{flow}: {len(diff - allowed)} byte(s) changed outside the declared edits')
        else:
            names = ', '.join(f'{ev} {param} {old} -> {new}' for ev, param, _, old, new in edits)
            print(f'{flow}: {len(diff)} byte(s) differ, exactly {names}')
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
