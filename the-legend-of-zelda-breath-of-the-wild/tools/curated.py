"""Curated per-layout decisions for the BOTW 4:3 build (starts empty; filled in as layouts are reviewed)."""
import os
# Free-floating selector layout(s): names listed here are left byte-identical to stock in EVERY pass (no root scale,
# no children pass). The game builds the corner frame from the target's already-compressed rect, so our own 0.75 on
# Pa_Cursor_00 compressed it twice (corner triangles inside the box). BOTW_CURSOR_KEEP=<empty> restores the old
# (0.75) behaviour for an A/B build.
CURSOR_ROOT_KEEP = {n for n in os.environ.get('BOTW_CURSOR_KEEP', 'Cursor_00').split(',') if n}

ROOT_SKIP = {                            # Pa* parts no prt1 references: game code instantiates them as children, so they stay (1,1) like every other part
    'PaAllControllerTipsNN_00','PaAppMapTemp_00','PaAppMapTime_00','PaCommonBtnTitle_00','PaDoCommandKeyNNA_00','PaDoCommandKeyNNB_00','PaDoCommandKeyNNC_00','PaMapIconKolog_00','PaMessageTipsDrcImageNN_00','PaMessageTipsDrcImgAmiiboNN_00','PaPlayerStatusUp_00','PaShortCutIconCrossNN_00','PaTitleBtn_00'}
