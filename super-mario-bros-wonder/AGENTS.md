# Agent instructions: Super Mario Bros. Wonder 4:3

Read the root [`../AGENTS.md`](../AGENTS.md) first. This file is the **source of truth for the current state** of the SMBW mod; [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) is the dated log of how it got here (its values may be superseded). The general method is in [`../docs/aspect-ratio-guide.md`](../docs/aspect-ratio-guide.md); its "Reference example" section describes this mod.

## Game and target

- Title ID `010015100B514000`, **version 1.2.1 only**, build ID `FF773E90972D544EB79406EAA65396D53C43EFB9`.
- Tested on Eden (yuzu family) with Graphics > Aspect Ratio > **Force 4:3**, on Windows (where agents can probe memory and take screenshots) and on the tester's Retroid Pocket Nova (Android). Other emulators and console are untested.
- Mod folder: `mod/Native 4x3 Aspect Ratio/` = `exefs/1.2.1.pchtxt` + `romfs/Layout/*.Nin_NX_NVN.blarc.zs` (115 changed archives) + `romfs/BancMapUnit/Course152_Sub4.bcett.byml.zs` (1 stage edit) + `README.txt` (ships with the mod; holds no install steps, only the link to `README.md#install`, the one install guide). Named "Nova Aspect Ratio 4x3 Native" before v1.0.0; don't rename it again.
- Installed for testing at `%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio`. Sync with the game closed: `robocopy "mod\Native 4x3 Aspect Ratio" "%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio" /MIR` (mirror: deletes archives the build no longer ships).
- Releases: tag prefix `smbw` (`.github/release-games.json`); procedure in the root AGENTS.md "Releasing". `layout_count` there counts every file under `romfs/` (115 layouts + 1 stage file = 116); bump it when that number changes.

## Local inputs (outside the repo)

