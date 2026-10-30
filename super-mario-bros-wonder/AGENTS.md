# Agent instructions: Super Mario Bros. Wonder 4:3

Read the root [`../AGENTS.md`](../AGENTS.md) first. This file is the **source of truth for the current state** of the SMBW mod; [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) is the dated log of how it got here (its values may be superseded). The general method is in [`../docs/aspect-ratio-guide.md`](../docs/aspect-ratio-guide.md); its "Reference example" section describes this mod.

## Game and target

- Title ID `010015100B514000`, **version 1.2.1 only**, build ID `FF773E90972D544EB79406EAA65396D53C43EFB9`.
- Tested on Eden (yuzu family) with Graphics > Aspect Ratio > **Force 4:3**, on Windows (where agents can probe memory and take screenshots) and on the tester's Retroid Pocket Nova (Android). Other emulators and console are untested.
- Mod folder: `mod/Native 4x3 Aspect Ratio/` = `exefs/1.2.1.pchtxt` + `romfs/Layout/*.Nin_NX_NVN.blarc.zs` (115 changed archives) + `README.txt` (player-facing, ships with the mod; keep its install steps in step with `README.md#install`). Named "Nova Aspect Ratio 4x3 Native" before v1.0.0; don't rename it again.
- Installed for testing at `%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio`. Sync with the game closed: `robocopy "mod\Native 4x3 Aspect Ratio" "%APPDATA%\eden\load\010015100B514000\Native 4x3 Aspect Ratio" /MIR` (mirror: deletes archives the build no longer ships).
- Releases: tag prefix `smbw` (`.github/release-games.json`); procedure in the root AGENTS.md "Releasing". Bump `layout_count` there if the number of layout archives changes.

## Local inputs (outside the repo)