NO_SHIFT_LAYOUT_ALL = set(ROOT_SKIP)     # layouts that only get the root scale (no fill, no shifts)
NO_SHIFT_LAYOUT = set()                   # layouts that get root scale + fill but no edge shifts
PA_SHIFT = {                              # unreferenced Pa* layouts that should still get edge shifts
    # real top-level screens despite the Pa prefix: pause-menu info page and cooking recipe page
    'PauseMenuInfo_00', 'PauseMenuRecipe_00',
}
FORCE_SHIFT = {                           # layout -> {pane names to shift whatever the rules say}
    # bottom dialog sheet (276 tall, just over the small-strip threshold); its capture source moves with it
    'AppSystemWindow_00': {'N_All_00', 'N_Capture_00'},
    # --- HUD review (sec/hud) ---
    # top-centre info strip shares y=190 with Pa_LocationName_00 / Pa_QuestName_00 (both edge-shifted); it was skipped only
    # because its own box (h=40) stays under the 252 threshold, which would leave it 120 lower than its siblings
    'MainScreen_00': {'Pa_Information_00'},
    # loading screen top-left text T_DummyText_00 (y=250) hangs under N_RegionTypePos_00 (ty 16 + RegionType TransY
    # keys), so the container walk never reached it: shift the container (its keys move with it)
    'Fade_00': {'N_RegionTypePos_00'},
    # DRC-base position of the heart gauge in the "MS" and one-hit-KO HUDs (N_Pos_00 is already shifted; the gauge's own
    # base at (0,220) was not, its far edge 245 < 252)
    'MainScreenMS_00': {'Pa_HeartGauge_00'},
    'MainScreenHeartIchigekiDLC_00': {'Pa_HeartGauge_00'},
    # bottom-centre horse spur pips: row y=-220 (far edge -247, just under the threshold) sits in the same row as
    # Pa_TempMeter_00 (-222) which IS shifted; shift the pips too (parents at ty 0 -> shift is in layout units)
    'MainHorse_00': {'N_InOut_01', 'N_InOut_02', 'N_InOut_03', 'N_InOut_04', 'N_InOut_05', 'N_InOut_06', 'N_InOut_07',
                     'N_InOut_08', 'N_InOut_12', 'N_InOut_13', 'N_ExtraIn_00'},
    # stacked on top of Pa_Sensor_00 in the right column (x=392); the siblings moved -120, so must the meter
    'EnergyMeterDLC_00': {'N_EnergyMeterDLC_00'},
    # Wolf Link bottom-left heart gauge (far edge -247): whole group moves; N_InOut_00 sits at ty=+10 so the sign is forced
    'WolfLinkHeartGauge_00': {'N_Capture_00', 'N_InOut_00'},
    # capture source/use pairs that must move together (verify.py section 10). Stock: the use panes sit on
    # exactly the source rect; the generic rules moved only one side.
    'MessageSp_00': {'N_CaptureHigh_00', 'N_Capture_00',    # sources were 'pivot split' (text counter-translated),
                                                            # but the window + 5 use panes moved: source text left behind
                     'N_SunLight_00'},                      # holds the circuit-arc end caps Nt_MsgDeco_09/02 at y=-235 (null
                                                            # container, under the 252 threshold): they stayed ~120 above the pill
    # speaker-name plate (N_NameS_00: P_Sh_00 + T_Name_*, y=-174; centre+half height 194 < 252, so it stayed ~75 above
    # the box) and its capture source N_Capture_00; the dialog box W_Base_*/W_SysBase_* (y=-235) is edge-shifted
    'Message_00': {'N_NameS_00', 'N_Capture_00'},
    'DemoName_00': {'N_InOut_00'},          # holds P_Sh_00/P_Light_00/P_SubText_00/P_Name_00 (centre y=-240 < edge threshold)
    'DemoNameEnemy_00': {'N_In_00'},        # holds P_BigTextSh_00/P_Light_01/P_BigText_0x (centre y=-220)
    'HardModeTextDLC_00': {'N_InOut_00'},   # holds P_BigTextSh_00, partner of N_Capture_01 (edge-shifted)
    'SystemWindow_01': {'N_HardModePos_00'},  # holds P_BigTextSh_00 + T_DummyText_01, partner of N_Capture_01
    # --- Sheikah-slate review (sec/sheikah) ---
    # bottom-right toast (360x80 at y -186, flush with the right edge, 134 above the bottom): corner-anchored,
    # just under the strip threshold; capture source N_Capture_00 and the whole N_InOut_00 group move together
    'AppSystemWindowNoBtn_00': {'N_Capture_00', 'N_InOut_00'},
    # 512x288 capture rect that sits exactly on the mini-map pose of N_MiniMap_00 (410,-216, scale 0.4, flush
    # with the bottom edge); 288 > SMALL_H so the rules skip it. N_MiniMap_00's final pose moves via LAST_KEY_SHIFT.
    'AppMapDungeon_00': {'N_Capture_01'},
}
FORCE_SIGN = {                            # layout -> {pane: +1/-1} direction for FORCE_SHIFT panes whose own centre is near 0
    'WolfLinkHeartGauge_00': {'N_InOut_00': -1},
}
NO_SHIFT_SUBTREE = {                      # layout -> {pane names whose subtree stays in place}
    # title / boot art: logos stay where they are (guide: "leave logos in place")
    'Title_00': {'Logo_W_00', 'Logo_W_00_JPja', 'N_Capture_01'},
    'BootUp_00': {'Logo_W_03', 'Logo_W_00_JPja_02'},
    # pause info page: the generic small-block rule (|ay|+h/2 >= 252, h <= 266) caught blocks that are NOT
    # edge-anchored. Pa_HaveNum_00: prt1 box 240x244 at y=146 whose real text sits at y 44..176, same column
    # (x~84) as the unshifted Ganbari/Sp/TempMeter/SetBonus panes. N_CaptureSlideInfoR_0x / P_CaptureSlideR_0x:
    # 50x200 right-of-screen slide-seam strips at y=-170 belonging to the unshifted info panel (Pa_Gear_00).
    'PauseMenuInfo_00': {'Pa_HaveNum_00', 'N_CaptureSlideInfoR_00', 'N_CaptureSlideInfoR_01',
                         'P_CaptureSlideR_00', 'P_CaptureSlideR_01'},
    # --- Sheikah-slate review (sec/sheikah) ---
    # focus-reticle bracket pieces: the *_01 pieces of RT/LB were authored anchored the other way round and fall
    # just over the 252 strip threshold at y +-257; the other six bracket pieces are not edge items. Moving two
    # of eight pieces breaks the reticle (RT_01 +120, LB_01 -120 against their siblings).
    'AppCamera_00': {'P_JudgmentRT_01', 'P_JudgmentLB_01'},
    # N_SunLight_00 is a wrapper whose only child P_3DSh_01 counter-translates back to the 3D rect (abs y -5).
    # The edge rule moved the wrapper +120 and dragged the (already filled) child to [-365,595]; its twins
    # P_3DSh_00/P_3D_00 sit at [-485,475]. N_Pos_00 / N_PosBase_00 are off-screen measuring anchors (y 505 / 446,
    # N_PosBase x 852): moving them has no visual purpose and may be read by game code, so they stay as authored.
    'AppMapDungeon_00': {'N_SunLight_00', 'N_Pos_00', 'N_PosBase_00'},
    # the sensor pill's own pose is shifted INSIDE PaAppMapSensor_00 (PART_SHIFT_Y) so that the full-screen
    # 'born' popup of that part stays centred; shifting the parent as well would double-move the pill.
    'AppPictureBook_00': {'N_MapPos_00'},
}
NO_FILL = {                               # layout -> {pane names not filled}
    # Link-with-bow cut-outs (732x800 art): the generic height-only fill stretched them 1.33x -> keep stock
    'Title_00': {'TitleBG_01', 'P_ImageArrow_00'},
    # DLC illustration picture (906x914): height-only fill stretched it; it grows uniformly instead (UNIFORM_GROW)
    'DLCWindow_00': {'WUPP_ALZ_illu06_1_R_ad-0'},
}
NO_UNIFORM = {}                           # layout -> {pic1 names that must NOT grow in width (height only)}
EXTEND_TO_EDGE = {}                       # layout -> {strip pane names grown outward by the edge shift}
FORCE_FILL = {                            # layout -> {pane: 'h'} off-centre full-screen backdrops the
    # generic rule skips (|ay|>10): grow height by K anyway. Both are dark backdrops, not captures.
    'ErrorViewer_00': {'W_Shadow': 'h'},       # 760-tall wnd1 at ay=-12 -> 1013
}
# Capture policy. FBLayout panes are screen-capture USE panes; their SOURCE (pan1 N_Capture*, same rect) defines
# the copied framebuffer rectangle. The use pane must be drawn at the source's size or the capture is stretched.
#   'match'       sources and uses keep their original size (correct whether or not the root scale reaches the
#                 capture rect, and whether the game reads local size as pixels or as scaled layout units);
#                 full-screen capture backdrops cover the central 3/4 of the 4:3 height only.
#   'grow_source' sources AND uses grow together by K (full coverage; needs the capture rect to follow
#                 root scale x pane size, i.e. rect = size * root scale).
CAPTURE_POLICY = 'fullframe'
#   'fullframe'   (children mode) framebuffer-copy SOURCES keep their stock local size (the engine copies a rect of
#                 the source's LOCAL size at its global centre); every FBLayout USE pane keeps its stock PROJECTED
#                 size: local h = stock h / ROOT_SY^n, n = number of 0.75-scaled panes in its parent chain (code-scaled
#                 panes are forced to scale 1 by the game and do not count). Full-frame backdrops therefore project to
#                 exactly 720 (960 local under a 0.75 parent, 720 local as a code-scaled direct child).
#                 In root mode this behaves like 'match'.

