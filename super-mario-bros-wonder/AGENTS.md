# Agent instructions: Super Mario Bros. Wonder 4:3

Read the root [`../AGENTS.md`](../AGENTS.md) first. This file is the **source of truth for the current state** of the SMBW mod; [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) is the dated log of how it got here (its values may be superseded). The general method is in [`../docs/aspect-ratio-guide.md`](../docs/aspect-ratio-guide.md); its "Reference example" section describes this mod.

## Game and target

- Title ID `010015100B514000`, **version 1.2.1 only**, build ID `FF773E90972D544EB79406EAA65396D53C43EFB9`.
- Tested on Eden (yuzu family) with Graphics > Aspect Ratio > **Force 4:3**, on Windows (where agents can probe memory and take screenshots) and on the tester's Retroid Pocket Nova (Android). Other emulators and console are untested.
- Mod folder: `mod/Native 4x3 Aspect Ratio/` = `exefs/1.2.1.pchtxt` + `romfs/Layout/*.Nin_NX_NVN.blarc.zs` (115 changed archives) + `romfs/BancMapUnit/*.bcett.byml.zs` (5 stage edits: Course152_Sub4, Course411_Course, Course415_Course, Course417_Course, Course403_Course) + `README.txt` (ships with the mod; holds no install steps, only the link to `README.md#install`, the one install guide). Named "Nova Aspect Ratio 4x3 Native" before v1.0.0; don't rename it again.
- Installed for testing at `%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio`. Sync with the game closed: `robocopy "mod\Native 4x3 Aspect Ratio" "%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio" /MIR` (mirror: deletes archives the build no longer ships).
- Releases: tag prefix `smbw` (`.github/release-games.json`); procedure in the root AGENTS.md "Releasing". `layout_count` there counts every file under `romfs/` (115 layouts + 5 stage files = 120); bump it when that number changes.

## Local inputs (outside the repo)

