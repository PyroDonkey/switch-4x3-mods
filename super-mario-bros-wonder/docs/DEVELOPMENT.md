# Development log: Super Mario Bros. Wonder 4:3

Dated log of how the mod got to its current state, kept for the reasoning behind each fix. **The current state is in [`../AGENTS.md`](../AGENTS.md)**; values here (file names, cave addresses, zoom values) may be superseded by later sections. Section numbers follow the original handoff notes; sections 1-5 and 7 now live in `AGENTS.md`.

Patch snapshots named in this log (`1.2.1.pchtxt.<variant>`) were working files and are not in the repo; git history replaces them, and any variant can be regenerated with `tools/gen_zoom_v2.py`. "User-confirmed" means the tester checked it in game. The mod folder was called "Nova Aspect Ratio 4x3 Native" until v1.0.0; paths below use the current name.

## 6. Pause-menu background stretch (FIXED 2026-10-15; history)

Tester report: when pausing, the world in the background "does this squish and stretch" and doesn't render properly. It was first seen while the 3D patch wasn't applying (game version mismatch). The tester now reports it is still present with the working build. Not investigated in depth yet.

What is known:
- The pause screen's world background is a blurred screen capture. The common blur layout is `CmnBlurBG` (likely the one used behind Pause; not yet verified). It does two capture passes: `N_Cap01` captures (user data `CaptureOn`, `RGBA8`, `CaptureOutputAlpha`) and `P_CapUse01` draws it; `N_Cap` captures again (`CaptureScale` 0.25, filter `Blur00` via `MultiFilterFile`) and `P_CapUse` draws it (user data `CaptureUseName`/`CaptureUseIndex` link use to capture).
- The layout build changed these: RootPane scale y 0.75, and **all four capture panes height-filled from 1080 to 1440** (`N_Cap01`, `P_CapUse01`, `N_Cap`, `P_CapUse`), width unchanged at 1920. Same treatment in `CmnOnUIBlurBg`, `CmnErrorBlurBG`, `TitleBlurBG`, `MainMenu` (`N_Cap`/`P_CapUse`). The `Pause` layout itself has no capture panes (`P_BGLeft` height-filled; `L_MMPGauge` shifted).
- None of the blur layers have transform animations, so a changing squish is not a layout animation.
- Two functions size buffers as width = height x 16 / 9 from an integer pixel height (likely capture/screenshot/render targets): `0x6ED514` and `0x6ED7FC` (`ldr s0,[x0,#0x40]; fmov s1,#16; fmov s2,#9; scvtf; fmul; fdiv`).

Suggested first experiments (one per test round):
1. **Layout side:** rebuild `CmnBlurBG` with the capture panes left at the original 1920x1080 (keep root scale 0.75), or test the won-aar version of that one archive. If the stretch changes, the capture region/texture size follows pane size and needs matching capture vs use sizes (or a different fill).
2. **exefs side:** test the 16/9 buffer sizing as 4/3 (verified encodings):
   ```
   006ED518 0110221E   (fmov s1, #4.0)
   006ED51C 0210211E   (fmov s2, #3.0)
   006ED800 0110221E
   006ED804 0210211E
   ```
   If this fixes it, find exactly what those buffers are before shipping.