# ---- Sheikah-slate window: the 608 high scanning window becomes 608 + 2*DELTA = 848 so it still meets the
#      edge strips (walls / moya / deco text bars) that moved out by DELTA. Everything that is the same window
#      (vignettes, scissor/clip, overlays) gets the same exact height. NON-capture panes only: capture
#      source/use pairs keep CAPTURE_POLICY (see the notes at PaAppMapSensor_00 in PART_FILL).
WINDOW_H = 848.0
EXACT_H = {                               # layout -> {pane: exact height, grown around the pane centre}
    'AppCamera_00':      {'W_Shadow_00': WINDOW_H, 'N_Scissor_00': WINDOW_H},
    'SeekPadMenuBG_00':  {'W_Shadow_00': WINDOW_H},
    'AppMap_00':         {'W_Shadow_00': WINDOW_H, 'P_VisitMark_01': WINDOW_H},
}
LAST_KEY_SHIFT = {                        # layout -> {pane: dy}: final pose of a multi-key TransY curve moves by dy
    # mini-map poses: the clip windows land in the bottom-right corner (AppMap_00 at (510,-240), 166x166;
    # AppMapDungeon_00 at (410,-216), flush with the bottom edge) and must keep their distance from the edge.
    'AppMap_00': {'N_Cut_00': -120.0, 'N_Cut_01': -120.0},
    'AppMapDungeon_00': {'N_MiniMap_00': -120.0},
}
PART_FILL = {                             # referenced part layout -> {pane: mode}
    # modes: 'h' height xK, 'u' uniform xK, 'H' height grown to exactly PART_FILL_H (default
    # 2*HALF_VIS), 'U' same but uniform. No TransY/SizeH anim on any of these panes (checked
    # against all bflans of each part).
    'PaSeekPadScanningLine_00': {'P_BootBG_00': 'h'},       # White8 dim 1280x720, camera/scope backdrop
    # (PaCameraPointer_00 scope vignettes 320x608 / 1280x608 are window-sized, NOT captures (textures CameraPointerL/R_00,
    #  wnd1): PART_EXACT_H below -- sheikah's 848 replaces the base 'H' (960) fills)
    # PaAppMapSensor_00 'born' popup: full-screen backdrops centred on the screen at every use site.
    # MERGE DECISION: P_FBLayout_00 (FBLayout use pane, 1280x720, same rect as source N_Capture_02) is NOT grown
    # (dpad 'match' policy: capture use panes keep the size of their source); P_CaptureBorn_00 and the other
    # panes carry no FBLayout texture and stay sheikah's 'u'/'h' fills.
    'PaAppMapSensor_00': {
        'P_BG_00': 'u', 'White8_00': 'u', 'P_BG_01': 'u', 'P_Abstract_00': 'u',
        'P_Abstract_01': 'u', 'P_CaptureBorn_00': 'u', 'P_Born_01': 'u'},
    'Pa_AppMapOpenEf_00': {'P_CaptureBorn_00': 'u', 'P_BornBg_00': 'u'},
}
# FBLayout use panes in parts, with their same-part source (grown only under CAPTURE_POLICY == 'grow_source').
# PaPauseQuest_00/P_CaptureMask_00 has no source inside the part: never grown (its source lives in the parent).
PART_CAPTURE_FILL = {
    'PaSystemWindow_02': {'P_Capture_00': 'h', 'N_Capture_00': 'h'},
    'PaDLCTipsBefore_00': {'P_Light_01': 'h', 'N_Capture_00': 'h'},
    'PaAppMapSensor_00': {'P_FBLayout_00': 'h', 'N_Capture_02': 'h'},   # merge: sheikah's P_FBLayout_00 fill, source added (untested variant)
}
if CAPTURE_POLICY == 'grow_source':
    for _k, _v in PART_CAPTURE_FILL.items():
        PART_FILL.setdefault(_k, {}).update(_v)