| Input | Where it comes from | Used by |
| --- | --- | --- |
| Original layouts (1.2.1) | `<workspace>\extracted\romfs-1.2.1\Layout` (235 archives; in the maintainer's workspace the `extracted` folder is named `SM Wonder Extracted`), extracted with nstool (see Gotchas). Not won-aar's `wonder.zip`: that cache is older, 30 layouts differ | `build.py`, `verify.py`, `find_toplevel.py` |
| `exefs/main` 1.2.1 | nstool from the update NSP (guide: Workflow and tools > Extracting) | `nso_to_bin.py` |
| Flat image `main-1.2.1.bin` | `python tools/nso_to_bin.py <main> <out.bin>`; point `SMBW_MAIN_BIN` at it for `gen_zoom_v2.py`; `xref.py` takes the path as its first argument | `gen_zoom_v2.py`, `xref.py`, Ghidra |
| romfs `Stage`, `BancMapUnit`, `Event`, `Gyml` | nstool with `--basenca` (see Gotchas); `<workspace>\extracted\romfs-1.2.1` | `byml.py`, `bymlpatch.py`, `build_stage.py`, `build_stage.py` |

## Build and verify

Python 3.14 (stdlib `compression.zstd`), plus `capstone` and `lz4` for the code tools. Don't use `-I` for scripts that need `capstone` (isolated mode hides per-user packages). Set `PYTHONIOENCODING=utf-8` when printing BYML (Japanese labels).

```
# Layouts: rebuild from the originals, check, compare
python tools/build.py tools <orig_layout_dir> <out_dir>          # <out_dir> outside the repo: romfs/Layout + build_report.json
python tools/verify.py tools <orig_layout_dir> <out_dir>/romfs/Layout   # must report 0 problem(s)
# then replace mod/Native 4x3 Aspect Ratio/romfs/Layout/ with <out_dir>/romfs/Layout/* (delete first: the build
# leaves unchanged archives out, so a stale file would otherwise stay); update layout_count in release-games.json

# Stage edits (BancMapUnit): rebuild from the originals, then check the shipped files
python tools/build_stage.py <orig_romfs> <out_dir>                # writes <out_dir>/romfs/BancMapUnit/*.bcett.byml.zs
python tools/build_stage.py --verify <orig_romfs> "mod/Native 4x3 Aspect Ratio/romfs"   # must report 0 problem(s)
python -B -m unittest discover -s tools -p test_build_stage.py -v # synthetic string-edit safety tests; no originals needed
# then replace mod/Native 4x3 Aspect Ratio/romfs/BancMapUnit/ with <out_dir>/romfs/BancMapUnit/*

python tools/build_stage.py <orig_romfs> <out_dir>              # writes <out_dir>/romfs/Gyml/Gfx/EnvPaletteParam/*.bgyml
python tools/build_stage.py --verify <orig_romfs> "mod/Native 4x3 Aspect Ratio/romfs" # must report 0 problem(s)
python -B -m unittest discover -s tools -p test_build_stage.py -v # synthetic float-edit safety tests; no originals needed
# then replace mod/Native 4x3 Aspect Ratio/romfs/Gyml/Gfx/EnvPaletteParam/ with <out_dir>/romfs/Gyml/Gfx/EnvPaletteParam/*

# Code patch: regenerate patch lines, then disassemble the shipped file
$env:SMBW_MAIN_BIN = '<path>\main-1.2.1.bin'      # PowerShell (bash: export SMBW_MAIN_BIN=...)
python tools/gen_zoom_v2.py <lines_out.txt>
python tools/verify_pchtxt.py                                     # defaults to the mod's exefs/1.2.1.pchtxt
```

A rebuild from the 1.2.1 originals reproduces the committed `romfs/Layout` byte for byte (GrandWorldMap is copied from `tools/hand-edited/`; its 1.2.1 original is identical to the one it was edited from). Re-run `find_toplevel.py tools <orig_layout_dir>` if the originals change. `gen_zoom_v2.py` prints address/word lines; merge them into `exefs/1.2.1.pchtxt` (header, comments and the optional lines after `@stop` are hand-maintained) and run `verify_pchtxt.py`.

| Script | Use |
| --- | --- |
| `lyt.py` (library), `find_toplevel.py`, `analyze.py`, `build.py`, `verify.py` | Layout (BFLYT/BFLAN) pipeline: parse, analyse, build, verify. First argument is the tools folder; `verify.py` exits 1 on any problem |
| `dump.py <layout_dir> [names...]` | Print every pane of the given archives |
| `nso_to_bin.py <main> <out.bin>` | NSO to flat image. A `.pchtxt` address with `offset_shift 0x100` equals the flat-image offset |
| `xref.py <bin> 2138650 <addr...>` / `--float <v> --ro-start 2139000` | Code references (ADRP + load) to data addresses, or a float's locations and users |
| `ghidra/DecompileAt.java` | Headless decompile of the functions containing given addresses (import the flat image as raw AArch64 at base 0) |
| `byml.py <file> [--grep text]` | Dump BYML/BGYML (and `.zs`) level/stage/event data |
| `bymlpatch.py` | Same-size in-place edit of one BYML value (or an actor's `--translate` / `--scale`), recompressed |
| `build_stage.py` | Stage edit tables (`EDITS`, `GYAML_EDITS`): builds the shipped `BancMapUnit` files from the originals; `--verify` exits 1 unless each differs only in declared float/string edits; Gyaml edits also require exact parsed-tree scope |
| `build_stage.py` | Environment palette edit table (`EDITS`): builds shipped `EnvPaletteParam` BYML files from originals; `--verify` exits 1 unless each differs only in declared float edits |
| `gen_zoom_v2.py` | Camera patch generator (caves A-H, Y, K, per-area base and delta, boss table); asserts delta <= max(0, (27.5556 - G*4/3)/2) |
| `verify_pchtxt.py [file]` | Disassembles every enabled line of a patch file |

Ghidra headless (Java 21): `analyzeHeadless <proj_dir> <proj_name> -process main-1.2.1.bin -noanalysis -scriptPath tools/ghidra -postScript DecompileAt.java "6c66b8,2e2b30"`.

Flat image layout (1.2.1): `.text` 0x0-0x2138650, `.ro` 0x2139000-0x338BC78, `.data` 0x338C000-0x3728DF8. Code cave: zero bytes 0x2138650-0x2139000 (executable, patchable), used 0x2138780-0x2138F23 (caves A, B, G, D, E, F1, F2, Y, K, table, H; 0x2138DC0-0x2138DFF free). Spare .bss words used as mailboxes: 0x037D1F00-0x037D1F3B (0x037D1F04 = current area RootAreaHash).

## Current state (2026-11-05)

Shipped patch `exefs/1.2.1.pchtxt`: 11 hooks (`verify_pchtxt.py`). Includes area-hash mailbox (`0x037D1F04`), cave Y (fight camera pin at y 3.25 in Course152_Sub4, hook `0x006C66E8`), cave K (`GetCameraBoundBox2f` Y bounds at `0x01781B70` for Bowser Jr. swim AI navigation), and `BOSS` table entries for full-arena zooms (Course150, Course152, Course411 Break Time! Wonder Token Tunes, Course415 Break Time! Bouncy Tunes, Course417 Break Time! Trottin' Piranha Plants and Course403 Break Time! Zip-Go-Round at G = 20.6667, delta = 0.0).

**Course403 visual framing approved (v1.1.8, 2026-11-05):** the maintainer confirmed the full-room framing and widened floor cloud look good in Windows/Eden. Its full-width camera (RootAreaHash `177084102`, G = 20.6667, delta = 0) and floor cloud edits (Translate Y 0.0 -> -0.4, Scale X 6.0 -> 28.0) cover the unrendered black void and seal the bottom corners and scalloped edge gaps off-screen, with 0 flicker and 0 art stretch. All 9 base clouds remain stock. Shipped RomFS count is 120 (115 layouts + 5 stages). `verify_pchtxt.py` passes (273 lines, 11 hooks). Stage verification passes across all five stages (Course403 differs by 7 bytes, 2 declared edits). Stage SHA-256: `d71bef2fab7e769391949622a8cbfa6259a88ece0201c18af64f9d3d079e3d6f`; Patch SHA-256: `08ebeeb79a458b90a5ba61ee3c457a13cfaef03d5d52a8ba1a5f6e0da508a5c5`. Completion and retry checks remain open.

**Course415 framing approved (v1.1.4, 2026-11-04):** the maintainer confirmed the new theater framing looks good in Eden. Its full-width camera (RootAreaHash `3684305666`, G = 20.6667, delta = 0) and five artwork translations remain unchanged. Tested v1.1.4 patch SHA-256: `862f90a7e131373eb94c1349b293ae57c606e1407efd5005998be2e5469f7027`; stage SHA-256: `8bcfee1751a6aed5f74b494d9a09f261413f10002a058133052191cd1b7d79e9`. The full moving-token sequence, completion, retry and Course411 regression were not reported; keep the checklist row open for those checks.

**Course417 visual framing approved (v1.1.7, 2026-11-04):** the maintainer said "Looks good" in Windows/Eden after being asked whether both pillars extend below the screen with the upper joints flush. This approves visual framing only, not full gameplay. The earlier v1.1.6 A01 pillar bases ended above the bottom edge; v1.1.7 selects the existing A00 variant used in Course411/415 for just those two actor hashes, at y = 14.45 (left authored offsets retained). All 19 actor/component definitions match after normalizing variant resource names, including physics; visible coverage was checked separately by the maintainer. Arch y = 18.545, walls y = 14.05 / 6.05, scales, camera and all other actors are unchanged from v1.1.6. `GYAML_EDITS` guards the shared value-string rename with a full parsed-tree comparison, allowing only those two Gyaml fields to change. Stage verification and 16 synthetic safety tests pass. Tested patch SHA-256 (unchanged): `0e7b9b513ec228bfeb715b66e47ffa6d90ce92d5de7833b637db17c801a0788d`; Course417 stage SHA-256: `aaea4bd8d67582658e7f5178ea4f7f8553f605af07ea84b181675be0d4400758`. The full enemy sequence, edge movement/activation, completion, retry and current Course411 regression remain unconfirmed; keep the checklist row open.

**Stage edits (`build_stage.py`):**
1. `Course152_Sub4` (W4 Bowser Jr.): `KoopaJrSystemWaterMixAreaPlane` (Hash 2115412732) Scale Y 1.0 -> 1.5 (water tint covers the taller 4:3 view, confirmed in game), plus Unit 1 Wall 0/1/2 bottom points y = -7.0 -> -10.0 so the arena and corridor wall terrain extends past the bottom of the screen (y = -8.42), eliminating the out-of-bounds black void boxes in the bottom-left and bottom-right corners. 7 float edits (13 bytes).
2. `Course411_Course` (Break Time! Wonder Token Tunes): in 4:3 with G = 20.6667 (matching stock 16:9 width 27.56), view height expands to 20.67. Top arch (`KazariHashiraTopA00`) and both side pillars (`AshibaHashiraA00`) moved +1.45 in Y together to crown the 4:3 ceiling with seamless corner joints. Upper wall (`MiddleKabeA01`) nudged down to y = 14.05, and backdrop / lower wall (`MiddleKabeA00`) moved to y = 6.05 (Scale 1.0) so the natural wood slats extend past the bottom of the screen (y = -2.08) and the backdrop tucks cleanly behind the upper scallops, eliminating both the bottom void and sky gaps without stretching any artwork (user-confirmed in game). 5 float edits (16 bytes). `build_stage.py --verify` reports 0 problems.
3. `Course415_Course` (Break Time! Bouncy Tunes), **artwork framing user-approved in Eden; gameplay checks pending**: arch and both pillars translated +1.45 in Y to the same final heights as Course411 (arch 18.545, pillars 14.45); upper wall y 14.5 -> 14.05, lower wall y 7.0 -> 6.05. Course415's original lower wall is one block below Course411's, so its displacement is -0.95, not -1.95. Scales remain 1.0. 5 float edits (15 bytes); existing Course152/411 output is byte-identical. `build_stage.py --verify` reports 0 problems across all four courses.
4. `Course417_Course` (Break Time! Trottin' Piranha Plants), **visual framing user-approved in Windows/Eden; gameplay checks pending**: arch y 17.25 -> 18.545; original A01 pillars are replaced with A00 at y = 14.45 (left retains its tiny authored X/Y offsets), matching Course411/415's approved A00 alignment. Upper wall y 14 -> 14.05; lower wall y 6 -> 6.05. No scales, X/Z, note blocks, enemies or rails changed. Five float edits plus one guarded pooled-string byte change affecting only the two pillar Gyaml fields: 15 changed bytes, 6 declared edits. The A00 actor pack is supplied by the game, not shipped by the mod. All earlier stage archives remain byte-identical.
5. `Course403_Course` (Break Time! Zip-Go-Round), **visual framing user-approved in Windows/Eden; gameplay checks pending**: floor cloud (`ObjectCloudArea` Hash 3184768010431751081) Translate Y 0.0 -> -0.4, Scale X 6.0 -> 28.0. Spans X [0.0, 28.0] and drops bottom puff lobes to Y = -2.40, completely covering the unrendered sky void below the red dash floor and sealing scalloped edge gaps off-screen, while keeping the top at Y = 1.6 flush against the red dash floor. 2 float edits (7 bytes). All other 9 clouds remain stock. `build_stage.py --verify` reports 0 problems across all five courses.


**Layouts (`build.py`, built from the 1.2.1 originals since 2026-10-30):** 115 of the game's 235 archives ship (114 changed top-level layouts incl. the 1.2.1-only `AmiiboReadWindow`, plus `LCursor`); the other 120 are unchanged and fall back to the game's copies. top-level RootPane scale y 0.75 (`ROOT_SY`); HUD/header/footer edge-anchored (+/-180 root-local units, TransY keys shifted too); full-screen layers grown x4/3 (captures and fades height only, artwork uniform); parts layouts untouched; curated per-screen tables `FORCE_SHIFT`, `NO_SHIFT_SUBTREE`, `NO_SHIFT_LAYOUT`, `NO_FILL`. 638 float writes, 46 fill panes, `verify.py` clean. Until 2026-10-30 the mod was built from won-aar's older cache and shipped all 234 archives, so 30 screens (incl. Pause, MainMenu, Title, CourseList, talk windows, button icons) carried pre-1.2.1 layouts; the 1.2.1 rebuild applies identical edits. **Play-tested after the 1.2.1 rebuild (2026-10-31): menus, HUD, pause, maps, transitions, course clear, cursor and amiibo look good.**

- Capture sources (`N_Cap*`, `N_Capture`) stay 1920x1080 (WipeMiss 1080x1080); only use panes fill.
- `CAPTURE_KEEP_FILL`: WipeCourseIn `N_Cap` stays 1440 with `P_CapUse` V cropped to 0.125-0.875 (round iris).
- `CAP_USE_LAYOUTS = {'BadgeShop'}`: small capture-use panes are stretched x4/3 only in the Poplin shop intro; everywhere else they stay authored size (stretching made HUD icons, glyphs and card rows ~1.3x too tall).
- `PROJECTED_PATTERN = {'WipeBadgeChallenge': {'W_WipeC', 'W_WipeLT'}}`: ortho-projected (texgen source 3) patterns follow the 16:9 screen, so their TexSRT X is scaled by 0.75.
- `ROOT_SKIP = {'Cursor'}` + `PART_SCALE_Y = {'LCursor': {'N_RB'}}`: the game places the menu pointer in screen coordinates, so the Cursor root stays 1; the arrow's 4:3 shape comes from unrotated `N_RB` sy 0.75.
- `PHOTO_4x3` (CourseOut, MainMenu): the course-clear photo is a 4:3 capture, so photo panes and frames are narrowed by 0.25 x photo width; `SHIFT_KEEP_KEY` keeps the View photo end key at 0.
- `GrandWorldMap` is hand-edited (`tools/hand-edited/`, band filler pane behind the 16:9 map art); build.py copies it over the generated file and verify.py skips it.

**Code patch** (generated by `gen_zoom_v2.py`):

| Lines | Purpose |
| --- | --- |
| `02AEEDB4 ABAAAA3F` | Aspect constant 1.7778 to 1.3333 |
| `02AEE9E8`, `02AEE968`, `02AEE834`, `02AEEBD8` | Hard-coded view widths 27.5556 / 13.7778 and negatives set to 20.6667 / 10.3333 |
| hook `00136A80` -> cave `02138780` | Level loader keeps 27.5556 for CameraAreas authored one screen wide (otherwise ~241 one-screen rooms shrink and box the player in) |
| hook `006C66DC` -> cave A `02138800` | Per-area base G and reach delta: boss table at `02138E00` first, else area width < 60 -> G 15.5 / delta 3.4444, else G 15.75 / delta 3.2778. Writes G `037D1F00`, current area hash `037D1F04`, delta `037D1F18`, width `037D1F1C`, controller/subject `037D1F20`/`28`; then the 16:9 reach rule |
| hook `002E2B30` -> cave B `02138900` | View height: stock `fmov s1,#15.5`, then `fmax` with G |
| `006C6358`, `006C6364` -> caves F1/F2 `02138D00`/`02138D20` | Camera-controller half-extents use G; width scaled by G/15.5 |
| hooks `00833B00`, `005E428C` -> caves D `02138B00`, E `02138C00` | Bowser Jr. pipe display box kept at authored size when G > 15.5 |
| hook `006C66E8` -> cave Y `02138D40` | Course152_Sub4 only (hash literal `02138D84`): camera Y limits use the stock half-height (half-height x 15.5 / G), so the camera centre matches stock (3.25) and pins during the fight zoom |
| hook `01781B70` -> cave K `02138D88` | Course152_Sub4 only (hash literal `02138DB4`): `GetCameraBoundBox2f` replaces minY with stock -5.50 and maxY with stock 12.00 so Bowser Jr.'s swim AI navigation targets points above the floor and never corners |
| hook `006C6FD0` -> cave G `02138A00` | Autoscrolls (`SetAutoScrollPos`): ride fixed X while moving; after 2 s still, ease towards focus in [0, 2*delta] (mailboxes `037D1F30`-`38`) |
| hook `006C7BEC` -> cave H `02138F00` | `StopScroll` side locks: X = lock X + clamp(normal X - lock X, +/- delta). Every StopScroll room goes through here, not cave G |

Boss/fixed-room table (all delta 0): Course150_Sub4 607466214 G 21.0; Course151_Sub2 101336182, Course152_Sub4 1778226157, Course153_Sub3 1019598315, Course411_Course 1607468536, Course415_Course 3684305666, Course417_Course 2579434623, Course403_Course 177084102 G 20.6667 (152's own zoom actor 17.5 multiplies the base). Course403, Course415 and Course417 visual framing is user-approved with gameplay checks still open. Course411's earlier framing fix is user-confirmed; regression on the current build is not yet reported. Optional lines commented after `@stop` (zone-lock disable, fixed zoom-outs 17-20) are not needed.

**Confirmed in game:** badge houses and one-screen rooms, pause/menu blur, course-entry iris, HUD and key glyphs vs stock, Select a User card, Poplin shop, kingdom map, Pipe-Rock Plateau Palace arena + pipes, wide-level base 15.75 (Outmaway Valley), airship autoscroll + Wonder Flower (Course101, re-checked with the [0, 2*delta] cave G on 2026-11-03), Piranha Plants on Parade seed after the stopped autoscroll (Course002_Main, issue #1), Puffy Lifts seed (Course021), course-clear photo and View photo, menu pointer, Badge Challenge restart wipe, W4 Bowser Jr. (Course152_Sub4: water tint plane Scale Y 1.5, cave Y fight camera at 3.25, Royal Seed reachable, cave K swim AI, wall terrain to y = -10.0 for corner voids).

**Not yet checked in game:** Course061_Sub2 (Chase Killers) seed after its stopped autoscroll (x 595.0, rail end 570.75: the pre-fix reach was only 0.03 past it); Course857_Main short scroll stops (104 and 100 frames, under cave G's 120-frame hold, so a `CourseDisplayBoxSwitch` at x 211.5 fires later than stock); whether 151/153 also release their arena area after the cutscene; Course150 arena since its delta became 0; Bowser Jr. rooms 151-153 (extra height; alternate zoom path when subject+0x1BE != 0 bypasses caves B/F1); WipeTo*/WipeWarp; pits, level ends and Wonder zooms at 15.75; last boss and airship boss rooms; multiplayer; Android flashing bars (WipeCourseIn's kept-fill capture reads 180 rows past the frame).

**Open items:**
- Break Time framing QA: use [docs/BREAK-TIME-REVIEW.md](docs/BREAK-TIME-REVIEW.md) for the complete grouped checklist and per-course test results. Course403 (Zip-Go-Round) visual framing approved on Windows/Eden on 2026-11-05. Course417's full enemy sequence and edge movement/activation, then completion/retry, Course415's full moving-token sequence and completion/retry, and Course403 completion/retry remain open. Re-check Course411 on the current build as the previously confirmed musical-theater reference; static inspection is not play-test confirmation.
- Death screen = `WipeMiss` (capture + spotlight) under `MissZanki`. WipeMiss has the capture setup that made WipeCourseIn's circle taller than wide, so its spotlight may be oval. Candidate fix: add `'WipeMiss': ('N_Cap','P_CapUse')` to `CAPTURE_KEEP_FILL` (N_Cap 1080 -> 1440, P_CapUse V 0.125-0.875). An A/B file was tried in Eden only; result unclear. Ship only after the tester confirms the spotlight round.
- Other screen-projected patterns (`CourseIn` P_BG checker, `MissZanki` P_BG dots) may be ~0.75 wide; add them to `PROJECTED_PATTERN` only if seen.

## Camera knowledge (1.2.1 addresses)

- Camera controller `FUN_006C5970` (x19 = controller, x20 = camera subject, x21 = camera object). Final clamp block `0x6C663C`-`0x6C6770`; final camera write `0x6C6AB8`-`0x6C6B00` (X override flag `controller+0x29` -> `controller+0x1A0`). Follow function `FUN_006C9AEC`.
- View setup `FUN_002E2990`: half-height = zoom x 15.5 x 0.5, half-width = half-height x aspect (`0x2AEEDB4`); zoom instruction `0x2E2B30`. Zoom = subject +0x204 / +0x1F0 (or +0x1F4 when +0x1BE != 0 and +0x1E0 != 2).
- Visible rectangle with hard-coded width: `FUN_004DCF90` (scales with zoom, so object activation follows the view). Player world position: `subject+0x244` (+12 x player index).
- Area records: table `*(0x37B2128+0x50)`, index signed byte `controller+0x10A`, hash `record+0x90` (= `RootAreaHash` in the room's `.bcett`), bounds `record+0x94` (min x,y,z, max x,y,z).
- Only `SetAutoScrollPos` (0x16C5548) writes subject+0x194/+0x1B4 (cave G path); `StopScroll` sets subject+0xA00/0xA01, which become controller+0x29/0x2A (cave H path).
- `SetChangeCourseZoom` (0x16CA4CC) stores zoomBlockCount/15.5 at subject+0x1F0; the view multiplies it by max(15.5, G).
- `0x001C3BF0` returns the camera-view box (global `0x37B4E00`, optionally area-transformed), which already follows the 4:3 view; 36 callers incl. the cave D/E sites. Not the CameraArea, and not what bounds Bowser Jr.'s water tint (that is the fixed-size `KoopaJrSystemWaterMixAreaPlane` model, following the camera in x only at its HomePos y/z).
- Royal Seed: `BossKoopaJr` AINB spawns `MotherWonderSeed` at `GetCourseCameraPosition` (`0x017860F4`, reads subject+0x60/+0x64) + (0, -2, 0); the -2 is in the AINB expression. subject+0x60/+0x64 is a snapshot of the camera, refreshed by camera init and events (CourseCameraRefresh, SetDemoCamera, MoveSeamlessCamera, StopCameraForCameraSpeed via `0x228DD8`), not every frame. NpcPrince and Bowser Jr.'s Wonder attack target read the same value.
- Camera limits: X in [controller+0x34 + half-width (+0x1B0), +0x3C - half-width], Y in [+0x38 + half-height (+0x1B4), +0x40 - half-height] (s1/s3, s0/s2 at `0x6C66E8`). When the view is taller than the area, `0x6C66E0`/`0x6C6700` -> `0x6C79A8`/`0x6C79BC` centre it (min = max = centre); in a taller area the camera rests on the bottom limit, which a taller 4:3 view raises by (half-height - stock half-height). `0x6C79D0` is a floor limit (subject+0xD18, off at -999.9). The controller bounds are the active CameraArea, or after an area is released (Course152_Sub4 after the cutscene) the union of the course's areas.
- Red herrings (symptoms of the shrunken one-screen area): hold flag `subject+0x9FF`, focus pointer `controller+0x1D8`, demo-camera X override, projection-derived limits.

## Gotchas

- With `offset_shift 0x100`, the patch address equals the flat-image offset (not offset - 0x100).
- Write patch bytes from encoder output and disassemble every enabled line before handing a build over (two hand-typing errors happened). Keep `.pchtxt` comments on their own lines.
- Before patching a shared constant, read every user (`xref.py`). Check the camera area size the game actually uses before suspecting camera logic.
- Code patches load only at game boot (Eden's JIT ignores live code writes); data constants and heap can be changed live for quick experiments. The guest base address changes per launch.
- Eden locks layout files while the game runs: close it before syncing.
- Course file numbers don't match in-game world numbers (Course021 is a W2 level); identify levels by their stage label in `Stage/StageParam/*.bgyml`.
- Layouts are version-specific. To extract 1.2.1's: `nstool --tik <update tik> --basenca <base program NCA> -x /1/Layout <out> <update program NCA>` (run from PowerShell with Windows paths; Git Bash path mangling breaks nstool).
- Have a second reviewer check every encoding, branch target and register claim before shipping a code change (registers are checked per hook, not per function: in the camera controller only s31 is unused throughout).
