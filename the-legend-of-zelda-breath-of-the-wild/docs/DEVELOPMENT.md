# Development log: The Legend of Zelda: Breath of the Wild 4:3

Dated log of how the mod got to its current state, kept for the reasoning behind each fix. **The current state is in [`../AGENTS.md`](../AGENTS.md)**; values here may be superseded by later sections. "Played and checked" means the tester confirmed it in game. Build snapshots named here (`previous_romfs_vN`, `installed_eden_backup_*`) are in the maintainer's workspace `extras` folder, not in the repo.

## Rounds 1-8 (2026-10, before the repo folder existed)

Built in the maintainer's workspace from the 1.6.0 originals, over several rounds of in-game feedback. The mod started as the maintainer's own "Nova Aspect Ratio 4x3 Native" (original copy kept in the workspace as `ORIGINAL_Nova Aspect Ratio 4x3 Native`).

- **Children mode.** The game overwrites RootPane's scale at run time, so a root scale of 0.75 in the BFLYT is lost. The build leaves RootPane alone and gives each direct child ScaleY and TransY x0.75 (static and animation keys). Panes the code rescales by name (`CODE_SCALE_PANES`) keep their own scale; the factor goes on their children and their SizeH. `BOTW_ROOT_MODE=root` still builds the old variant.
- **Capture policy `fullframe`.** Framebuffer-copy sources keep their stock size; every FBLayout use pane keeps its stock projected size (local h = stock h / 0.75^n, n = 0.75-scaled panes in its chain). verify check 11.
- **Cursor_00** stays byte-identical to stock: the game builds the corner frame from the target's already-compressed rect, so a 0.75 on the cursor compressed it twice. verify check 12.
- **Round 2:** `UNIFORM_GROW` (Title wallpaper, DLC art), `EDGE_GROW` (PauseMenuBG band rings +240), PaFadeBar_00/Fade_00 corner shifts, tip-text font height x0.75 (`TXT_FONT_Y_LAYOUTS`). Checks 13/14.
- **Round 3:** `LEAF_TY`/`UNIFORM_TY_GROW` (Title art), `CAPTURE_BG_FULLFRAME` (Title glow), `SIZEH_RETARGET` for the Sheikah map scissor and capture uses (the 0.75 chain would clip the map to the middle 540 of 720). An optional exefs patch raising the map code's view height 720 -> 960 was written and left disabled; it was never needed. Check 15.
- **Round 4:** `CAPTURE_APPLY_INVARIANT` (D-pad icon list edge masks, MainShortCut_00 N_Capture_00/01: h x0.75, ScaleY / 0.75^n, correct whether the engine's CaptureApplyScale flag is on or off), `SRC_H_SCALE` (N_DmcCapture_00). Check 16.
- **Round 5:** `FORCE_SHIFT` MessageSp_00 N_SunLight_00 (arc end caps of the system message pill), `SHIFT_FOLLOW`. Check 17.
- **Round 6:** N_Slide_00/01/02 added to `CODE_SCALE_PANES` (pause-menu page containers). Kept, but it was not the Memories fix. Check 18.
- **Round 7:** Adventure Log > Memories drew rows #6 and later on top of #5. Found by an in-game bisect with pack-only test builds (layouts reverted to stock one group at a time): only `PauseMenu_00/N_InOutQuest_02` at stock was clean; pushing its 0.75 to `Pa_Quest_00` or to all root children of `PaPauseQuest_00` stayed broken. `NO_SCALE_SUBTREES` leaves that subtree at stock. Resolution scale, post-processing and the shader cache were ruled out. Check 19. The code patch became the exact-4/3 variant in the same round.
- **Round 8:** HUD enlargement (`HUD_SCALE` 4/3, `HUD_PANES`): hearts, Divine Beast gauges and weapon/shield icons about the top-left corner; sensor, noise meter, temperature and clock about the bottom-right; static values and TransX/TransY/Scale keys. Restores the 16:9 pixel size (the UI was 75% of it). Check 20 compares against a build with `BOTW_HUD_SCALE=1.0`. Not enlarged: D-pad window (captures), stamina wheel, message and banner text, minimap circle (code-drawn), MainScreenMS/HeartIchigekiDLC hearts, Time_00.

## Stamina wheel and speaker name plate (2026-11-10, earlier session)

Developed in the workspace copy of the tools after the repo copy was taken, and found in the maintainer's Eden install; merged into the repo tools later the same day (the six affected layouts are byte-identical to that install).

- **Stamina wheel:** the code (writes at `0x117c8e8` / `0x117cf24`) overwrites both ScaleX and ScaleY of the hosts `Pa_Ganbari_00` / `Pa_GanbariEx_00` with one distance-based value, so a 0.75 on the host's ScaleY was lost and the wheel was drawn stretched. The squash moved into the parts (`PART_SY`: PaGanbariGauge_01 N_All_00, PaGanbariGaugeEx_00 N_AllL/R_00/01), and the hosts' ScaleY is compensated so every chain nets 0.75 (`HOST_SY_FACTOR`, MainScreen3D_00 and PauseMenuInfo_00). Check 21.
- **Speaker name plate:** Message_00 `N_NameS_00` (y -174, under the edge threshold) stayed about 75 units above the edge-shifted dialog box; it and its capture source `N_Capture_00` are now force-shifted with the box.

## Round 9: Adventure Log aspect (2026-11-10)

Tester report: quest menu text looked squished. Round 7 left the page at stock height while the game squeezes width to 0.75, so its text and art were 75% wide. Measured in a screenshot: quest text about 0.42 glyph height per character against 0.59 for evenly scaled text ("Back"), ratio 0.71. Long quest descriptions were also cut off mid-word.

The 0.75 now goes one level below the panes round 7 ruled out, on direct RootPane children of the page's parts (`PART_SQUASH_Y`). Three variants were built for an in-game test: A (detail panel only), B (A + category tabs + the five list row slots of PaPageChallenge5_00, row pitch 70 -> 52.5), C (A + each row's contents, pitch kept). B was tested first and was clean: quest list and full description correct, Memories rows #6 and #7 below #5. `N_InOutQuest_02`, `Pa_Quest_00`, `N_Cut_00` (list container), `Null_00` (full-height art) and `Null_01` (full-frame mask) stay stock. Check 22.