PART_EXACT_H = {                          # referenced part layout -> {pane: exact height}
    # MERGE DECISION: P_ScanningLine_00 is an FBLayout capture USE pane (1280x608); growing it to 848 without a matching
    # source stretches/blurs the capture (dpad rule), so it keeps its stock size. The frame walls still move out 120;
    # the window-to-wall gap is exempted in verify (CONT_EXEMPT).
    'PaCameraPointer_00': {'P_CameraPointerL_00': WINDOW_H, 'P_CameraPointerR_00': WINDOW_H,
                           'W_Shadow_00': WINDOW_H},               # scope vignettes = the same window
    'PaAppMapSensor_00': {'W_Shadow_00': WINDOW_H},                # popup vignette = same window
}
PART_SHIFT_Y = {                          # part -> {pane: signed dy in layout units}; use sites may be off-origin
    # sensor pill (bottom-right HUD row, same row as Comp/Time/Temp which moved -120). Only the pill group
    # moves; the popup backdrops (N_Capture_01/02, N_BornBg_*) stay centred on the screen. N_BornPos_00's
    # BornMove end pose moves with it (start pose = popup centre is the first key / a single-key curve).
    'PaAppMapSensor_00': {'N_Capture_00': -120.0, 'N_InOut_00': -120.0, 'N_BornEf_00': -120.0,
                          'N_BornPos_00': -120.0},
}
PART_TY_SCALE = {                         # part -> {pane: factor on TransY (static + all keys + slopes)}
    # scope light-sweep bars travel the window height: stretch their travel with the window (848/608)
    'PaCameraPointer_00': {'P_AbstractL_00': WINDOW_H / 608.0, 'P_AbstractR_00': WINDOW_H / 608.0},
}
PART_GROW_H = {                           # part -> {pane: height added around its centre}; no SizeH/TransY anim allowed
    # Round 10 (played and checked): map player locator (PaMapPlayer_00, only user AppMap_00/Pa_PlayerNavi_00). The code
    # reads N_PosSize_00 by name as the box the locator bubble is clamped to and shown outside of. Stock 1200x590 = the 720
    # view minus 65 per edge; the 4:3 map view is 960 tall, so the box grows by 2*120 (65 per edge kept). With the stock box
    # the bubble showed pinned 237 units above centre while Link's own icon was visible above it.
    'PaMapPlayer_00': {'N_PosSize_00': 240.0},
}
PART_FILL_H = {}                          # exact target height for 'H'/'U' modes (default 2*HALF_VIS)
# N_Deco_00 corner/edge ornaments of the Sheikah frame: every piece is a corner-anchored picture whose outer
# edge touches y=+-360. Each piece moves rigidly by DELTA towards its own edge (top group +, bottom group -), so
# corner caps keep touching their side segments and nothing is stretched (textures keep their aspect).
FRAME_CORNERS = ({f'P_BlurSh_{i:02d}' for i in range(7)} | {f'P_Core_{i:02d}' for i in range(7)}
                 | {f'P_Abst_{i:02d}' for i in range(7)} | {f'P_Alb_{i:02d}' for i in range(10)}
                 | {f'P_Ind_{i:02d}' for i in range(9)} | {f'P_Em_{i:02d}' for i in range(6)})