| Input | Where it comes from | Used by |
| --- | --- | --- |
| Original layouts (1.2.1) | `<workspace>\extracted\romfs-1.2.1\Layout` (235 archives; in the maintainer's workspace the `extracted` folder is named `SM Wonder Extracted`), extracted with nstool (see Gotchas). Not won-aar's `wonder.zip`: that cache is older, 30 layouts differ | `build.py`, `verify.py`, `find_toplevel.py` |
| `exefs/main` 1.2.1 | nstool from the update NSP (guide: Workflow and tools > Extracting) | `nso_to_bin.py` |
| Flat image `main-1.2.1.bin` | `python tools/nso_to_bin.py <main> <out.bin>`; point `SMBW_MAIN_BIN` at it for `gen_zoom_v2.py`; `xref.py` takes the path as its first argument | `gen_zoom_v2.py`, `xref.py`, Ghidra |
| romfs `Stage`, `BancMapUnit`, `Event` | nstool with `--basenca` (see Gotchas); `<workspace>\extracted\romfs-1.2.1` | `byml.py`, `bymlpatch.py`, `build_stage.py` |

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
# then replace mod/Native 4x3 Aspect Ratio/romfs/BancMapUnit/ with <out_dir>/romfs/BancMapUnit/*

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
| `build_stage.py` | Stage edit table (`EDITS`): builds the shipped `BancMapUnit` files from the originals; `--verify` exits 1 unless each differs from its original only in the edited floats |
| `scan_autoscroll_ends.py <orig_romfs>` | Surveys RomFS course rails and autoscroll actors for intermediate pauses (>= 120 frames) and prints AUTOSCROLL_ENDS table for gen_zoom_v2.py |
| `gen_zoom_v2.py` | Camera patch generator (caves A-H, Y, K, per-area base and delta, boss table, autoscroll ends table); asserts delta <= max(0, (27.5556 - G*4/3)/2) |
| `verify_pchtxt.py [file]` | Disassembles every enabled line of a patch file |

Ghidra headless (Java 21): `analyzeHeadless <proj_dir> <proj_name> -process main-1.2.1.bin -noanalysis -scriptPath tools/ghidra -postScript DecompileAt.java "6c66b8,2e2b30"`.

Flat image layout (1.2.1): `.text` 0x0-0x2138650, `.ro` 0x2139000-0x338BC78, `.data` 0x338C000-0x3728DF8. Code cave: zero bytes 0x2138650-0x2139000 (executable, patchable), used 0x2138780-0x2138F23 (caves A, B, G helper, G, D, E, F1, F2, Y, K, boss table, autoscroll ends table, H; 0x2138988-0x21389FF, 0x2138DC0-0x2138DFF, 0x2138E74-0x2138EFF free). Spare .bss words used as mailboxes: 0x037D1F00-0x037D1F3B (0x037D1F04 = current area RootAreaHash).

## Current state (2026-11-03)

Shipped patch `exefs/1.2.1.pchtxt`: SHA-256 `1F0F8FFD...D9DA`, 356 lines, 11 hooks (`verify_pchtxt.py`). Since the tested v1.0.0 build it adds cave A's area-hash mailbox (`0x037D1F04`), cave Y (fight camera pin at y 3.25 in Course152_Sub4, hook `0x006C66E8`), cave K (`GetCameraBoundBox2f` Y bounds at `0x01781B70` for Bowser Jr. swim AI navigation), and autoscroll end-stop table (`TABLE_ENDS` at `0x02138E3C`) with Cave G helper (`0x02138914`) to keep autoscroll cameras locked during mid-scroll pauses; the cave W experiment was removed.

**Stage edit (`build_stage.py`):** `Course152_Sub4` (W4 Bowser Jr.) `KoopaJrSystemWaterMixAreaPlane` (Hash 2115412732, `Course152_Sub4[Design].muunt/obj451`) Scale Y 1.0 -> 1.5 (water tint covers the taller 4:3 view, confirmed in game), plus Unit 1 Wall 0/1/2 bottom points y = -7.0 -> -10.0 so the arena and corridor wall terrain extends past the bottom of the screen (y = -8.42), eliminating the out-of-bounds black void boxes in the bottom-left and bottom-right corners. 7 float edits (13 bytes), `build_stage.py --verify` 0 problems.

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
| hook `006C6FD0` -> cave G `02138A00`, helper `02138914` | Autoscrolls (`SetAutoScrollPos`): ride fixed X while moving; after 2 s still, query TABLE_ENDS (`02138E3C`): areas in table remain locked unless at rail end (|fixed X + delta - key| <= 0.05); at end stop or for unlisted areas, ease towards focus in [0, 2*delta] (mailboxes `037D1F30`-`38`) |
| hook `006C7BEC` -> cave H `02138F00` | `StopScroll` side locks: X = lock X + clamp(normal X - lock X, +/- delta). Every StopScroll room goes through here, not cave G |

Boss table (all delta 0): Course150_Sub4 607466214 G 21.0; Course151_Sub2 101336182, Course152_Sub4 1778226157, Course153_Sub3 1019598315 G 20.6667 (152's own zoom actor 17.5 multiplies the base). Optional lines commented after `@stop` (zone-lock disable, fixed zoom-outs 17-20) are not needed. Autoscroll end stops table (`TABLE_ENDS` at `0x02138E3C`, surveyed by `scan_autoscroll_ends.py`): areas with intermediate pauses >= 120 frames (Course002_Main 885847797, Course022_Main 2740185052, Course062_Sub1 3839196513, Course102_Main 4167497323, Course290_Main 2931365200, Course857_Main 3856421716) mapped to rail end X + 13.7778. Camera unlocks only when |fixed X + delta - key| <= 0.05.

**Confirmed in game:** badge houses and one-screen rooms, pause/menu blur, course-entry iris, HUD and key glyphs vs stock, Select a User card, Poplin shop, kingdom map, Pipe-Rock Plateau Palace arena + pipes, wide-level base 15.75 (Outmaway Valley), airship autoscroll + Wonder Flower (Course101, re-checked with the [0, 2*delta] cave G on 2026-11-03), Piranha Plants on Parade (Course002_Main: camera stays locked during mid-scroll singing pause and unlocks at the final stop to reach the Wonder Seed, issue #1), Puffy Lifts seed (Course021), course-clear photo and View photo, menu pointer, Badge Challenge restart wipe, W4 Bowser Jr. (Course152_Sub4: water tint plane Scale Y 1.5, cave Y fight camera at 3.25, Royal Seed reachable, cave K swim AI, wall terrain to y = -10.0 for corner voids).

**Not yet checked in game:** Course061_Sub2 (Chase Killers) seed after its stopped autoscroll (x 595.0, rail end 570.75: the pre-fix reach was only 0.03 past it); Course857_Main short scroll stops (104 and 100 frames, under cave G's 120-frame hold, so a `CourseDisplayBoxSwitch` at x 211.5 fires later than stock); whether 151/153 also release their arena area after the cutscene; Course150 arena since its delta became 0; Bowser Jr. rooms 151-153 (extra height; alternate zoom path when subject+0x1BE != 0 bypasses caves B/F1); WipeTo*/WipeWarp; pits, level ends and Wonder zooms at 15.75; last boss and airship boss rooms; multiplayer; Android flashing bars (WipeCourseIn's kept-fill capture reads 180 rows past the frame).

**Open items:**
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