## Round 10: Sheikah map (2026-11-10)

**Terrain stretch.** Tester report: place names didn't move correctly with the map. In a screenshot the map grid cells measured 77.5 x 103 px, but they are square in stock: the terrain and grid were 1.33x too tall while names and icons were correct, so they drifted apart when panning. Stock keeps each map capture source and its use the same size in every pose (`AppMap_00_MiniMap`: 720 full map, 192 mini-map). Round 3 retargeted the uses (and the scissor) to 960 but kept the sources N_Capture_00-04 at 720; giving the sources the same 960 fixed it. Played and checked against a stock 16:9 screenshot: grid cells square (311 x 310 px), names on their terrain. The guide's capture note (a plain source copies a rectangle of its local size) does not by itself predict this; the tested rule is "source = use".

**Player locator.** Tester report: the bubble pointing to Link sat on the map edge and appeared at the wrong times. The bubble is `PaMapPlayer_00` (`Pa_PlayerNavi_00`): shown when Link is off screen, clamped to the box `N_PosSize_00` (1200 x 590, the 720 view minus 65 per edge), pointing at him. In stock and modded screenshots with the map scrolled differently, the bubble stayed at the same screen spot (about 237 units above centre), i.e. pinned to the stock box's top edge, while in 4:3 Link's own icon was visible above it. The code reads `N_PosSize_00` by name; growing it by 240 to 830 (`PART_GROW_H`, margins kept) fixed it. Played and checked.

## Repo setup (2026-11-10)

Mod folder renamed to "Native 4x3 Aspect Ratio" (same as SMBW); the unused optional map-view patch dropped; the shipped code patch moved to `tools/hand-edited/exefs/1.6.0.pchtxt` (`mkpatch.py` emits a different cave-based variant that never shipped). verify check 0 added: no archive identical to the original and nothing else in the output folder. The combined build (earlier-session fixes plus rounds 9 and 10) was installed as "Native 4x3 Aspect Ratio" and played and checked: stamina wheel, speaker name plate, Adventure Log and map.