PART_SHIFT = {                            # referenced part layout -> {pane names edge-shifted by DELTA}
    # bottom-left location-name banners (users: MainScreen_00 / MainDungeon_00, both at layout origin); N_Capture_00
    # (text capture source, centred) stays
    'PaLocationNameS_00': {'N_In_00'},
    'PaLocationNameHokoraS_00': {'N_In_00'},
    # loading screen (Fade_00) logo + load bar, bottom-right; only user Fade_00/Pa_LoadBar_00 (chain 0.75)
    'PaFadeBar_00': {'P_TitleLogo_00', 'P_BarUS_00', 'P_JPBase_00', 'P_BarJP_00', 'P_CNTWBase_00', 'P_BarCNTW_00'},
    # shrine-camera pin row at the bottom of the viewfinder (y=-255 in part space)
    'PaCameraPointer_00': {'Pa_Pin_00', 'Pa_Pin_01', 'Pa_Pin_02', 'Pa_Pin_03', 'Pa_Pin_04'},
    # bottom-right weather HUD cluster (only user: MainScreen_00)
    'PaWeather_00': {'N_InOut_00'},
    # DLC notice bottom buttons (prt1 at layout origin in DLCWindow_00); caption T_TextDLC_00 stays on the art
    'PaDLCTipsBefore_00': {'Pa_BtnL_00', 'Pa_BtnC_00'},
    # scanning-line strips/text bars that touched the 16:9 edge (users: AppCamera/AppHome/PaCameraPointer)
    'PaSeekPadScanningLine_00': {
        'P_MoyaU_01', 'P_MoyaD_01', 'P_WallU_00', 'P_WallD_00',
        'N_CaptureText_01', 'N_Capture_01', 'T_DecoU_00', 'T_DecoD_00', 'N_Align_00',
        # use panes of N_CaptureText_01/N_Capture_01 (same rect y=320) -- dpad; sheikah lists the same two
        'P_Sh_00', 'P_Text_00',
        # moya haze strips anchored to the old +-304 window edge -- sheikah
        'P_MoyaU_00', 'P_MoyaD_00'} | FRAME_CORNERS,
    # bottom dialog sheet embedded in AppMap_00 (276 high, flush with the bottom); same treatment as the
    # top-level AppSystemWindow_00 (FORCE_SHIFT above) -- sheikah
    'PaAppSystemWindow_00': {'N_Capture_00', 'N_All_00'},
    # sensor-setting sheet (1880x276 at y -185 = [-323,-47], 37 px above the bottom edge; users AppMap_00 and
    # AppMapDungeon_00 at the layout origin). Same 276 px sheet family as the system window; it sits over the
    # bottom HUD row (Comp/Time/Temp/sensor pill, all moved -120), so it moves with it. N_Capture_00 is the
    # capture source of the title text (same y as T_SensorTitle_00/P_Sh_00). -- sheikah
    'PaAppMapSensorSetting_00': {'N_All_00', 'N_Capture_00'},
}





# ---------------------------------------------------------------------------------------------
# Root-scale mechanism.
#   'root'     : RootPane scale Y = 0.75 (original technique).
#   'children' : RootPane stays (1,1); every DIRECT child of RootPane of a top-level layout gets
#                TransY x0.75 and ScaleY x0.75 (static + every TransY/ScaleY key and slope), which is
#                geometrically identical to the root scale.  Why it exists: the game's own code writes
#                RootPane scale ((S,S/2) or (1,1), see REPORT.md: 0x1a38860 and ~20 overrides), so a
#                root scale authored in the BFLYT can be overwritten at runtime.
# Environment variable BOTW_ROOT_MODE overrides this value (used to build both variants).
import os as _os
ROOT_MODE = _os.environ.get('BOTW_ROOT_MODE', 'children')
assert ROOT_MODE in ('root', 'children'), ROOT_MODE