| Input | Where it comes from | Used by |
| --- | --- | --- |
| Original layouts (1.2.1) | `<workspace>\extracted\romfs-1.2.1\Layout` (235 archives; in the maintainer's workspace the `extracted` folder is named `SM Wonder Extracted`), extracted with nstool (see Gotchas). Not won-aar's `wonder.zip`: that cache is older, 30 layouts differ | `build.py`, `verify.py`, `find_toplevel.py` |
| `exefs/main` 1.2.1 | nstool from the update NSP (guide: Workflow and tools > Extracting) | `nso_to_bin.py` |
| Flat image `main-1.2.1.bin` | `python tools/nso_to_bin.py <main> <out.bin>`; point `SMBW_MAIN_BIN` at it for `gen_zoom_v2.py`; `xref.py` takes the path as its first argument | `gen_zoom_v2.py`, `xref.py`, Ghidra |
| romfs `Stage`, `BancMapUnit`, `Event` | nstool with `--basenca` (see Gotchas) | `byml.py`, `bymlpatch.py` |

## Build and verify

Python 3.14 (stdlib `compression.zstd`), plus `capstone` and `lz4` for the code tools. Don't use `-I` for scripts that need `capstone` (isolated mode hides per-user packages). Set `PYTHONIOENCODING=utf-8` when printing BYML (Japanese labels).

```
# Layouts: rebuild from the originals, check, compare
python tools/build.py tools <orig_layout_dir> <out_dir>          # <out_dir> outside the repo: romfs/Layout + build_report.json
python tools/verify.py tools <orig_layout_dir> <out_dir>/romfs/Layout   # must report 0 problem(s)
# then replace mod/Native 4x3 Aspect Ratio/romfs/Layout/ with <out_dir>/romfs/Layout/* (delete first: the build
# leaves unchanged archives out, so a stale file would otherwise stay); update layout_count in release-games.json

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
| `bymlpatch.py` | Same-size in-place edit of one BYML value, recompressed |
| `gen_zoom_v2.py` | Camera patch generator (caves A-H, per-area base and delta, boss table); asserts delta <= max(0, (27.5556 - G*4/3)/2) |
| `verify_pchtxt.py [file]` | Disassembles every enabled line of a patch file |

Ghidra headless (Java 21): `analyzeHeadless <proj_dir> <proj_name> -process main-1.2.1.bin -noanalysis -scriptPath tools/ghidra -postScript DecompileAt.java "6c66b8,2e2b30"`.

Flat image layout (1.2.1): `.text` 0x0-0x2138650, `.ro` 0x2139000-0x338BC78, `.data` 0x338C000-0x3728DF8. Code cave: zero bytes 0x2138650-0x2139000 (executable, patchable), used 0x2138780-0x2138F23. Spare .bss words used as mailboxes: 0x037D1F00-0x037D1F3B.

## Current state (2026-10-30)

Shipped patch `exefs/1.2.1.pchtxt`: SHA-256 `51A8B589...FE55`, 266 lines (only comments changed since the tested `EE1EF2D8...F167`). The tester reports the mod working well.

**Layouts (`build.py`, built from the 1.2.1 originals since 2026-10-30):** 115 of the game's 235 archives ship (114 changed top-level layouts incl. the 1.2.1-only `AmiiboReadWindow`, plus `LCursor`); the other 120 are unchanged and fall back to the game's copies. top-level RootPane scale y 0.75 (`ROOT_SY`); HUD/header/footer edge-anchored (+/-180 root-local units, TransY keys shifted too); full-screen layers grown x4/3 (captures and fades height only, artwork uniform); parts layouts untouched; curated per-screen tables `FORCE_SHIFT`, `NO_SHIFT_SUBTREE`, `NO_SHIFT_LAYOUT`, `NO_FILL`. 638 float writes, 46 fill panes, `verify.py` clean. Until 2026-10-30 the mod was built from won-aar's older cache and shipped all 234 archives, so 30 screens (incl. Pause, MainMenu, Title, CourseList, talk windows, button icons) carried pre-1.2.1 layouts; the 1.2.1 rebuild applies identical edits. **Not yet played in game since the 1.2.1 rebuild.**

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
| hook `006C66DC` -> cave A `02138800` | Per-area base G and reach delta: boss table at `02138E00` first, else area width < 60 -> G 15.5 / delta 3.4444, else G 15.75 / delta 3.2778. Writes G `037D1F00`, delta `037D1F18`, width `037D1F1C`, controller/subject `037D1F20`/`28`; then the 16:9 reach rule |
| hook `002E2B30` -> cave B `02138900` | View height: stock `fmov s1,#15.5`, then `fmax` with G |
| `006C6358`, `006C6364` -> caves F1/F2 `02138D00`/`02138D20` | Camera-controller half-extents use G; width scaled by G/15.5 |
| hooks `00833B00`, `005E428C` -> caves D `02138B00`, E `02138C00` | Bowser Jr. pipe display box kept at authored size when G > 15.5 |
| hook `006C6FD0` -> cave G `02138A00` | Autoscrolls (`SetAutoScrollPos`): ride the fixed X exactly while it moves; after 2 s still, ease towards focus within +/- delta (mailboxes `037D1F30`-`38`) |
| hook `006C7BEC` -> cave H `02138F00` | `StopScroll` side locks: X = lock X + clamp(normal X - lock X, +/- delta). Every StopScroll room goes through here, not cave G |

Boss table (all delta 0): Course150_Sub4 607466214 G 21.0; Course151_Sub2 101336182, Course152_Sub4 1778226157, Course153_Sub3 1019598315 G 20.6667 (152's own zoom actor 17.5 multiplies the base). Optional lines commented after `@stop` (zone-lock disable, fixed zoom-outs 17-20) are not needed.

**Confirmed in game:** badge houses and one-screen rooms, pause/menu blur, course-entry iris, HUD and key glyphs vs stock, Select a User card, Poplin shop, kingdom map, Pipe-Rock Plateau Palace arena + pipes, wide-level base 15.75 (Outmaway Valley), airship autoscroll + Wonder Flower (Course101), Puffy Lifts seed (Course021), course-clear photo and View photo, menu pointer, Badge Challenge restart wipe.

**Not yet checked in game:** Course150 arena since its delta became 0; Bowser Jr. rooms 151-153 (extra height; alternate zoom path when subject+0x1BE != 0 bypasses caves B/F1); WipeTo*/WipeWarp; pits, level ends and Wonder zooms at 15.75; last boss and airship boss rooms; multiplayer; Android flashing bars (WipeCourseIn's kept-fill capture reads 180 rows past the frame).

**Open items:**
- Death screen = `WipeMiss` (capture + spotlight) under `MissZanki`. WipeMiss has the capture setup that made WipeCourseIn's circle taller than wide, so its spotlight may be oval. Candidate fix: add `'WipeMiss': ('N_Cap','P_CapUse')` to `CAPTURE_KEEP_FILL` (N_Cap 1080 -> 1440, P_CapUse V 0.125-0.875). An A/B file was tried in Eden only; result unclear. Ship only after the tester confirms the spotlight round.
- Other screen-projected patterns (`CourseIn` P_BG checker, `MissZanki` P_BG dots) may be ~0.75 wide; add them to `PROJECTED_PATTERN` only if seen.
- Play-test the 1.2.1 rebuild (menus, HUD, pause, maps, transitions, course clear, cursor, amiibo screen) on Windows and the Nova before v1.0.0.

## Camera knowledge (1.2.1 addresses)

- Camera controller `FUN_006C5970` (x19 = controller, x20 = camera subject, x21 = camera object). Final clamp block `0x6C663C`-`0x6C6770`; final camera write `0x6C6AB8`-`0x6C6B00` (X override flag `controller+0x29` -> `controller+0x1A0`). Follow function `FUN_006C9AEC`.
- View setup `FUN_002E2990`: half-height = zoom x 15.5 x 0.5, half-width = half-height x aspect (`0x2AEEDB4`); zoom instruction `0x2E2B30`. Zoom = subject +0x204 / +0x1F0 (or +0x1F4 when +0x1BE != 0 and +0x1E0 != 2).
- Visible rectangle with hard-coded width: `FUN_004DCF90` (scales with zoom, so object activation follows the view). Player world position: `subject+0x244` (+12 x player index).
- Area records: table `*(0x37B2128+0x50)`, index signed byte `controller+0x10A`, hash `record+0x90` (= `RootAreaHash` in the room's `.bcett`), bounds `record+0x94` (min x,y,z, max x,y,z).
- Only `SetAutoScrollPos` (0x16C5548) writes subject+0x194/+0x1B4 (cave G path); `StopScroll` sets subject+0xA00/0xA01, which become controller+0x29/0x2A (cave H path).
- `SetChangeCourseZoom` (0x16CA4CC) stores zoomBlockCount/15.5 at subject+0x1F0; the view multiplies it by max(15.5, G).
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