3. Identify which blur layout the pause screen loads (search the executable/romfs for references to `CmnBlurBG` or the pause sequence) so tests target the right file.
4. Ask the tester to describe the motion precisely (direction, when it starts/stops, during the menu's slide-in?) or send a screenshot.

### Update 2026-10-15: capture fix (confirmed)

Tester's description: in pause and menus the world behind the menu is drawn like a 16:9 image squeezed into the middle of the 4:3 screen, with streaky lines above and below. It appears as the menu opens and stays.
Diagnosis: the game copies a capture source pane's *local* size as framebuffer pixels and ignores the root 0.75. The 1440-tall `N_Cap` copied 180 rows past each edge (the clamped edge rows make the streaks), and that 1440-row image was squeezed into the 1080-row screen.
Fix (in `build.py`): capture source panes (`N_Cap*`, `N_Capture`) are no longer filled and stay 1920x1080 (WipeMiss 1080x1080). Use panes stay filled to 1440. 16 panes changed in 16 layouts: CmnBlurBG (2), CmnErrorBlurBG, CmnLobbyBG, CmnOnUIBlurBg, CourseInWindow, KakashiGet, MainMenu, TitleBlurBG, WipeCourseIn, WipeMiss, WipeToUp/Down/Left/Right, WipeWarp. `verify.py` reports 0 problems. Previous layouts are backed up in `tools\layout-backup-before-capture-fix\`.
If the background now looks vertically *zoomed* (stretched taller, top/bottom cut off), the hypothesis is wrong: the copy uses the screen rect after all, and the cause is elsewhere (see the 16/9 buffer leads above; `0x6ED4F8`/`0x6ED7E0` are vtable methods of an agl::TextureData render pass, vtable `0x35F6D90`, built at `0x90E744`).

Result: user confirmed the pause/menu background is fixed. New report: the course-entry circle wipe (shrinks onto Mario) now looks oval. Layout check: W_Wipe (size anim 25.5->16 at scale 240), P_Edge00-02 (procedural rings, 330x330) are all uniform; pane names are not in the exe. A/B test installed: WipeCourseIn reverted to the pre-fix file (N_Cap 1440); the capture-fix version is saved as tools\WipeCourseIn.Nin_NX_NVN.blarc.zs.capture-fix. Round again -> WipeCourseIn's capture is involved; still oval -> another layout or the oval predates this build.

A/B results for the world-map course-entry circle (WipeCourseIn; the pipe/door circle is `Wipe`, unchanged and round):
- N_Cap 1440 (pre-fix): circle round, snapshot jumps on course entry (squeezed).
- N_Cap 1080: snapshot right, circle taller than wide.
- N_Cap 1080 + N_Pos children squashed sy x0.75: circle wider than tall (overcorrected; so the shape is not a simple 1/N_Cap.h factor).
Current build (build.py `CAPTURE_KEEP_FILL`): WipeCourseIn N_Cap kept at 1440 (the round state), P_CapUse V coords cropped 0..1 -> 0.125..0.875 so only the real frame rows are drawn. CONFIRMED by the tester 2026-10-15: circle round, no snapshot jump, text fine. Not yet checked: WipeMiss (after losing a life; its capture pane also went 1440 -> 1080) and the WipeTo*/WipeWarp slides.

## 7. Gotchas learned

Moved to [`../AGENTS.md`](../AGENTS.md) (Gotchas).

## 8. Update 2026-10-18: Eden is now on this PC; Pipe-Rock Plateau Palace (Course150)

**Test setup:** Eden on a Windows PC, data in `%APPDATA%\eden`, base game + 1.2.1 update in its game list, a 100% save file for testing. Mod installed at `%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio` (re-sync with `robocopy "<repo>\super-mario-bros-wonder\mod\Native 4x3 Aspect Ratio" "<that>" /E`). Eden's player 1 is bound to a physical gamepad (no keyboard bindings), so the game cannot be driven from scripts; the tester plays and reports.

**Level map:** Pipe-Rock Plateau Palace = `Course150` ("ドカンロック平原のパレス", World 1). Areas: Main (entrance, one 27.5x15.5 CameraArea, ground x -4..16, stairs object at x=18, `AreaInRightNextGoTo` at x=27.5), Sub2 (pre-boss room), Sub3 (main route, 3 CameraAreas, 78 / 222 / 38 wide), Sub4 (boss arena, Bowser Jr., `BossKoopaJr` KoopaJrType 3). Sub4 has NO goal object: the clear comes from event `BossKoopaJrFinish` -> creates `ItemMotherSeed` (Grand Seed) -> `GetGrandSeed`; the flow includes `Event_MoveFarFromKoopaJrAndGrandSeed` + `Event_PlayerDemoControl` waits.

**Boss arena (Sub4):** locked by a `StopScroll` actor at (11, 6.5) (lockSide + lockVertical) and a `entryCourseZoomSignalKoopaJr04` (zoomBlockCount = view height in blocks, 15.5 = stock). Arena content spans x -1..23 (ceiling pipes at x=-1 and 23), the stock 16:9 view is 27.56 wide, 4:3 at zoom 15.5 is only 20.67. Fix applied: zoomBlockCount 15.5 -> 21.0 (28 wide at 4:3) in `romfs\BancMapUnit\Course150_Sub4.bcett.byml.zs` (made with `tools\bymlpatch.py`, same-size in-place edit, recompressed with stdlib zstd, no dictionary). Verified by dump diff: only that value changed. The visible-rect function `FUN_004DCF90` scales with zoom (`zoom*15.5` tall, `zoom*hardcoded width` wide), so object activation follows the new zoom.

**Likely cause of "can't finish" (UNVERIFIED hypothesis):** the exefs "fixed-camera rooms" patch (`006C6FD0`) turns StopScroll-locked cameras into follow cameras, and the reach rule (cave `02138740`) always allows at least +/-3.44 camera travel regardless of zoom. In the stock game the boss-finish sequence runs with a pinned camera; with a following camera something that waits on a screen/arena position may never complete. Next experiments: (1) ask the tester to test the finish with the mod disabled in Eden (Add-Ons) to confirm it is the mod; (2) if confirmed, restrict the `006C6FD0` patch so it does not apply to StopScroll arenas (needs the meaning of the flag at manager+0x1B4 in the branch at `006C6FB8`).

**Entrance cut-off (NOT diagnosed):** from data alone Main looks consistent with the stock layout; needs a screenshot or description of what is missing (left/right/top, background or ground, at start or while walking right).

Tools added: `tools\bymlpatch.py`.

## 9. Update 2026-10-18 (later): boss-arena zoom hook (confirmed in-game), live memory tooling

**Status:** Pipe-Rock Plateau Palace boss arena now shows the whole 16:9 room at 4:3 (side walls, corner pipes, floor, ceiling); fight, phase 2 and the clear all completed with the patch. The earlier "stuck after the boss" did not recur once the arena was fully visible and Jr. no longer died off-screen (it was seen stuck once in the red post-boss palette; cause not isolated, so treat as possibly intermittent).

**Why the data edit (section 8) did not work:** `entryCourseZoomSignalKoopaJr04.zoomBlockCount` is loaded (verified in memory) but is not what frames the normal fight. The view height is `zoom * 15.5` in `FUN_002E2990`: zoom = camera-subject fields (+0x204 / +0x1F0, or +0x1F4 when +0x1BE != 0 and +0x1E0 != 2; subject = `*(*(**(*(*(*(*0x37B4E00+0x30)+8)+8)))+0x120)`). The data edit was removed from the mod.

**Shipped fix (exefs/1.2.1.pchtxt, generated by `tools\gen_boss_zoom_patch.py`, checked with `verify_pchtxt.py`):**
- Cave A2 `02138800` (the reach-rule cave's final branch at `02138768` now goes here): looks up the current area record (`*(*0x37B2128+0x50)` table, `[+8]` array, signed byte `controller+0x10A` index) and compares the hash at `record+0x90` with 607466214 (Course150_Sub4 RootAreaHash); writes 21.0f (match) or 0 into an unused zero word at `0x037D1F00` (end of .bss; last used byte 0x37D182C).
- Cave B `02138900` (hooked from the zoom instruction `002E2B30`): original `fmov s1,#15.5`, then `s1 = max(s1, [0x037D1F00])`. Only x16/x17/s16 are used (verified unused in both functions).
- Backup of the previous patch file: `tools\1.2.1.pchtxt.before-boss-zoom`. To reuse for another room: change HASH and ZOOM_BITS in the generator (area hash = `RootAreaHash` in the room's .bcett; 21.0 = 28 wide at 4:3, i.e. the full 16:9 width).

**Open items:**
1. Phase 2 (Wonder phase): the two corner pipes sit about one block below the ceiling and look taller than in phase 1 (they lower again during the seed demo). Same with the live-forced zoom and with the patch, so it is not the zoom mechanism. Unknown whether stock 16:9 does the same; need a 16:9 phase-2 reference screenshot.
2. Palace entrance (Main) cut-off: still not diagnosed; needs a screenshot/description.
3. Other fixed-camera boss rooms (KoopaJr01-03, castle bosses) probably have the same too-narrow framing; the same generator works per room.

**Live memory tooling (Eden on this PC, scripts in `%TEMP%\smw_mem`, not kept in the project):** ReadProcessMemory/WriteProcessMemory from PowerShell works on the Eden process. Find the guest image by searching all committed regions for the first 48 bytes of `FUN_006C5970` and keeping the page-aligned hit whose `+0x2AEEDB4` float is 1.3333; guest base is 0x8004B000 (host = image + guest - 0x8004B000). Data constants (.ro) and heap are writable live; code is not (JIT cache). The camera subject object only exists while a level is loaded. Screenshots: CopyFromScreen of the Eden window rect (find it by title, the main window handle can return a menu popup).

> Superseded: the guest base is not fixed; it changes every launch (see section 10 and the live probe notes in section 17).

## 10. Update 2026-10-18 (latest): pipe anchoring root cause, global zoom 17

**Pipe root cause (confirmed by a fork agent from live node values, fix not yet seen in-game):** the pipe AI (`KoopaJrObjectDokanPopUp.root.ainb`) is screen anchored. Node `GetDisplayBoxWithAreaID` (class methods `0x833AC4` per-frame update and `0x5E4150` initializer; box from `0x1C3AC4/0x1C3BF0` = world AABB of the camera view) feeds `BossKoopaJrMoveCameraRatePos` (`0x158C960` measures rates ONCE at start: `rateX=(pipeX-boxCx)/boxW`, `rateY=(pipeY-boxCy)/boxH`, `zoomRate=boxH/15.5`; `0x158CAB8` each frame: `pos = boxCentre + rate*(27.5,15.5)*s + (0,-1,0)`, s eases from zoomRate to the end scale). Stock 16:9 box 27.56x15.5 gives zoomRate 1 and true fractions. With the boss-room zoom (28x21) the start measurement was wrong (zoomRate 1.355, rateY 0.357 vs 0.484), so the pipes landed ~2 blocks low and scaled by 1/1.355. Our first fix (cave D at `0x833B00`) only covered the per-frame method; the startup measurement uses the initializer, now cave E at `0x5E428C`. Marker words: `0x037D1F10` (D) and `0x037D1F14` (E) hold k=15.5/21=0.738 once they have run. Note: the guest base is NOT constant across game launches (it was 0x8004B000 once, 0x80BC1000 another time); only host-image offsets were used for the marker reads. Live JIT injection into already-run code does NOT work (Eden keeps translated code); every code patch needs a game restart.

**Global zoom (agent proposal, bytes cross-checked against my generator):** base view height G=17 (22.67 wide at 4:3 = 82% of 16:9 width; 18/19 also encodable: edit `G` in the generator): cave B first word `fmov s1,#17`, camera-controller clamp (`006C6358 fmov s9,#17`, `006C6364 -> cave F @02138D00` multiplies the width base `0x2AEE9E8` value by 17/15.5), reach-rule delta literal `0213876C` = (27.5556-G*4/3)/2 = 2.4444. The visible-rectangle function derives its zoom from the real view height, so activation follows automatically. Known cosmetic risks (unverified): three zoom-ignoring clamps near `0x157C914`, `0x1617178/84/940/C18/C24`; background layer bounds in the rectangle function around `0x4DD204-0x4DD27C`. To validate in game: flat level start/end (no void past camera limits), a pit/shaft level, a one-screen room, a Wonder zoom + pipe warp, enemy pop-in at the edges.

**Files:** current mod patch = `Native 4x3 Aspect Ratio\exefs\1.2.1.pchtxt` (copy: `tools\1.2.1.pchtxt.pipe-fix-plus-global-zoom-17`). Fallbacks in `tools\`: `1.2.1.pchtxt.pipe-fix-only` (pipe fix, no global zoom), `1.2.1.pchtxt.before-global-zoom` (boss zoom + cave D only), `1.2.1.pchtxt.boss-zoom-on` (boss zoom only), `1.2.1.pchtxt.before-boss-zoom` (original). `verify_pchtxt.py [file]` disassembles a patch file.

**Pending test:** relaunch the game, play the palace to phase 2: (1) pipes should stay on the ceiling (read markers via memory), (2) check global zoom behaviour above, (3) arena framing unchanged.

## 11. Result 2026-10-18: Pipe-Rock Plateau Palace boss fixed (user-confirmed)

Tester confirmed in-game with the current patch (`1.2.1.pchtxt` = `1.2.1.pchtxt.pipe-fix-plus-global-zoom-17`): the arena is fully framed, phase 2 pipes stay anchored (possibly a very slight shift, not noticeable), the fight and clear work. Entrance (Main) was reported fine. The earlier "stuck after the boss" did not recur once the arena was fully visible.
Still unvalidated by the tester: the global base-17 zoom in other levels (edges, pits/shafts, one-screen rooms, Wonder zoom + pipe warp, enemy pop-in). If anything looks wrong use `1.2.1.pchtxt.pipe-fix-only` (no global zoom) or change G (17/18/19) in `tools\gen_boss_zoom_patch.py`.
Other boss rooms (Koopa Jr 01-03, castle bosses) were not checked; the generator can add a room by changing HASH/zoom and, if a room has screen-anchored actors, the box caves.

## 12. Update 2026-10-18 (late): global zoom 17 reverted

The tester found that the global base-17 zoom shows outside the level in small interior rooms (e.g. a power-up hut shows sky at the top corners above the ceiling art): the extra 1.5 blocks of VERTICAL view reveal space beyond art painted for exactly the stock 15.5 frame, and the camera clamp cannot hide it. Reverted: the mod's `exefs\1.2.1.pchtxt` is now `1.2.1.pchtxt.pipe-fix-only` (boss-room zoom + both pipe box caves, base height 15.5 elsewhere, original reach delta). The global-zoom variant is kept as `1.2.1.pchtxt.pipe-fix-plus-global-zoom-17`. If a global zoom is revisited, it must skip small interior rooms (e.g. only apply where the area's camera width is large) or accept the vertical overshoot; a horizontal-only widening is impossible without distorting the picture at 4:3.

## 13. Update 2026-10-18 (late): per-area zoom v2 (built, NOT yet run in game)

Request: Poplin houses at stock 15.5, world levels at 17. Course kinds in CourseInfo: BadgeHouse (Course500) and GeneralFacility/PlayableFacility (Course510-590) are the houses/shops; there are also ~67 one-screen sub-rooms inside normal levels (27.5 wide), which have the same painted-backdrop problem. Instead of a course list, the hook decides by the loaded area's bounds width (area record `+0x94` min x, `+0xA0` max x): narrower than 60 -> small room, stock base 15.5, reach delta 3.4444; wider -> 17.0, delta 2.4444; the boss table (hash 607466214 = Course150_Sub4) overrides with 21.0. Everything that depends on the base (view height cave B, camera-controller half-extents caves F1/F2, pipe display-box caves D/E, reach rule) now reads the per-area base from the mailbox word `0x037D1F00`. Generator `tools\gen_zoom_v2.py`; patch file `1.2.1.pchtxt.zoom-v2` (= mod); previous pipe-fix-only build `1.2.1.pchtxt.before-zoom-v2`. Cave A pushes x15 on the stack (`str x15,[sp,#-16]!` ... `ldr x15,[sp],#16`) and uses s16/s31, x16/x17.
To verify in game (read via memory): `0x037D1F00` = G (15.5 in a hut/small room, 17.0 in a wide level, 21.0 in the boss arena), `0x037D1F1C` = measured area width, `0x037D1F18` = delta bits. Unverified assumption: area bounds for houses are < 60 wide (camera-area unions of all Facility/BadgeHouse courses are < 60). The area-hash table in cave A is the place to add the other Bowser Jr. rooms (151_Sub2 hash 101336182 -> 20.6667, 152_Sub4 hash 1778226157 -> 23.3333, 153_Sub3 hash 1019598315 -> 20.6667); not added yet.

## 14. Update 2026-10-18 (end of session): kingdom map fill, zoom v2 confirmed, state of the mod

User-confirmed good in game: per-area zoom v2 (section 13; houses/small rooms 15.5, wide world levels 17, boss arena 21 plus pipe box caves) and the kingdom-map fix below.
Kingdom map (layout `GrandWorldMap`, used by both the menu "view map" screen and the world-to-world travel view): the art pane `P_GrandWorldMap` (1920x1080) stays at its true 16:9 size (build.py NO_FILL keeps it unfilled), which leaves ~180-unit bands at the top and bottom of the 1440-tall 4:3 root space. In the menu view the CourseList layer beneath (header, round map button, course cards) showed through those bands (it is hidden by the opaque art in 16:9), and in the travel view the bands were black. Fix = a new full-root pic1 pane as the first child of `N_Offset` behind the art, flagged to follow parent alpha, using the layout's own `CmnStripe16x16^r` texture with the checker's two colour registers (linear (9,14,9) / (13,19,13), screen ~ (53,66,53)/(64,77,64)); cand_D2b_stripe uses TexSRT scale 1/3 (tile ~48 units). Lesson: TexSRT scale on these materials acts in texture-pixel units (the game's own tiling materials use scale (1,1)), so a scale of 40 aliased to a flat colour. Textures can only be used from the layout's own archive (every material in all 234 layouts uses only its own archive's textures); copying the real checker (`CmnPtnCheckFractal^r`) would need BNTX name/dict/relocation edits and was not attempted.
Candidates, mock-ups and `changes.txt` for each variant are in `Map layout candidates\`; the agent's helpers (lytedit.py, make_band_candidates.py, make_candidates.py) are in `%TEMP%\smw_agentC` (not kept in the project; copy them if the layout needs rework). The build.py integration was NOT done: the current `romfs\Layout\GrandWorldMap...` in the mod is the hand-edited candidate, so a full `build.py` run would overwrite it (to keep it across rebuilds, drop `'GrandWorldMap': {'P_GrandWorldMap'}` handling in NO_FILL and re-apply the pane insert from `make_band_candidates.py`).

> Superseded: the hand-edited GrandWorldMap now lives in `tools/hand-edited/` and `build.py` copies it over the generated file (section 16), so a full build keeps it.
Flashing bars when entering a level from the map (user: intermittent, mostly on an Android handheld, not seen on PC): not reproduced; the wipe layouts all have full-size panes, the map's out animation used to expose the CourseList layers (now covered by the band), and the one remaining driver-dependent suspect is `WipeCourseIn`'s `N_Cap` copy that reads 180 rows past the framebuffer (section 6); changing it risks an oval iris. Ask the tester whether it still flashes on the Android device with this build.
Other pending items: other Bowser Jr. rooms (add to the table in cave A of `gen_zoom_v2.py`: 151_Sub2 hash 101336182 -> 20.6667, 152_Sub4 1778226157 -> 23.3333, 153_Sub3 1019598315 -> 20.6667, all untested); last-boss and airship boss rooms not assessed; the tester's Android install needs the same `exefs\1.2.1.pchtxt` and `romfs\Layout` files (the Android emulator may order patches differently).

## 15. Update 2026-10-19: wide-level base height tuned to 15.75 (user-confirmed in frame)

Zoom v2's wide-level base 17 showed bare sky above the icicle/pillar backdrop in W2 Fluff-Puff Peaks "Outmaway Valley" (ice-block spot): the backdrop is painted for the stock 15.5 view height, so any increase shows past its top edge. Tried 16.25 (thin strip left), 16.0 (small sliver left), 15.75 (user: "in frame"). Installed mod patch = `tools\1.2.1.pchtxt.zoom-v2-15.75`: only the G (15.75) and reach-delta (3.2778) literal words differ (now at `021388D8`/`021388DC` after later cave changes; `021388D0` is the branch back and `021388D4` the 60.0 width threshold) from `1.2.1.pchtxt.zoom-v2` (G 17). Other variants kept: `zoom-v2-16.25`, `zoom-v2-16.0`. To change G again: generate with `gen_zoom_v2.py` (edit G_LARGE/D_LARGE), diff against the old output, patch those two words. Delta = (27.5556 - G*4/3)/2. Width gain over stock is small (76.2% vs 75% of 16:9). Idea not built: shift the camera down so all extra height falls at the bottom, allowing a bigger G. Other levels (pits, level ends, Wonder zoom, pop-in) still not checked at 15.75.

Cleanup 2026-10-19 (tester request): all unused `1.2.1.pchtxt.*` variants in `tools` were deleted, so the fallbacks named in sections 9-15 (before-boss-zoom, boss-zoom-on, pipe-fix-only, zoom-v2, global-zoom-17, 16.0, 16.25 etc.) no longer exist. Only `1.2.1.pchtxt.zoom-v2-15.75` (= the installed mod patch, also synced into the project's `Native 4x3 Aspect Ratio\exefs\1.2.1.pchtxt`) remains. Regenerate any variant with `gen_zoom_v2.py`.
Also deleted at the tester's request: `tools\layout-backup-before-capture-fix\`, `WipeCourseIn...capture-fix`, and `Map layout candidates\` (the chosen GrandWorldMap stripe layout is already in the mod's `romfs\Layout`; a full `build.py` run would overwrite it, see section 14).

## 16. Update 2026-10-19: capture "use" panes (HUD / shop squish), now in build.py

Cause: the game copies a capture pane's LOCAL size as framebuffer pixels (section 6) and the P_Cap* use pane draws it back 1:1; the 0.75 root y-scale drew every 1:1 use pane 25% too short (HUD coin/flower/lives/seed icons in GameDisplay, button names, list-end masks, Miss/YouWin, Wonder timer...). Fix = use pane height x 4/3 about its centre, in top AND parts layouts. It is now `CAP_USE` in `build.py` (regex `^P_(Blank)?Cap(?!ture|EasyBG)\w*$`, height < 1000, WipeCourseIn skipped); the old `SQUARE_FIX` (BadgeShop only) was removed since the rule covers it. 42 panes. A rebuild from `%APPDATA%\AnyAspectRatio\perm\won\wonder.zip` reproduced the previous mod byte-for-byte except GrandWorldMap, so build.py is again the single source of the layouts.
GrandWorldMap is hand-edited: the file lives in `tools\hand-edited\` and build.py copies it over the generated one; verify.py skips it. `capfix.py` was a temporary post-pass and is deleted.
verify.py reports 2 known notes: WonderTimer P_CapUse/P_CapUse01 poke ~10 units past the top edge (cosmetic).
UNVERIFIED in game: the HUD fix. Not changed, need a look in game: `P_Screenshot` (1152x648) in CourseOut and MainMenu photo frames (a 4:3 screenshot may be shown stretched in a 16:9 frame); Poplin shop dialog squish still undiagnosed (needs screenshot).
Eden sync: files are locked while Eden runs; close Eden, then copy `romfs\Layout\*` into `%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio\romfs\Layout`.

### 16b. Result 2026-10-19 (user-confirmed X; L/R/+ verified from screenshot vs stock)
The x4/3 capture rule is WRONG for key-glyph captures: the X/Y/+ and L/R badges are font glyphs drawn through a capture, and x4/3 made them tall ovals (0.72-0.77 wide/tall vs stock ~1.1). `build.py` now skips `LCmnShortcutBtn` (X, "Kingdom Map" button) and `LKeyGuideIcon` (L/R/+ key guides) via `CAP_USE_SKIP_LAYOUT`; both verified in Eden against stock-16:9 crops. The rule stays for the other 40 panes: the top HUD (`GameDisplay`, coin/flower/lives/seed) was checked against stock and looks right. Not yet verified: other text/glyph captures (LCharacterSelectBtn, LCharacterSlot, LPlayerName*, LFriendMatchBtn, LAccountSelectBtn, LBalloonCountDown...), Option/Manual/ControlGuide masks, Miss/YouWin/WonderTimer/WonderCountDown, and the Poplin shop dialog (user still to confirm). If any shows tall glyphs/text, add its layout to the skip set. Stock reference: set Eden to run without the mod (aspect ratio is already Default 16:9).

> Superseded by 16e: `CAP_USE_SKIP_LAYOUT` no longer exists; `build.py` applies the rule only to `CAP_USE_LAYOUTS = {'BadgeShop'}`.

### 16c. 2026-10-19: Select a User card (user-confirmed by measurement vs stock)
`LAccountSelectBtn` (profile card: Mario head, lives "84", flower, seed/flower rows) is also skipped by the x4/3 capture rule: with it the head row was ~1.4x too tall vs the card; without it the head/number measure 0.75x stock in both axes (same as the card). Skip set is now `{WipeCourseIn, LCmnShortcutBtn, LKeyGuideIcon, LAccountSelectBtn}`; rule still applies to 39 panes. Checked OK vs stock: Select a User world icon, Select Number of Players silhouettes/labels/cards, Poplin shop, top HUD (GameDisplay).
Pattern: captures that hold small icon/number rows inside scaled cards/buttons or key glyphs must NOT be stretched; capture panes at screen level with unscaled parents (HUD, BadgeShop) need it. Remaining unchecked captures: LCharacterSelectBtn, LCharacterSlot, LPlayerName/LPlayerNameCourse, LFriendMatchBtn, LBalloonCountDown, LOutOfScreenMarker, LRaceBlockTimer, LRequestInfo, Option/Manual/ControlGuide masks, Miss/YouWin, WonderTimer/Countdown, NowConnecting, StaffCreditsDisplay, BadgeChallengeIntro, CourseList/CourseInCourseName, KakashiGet.

### 16d. 2026-10-19: in-level HUD (GameDisplay) also excluded
Measured vs stock 16:9 (same level, zoom crops, normalised by window width 963/1277): with x4/3 the coin/flower/Mario head/numbers were ~1.3x too tall (item ring, not a capture, was round). Without it they measure 36x36 (coin), 32x36 (flower), 40x40 (head), 25x27 (79): within ~10% of 0.75 x stock. `GameDisplay` added to `CAP_USE_SKIP_LAYOUT` (now 5 entries: WipeCourseIn, LCmnShortcutBtn, LKeyGuideIcon, LAccountSelectBtn, GameDisplay; rule applies to 38 panes).
CONCLUSION so far: the x4/3 capture rule was wrong in every case measured except the BadgeShop intro (inherited from the original build, user-confirmed good). Safest default: skip all capture panes except BadgeShop (and check the rest only if a screen looks off). Not yet done; ask the tester.

### 16e. 2026-10-19: capture rule restricted to BadgeShop (final state)
`build.py` now stretches capture use panes only in `CAP_USE_LAYOUTS = {'BadgeShop'}` (the original, user-confirmed Poplin shop intro). All others stay at authored size. The course-list header (CourseList: world name, seed counter "30", completion check) was visibly tall with the old rule (check circle ~0.74 wide/tall); that and the 37 other panes revert to authored size in this build. verify.py: 0 problems. Rebuild: `python build.py . %TEMP%\orig_layout <out>` with originals extracted from `%APPDATA%\AnyAspectRatio\perm\won\wonder.zip`. Pending: copy `romfs\Layout\*` to Eden with the game stopped (22 files were locked), restart the game, re-check the course list header, Select a User card, in-level HUD and key glyphs (expected to match stock). Unmeasured: whether any screen needs the stretch back; add its layout to CAP_USE_LAYOUTS only after measuring against stock.

> Superseded: builds now read the 1.2.1 originals from the workspace, not `wonder.zip`; see the build commands in `../AGENTS.md`.

## 17. Update 2026-10-25: autoscroll / fixed-position camera fix (cave G, user-confirmed on the airship)

**Bug:** W2 Fluff-Puff Peaks Flying Battleship (Course101) died with "Too Bad!" when grabbing the Wonder Flower (Main area); Up 'n' Down with Puffy Lifts reported as "camera won't let you reach the seed" (this is **Course021** Main, W2 in game; NOT Course064 as first guessed: Course064 is a W8 level with pump lifts). The airship engine-room button (Course101_Sub1, `ObjectSwitchEnemyPlant`) turned out to work fine.
**Cause (measured live):** the old lines `006C6FD0-006C6FE4` set the fixed-position camera target X to the focus X with no limit. The game uses that path (subject+0x1B4 set, +0x1B8 clear; fixed position at subject+0x194) for StopScroll locks AND autoscrolls, so in the airship autoscroll the camera followed Mario and he outran the scroll (scroll x~132, Mario x~210). The Wonder start snaps the camera to the game's position, Mario is off-screen -> Too Bad.
**Fix (gen_zoom_v2.py cave G at 0x02138A00, hook 0x006C6FD0 -> 0x6C6FE8):** target X = fixed X + offset; offset eases (0.08/frame) towards 0 while fixed X moves (>0.002/frame; held 120 frames after it stops) = stock autoscroll, else towards clamp(focus X - fixed X, +/- reach delta 0xF18) = locked rooms pan inside the 16:9 frame; a fixed-X jump > 1 block resets the offset directly. Mailbox 0x037D1F30 previous fixed X, 0x037D1F34 hold, 0x037D1F38 offset. Registers: s0 (dead there), s31, x9, x10, x17 (only s31 is unused in the whole controller; s16 is live there).
**Verified:** airship autoscroll trace: |target - fixed| <= 0.03 throughout, Wonder Flower works (user-confirmed "working well"). An intermediate always-clamped build (`1.2.1.pchtxt.clamped-follow`) also fixed the Wonder but let the camera drift backward in autoscrolls. NOT yet re-tested: Puffy Lifts seed, a locked room (Pipe-Rock Palace boss arena) with the new cave.
**Other changes:** cave A also stores the camera controller (x19) at 0x037D1F20 and subject (x20) at 0x037D1F28 (debug), and the area table moved to 0x02138E00 (room up to 0x02139000 for more boss rooms). Files: mod patch = `tools\1.2.1.pchtxt.split-autoscroll`; previous = `1.2.1.pchtxt.before-2026-10-25`; generator backup `gen_zoom_v2.py.bak-2026-10-25`.
**Second lock path, cave H (Puffy Lifts):** Course021 Main's Wonder (flower `ItemWonderHole` at (260.5, 27.5), balloon morph, vertical shaft CameraAreaSignal 27.5x74 at x 260) is framed by `StopScroll` at (260.5, 29) with lockSide=True, lockVertical=False. That lock does not use subject+0x1B4; it sets controller+0x29 and the final camera write takes X from controller+0x1A0 (0x006C6ADC -> 0x006C7BEC `ldr s9,[x19,#0x1a0]`). The finish seed is at (272, 82.7): inside the 16:9 frame (260.5 +/- 13.78) but outside 4:3 (+/- 10.33); trace showed the player pinned at x=268.999 by the screen edge. Cave H at 0x02138F00 (hook 0x006C7BEC): X = locked X + clamp(s13 - locked X, +/- delta), s13 = the normally computed (area/reach-limited) camera X. Patch copy `1.2.1.pchtxt.side-lock` (= mod). User-confirmed 2026-10-25: the Puffy Lifts seed is reachable.
**Coverage (scan of all BancMapUnit files):** autoscroll in 22 courses (002, 010, 016, 019, 022, 023, 049, 061, 062, 064, 100, 101, 102, 290, 407, 460, 853, 854, 857, 858 ...), side-only StopScroll in 22 (010, 016, 021, 023, 033, 034, 047, 051, 054, 056, 059, 151, 152, 153, 290, 452, 453, 858 ...). Both fixes are code-level, so they apply to all of them; only Course101 and Course021 were played. The Bowser Jr. rooms 151/152/153 are side-locked; panning alone is not enough for a boss fight (the whole arena must be visible), so they were added to the zoom table (2026-10-25, `1.2.1.pchtxt.jr-rooms` = mod): Course151_Sub2 101336182, Course152_Sub4 1778226157, Course153_Sub3 1019598315, all G = 20.6667 (full 16:9 width at 4:3) with delta 0 (camera stays exactly at the lock). 152_Sub4's own zoom signal (17.5) multiplies the base, so 20.6667 also reproduces its stock zoomed width (31.1); the 23.3333 noted in section 13 would have overshot. NOT yet tested in game (check: mailbox 0x037D1F00 = 20.6667 in the arena, whole arena visible, vertical overshoot acceptable, pipes/Jr. anchored). WorldMapInfo file numbers do not match in-game world numbers (Course021 is in World003.bgyml but in-game W2). The Y override (controller+0x2A -> +0x1A4, lockVertical) is untouched (the 4:3 view is not shorter than 16:9).
**Adversarial review 2026-10-25 (Grok 4.7 High + Kimi K3 High via cursor-agent, Opus subagent; bundle and reports in the session scratchpad `review\`, `review_*.txt`):** all encodings, branch targets and register claims were confirmed (s0 at 0x6C6FD0 is dead: every path from 0x6C6FFC reaches `ldr s0` at 0x6C653C or 0x6C7018; s13 at 0x6C6ADC = the area/reach-limited camera X; cave H's delta is current, cave G's is one call old). Key correction (Opus, consistent with the traces): **subject+0x194/+0x1B4 is written only by the SetAutoScrollPos node (0x16C5548)**; StopScroll (param loader 0x80F958, node 0x17016B0-0x1701A54) sets subject+0xA00/0xA01 which the controller turns into controller+0x29/0x2A, i.e. **every StopScroll room, including Course150_Sub4, goes through cave H, not cave G**. With Course150's leftover delta 3.4444 at G = 21, cave H would have panned that confirmed arena off its walls (ceiling pipes follow the display box). Fixed in `1.2.1.pchtxt.reviewed` (= mod): Course150_Sub4 delta 0, generator asserts delta <= max(0, (27.5556 - G*4/3)/2); cave G jump path (fixed-X step > 1 or controller x19 != [0x037D1F20]) now sets offset 0 + hold 120 instead of snapping to the player clamp (respawn/area entry mid-autoscroll could push the player into a wall). Kept by design: vertical autoscrolls and scrolls stopped > 2 s pan within the 16:9 frame. Course152_Sub4 zoom: SetChangeCourseZoom (0x16CA4CC) stores zoomBlockCount/15.5 at subject+0x1F0 and the view code multiplies it by max(15.5, G), so G = 20.6667 is right. Open, unverified: the new Jr. rooms show ~2.6-2.9 extra blocks above/below; cave B/F1 are bypassed when subject+0x1BE != 0 (alternate zoom source) - check live in those rooms; multiplayer.
**Live probe (`%TEMP%\smw_mem\probe.ps1`):** `. probe.ps1; Load; Sample name; Trace name seconds` (CSV in `%TEMP%\smw_shots`). Attach: Eden keeps stale image copies in its 4 GB backing region (type MEM_MAPPED); use the copy whose .bss (+0x37D1F00) is live and whose heap pointers resolve (host = image - guestbase + guest). Guest base = best score of `gbase.py` on the 12 vtable entries at image+0x35F6D90 (changes per launch, e.g. 0x80129000, 0x806BC000, 0x80EC9000). Write PowerShell hex literals >= 0x80000000 with an `L` suffix (otherwise they are negative Int32).

## 18. 2026-10-26 to 2026-10-30: last screen fixes, repo, 1.2.1 rebuild (summary)

- **Menu pointer** (user-confirmed): the game places the pointer in screen coordinates, so a 0.75 root pulled it towards the middle. `Cursor` root left at 1 (`ROOT_SKIP`), the arrow's shape kept by scale y 0.75 on the unrotated `LCursor` `N_RB` (`PART_SCALE_Y`).
- **Course-clear photo and View photo** (user-confirmed): the photo is a 4:3 capture drawn in a 16:9 frame; photo panes and frames narrowed by 0.25 x photo width (`PHOTO_4x3`), View photo end key kept (`SHIFT_KEEP_KEY`).
- **Badge Challenge restart wipe** (user-confirmed): its badge pattern uses a screen projection (texgen source 3) that ignores the root scale; TexSRT X x0.75 (`PROJECTED_PATTERN`).
- **Death screen**: `WipeMiss` may draw its spotlight slightly oval (same capture setup as the old course-entry iris). A keep-fill candidate was tried in the emulator only; result unclear, not shipped.
- **Repo**: the project moved into this git repo (2026-10-30); the old handoff notes became `AGENTS.md` and this log. The mod folder was renamed from "Nova Aspect Ratio 4x3 Native" to "Native 4x3 Aspect Ratio" before the first release.
- **1.2.1 rebuild**: extracting the game's own 1.2.1 layouts showed won-aar's cache was older: 30 of its 234 archives differed (Pause, MainMenu, Title, CourseList, talk windows, button icons...) and 1.2.1 adds `AmiiboReadWindow`. Rebuilt from 1.2.1 with identical edits (638 writes); the build now writes only changed archives, so 115 ship instead of 234. Play-tested 2026-10-31: menus, HUD, pause, maps, transitions, course clear, cursor and amiibo look good.

## 19. 2026-11-01 to 2026-11-02: World 4 Bowser Jr. water tint, fight camera and swim AI (Cave W removed; tint plane scaled; caves Y and K confirmed in game)

**Symptom:** In World 4 Bowser Jr. boss (`Course152_Sub4`, `RootAreaHash = 1778226157`) the underwater tint, caustics and light rays stop at hard horizontal lines; above the top line the brick wall is untinted. The view there is 23.33 blocks tall (G 20.6667 x stage zoom 17.5/15.5) vs stock 17.5 (`CameraArea` `y in [-5.5, 12.0]`, centre 3.25).

**First attempt (2026-11-01, Cave W, removed 2026-11-02):** the lines were taken for parked water surfaces of two `WaterTagKoopaJr` actors:
- `obj0` (ceiling water, `IsReverseWater = True`, `HomePos.y = 13.5`): when parked, surface sits at `y = 13.5`. In stock (`y <= 12.0`) it is off-screen; in 4:3 (`y <= 14.92`) it floats ~1.4 blocks below the top edge.
- `obj449` (floor water, `HomePos.y = 4.5`): when drained, offsets `(0, -12, 0)` / `(0, -13, 0)` park surfaces at `y = -7.5` and `-8.5`. In stock (`y >= -5.5`) it is off-screen; in 4:3 (`y >= -8.42`) it renders below the arena floor.

**Refuted hypothesis:** An early proposal to patch the WaterMap texture height at `0x015A94F8` (720 -> 960) only changes offscreen render-target pixel density. The world-space projection derives from the camera frustum (`FUN_002E2990` / Cave B), which already scales with `G`. More pixels does not expand world coverage.

Cave W (hook `0x01C5B694` in `FluidTagInfo::method4` `0x01C5B658`, which returns 0 when a surface is outside a box's y range) culled surfaces outside `[-5.5, 12.0]` in this room only. The tester's screenshots then showed the real symptom: the cut-off is the edge of the tint itself, so culling surfaces outside the stock box only enforced it. Cave W, its hook and its verifier checks were removed; its cave space (`0x2138D38`-`0x2138DFF`) is free again. Kept from that change: cave A clears `0x037D1F04` at entry and stores the current area's `RootAreaHash` there (for any per-room fix later), and the expanded `verify_pchtxt.py`.

**Diagnosis (static, 2026-11-02):**
- The tint is drawn by `KoopaJrSystemWaterMixAreaPlane` (`Course152_Sub4[Design].muunt/obj451`, Hash 2115412732, at (70.5, 4.5, -4.0), Scale (1,1,1); the main muunt also has an `obj451`, so select it by Hash). Its pack holds model `SystemWaterMixAreaPlane` (model project `SystemWaterDefault`) and one AINB that runs `ChangeWaterMapSettingKoopaJrType02` (node method `0x015A94D4`: WaterMap settings 720 / 1 / 2.0, then `0x01BCD674` enables two draw passes) and moves the plane each frame to (camera x, 4.5, -4.0). It follows the camera in x only, so its fixed height (sized for 17.5) runs out in the 4:3 view. The top edge of the tint is straight (water surfaces here are wavy) and moves with the camera, as geometry behind the play plane does.
- Refuted from the brief: `0x00937A08` is not a FluidTagMgr but a callback near the heap code that grows the display box by 7 blocks; `0x001C3BF0` returns the camera-view box (`0x37B4E00`), which already follows the 4:3 view, not the CameraArea. It has 36 callers (incl. the cave D/E sites), so scaling it would not move the tint and would affect culling everywhere.
- The model size is unverified (Model romfs not extracted).

**Fix (stage data, no code):** new `tools/build_stage.py` with an edit table:
- `KoopaJrSystemWaterMixAreaPlane` (`Course152_Sub4[Design].muunt/obj451`, Hash 2115412732): Scale Y 1.0 -> 1.5, so the underwater tint, caustics and light rays cover the taller 4:3 view. **Confirmed in game 2026-11-02:** the tint fills the view during the fight and after the defeat.
- `BgUnits` Unit 1 Wall 0/1/2 bottom points: in stock, the arena walls (Wall 1 and 2) bottom out at `y = -7.0`. In 4:3 with the fight camera pinned at `y = 3.25`, the view reaches `y = -8.42`, exposing unrendered black void boxes in the bottom-left and bottom-right corners below the walls. Extending the 6 bottom points (`[-8, -7]`, `[23, -7]`, `[39, -7]`, `[50, -7]`, `[79, -7]`, `[92, -7]`) from `y = -7.0` to `y = -10.0` pulls the wall terrain past the bottom of the screen, filling the corner voids. **Confirmed in game 2026-11-02.**
- Built and verified from 1.2.1 originals; 7 float edits (13 bytes), `build_stage.py --verify` 0 problems. Mod ships 116 romfs files (`layout_count` 116).

**Fight camera pin (Cave Y, hook 0x006C66E8 at 0x02138D40):** after the opening cutscene the camera clamps to the union of the course's areas (`y -5.5 to 20.25`), so the camera drifted up to 6.167 (and stayed stuck high) and the Royal Seed spawned out of reach (4.17 vs stock 1.25).
- Cave Y adds `(s4 - s4 * 15.5 / G)` to the upper limit and subtracts it from the lower one; with the fight zoom (stock half-height 8.75) it pins `upper = lower = 3.25`, locking the camera vertically to stock 3.25. **Confirmed in game 2026-11-02:** the camera never drifts up when swimming, and the Royal Seed spawns at stock `3.25 - 2 = 1.25`.

**Bowser Jr. corner-stuck bug (Cave K, hook 0x01781B70 at 0x02138D88):**
- In the tester's test with Cave Y, Bowser Jr got completely stuck spinning indefinitely in the bottom-left corner.
- **Mechanism:** Pinning the 4:3 camera to y = 3.25 pushed the camera frustum's vertical extents (`CameraBoundBox2f`) to `[-8.417, 14.917]`. Bowser Jr.'s swim AI (`_LocalModule_812900449ac9`, `WaterDash`) queries `GetCameraBoundBox2f` and computes swim target Y as `minY + 3.0`. In stock: `-5.50 + 3.0 = -2.50` (1.5 blocks above the floor at -4.00). With Cave Y: `-8.417 + 3.0 = -5.417` (1.42 blocks below the solid floor). Jr tried to swim to `(51.95, -5.417)`, collided with the floor and left wall, and because he could never get within arrival distance (`IsSuccessDis`), the move never finished.
- **Fix:** Cave K hooks `GetCameraBoundBox2f` (`ldp x8, x9, [x8, #0x50]`) at `0x01781B70`. In Course152_Sub4 only (mailbox `0x037D1F04 == 1778226157`), it sets `minY` to stock -5.50 (upper 32 bits of x8) and `maxY` to stock 12.00 (upper 32 bits of x9). Jr's AI targets `y = -2.50` above the floor and navigates freely, while the camera remains pinned at 3.25. **Confirmed in game 2026-11-02:** Jr no longer sticks in the corner; the fight camera stays at stock height while swimming; the Royal Seed is reachable after the defeat.

## 22. 2026-11-03: issue #1, stopped autoscroll leaves the Wonder Seed off-screen (cave G reach)

**Report:** Piranha Plants on Parade (`Course002_Main`, label `002_歌って踊って パックンマーチ`): after the Wonder Flower the autoscroll stops with the finish seed (`ItemWonderFinishWonderSead` at (273.0, 15.0)) off the right edge; the camera does not move and the level cannot be finished.

**Cause (measured live in Eden, mod v1.1.0 code):** the autoscroll rail (`Scroll` rail of `AutoScrollControlSignalFrame` obj1175) ends at x 247.25. Every AINB caller of `SetAutoScrollPos` (`0x016C5548`; 6 local modules in `AutoScrollControlSignalFrame.pack.zs` and `SoundRhythmAutoScrollControlSignalFrame.pack.zs`, the only two archives in the romfs that name it) passes `scrollPos + (GetScreenCenterPos.WidthHalfSize, 0, 0)`, and `GetScreenCenterPos` (`0x017C8214`) reads the current view box (`0x001C3BF0`). The rail point is the view's left edge, so at 4:3 the fixed X is rail + 10.5 = 257.75 instead of stock 261.03: the narrower view is left-aligned in the stock frame [247.25, 274.81]. Cave G's stopped-scroll pan, fixed X + clamp(focus - fixed X, +/- delta), therefore only got back to the stock centre (live: offset 3.2778, camera 261.03, right edge 271.53, Mario at x 267.86).

**Fix (gen_zoom_v2.py, cave G only, 0x02138A28-0x02138AF0):** relative to the fixed X the stock frame is offset [0, 2 delta] (delta = 13.7778 - current half-width), so the stopped-scroll target is clamp(focus - fixed X - delta, +/- delta) + delta, and the eased offset is clamped to [0, 2 delta] (it was also capped at +/- delta, which alone would have kept the bug). Moving scrolls, the hold, the jump reset, cave H and the boss rooms (delta 0) are unchanged. Course002: offset 6.5556, camera 264.31, right edge 274.81 = stock. A symmetric +/- 2 delta was rejected: it would pan 6.6 blocks past the stock left edge and let the player walk back out of the scroll section.

**Status:** built and verified (`verify_pchtxt.py`, words diffed against the generator, cave G disassembled). User-confirmed 2026-11-03 in Eden: the Course002 seed is reachable and the Course101 airship autoscroll + Wonder Flower still work.

**Scan of the bug class (read-only review, QA-checked against the stage data):** only `AutoScrollControlSignalFrame` and `SoundRhythmAutoScrollControlSignalFrame` call `SetAutoScrollPos`, so the fix covers every stopped autoscroll. `Course061_Sub2` (seed x 595.0, rail end 570.75) was 0.03 blocks inside the old reach and now has 3.3; coins and display-box triggers at stops in Course002 (mid-rail pause at x 166), Course010, Course064_Sub1, Course290 and Course858 also come into view (note: §23 superseded this for the six `AUTOSCROLL_ENDS` stages—including `Course002_Main` and `Course290_Main`—where Cave G locks horizontal camera offset to 0.0 at intermediate pauses and vertical climbs, so `CourseDisplayBoxSwitch` triggers and actors in `[rail_X + 21.0, rail_X + 27.56]` require stage edits; see lesson learned in §44 on auditing and shifting entire relay chains via `tools/audit_autoscroll_relays.py`). Not covered: while a scroll moves the view stays left-aligned (the rightmost 6.56 blocks appear only after 2 s still; centring would make the left push edge 3.3 blocks earlier than stock), and Course857_Main's stops last 104 and 100 frames, under the 120-frame hold, so its `CourseDisplayBoxSwitch` triggers (a `DisplayAreaSwitch` node, not a player switch) fire later than stock instead of during the pause. Vertical autoscrolls keep the stock top edge (fixed Y = rail Y - half-height). `StopScroll` side locks are authored at the 16:9 centre, so cave H's lock X +/- delta covers their frames. POW blocks hit the visible 4:3 screen.

## 23. 2026-11-03: autoscroll camera locking during mid-scroll pauses (Cave G end-stop table)

**Problem:** In v1.1.1, stopped autoscrolls ease camera offset towards the player after 120 frames (~2 s) of stillness. On stages with long intermediate pauses, notably Course002 *Piranha Plants on Parade* (`Course002_Main`, which pauses for 361 frames during the Wonder musical section), the stillness counter expired mid-scroll. The camera unlocked, drifted towards the player, and then abruptly snapped back when autoscrolling resumed.

**Survey (`tools/scan_autoscroll_ends.py`):**
Added an automated scanner to examine all 22 autoscroll courses in RomFS for any intermediate pauses $\ge 120$ frames prior to the final rail point across three mechanisms:
1. `WaitFrame` attributes on autoscroll rail points.
2. Plateaus (consecutive identical rail coordinates with duration $\ge 120$ frames).
3. `PulledWaitFrame` initial start delays on autoscroll actors.

The scan confirmed intermediate pauses $\ge 120$ frames on the autoscroll rail in 6 areas:
- `Course002_Main` (885847797): plateau pts 1->2 (361f pause at rail x 166.0, margin 81.25 blocks from rail end 247.25)
- `Course022_Main` (2740185052): WaitFrame on pt 0 (120f pause at rail x 445.25, margin 247.75 blocks from rail end 693.00)
- `Course062_Sub1` (3839196513): plateau pts 0->1 (150f pause at rail x 138.25, margin 65.00 blocks from rail end 203.25)
- `Course102_Main` (4167497323): actor PulledWaitFrame (120f start pause at rail x 8.00, margin 10.50 blocks from rail end 18.50)
- `Course290_Main` (2931365200): plateau pts 16->17 (360f pause at rail x 174.00, margin 197.00 blocks from rail end 371.00)
- `Course857_Main` (3856421716): plateau pts 0->2 (360f pause at rail x 53.00, margin 483.25 blocks from rail end 536.25)

Every listed pause has a margin $> 0.05$ blocks from the rail's final point, preventing any false unlock.

**Fix (`tools/gen_zoom_v2.py`):**
1. Added `AUTOSCROLL_ENDS` table in `gen_zoom_v2.py`, emitted as `TABLE_ENDS` at `0x02138E3C` (after the boss table). Each entry stores `(RootAreaHash, rail_end_X + 13.7778)` pairs terminated by `(0, 0)`.
2. Added helper in Cave G at `0x02138914`: when the 120-frame stillness counter reaches 0, Cave G jumps to helper `0x02138914`. It compares current `fixed X + delta` against the table key.
   - If the area is listed in the table and $|(\text{fixed X} + \Delta) - \text{key}| \le 0.05$, the camera unlocks to follow the player within $[0, 2\Delta]$.
   - If the area is listed in the table but not at the end stop, desired offset remains 0.0, keeping the camera locked to scroll coordinates. Because Cave G locks desired offset to 0.0 whenever $|(\text{fixed X} + \Delta) - \text{key}| > 0.05$ (both at mid-scroll horizontal plateaus and during vertical climbs where fixed X is stationary below rail_end_X), right-edge `CourseDisplayBoxSwitch` triggers and actors in `AUTOSCROLL_ENDS` courses stay cropped by 6.56 blocks until the final stop.
   - If the area is not listed in `TABLE_ENDS` (standard locked rooms or autoscrolls with no mid-scroll pauses), it falls through to unlocked camera follow.

**Status:** Built and verified with `verify_pchtxt.py` (304 patch lines, 11 hooks). Confirmed in game on Course002 in Eden: camera remains locked during the mid-scroll singing pause, and unlocks at the final stop to reach the Wonder Seed.

## 23b. 2026-11-03: Break Time! Wonder Token Tunes (`Course411_Course`) full-room 4:3 framing

**Report:** In 4:3 with stock base height (15.5), Break Time! Wonder Token Tunes (`Course411_Course`, label `411_ちょっと一息 ワンダーピースの音楽室_Course`, RootAreaHash `1607468536`) cuts off the left and right sides of the room by 25%. In 16:9 this single-screen rhythm puzzle is designed to show all note blocks and wonder tokens across the room at once; at 4:3, players had to guess where tokens spawned off-screen.

**Analysis:**
- Sizing: Room width is 27.5 blocks, framed by pillars at x = 0.0 and x = 28.0 with `CameraArea` `[14.0, 0.5, 0.0]`, `[27.5, 15.5, 1.0]`. In 4:3, showing the full 27.56-block width requires base view height G = 20.6667 (`20.6667 * 4/3 = 27.5556`).
- Code patch: Added `(1607468536, 20.6666667, 0.0)` to the `BOSS` table in `gen_zoom_v2.py`. Cave A assigns G = 20.6667, delta = 0.0, fitting the room width exactly to the screen edges.
- Framing challenge: With G = 20.6667, view height expands from 15.5 to 20.67 blocks (5.17 blocks taller). Centered at stock y = 8.25, the screen reaches y = 18.58 at the top and y = -2.08 at the bottom. The original room artwork is only ~17.5 blocks tall (y = 0.0 to 17.5). At the top, the arch (`MapObjCommonMiniMokkinKazariHashiraTopA00` at y = 17.095) sat below the ceiling, exposing 1.5 blocks of bare wall planks above it; at the bottom, an unrendered pitch-black void was exposed below the wood slats (y in [-2.08, 0.0]).
- Attempt 1 (rejected): Translating the arch up alone to y = 19.68 broke the sculpted corner joints with the side pillars (`MapObjCommonMiniMokkinAshibaHashiraA00` at y = 13.0). Scaling the lower wall `DVCommonMiniMokkinMiddleKabeA00` by 1.45 in Y vertically stretched the wavy red curtain and music staff, looking visibly deformed while still leaving a bottom void.
- Solution (stage edits via `build_stage.py`, 0 problems on `--verify`):
  1. Synchronized frame: moved arch `KazariHashiraTopA00` (y 17.095 -> 18.545) and both side pillars `AshibaHashiraA00` (y 13.0 -> 14.45) together by +1.45 in Y. The arch crowns the 4:3 ceiling exactly as in 16:9 while corner joints remain 100% flush.
  2. Background wall framing: nudged upper wall `DVCommonMiniMokkinMiddleKabeA01` to y = 14.05 (matching Course417) and shifted backdrop / lower wall `DVCommonMiniMokkinMiddleKabeA00` to y = 6.05 (Scale 1.0). Its top edge (y = 13.9) tucks cleanly behind the upper scallops (sealing the sky blue gap), while its bottom extends the unstretched vertical slats past the bottom of the screen (y = -2.08), eliminating the void box with zero distortion.

**Status:** Built, verified and user-confirmed in Eden.

## 24. 2026-11-04: complete Break Time census and grouped review checklist

**Scope:** read-only inspection of the local 1.2.1 originals identified 19 Break Time courses (Course400–418). All 151 CourseInfo and 451 StageParam records were checked; the Mini category, Break Time labels and existing world-map entries agree. Recursive stage references cover 24 map-unit files, including container roots and background subareas. Course450–453 (SecretSquare) and Course460 (Bonus) are not Break Time courses.

**Tracking:** added [BREAK-TIME-REVIEW.md](BREAK-TIME-REVIEW.md) as the working checklist, linked from AGENTS.md. Course411 remains the user-confirmed reference from §23; the other 18 courses are pending human play-tests, not confirmed bugs. The audit baseline is mod commit `6bfcf0d`. English titles were cross-checked against public course references rather than read from a local 1.2.1 English message archive.

**First group:** Course415 (Bouncy Tunes) and Course417 (Trottin' Piranha Plants) share Course411's Mokkin theater assets and one-screen camera geometry. Review full-room gameplay visibility and artwork coverage together, but do not copy Course411's stage coordinates: their original framing differs. Next full-room candidates are Course403, Course408 and Course401. Course407's vertical autoscroll is a separate early behavior check; the remaining checklist groups distinguish linked backgrounds, vertical traversal, a rotating room and horizontal traversal.

**Status:** documentation and static-review findings only. No new mod output, candidate fixes or in-game results.

## 25. 2026-11-04: Course415 Bouncy Tunes full-width camera candidate

**Request:** the maintainer chose to build and test a full-room camera for Course415 before doing a baseline play-test. This is a requested candidate, not a human-reproduced defect or a confirmed fix.

**Camera:** the local 1.2.1 original confirms `Course415_Course` RootAreaHash `3684305666` and a `CameraArea` at `[14.0, 0.5, 0.0]`, scale `[27.5, 15.5, 1.0]`. Added `(3684305666, 20.6666667, 0.0)` after Course411 in `gen_zoom_v2.py`'s existing per-area table. This restores about 27.56 blocks of horizontal view at 4:3, with no lock panning. The view is also taller; Course415's stage artwork is deliberately unchanged for this first test. Course417 is unchanged.

**Build identity:** development v1.1.3 over `6bfcf0d` (uncommitted); patch SHA-256 `7df9c5b273902858e61e7e416d859362b9b3a49871763eb78c53e72932ec9304`. The regenerated patch replaces the old table terminator's hash/height at `0x02138E3C` / `0x02138E40`, retains zero delta at `0x02138E44`, and places the new terminator at `0x02138E48–0x02138E53`, before cave H. Exact word comparison shows all prior hooks, instructions and other area settings are unchanged. Repository and installed-mod backups were made outside the repo before editing.

**Verification:** `verify_pchtxt.py` passes (267 patch lines, 11 hooks, 0 errors), now independently checking all six area overrides and table termination. It rejects the previous patch without Course415, incorrect Course415 hash/height/delta, a missing terminator and a Course411 height regression. A separate read-only review found no issue in the generator/table/verifier diff. `build_stage.py --verify` reports 0 problems for the unchanged two stage files. The layout verifier requires an external build report, so a fresh layout rebuild was verified (0 problems) and compared byte-for-byte with all 115 shipped layout archives; no layouts changed. `check_repo.py` and `git diff --check` pass.

**Status:** built and verified, awaiting the maintainer's first Course415 play-test in Eden. Check full-room token/block visibility, theater coverage and joints, then completion/retry and the Course411 reference. No additional human confirmation, commit or release.

## 26. 2026-11-04: Course415 theater artwork candidate after the camera preview

**Human preview:** the maintainer provided a screenshot from Windows/Eden using the v1.1.3 camera-only trial from §25. The room spans the screen, but the taller view exposes a black strip below the lower backdrop and leaves a plank band above the arch. This is a reproduced artwork problem, not confirmation of full token-sequence visibility, completion or retry.

**Stage candidate (v1.1.4):** applied Course411's framing approach to Course415's own original actors. The arch and both pillars have the same original placements as Course411, so they move together +1.45 in Y (arch to 18.545, pillars to 14.45). The upper wall moves 14.5 -> 14.05. Course415's lower wall starts at 7.0, unlike Course411's 8.0, so it moves only -0.95 to the same final height 6.05. Five `Translate` Y edits; scales stay 1.0, with no gameplay actors moved. These positions target the same ceiling alignment and unstretched backdrop coverage as the confirmed Course411 fix, but Course415's result still needs its own human check.

**Scope:** Course417 remains unchanged. The initial exact-A00 check found different arch/wall placements and no `AshibaHashiraA00` actors, so it must not inherit the Course415 table blindly. A broader check later found A01 pillar variants (see §28). Course411 and Course152 stage outputs rebuild byte-for-byte unchanged. The release configuration now counts 118 RomFS files (115 layouts + 3 stage archives).

**Verification and identity:** `build_stage.py --verify` reports 0 problems across all three courses; Course415 differs from its original by 15 bytes, all within five float edits. Negative checks reject a missing Course415 file and an unchanged original. `verify_pchtxt.py` still passes (267 lines, 11 hooks); every enabled patch word matches the human-previewed camera trial, with only explanatory comments updated. A separate read-only review approved the stage-table and archive-count changes. Current patch SHA-256: `862f90a7e131373eb94c1349b293ae57c606e1407efd5005998be2e5469f7027`; Course415 archive SHA-256: `8bcfee1751a6aed5f74b494d9a09f261413f10002a058133052191cd1b7d79e9`.

**Status:** built and verified; artwork re-test pending in Eden. Keep Course415 open until the frame, moving-token sequence, completion and retry are checked; Course411 remains the regression reference. No commit or release.

## 27. 2026-11-04: Course415 framing approved; Course417 camera-only candidate

**Course415 result:** after testing the v1.1.4 artwork candidate, the maintainer said it looks good and requested the next level. This approves its visual framing in Windows/Eden, not the unreported full moving-token sequence, completion, retry or Course411 regression. The checklist therefore records the approval but keeps Course415 open. Tested identity: v1.1.4 over `6bfcf0d` (uncommitted), patch SHA-256 `862f90a7e131373eb94c1349b293ae57c606e1407efd5005998be2e5469f7027`, Course415 stage SHA-256 `8bcfee1751a6aed5f74b494d9a09f261413f10002a058133052191cd1b7d79e9`.

**Course417 candidate (v1.1.5):** the local original confirms `Course417_Course` RootAreaHash `2579434623`, `CameraArea` at `[14.0, 0.5, 0.0]`, scale `[27.5, 15.5, 1.0]`. Added `(2579434623, 20.6666667, 0.0)` to the existing per-area table, restoring about 27.56 blocks of width at 4:3. Its stage artwork is unchanged for the first preview: arch/wall placements differ from Course415 and there are no A00 pillar actors (A01 variants were subsequently found in §28). This is a candidate, not a reproduced Course417 defect or a confirmed fix.

**Build and verification:** only the new hash/height at `0x02138E48` / `0x02138E4C` and relocated zero terminator at `0x02138E54–0x02138E5F` change; delta at `0x02138E50` stays zero. Every prior patch word, including Course415's override, is unchanged. `verify_pchtxt.py` passes (270 lines, 11 hooks), independently checking seven overrides and termination. Seven negative/regression controls reject the prior patch without Course417, a wrong Course417 hash/height/delta, a missing terminator, and Course415/Course411 height regressions. A separate read-only review found no issue. Stage verification reports 0 problems for the unchanged three archives; all 115 shipped layouts match the externally rebuilt/verified layouts (0 problems). Backups of both repository and installed mod were saved outside the repo before editing. Current patch SHA-256: `a4bf30a5f784d5bbfd08f97f5ef8f1a804f2c6d025c49c290fc20bb05b84c9c9`.

**Status:** Course417 built and verified, awaiting its first human preview in Eden. Check whole-room framing, top/bottom artwork coverage, edge enemy movement/activation, completion and retry. The RomFS count remains 118; no Course417 stage archive is shipped. No commit or release.

## 28. 2026-11-04: Course417 theater artwork candidate with A01 pillars

**Human preview:** the maintainer supplied a Windows/Eden screenshot from the v1.1.5 camera-only trial (§27). The room spans the screen, but there is space above the arch and dark space below the backdrop. The maintainer requested the same framing approach as the earlier theater fixes. This does not establish enemy movement/activation, completion or retry behavior.

**Actor-family correction:** the earlier exact-name search found no A00 pillars, not an absence of side pillars. A broader search found two `MapObjCommonMiniMokkinAshibaHashiraA01` actors. Current instructions and the checklist now name the variant explicitly; the guide recommends checking related actor-name variants instead of relying on exact matches.

**Stage candidate (v1.1.6):** Course417's arch starts at y = 17.25, so reaching the shared target 18.545 needs +1.295, not Course415's +1.45. Both A01 pillars receive that same shift to y = 14.295; the left retains its tiny authored X/Y offsets. The rebuilt floats give all three frame actors the exact same +1.2950000762939453 displacement. Upper/lower wall panels start at y = 14 / 6 and move to the proven final heights 14.05 / 6.05. Five Translate Y edits; no scales, X/Z, note blocks, enemies or rails changed. The wall shifts are small because Course417 already starts near the shared targets; final visual coverage remains a test question, not a claim.

**Build and verification:** `build_stage.py --verify` reports 0 problems across all four stages; Course417 differs by 14 bytes, all inside five float edits. Controls reject a missing Course417 archive, an unchanged original and an incorrectly copied Course415 pillar height. A separate read-only review found no issue with the entries or archive count. All three earlier stage archives rebuild byte-for-byte unchanged. Every enabled camera patch word matches the screenshot-tested trial, and `verify_pchtxt.py` passes (270 lines, 11 hooks); only patch comments changed. RomFS count is now 119 (115 layouts + 4 stages). Repository and installed-mod backups were saved outside the repo before editing.

**Identity:** v1.1.6 over `6bfcf0d` (uncommitted); patch SHA-256 `0e7b9b513ec228bfeb715b66e47ffa6d90ce92d5de7833b637db17c801a0788d`; Course417 archive SHA-256 `c7e89c9646de44aef2d17e86dff3c384700ce133153f8585377cd058b993c726`.

**Status:** built and verified, awaiting artwork re-test in Eden. Check arch/side joints and top/bottom coverage, then enemy movement/activation, completion and retry. Course415 remains visually approved with its separate gameplay checks open. No commit or release.

## 29. 2026-11-04: Course417 pillar bases and a guarded A00 substitution

**Report:** the maintainer's screenshot of v1.1.6 shows both A01 pillar bases ending above the bottom of the screen. The upper frame is aligned, but raising the shorter visible A01 artwork did not extend its bases. Tested identity: patch SHA-256 `0e7b9b513ec228bfeb715b66e47ffa6d90ce92d5de7833b637db17c801a0788d`, Course417 stage `c7e89c9646de44aef2d17e86dff3c384700ce133153f8585377cd058b993c726`; Windows/Eden, over `6bfcf0d` with uncommitted changes.

**Investigation:** the local A00/A01 actor packs have 19 actor/component definitions that compare equal after normalizing variant resource names, including the static-map parent and collision shape. Their matching collision bounds do not establish matching visible mesh coverage. The existing A00 artwork already covers the approved Course411/415 view. Course417's original value-string table contains A01 but no A00 entry; the A01 text is consumed only by the two pillar Gyaml fields.

**Candidate (v1.1.7):** select `MapObjCommonMiniMokkinAshibaHashiraA00` for only the two Course417 pillar hashes and align them at y = 14.45, as in Course411/415, retaining the left actor's tiny authored offsets. The arch, wall panels, camera, scales and every other actor remain unchanged from v1.1.6. No actor/model pack is shipped: the game supplies the referenced A00 resource. This avoids stretching the A01 artwork or lowering the correctly aligned arch.

**Guarded edit:** added `GYAML_EDITS` and a same-length pooled-string helper to `build_stage.py`. It checks unique actor selection, original types/names, string bounds/order/NUL and overlapping storage, then requires the complete parsed tree to differ only in the selected Gyaml fields before mutating the input. The one changed string byte affects exactly the two intended references. The verifier retains same-size, byte-allowlist and exact reconstructed-output checks. Sixteen synthetic unit tests in `tools/test_build_stage.py` cover the successful rename, aliases, overlapping storage, wrong/missing/duplicate actors, UTF-8 lengths, sorting and atomic rejection, without any game data.

**Verification:** all 16 tests pass. Stage verification reports 0 problems across four courses; Course417 differs from its original by 15 bytes across five float edits and one guarded string edit. Independent semantic comparison against v1.1.6 confirms only the two pillar Gyaml values and their Y alignment changed. The previous A01 candidate, A01 at A00 height and an unrelated actor shift are rejected. A separate read-only review found no issue. All earlier stage archives are byte-identical; the camera patch is byte-identical and its verifier passes (270 lines, 11 hooks). RomFS count remains 119. Backups were saved outside the repo before editing.

**Identity/status:** v1.1.7 pillar candidate over `6bfcf0d` (uncommitted); Course417 archive SHA-256 `aaea4bd8d67582658e7f5178ea4f7f8553f605af07ea84b181675be0d4400758`. Built and verified, not yet human-confirmed. Re-test both pillar bases and upper joints, then the remaining enemy/gameplay checks. No commit or release.

## 30. 2026-11-04: Course417 full-height pillar framing approved

**Human result:** after the v1.1.7 test question asking whether both pillars continue below the screen with their upper arch joints flush, the maintainer replied "Looks good" in Windows/Eden. This approves visual framing only. The full enemy sequence, edge movement/activation, completion, retry and current-build Course411 regression were not reported; Course417's checklist row stays open, as does Course415's separate gameplay follow-up.

**Tested identity:** development v1.1.7 over `6bfcf0d` with uncommitted changes. Unchanged patch SHA-256 `0e7b9b513ec228bfeb715b66e47ffa6d90ce92d5de7833b637db17c801a0788d`; Course417 stage SHA-256 `aaea4bd8d67582658e7f5178ea4f7f8553f605af07ea84b181675be0d4400758`. No mod output changed to record this approval. It does not establish full gameplay confirmation or a release.


## 31. 2026-11-04: Course403 Zip-Go-Round camera-only candidate

**Request:** the maintainer chose to apply the next full-room camera candidate before looking at the level. Course403 remains untested; this is not a human-reproduced defect or a confirmed fix. Course415/417 retain their separate visual framing approvals, with full gameplay checks and the current-build Course411 regression still open.

**Camera (v1.1.8):** the local 1.2.1 original confirms `Course403_Course` RootAreaHash `177084102`, with a `CameraArea` at `[14.0, 0.5, 0.0]`, scale `[27.5, 15.5, 1.0]`. Appended `(177084102, 20.6666667, 0.0)` to the existing per-area table in `gen_zoom_v2.py`. This restores about 27.56 blocks of width at 4:3 without lock panning, so the opposing rails and moving Wonder Tokens can be reviewed together. Stage artwork is deliberately unchanged for the first preview; no Course403 stage archive is shipped. All 119 RomFS files remain byte-identical.

**Patch scope:** the generator replaces the former terminator's hash/height at `0x02138E54` / `0x02138E58`, keeps delta zero at `0x02138E5C`, and adds a three-word zero terminator at `0x02138E60–0x02138E6B`, before cave H. Exact enabled-word comparison confirms every previous hook, instruction and area override is unchanged. The independent verifier now requires eight entries and the relocated terminator.

**Verification:** `verify_pchtxt.py` passes (273 lines, 11 hooks, 0 errors). Eight negative/regression controls reject the previous patch without Course403, incorrect Course403 hash/height/delta, a missing terminator, and Course411/415/417 height regressions for the intended reasons. Stage verification reports 0 problems across all four unchanged archives; all 16 stage-tool unit tests pass. A fresh external layout rebuild verifies with 0 problems and matches all 115 shipped layouts byte-for-byte. A separate read-only review found no issue in the generator, generated table, independent verifier or candidate-status docs. `check_repo.py` and `git diff --check` pass.

**Identity and handoff:** development v1.1.8 over `68af3fd` (uncommitted); patch SHA-256 `08ebeeb79a458b90a5ba61ee3c457a13cfaef03d5d52a8ba1a5f6e0da508a5c5`. Repository and installed-mod backups were saved outside the repo before editing. With Eden at its idle game-list window, mirrored the candidate into the existing test mod using `robocopy /MIR`; all 121 installed files match, with only the patch changed. Built and verified, awaiting the first human preview. Ask whether both side rails and moving tokens are visible together without top/bottom artwork gaps; completion/retry follow later. No commit or release.

## 32. 2026-11-04: Course403 background evaluation and camera-only decision

**Report and investigation:** the maintainer play-tested the v1.1.8 camera candidate in Eden on Windows and reported that the framing "looks fairly good already", but questioned the dark bottom band beneath the bottom rail. Investigation of screenshot `step_408_media_0.png` and extracted 1.2.1 assets confirmed:
1. The rail box is vertically centered (top margin 195 px, bottom margin 172 px; center y = 8.25 matches stock).
2. The dark bottom gradient is 100% attached to the background sky dome: the panoramic sphere fades to black at its bottom nadir pole. In stock 16:9, the camera bottom stops at the bottom rail (y = 0.5), keeping the bottom pole completely off-screen. In 4:3 with full-room zoom (G = 20.6667), the taller view extends 2.58 blocks below the rail (y = -2.08), revealing the bottom pole of the sphere.
3. Sibling sky stages (such as `AA_Yama_Jyoku_Hare`) mask this nadir with a vertical height fog (`Fog.MainWorld`), which is disabled in Course403's exclusive palette (`AA_Yama_Jyoku_AxcelBlockMini`).

**Decision:** after evaluating background behavior, the maintainer directed to leave the mod at the camera zoom and nothing else. No stage or palette archives are shipped. Course403 runs cleanly with full-room zoom (G = 20.6667, delta = 0), fitting the entire 27.5-wide level inside the 4:3 screen.

**Identity and state:** development v1.1.8 over `68af3fd` (uncommitted); patch SHA-256 `08ebeeb79a458b90a5ba61ee3c457a13cfaef03d5d52a8ba1a5f6e0da508a5c5`. RomFS count is 119 files (115 layouts + 4 stages). `verify_pchtxt.py` passes (273 lines, 11 hooks). `build_stage.py --verify` passes on all 4 unchanged stage files; 16 stage unit tests, `check_repo.py` and `git diff --check` pass.

## 33. 2026-11-05: Course403 floor cloud expansion and visual framing approval

**Follow-up report:** during subsequent testing, the maintainer requested covering the dark bottom sky void using the level's cloud assets, reporting visible flickering on initial wide-cloud trials.

**Reverse engineering `ObjectCloudArea`:**
1. Analysis of `Pack/Actor/ObjectCloudArea.pack.zs` and executable functions at `0x015b14bc`–`0x015b20c8` confirmed `ObjectCloudArea` has zero physics collision bodies (`ControllerEntityNamePathAry: []`), only an `AreaSensor` (`Box1x1Center`). Players and objects pass through freely; the actor is 100% cosmetic decorative fluff.
2. The actor allocates decorative cloud puffs on an integer grid: `count = ceil(Scale.X) * ceil(Scale.Y)`, allocating 184 bytes (`0xb8`) per puff. Puff positions are placed deterministically at cell centers (`min + 0.5 + i`), with zero random jitter.
3. Draw capacity cap: at `0x01b808ec`–`0x01b80908` in `main-1.2.1.bin`, the engine compares the accumulated puff draw count against a fixed capacity buffer (`[x8, #0xd40]`). If count exceeds the limit, the draw call silently early-returns (`b.le #0x1b80960`), causing puffs to pop on and off (flicker). A single 30-wide actor (120 puffs) saturated this limit when combined with the right-wall clouds.

**Candidate iterations:**
- Candidate A / A2 / A3: Scale X = 30.0, Translate Y = -1.5. Covered the dark band but suffered puff flickering due to the draw buffer limit. An overlap audit of A3 confirmed zero bounding box overlaps, proving the flicker was capacity-driven, not coincident z-fighting.
- Diagnostic B2: five separate 6x4 clouds at Y = -1.5. Proved 100% flicker-free, confirming puff capacity, but removing the right wall clouds stripped the stage framing and exposed a horizontal gap under the red dash platform.
- Candidate C: restored all 9 base clouds (4 ceiling, 5 side walls) and widened the floor cloud to Scale X = 20.0. Clean and flicker-free, but left corner gaps.
- Candidates C26 / C27: widened floor cloud to 26 and 27 blocks. Flicker-free, but left scalloped edge gaps at Y = -2.08 (the 4:3 view bottom).
- Candidate C28 (Approved): Floor cloud Hash `3184768010431751081`:
  - `Translate`: `[12.5, 0.0, 0.0]` -> `[14.0, -0.4, 0.0]`
  - `Scale`: `[6.0, 4.0, 1.0]` -> `[28.0, 4.0, 1.0]`
  Centering at X = 14.0 spans [0.0, 28.0], past the screen edges [0.22, 27.78]. Shifting Translate Y to -0.4 pushes bottom puff lobes to Y = -2.40 (past view bottom Y = -2.08), sealing both bottom corners and scalloped edge gaps off-screen, while keeping top puff lobes at Y = 1.60 neatly tucked inside the red dash floor thickness (Y in [1.0, 2.0]). Total puffs (112) remain safely within the engine draw budget.

**Human verification:** the maintainer play-tested Candidate C28 in Windows/Eden and approved the result: "Yes that's good" (seamless coverage across the full width, no bottom void, unobstructed rails, 100% flicker-free).

**Build and verification:** added Course403 to `EDITS` in `tools/build_stage.py`. `build_stage.py --verify` passes with 0 problems across all 5 stages; Course403 differs from 1.2.1 stock by exactly 7 bytes across 2 float edits. Shipped RomFS count is 120 (115 layouts + 5 stage archives). Shipped patch SHA-256: `08ebeeb79a458b90a5ba61ee3c457a13cfaef03d5d52a8ba1a5f6e0da508a5c5`; Course403 stage SHA-256: `d71bef2fab7e769391949622a8cbfa6259a88ece0201c18af64f9d3d079e3d6f`.

## 34. 2026-11-06: Course008_Sub2 (Angry Spikes Sinkin' Pipes) Wonder area full-width camera zoom

**Bug report:** in W2 Angry Spikes Sinkin' Pipes, entering the Wonder area resulted in a soft lock because the player could not reach/collect the Wonder Seed due to camera positioning. The camera zoom needed adjustment to show the full room width as in 16:9.

**Investigation:**
1. Course identification: Course008_Course StageParam has label 008 (Gabon's Hideout, Valley of the Sinking Pipes == W2 Angry Spikes Sinkin' Pipes).
2. The Wonder sequence takes place in sub-area Course008_Sub2 (RootAreaHash 3214359175, 0xBF973A87), which contains CameraArea with Scale X 27.5 and Translate X 19.0, spanning X in [5.25, 32.75] with solid walls at X [1.0, 7.0] (Wall 0) and X [31.0, 37.0] (Wall 1).
3. The vertical rhythm autoscroll runs along Y from 16 to 81, ending at ItemWonderFinishWonderSead at Y = 76.24 and Exit Dokan at Y = 77.0. Rising and sinking pipes span X = 7.0 to 31.0.
4. In stock 16:9, view width is 27.56 blocks (15.5 * 16 / 9), so the full 27.5 width fits on screen with zero horizontal camera panning required.
5. In 4:3 with default small-room base G = 15.5, view width was only 20.67 blocks (15.5 * 4 / 3), cropping the left pipes (X in [7, 8]) and right pipes (X in [30, 31]) off-screen, and preventing proper tracking of the seed spawn.

**Fix:**
Added Course008_Sub2 (RootAreaHash 3214359175, G = 20.6666667, delta = 0.0) to BOSS table in tools/gen_zoom_v2.py. At G = 20.6667, 4:3 view width expands to 20.6667 * 4 / 3 = 27.56 blocks, matching stock 16:9 width exactly. With delta = 0.0, the camera remains centered at X = 19.0, extending into the solid side walls with 0 out-of-bounds void exposed and all rising/sinking pipes and the Wonder Seed fully visible.

## 35. 2026-11-06: Course400 (Pop Up, Hoppo!) Break Time full-width camera candidate

**Request:** apply a camera fix to Course400 (Break Time! Pop Up, Hoppo!, World 1 - Pipe-Rock Plateau) so it fits within the 4:3 display.

**Investigation:**
1. Course identification: `Course400_Course` (`RootAreaHash` 2214662437, `0x84011125`), World 1 Pipe-Rock Plateau.
2. Contains a `CameraArea` (`Hash` 5315702174901982453) with Translate `[14.0, 0.5, 0.0]` and Scale `[27.5, 15.5, 1.0]`, authored for a single stock 16:9 screen (width 27.56 blocks).
3. In stock 16:9, the camera remains fixed in place to display the Hoppo rebound puzzle across the room.
4. In 4:3 with default small-room base G = 15.5, the visible width shrinks to 20.67 blocks, unlocking the camera to pan horizontally following Mario and cropping ~25% of the room.
5. Added `(2214662437, 20.6666667, 0.0)` to the `BOSS` table in `tools/gen_zoom_v2.py`. With G = 20.6667, 4:3 view width expands to 20.6667 * 4 / 3 = 27.56 blocks, matching the stock 16:9 width with zero horizontal panning (delta = 0.0).
6. Stage artwork is deliberately unchanged for the first candidate preview.

**Build and verification:**
- Patch lines generated via `tools/gen_zoom_v2.py` and checked with `tools/verify_pchtxt.py` (279 patch lines, 11 hooks, 0 errors).
- All 16 stage tool unit tests and stage verifiers pass (`build_stage.py --verify` reports 0 problems).
- Shipped patch SHA-256: `ca091bb6d71f87bcd5df3e25bb145b413fb3911c6b325a20305846808970bb67`.

## 36. 2026-11-06: Course400 visual framing approved and Hoppo spawn elevation fix

**Human verification:** the maintainer play-tested the Course400 full-width camera ($G = 20.6667$, $\text{delta} = 0$) in Windows/Eden and confirmed:
- Framing and camera lock approved: "Okay, looks good."
- Observed issue: "The one thing that looks a little weird is that the hippo spawns on screen now so you see it pop in. Is there potentially a safe adjustment that can be made to fix this?"

**Investigation:**
1. In stock 16:9 ($G = 15.5$), the camera view height is 15.5 blocks, placing the top screen edge at $Y \approx 11.0$ (or ~14.8 at peak jump). Nintendo authored `EnemyKoropon` at $Y = 12.0$ (and linked `PopUpTag` at $Y = 16.5$) specifically so the Hoppo would spawn off-screen above the visible frame and fall into the room.
2. In 4:3 with $G = 20.6667$, the view height expands to 20.67 blocks (center $Y \approx 3.5$–$4.5$), placing the visible top of the screen at $Y \approx 14.0$–$14.8$.
3. As a result, the original spawn coordinate ($Y = 12.0$) sits inside the active viewport, causing the Hoppo to visually materialize in mid-air on-screen when triggered.

**Fix:**
Added stage edits for `Course400_Course` to `EDITS` in `tools/build_stage.py`:
- `EnemyKoropon` (Hash `17703685394400552912`): `Translate.Y` $12.0 \to 17.0$ ($+5.0$ blocks).
- `PopUpTag` (Hash `3402723882765168318`): `Translate.Y` $16.5 \to 21.5$ ($+5.0$ blocks, preserving the relative 4.5-block offset and 4.0 jump height parameter).
- At $Y = 17.0$, the spawn occurs safely above the 4:3 top screen edge even when jumping. Horizontal position ($X = 3.0$) and falling trajectory are unchanged; drop time increases by ~0.3s.

**Build and verification:**
- Stage build via `tools/build_stage.py` wrote `mod/Native 4x3 Aspect Ratio/romfs/BancMapUnit/Course400_Course.bcett.byml.zs` (SHA-256: `c51dc7836e74ce07e9e7b913ec7b50a0fce691600efdcd5c4d152371188b1add`).
- `build_stage.py --verify` passes with 0 problems across all 6 stage files (`Course400_Course: 2 byte(s) differ, all inside 2 edit(s)`).
- All 16 stage tool unit tests pass; `verify_pchtxt.py` passes (279 lines, 11 hooks, 0 errors).
- Synchronized to `%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio` via robocopy.

## 37. 2026-11-06: Course401 ice-block spawn elevation

The full-room Course401 camera uses $G = 20.6667$, which expands the 4:3 view enough to expose the stock ice-block spawn points. Added 14 `Course401_Course` actor edits to `tools/build_stage.py`: eight `ObjectBlockPushIce` actors move from $(24.0, 18.0, 0.0)$ to $(24.0, 27.0, 0.0)$, and six `ObjectBlockPushIce4x4` actors move from $(23.0, 19.0, 0.0)$ to $(23.0, 28.0, 0.0)$. X/Z placement and relative spacing are unchanged.

**Build and verification:**
- Rebuilt `mod/Native 4x3 Aspect Ratio/romfs/BancMapUnit/Course401_Course.bcett.byml.zs` from the 1.2.1 originals (SHA-256: `EDDB23C7711DB860072139B3101C3BB57F4EBAAEAB87DAE07240F88F45576112`).
- `build_stage.py --verify` reports 0 problems across all 7 stage files; Course401 differs by 14 bytes, all inside the 14 declared edits.
- All 16 `test_build_stage.py` tests pass; `scripts/check_repo.py` passes. Gameplay, completion, and retry remain untested.

## 38. 2026-11-06: Course408 camera horizontal lock and Balloon Killer spawn relocation

In Course408 (Break Time! Floating Wonder Tokens), the maintainer requested zooming the camera in slightly ( = 18.5$) to cut off the unrendered lower gradient while keeping all Wonder tokens and gameplay visible, locking the horizontal camera panning at center  = 64.0$ while keeping the stock vertical camera height ( = 0.5$), and eliminating mid-air Balloon Killer pop-in.

**Implementation:**
- Code patch: Added Course408 (AreaHash 1474562704) to the BOSS table in 	ools/gen_zoom_v2.py with  = 18.5$ and $\text{delta} = 0.0$.
- Stage edits (	ools/build_stage.py):
  - CameraArea (Hash 892663682): Translate stays at stock 64 0.5 0$; Scale adjusted from 27.5 15.5 1$ to 24.6667 15.5 1$. Matching the area width to the camera's 4:3 view width (.5 \times 4/3 = 24.6667$) locks the camera horizontally at  = 64.0$ without lateral panning, while retaining the stock  = 0.5$ height.
  - Left EnemyBalloonKiller (Hash 3427707647): Translate moved from 54 17.5 0$ to 45 10 0$, spawning off-screen left.
  - Right EnemyBalloonKiller (Hash 2369650736): Translate moved from 84.5 18.5 0$ to 85 10 0$, spawning off-screen right.

**Build and verification:**
- Stage build wrote mod/Native 4x3 Aspect Ratio/romfs/BancMapUnit/Course408_Course.bcett.byml.zs.
- uild_stage.py --verify reports 0 problems (7 bytes differ, all inside 3 edits).
- Verified with erify_pchtxt.py (291 lines, 11 hooks, 0 errors).

## 39. 2026-11-06: Course407 top-right background void coverage

In Course407 (Break Time! Watery Wonder Tokens), the camera zoom ( = 20.6667$, $\text{delta} = 0.0$) was approved, but an unrendered triangular background void in the top-right corner was exposed.

**Implementation:**
- Stage edit (	ools/build_stage.py):
  - The foreground carved pillar DVWaKaiganFarIwaA01 (Hash 3373664933504165692) is kept stock, preserving its square carved top surface.
  - Background rock wall actor DVWaKaiganFarIwaA02 (Hash 14008780977747261966 at  = -193.0$): Translate.Y raised from .5$ to .0$ ($+4.5$ in Y) so the rock wall rises naturally behind the unmodified pillar to cover the void.

**Build and verification:**
- Stage build wrote mod/Native 4x3 Aspect Ratio/romfs/BancMapUnit/Course407_Course.bcett.byml.zs.
- uild_stage.py --verify reports 0 problems (1 byte differs, inside 1 edit).

## 40. 2026-11-06: Course409 reversion to stock

Per maintainer request, all modifications for Course409 (Raise the Stage) were reverted:
- Removed Course409_Main entry from BOSS table in 	ools/gen_zoom_v2.py.
- Rebuilt exefs/1.2.1.pchtxt.
- Removed stage edits from 	ools/build_stage.py and deleted mod/Native 4x3 Aspect Ratio/romfs/BancMapUnit/Course409_Main.bcett.byml.zs.
- Kept Course409 listed on the Break Time review TODO list for later investigation.

## 41. 2026-11-06: Course408 spawn elevation and Course407 proportional rock coverage

Updated the Break Time stage edits in `tools/build_stage.py`:
- Course408 keeps the CameraArea scale change from $(27.5, 15.5, 1.0)$ to $(24.6667, 15.5, 1.0)$, and raises both `EnemyBalloonKiller` actors plus their `CreateTag` actors by +9.0 in Y while preserving X/Z placement.
- Course407 reverts `DVWaKaiganFarIwaA02` and instead adjusts `DVWaKaiganFarIwaA01` (Hash `3373664933504165692`) from Translate $(23.5, 48.0, -167.5)$ / Scale $(0.7, 0.7, 0.7)$ to Translate $(23.5, 49.5, -167.5)$ / Scale $(0.82, 0.82, 0.82)$.

**Build and verification:**
- Rebuilt all nine declared `BancMapUnit` archives from the 1.2.1 originals.
- `build_stage.py --verify` reports 0 problems: Course408 differs by 7 bytes across 5 edits; Course407 differs by 10 bytes across 2 edits.
- All 16 `test_build_stage.py` tests pass; `scripts/check_repo.py` passes. Gameplay remains untested for these changes.

## 42. 2026-11-07: Course408 (Floating Wonder Tokens) Balloon Killer spawn investigation and final edits

The camera-only build for Course408 (CameraArea Hash `892663682`, Scale $(27.5, 15.5, 1.0) \to (24.6667, 15.5, 1.0)$, Translate stock $(64.0, 0.5, 0.0)$) spawned all four Balloon Killers, but the top-right and bottom-right pairs visibly popped into existence at the screen edges. Top-left and bottom-left were fine.

**Probes (all observed by the maintainer in Eden; cause unknown):**
- Moving both the Balloon Killer and its `CreateTag` by a small diagonal step (X and Y together) stopped every pair spawning; larger diagonal shifts also produced no spawns.
- A Y-only $+9.0$ move of the top pair (the Course401-style fix) spawned, but the bottom pairs were still stock and still popped in.
- X-only $+3$ on the top-right `CreateTag` (`2021327989`): no spawn.
- Y-only $-3$ on the bottom-right `CreateTag` (`1001471908`): spawned, and the pop-in was no longer visible.
- Final Y-only probe: top-right tag $+6.0$, bottom-left/bottom-right tags $-1.5$; all four spawned with no visible pop-in and unchanged paths/timing. Approved by the maintainer on 2026-11-07.

**Rule observed in Eden, cause unknown:** keep each `CreateTag` X at stock and change only Y. No code or data mechanism for the X sensitivity has been established; do not state one.

**Stock data note:** all four Course408 `CreateTag` actors have `onAppearSensor` false and `SensorRateY` 1.0, so the earlier sensor-range explanation does not apply. Each Balloon Killer stores a `PopUp` link to its tag; the top-left and bottom-left tags also receive `Create` from `LogicalSignalORTag` `3900693894`, which is fed by `AreaSwitchLocal` `4039892632`, `671366925` and `3555004888`. That link graph is data, not an explanation for the X sensitivity.

**Final stage edits in `tools/build_stage.py` (all four Balloon Killers and tag `2621681372` stock):**
- `CameraArea` `892663682`: Scale $(27.5, 15.5, 1.0) \to (24.6667, 15.5, 1.0)$.
- `CreateTag` `2021327989` (top-right): Translate Y $13.5 \to 19.5$ ($+6.0$).
- `CreateTag` `1522517719` (bottom-left): Translate Y $-1.5 \to -3.0$ ($-1.5$).
- `CreateTag` `1001471908` (bottom-right): Translate Y $-1.5 \to -3.0$ ($-1.5$).

This supersedes §§38 and 41 for Course408. Rebuild and verification: `build_stage.py --verify` reports 0 problems with `Course408_Course: 8 byte(s) differ, all inside 4 edit(s)`; `verify_pchtxt.py` reports OK (291 lines, 11 hooks, 0 errors); all 16 stage tests pass. Course408 stage SHA-256: `04c887078a75fedb2412975ae9a2280b6ae4b9f7221a379aa495a002eae18898`.

## 43. 2026-11-07: Break Time play-test approvals (Course401, Course404, Course407, Course408)

The maintainer play-tested the current build in Windows/Eden and approved Course401, Course404, Course407 and Course408. Course409 remains stock on the TODO list. Course408 is described in §42; Course401 keeps its 14 ice-block Y moves, Course407 keeps the A01 pillar translate/scale, and Course404 keeps its `Course404_Main` BOSS entry. Completion and retry were not separately reported for these four courses.

The mod now ships 124 romfs files (115 layouts + 9 stage archives). Patch SHA-256: `636492eb2b6a2bac8098d70f409aaf4b38ca1109d4ff3e842791e83e5962aadf`. Stage verification covers all nine stage files with 0 problems; `scripts/check_repo.py` passes.

## 44. 2026-11-07: Course290_Main (Bowser's Rage Stage) autoscroll triggers and rail framing

**Context & Findings:**
In `Course290_Main` (Bowser's Rage Stage, RootAreaHash `2931365200`), autoscroll signals pass `rail_X + current_half_width` to `SetAutoScrollPos`, left-aligning the 21.0-wide 4:3 view to `rail_X` (cropping 6.56 blocks off the right edge compared to stock 16:9 width 27.56). Because `Course290_Main` is listed in `AUTOSCROLL_ENDS`, Cave G locks camera offset to 0.0 at intermediate pauses and during vertical climbs, leaving right-edge `CourseDisplayBoxSwitch` triggers unactivated and actors cropped:
1. **Bowser statue Wonder Bulls spawn (commit `20f19cb`, confirmed in Eden):** Four statue-section `CourseDisplayBoxSwitch` triggers (`777445035`, `212790001`, `12855344573256944945`, `4029477259`) shifted left by 6.56 blocks in X, ensuring `EnemyTossinGroup` spawns during the approach and the post-statue rhythm pause activates correctly.
2. **Dragon section & vertical shaft ground/bars:** Seven `CourseDisplayBoxSwitch` triggers (`999420502`, `1755951341`, `1787195044`, `1117151842`, `4273434636`, `3717095890`, `1344248650`) shifted left by 6.56 blocks in X. Shifting `999420502` (Ring 1 spawn) alongside `1755951341` (Ring 1 delete / Ring 2 spawn) and `1787195044` (dragon transform) while keeping rail `pt 6` at stock 92.0 preserves the exact stock 16:9 timing intervals (403f and 488.9f), allowing Ring 1's 300-frame roll to complete. Switch `4273434636` activates to spawn bottom snake-block ground (`ObjectBlockSnakePole 34729090`) and guide coins. On `Rail 185828596`, `pt 8` shifted right to 102.0 (framing Wall 1 without pushing the player off Wall 0) and `pts 9-11` shifted right by +3.28 (115.28, 128.28, 128.28) so the 840-frame vertical shaft climb (`CameraArea 3010860670`, X = [124.75, 152.25]) is centered at X = 138.78, framing all four vertical snake poles.
3. **Post-statue Spike thrower pause framing & rhythm pipe compression:** On `Rail 185828596`, rhythm pause plateau `pts 16-17` shifted from 174.0 to 179.0 to frame X = [179.0, 200.0] in 4:3. To prevent the left group of 3 rising rhythm pipes (`SoundRhythmObjectUpDownDokan`) and 3 singing Piranha Plants (`EnemySoundRunRunPackun`) from being clipped by the left screen edge (authored at X = 178, 180, 182), they were compressed +2.0 blocks right to X = 180, 182, 184 (6 actor edits). In `BgUnits[0]`, Wall 2 right edge (pts 2-3) and Wall 5 left edge (pts 0-1) were shifted +2.0 in X across both `Walls` (4 bg edits) and `BeltRails` (4 belt edits), moving the pipe gap from [177, 183] to [179, 185] with aligned visual geometry and collision. This cleanly frames all 3 singing plants ([179.0, 185.0]) and the right Spike thrower (`EnemyRhythmGabon` 15920962010745316511 at X = 199.0) + pipe simultaneously with 1.0 block of margin on both sides.
4. **Relay chain audit & trigger synchronization (`tools/audit_autoscroll_relays.py`, commit `f4755aa`):**
   - **Lesson learned:** when shifting a `CourseDisplayBoxSwitch` in an autoscroll stage, audit and shift every switch in its relay chain (including sibling effect/smoke/tilt triggers) so relative frame intervals between spawn, effect/zap, and delete triggers do not collapse or invert.
   - Built `tools/audit_autoscroll_relays.py` to simulate `AutoScrollControlSignalFrame` movement and verify trigger activation timing against stock 16:9.
   - Shifted 9 additional `CourseDisplayBoxSwitch` triggers left by 6.56 blocks in X across the Kuribo section (`578319643`, `1536962149`, `14869113733391977869`), spiked ball tilt/roll (`1060316225`, `206918284`), and fossil zap relay (`663300194`, `17459050152995009628`, `742103869`, `2303338937`). Switch `4029477259` was kept at stock X = 206.00 to activate safely after the post-statue rhythm pause rather than prematurely during it.
5. **Opening fists rail shifts reverted (`6f8b393`):** Shifting rail `pts 0-4` right pushed the left edge into the player on initial descent and during the fist punches. A localized zoom-out (`G > 15.75` in `CameraArea 2220801104`, Y = [19.5, 35.0]) was rejected without stage scenery edits because `DVCommonTorideKemuriB` (bottom smoke) ends at Y = 18.50 and `DVCommonTorideKemuriA` (top smoke) ends at Y = 36.75, exposing visual voids. The opening fists section remains at stock camera framing.