# Pane names whose ScaleX/ScaleY the game CODE overwrites (found by static scan of main:
# findPane(name) result stored to pane+0x48/+0x4c, see REPORT.md section 2).  In 'children' mode a
# direct child with one of these names does NOT receive the scale factor itself (the game would
# replace it with (1,1)/(S,...)); the factor is pushed down to its own children instead and the pane
# gets TransY x factor and SizeH x factor so that attach/size geometry stays equivalent.
CODE_SCALE_PANES = {
    'N_All_00', 'N_BlurIn_00', 'N_CaptureBG_01', 'N_CaptureBlur_00', 'N_Capture_00', 'N_CopyRight_00',
    'N_InOutDemo_00', 'N_InOut_00', 'N_LoopLD_00', 'N_LoopLT_00', 'N_LoopRD_00', 'N_LoopRT_00',
    'N_SetOff_00', 'P_BG_00', 'P_Black_00', 'P_CaptureMask_00', 'P_CaptureSlideR_00', 'P_CaptureSlideR_01',
    'P_Capture_00', 'P_Capture_01', 'P_Grad_00', 'Pa_Temp_01', 'Pa_Time_01', 'T_Text_00', 'T_Time_00',
    # Pause-menu page containers (PauseMenu_00 / PauseMenuBG_00 root children); factor goes to their children.
    # (Round 6 blamed these for the Memories overlap; the real cause is NO_SCALE_SUBTREES below, round 7.)
    'N_Slide_00', 'N_Slide_01', 'N_Slide_02',
}
# Subtrees left completely at stock scale/translation/size (not even pushed down to children).
# PauseMenu_00/N_InOutQuest_02 holds Pa_Quest_00 (Adventure Log page). With ScaleY 0.75 on it, on Pa_Quest_00, or on the
# root children inside PaPauseQuest_00, the Memories list rows #6+ draw on top of #5. Found in round 7 by in-game bisect
# (pack-only tests: all pause layouts stock = clean; only PauseMenu_00 stock = clean; only N_InOutQuest_02 stock = clean).
NO_SCALE_SUBTREES = {'PauseMenu_00': {'N_InOutQuest_02'}}
NO_SCALE_NAMES = set().union(*NO_SCALE_SUBTREES.values())   # pane names (unique across layouts) skipped by build/verify visit rules
# Round 9: the stock Adventure Log page is squeezed to 0.75 width by the game but keeps full height, so its text and art
# looked narrow. PART_SQUASH_Y = {part layout: {direct children of its RootPane}} gives those panes ScaleY and TransY x0.75
# (static + keys) about the part centre, BELOW the levels round 7 ruled out (N_InOutQuest_02, Pa_Quest_00, all
# PaPauseQuest_00 root children at once). Each part here is used by exactly one layout, at the origin.
# Never squashed: Null_00 (full-height art), Null_01 (P_CaptureMask_00, full-frame mask), N_Cut_00 (list container/clip).
# Squashed: detail panel (frames, title/NPC/place/caption, Memories preview, CLEAR stamp capture), category tabs, and the
# five list row slots (row pitch 70 -> 52.5). Played and checked: quest list + description (no more mid-word cut-off) and
# Memories with rows #6/#7 below #5 (no overlap). Two other variants were built for the bisect and not needed: panel only,
# and row contents only (PaChallengeListBtn_00 N_Born_00 + B_Hit_00, pitch kept).
PART_SQUASH_Y = {
    'PaPauseQuest_00': {'N_Type_00', 'N_TypeDemo_00', 'N_Capture_00', 'W_Base_00', 'W_Base_01', 'W_Base_02', 'N_Category_00'},
    'PaPageChallenge5_00': {f'Pa_Btn_{i:02d}' for i in range(5)},
}
# Gameplay-HUD enlargement (round 8): scale a HUD group by HUD_SCALE about a screen corner/anchor
# so it is as large as on 16:9 (1/0.75 = 1.3333) instead of 75% of it. {layout: {pane: (anchor_x, anchor_y)}}; anchors and
# pane translation are in the pane's PARENT-local units and the parent chain must have identity scale (true for children of
# the code-scaled N_All_00). BOTW_HUD_SCALE=1.0 turns it off.
HUD_SCALE = float(_os.environ.get('BOTW_HUD_SCALE', '1.3333333'))   # 1.0 = off (also the baseline build for verify check 20)
_TL, _BR = (-640.0, 360.0), (640.0, -360.0)                 # visible-canvas corners (layout units, parent chain identity)
HUD_PANES = {
    'MainScreen_00': {
        'N_State_00': _TL,                                      # hearts
        'Pa_SinJu_00': _TL, 'Pa_SinJu_01': _TL, 'Pa_SinJu_02': _TL, 'Pa_SinJu_03': _TL,   # Divine Beast gauges (left edge)
        'Pa_Sensor_00': _BR, 'Pa_SoundGauge_00': _BR, 'Pa_TempMeter_00': _BR, 'Pa_Time_00': _BR,   # sensor / noise / temperature / clock
    },
    'MainShortCut_00': {'N_MainAll_00': _TL},                   # weapon / shield / bow / arrow icons
}
# Pane names whose translation the game code writes (cannot be factored; reported only).
CODE_TRANS_PANES = {'N_Pos_00', 'N_Full_00', 'N_Gauge_00', 'N_DmcCapturePos_00', 'N_CopyRight_00',
                    'N_TextOut_00', 'T_TextBox'}
PIVOT_SPLIT = {                           # layout -> {pan1 containers never shifted whole; children judged separately}
    # N_State_01 sits at the bottom-left corner (-554,-314) and its child Pa_PlayerStatusUp_00 counter-translates
    # +608 to the TOP-left (abs y 294, under the hearts). The child is itself an edge pane, so the generic pivot
    # test ("child not edge") missed it and shifting the container moved the child 120 TOWARDS the centre (174).
    'PauseMenuInfo_00': {'N_State_01'},
}
PROP_GROW = {                             # layout -> {pane: 'h'} screen-proportional wnd1 decoration, height x K
    # (centre kept, no coverage requirement). Stock: 574-tall rule lines / 608-tall vignette inside a 720 screen.
    # 'SeekPadMenuBG_00': W_Shadow_00 'h' (608 -> 811) DROPPED in the merge: Sheikah-slate layout, sheikah's EXACT_H 848 wins
}

# Art that grows UNIFORMLY (width and height x K, centre kept): textured pictures that must keep their aspect.
# Title wallpaper slots 0 and 6: 1920x1080 sky + foreground at ty -30/-45, skipped by the generic fill rule (|ay|>10).
UNIFORM_GROW = {
    'Title_00': {'P_MainV_00', 'P_MainV_01', 'P_MainV_02', 'P_MainV_03',
                 'P_MainVOE_00', 'P_MainVOE_01', 'P_MainVE_00', 'P_MainVE_01'},
    'DLCWindow_00': {'WUPP_ALZ_illu06_1_R_ad-0'},
}
# Edge-anchored decoration that must move out WITH the header/footer rows: height += amount (pre-scale units), centre kept.
# (x K would scale the distance to the edge, not keep it.) PauseMenuBG_00: BlackBG 758 -> 998 (outer edges 480 / -518),
# W_Line rings 574 -> 814.
EDGE_GROW = {
    'PauseMenuBG_00': {'W_BlackBG_00': 2 * 120.0, 'W_Line_00': 2 * 120.0, 'W_Line_02': 2 * 120.0},
}
# Title wallpaper cut-outs (round 3): leaf panes under a 0.75 parent. Height x K alone is not enough: the leaf's own
# TransY (static + every key) must also be x K (parent carries 0.75; K*0.75 = 1 keeps the stock screen fraction).
# TransX/tx are NOT touched (right-anchored TitleBGLink keys are the exit from the screen).
UNIFORM_TY_GROW = {                        # layout -> panes grown uniformly x K by an own writer (TransY keys allowed)
    'Title_00': {'P_ImageArrow_00', 'TitleBG_01', 'P_Image_Gurdian_00', 'TitleBG_03', 'P_ImageHorse_00', 'TitleBG_02',
                        'TitleBG_04', 'TitleBG_06', 'TitleBGLink_00', 'TitleBGLink_01'},
}
LEAF_TY = {                                # layout -> panes whose static ty and TransY keys/slopes are x K
    'Title_00': {'P_ImageArrow_00', 'TitleBG_01', 'P_Image_Gurdian_00', 'TitleBG_03', 'P_ImageHorse_00', 'TitleBG_02',
                        'TitleBG_04', 'TitleBG_06', 'TitleBGLink_00', 'TitleBGLink_01',
                 'P_MainV_00', 'P_MainV_01', 'P_MainV_02', 'P_MainV_03',
                 'P_MainVOE_00', 'P_MainVOE_01', 'P_MainVE_00', 'P_MainVE_01'},
}
# live pane <-> capture-copy twin (must stay identical in the built layout)
TITLE_TWINS = [('P_ImageArrow_00', 'TitleBG_01'), ('P_Image_Gurdian_00', 'TitleBG_03'), ('P_ImageHorse_00', 'TitleBG_02'),
               ('TitleBG_04', 'TitleBG_06'), ('TitleBGLink_00', 'TitleBGLink_01'), ('P_MainV_00', 'P_MainV_02'),
               ('P_MainV_01', 'P_MainV_03'), ('P_MainVOE_00', 'P_MainVE_00'), ('P_MainVOE_01', 'P_MainVE_01')]
# CaptureBGColor (subtree-to-texture) sources that are full-frame glow layers: the source keeps its stock local size
# (the offscreen ortho is +-w/2 x +-h/2 of the LOCAL size), children keep the 0.75 pushdown, uses -> local h/0.75^n.
CAPTURE_BG_FULLFRAME = {'Title_00': {'N_Capture_00'}}
# panes whose SizeH (static and every key equal to 720) goes to the target: the Sheikah map scissor / capture uses
# (the 0.75 chain would clip the map to the middle 540 of 720). Keys at the mini-map pose (166/192/...) stay.
# Round 10 (played and checked): the capture SOURCES N_Capture_00-04 follow their uses (round 3 kept them at stock).
# Stock keeps each source and its use the same size in every pose (720 full map, 192 mini-map). With only the uses at 960
# the terrain and grid were 1.33x too tall (grid cells measured 77.5 x 103 px) and drifted against the correct map names
# and icons when panning; with source = use they are square again (311 x 310 px). Black8_01 (the map backdrop inside
# N_Capture_00) already reaches 960 through the generic fill.
MAP_CAPTURE_PAIRS = {'N_Capture_00': 'P_MapCapture_00', 'N_Capture_01': 'P_MapCaptureBlur_00',
                     'N_Capture_02': 'P_MapCaptureBlur_01', 'N_Capture_03': 'P_MapCaptureBlur_02',
                     'N_Capture_04': 'P_MapCaptureBlur_03'}
SIZEH_RETARGET = {
    'AppMap_00': {'N_Cut_00': 960.0, 'P_MapCapture_00': 960.0, 'P_MapCaptureBlur_00': 960.0, 'P_MapCaptureBlur_01': 960.0,
                  'P_MapCaptureBlur_02': 960.0, 'P_MapCaptureBlur_03': 960.0,
                  **{src: 960.0 for src in MAP_CAPTURE_PAIRS}},
}
# CaptureApplyScale framebuffer sources (only these two exist in the game: the D-pad icon-list edge masks, 90x98 under a
# 0.75 chain). The engine multiplies the copy rect by (parent scale x own scale) only when a global VR-type flag is on, so
# the build must be correct with the flag on AND off: local h = stock h x 0.75 and own ScaleY = stock / 0.75^n (n = number of
# 0.75-scaled ancestors). Flag off: rect = 73.5 units; flag on: 73.5 x 0.75 x 1.333 = 73.5. The use panes stay as they are.
CAPTURE_APPLY_INVARIANT = {'MainShortCut_00': {'N_Capture_00', 'N_Capture_01'}}
# plain capture sources whose height simply follows their 0.75-scaled host (static SizeH and SizeH keys x 0.75): the HUD icon
# base capture; its TransY is NOT changed (the code writes N_DmcCapturePos_00 itself).
SRC_H_SCALE = {'MainShortCut_00': {'N_DmcCapture_00'}}
# panes that must move exactly like an anchor pane of the same layout (verify.py check 17):
# layout -> (anchor pane, {followers}). MessageSp_00: the circuit-arc end caps hang off N_SunLight_00 and must stay
# centred on the pill W_Base_01.
SHIFT_FOLLOW = {'MessageSp_00': ('W_Base_01', {'N_SunLight_00'})}
# panes exempt from the "ends inside the 4:3 height" checks (reviewed overshoot)
OVERSHOOT_OK = {}
for _d in (FORCE_FILL, UNIFORM_GROW, EDGE_GROW, UNIFORM_TY_GROW, LEAF_TY):
    for _l, _n in _d.items():
        OVERSHOOT_OK.setdefault(_l, set()).update(_n)
# txt1 panes the game rescales by name (CODE_SCALE_PANES): when children_pass pushes SizeH x0.75 into them the glyphs
# must be squashed too (fontSizeY and lineSpace x0.75), or 3-line tips overflow their 0.75 box.
TXT_FONT_Y_LAYOUTS = {'MessageTipsRunTime_00', 'MessageTipsPauseMenu_00'}

CONT_EXEMPT = {'P_ScanningLine_00'}      # panes excluded from the frame-continuity check (capture-use window kept at stock size)


# ---- fullframe capture policy tables ----
# Layouts whose capture panes are masked map views / Sheikah windows: untouched by the capture pass.
CAPTURE_SKIP_LAYOUTS = {'AppMap_00', 'AppMapDungeon_00'}
# Use panes whose size the game code sets itself at runtime (slide seams): untouched.
CAPTURE_SKIP_PREFIX = ('P_CaptureSlide',)
# Part layouts whose FBLayout use pane is a framebuffer copy: pane -> same rule as top-level uses, with n taken from
# the host prt1's parent chain (all use sites must agree, build.py warns and skips otherwise).
PART_CAPTURE_USE = {
    'PaPauseQuest_00': ['P_CaptureMask_00'],     # source N_Capture_00 lives in PauseMenu_00
    'PaSystemWindow_02': ['P_Capture_00'],       # source N_Capture_00 in the part; host AppCamera_00
}


# ---- Stamina wheel (PaGanbariGauge_01 = circle, PaGanbariGaugeEx_00 = extra-stamina bar) ----
# The game code (class holding Pa_Ganbari_00 / Pa_GanbariEx_00, writes at 0x117c8e8 / 0x117cf24) overwrites both ScaleX and
# ScaleY of the host panes with one distance-based value (0.75..1.0), so a 0.75 on the host's ScaleY is lost and the wheel
# is drawn stretched. The squash lives in the part instead: the panes that hold every visible (capture-USE) picture of the
# part get ScaleY x0.75 (the CaptureOn sources stay stock; the uses just sample them into a flatter quad). The hosts'
# ScaleY is then put back to what the part-internal squash needs: net 0.75 everywhere (verify check 21).
PART_SY = {
    'PaGanbariGauge_01': {'N_All_00'},
    'PaGanbariGaugeEx_00': {'N_AllL_00', 'N_AllL_01', 'N_AllR_00', 'N_AllR_01'},
}
# layout -> {host pane: factor on its ScaleY applied AFTER the children pass}. MainScreen3D_00 hosts are direct root children
# (children pass already x0.75; x1/0.75 returns them to stock 1.0 because the part now squashes). PauseMenuInfo_00 hosts sit
# under a 0.75 chain (N_State_00), which the part would double: they get 1/0.75 so the chain nets 0.75 again.
HOST_SY_FACTOR = {
    'MainScreen3D_00': {'Pa_Ganbari_00': 1 / 0.75, 'Pa_GanbariEx_00': 1 / 0.75},
    'PauseMenuInfo_00': {'Pa_Ganbari_00': 1 / 0.75, 'Pa_GanbariEx_00': 1 / 0.75},
}
if os.environ.get('BOTW_GANBARI_FIX', '1') == '0':
    PART_SY, HOST_SY_FACTOR = {}, {}
