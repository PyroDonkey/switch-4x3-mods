# Agent instructions: The Legend of Zelda: Breath of the Wild 4:3

Read the root [`../AGENTS.md`](../AGENTS.md) first. This file is the **source of truth for the current state** of the BotW mod; [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) is the dated log of how it got here (its values may be superseded). The general method is in [`../docs/aspect-ratio-guide.md`](../docs/aspect-ratio-guide.md); its "Second reference" section describes this mod.

## Game and target

- Title ID `01007EF00011E000`, **version 1.6.0 only**, build ID `8E9978D50BDD20B4C8395A106C27FFDE`. Tested with both DLC packs installed; without DLC is untested.
- Tested on Eden (yuzu family) on Windows with Graphics > Aspect Ratio > **Force 4:3**. Android and console are untested.
- Mod folder: `mod/Native 4x3 Aspect Ratio/` = `exefs/1.6.0.pchtxt` (exact 4/3, copied from `tools/hand-edited/exefs/1.6.0.pchtxt`) + `romfs/Layout/BootUp.sblarc`, `romfs/Layout/Horse.sblarc`, `romfs/Pack/Bootup.pack` (holds `Layout/Common.sblarc`, almost every UI layout), `romfs/Pack/Title.pack` + `README.txt` (no install steps, only the link to `README.md#install`). Named "Nova Aspect Ratio 4x3 Native" in the maintainer's earlier test builds and "Aspect Ratio 4x3 Native" briefly before v1.0.0; don't rename it again.
- Installed for testing at `%APPDATA%\eden\load\01007EF00011E000\<mod folder>`. Sync with the game closed: `robocopy "mod\Native 4x3 Aspect Ratio" "%APPDATA%\eden\load\01007EF00011E000\Native 4x3 Aspect Ratio" /MIR`. Make sure only one 4:3 folder is ticked in Eden's add-ons (older test folders contain the same archives).
- Releases: tag prefix `botw` (`.github/release-games.json`); procedure in the root AGENTS.md "Releasing". `layout_count` there is the number of files under `romfs/` (4).

## Local inputs (outside the repo)

| Input | Where it comes from | Used by |
| --- | --- | --- |
| romfs 1.6.0 (base + update merged) | `<workspace>\dump\01007EF00011E000\romfs`, extracted from the maintainer's own base and v1.6.0 update NSPs. It contains the DLC-era layouts, so it is not the 1.0.0 base alone | `build.py`, `verify.py` |
| `exefs/main` 1.6.0 | `<workspace>\work\exefs\main` (build ID above) | patch research; `mkpatch.py` (capstone) |

## Build and verify

Python 3.14; stdlib only for build and verify (`-I` is fine). `mkpatch.py` needs `capstone` (run without `-I`).

```
# <out_dir>: a new empty folder outside the repo, with Layout\ and Pack\ subfolders (the build does not create them)
python -I tools/build.py "<workspace>/dump/01007EF00011E000/romfs" <out_dir>
# verify check 20 compares the HUD enlargement against a build with it off:
BOTW_HUD_SCALE=1.0 python -I tools/build.py "<workspace>/dump/01007EF00011E000/romfs" <hud1_dir>
BOTW_HUD_BASE=<hud1_dir> python -I tools/verify.py "<workspace>/dump/01007EF00011E000/romfs" <out_dir>   # must print FAILS: 0
# then copy the 4 archives from <out_dir> into mod/Native 4x3 Aspect Ratio/romfs/ (not build_report.json), and
# tools/hand-edited/exefs/1.6.0.pchtxt into its exefs/
python scripts/check_repo.py
python scripts/release.py check botw <version>
```

Environment switches (defaults are the shipped build): `BOTW_ROOT_MODE=children|root`, `BOTW_HUD_SCALE` (1.3333333; 1.0 = off), `BOTW_CURSOR_KEEP` (`Cursor_00`), `BOTW_GANBARI_FIX` (1; 0 = stamina wheel fix off). verify.py reads `build_report.json` from `<out_dir>`, so verify the build folder, not the mod folder.

## Current state (2026-11-13, v1.0.0)

Code patch: `exefs/1.6.0.pchtxt` replaces the three aspect instructions used by the community 1.6.0 patch (`0x00E0AD68`, `0x015C2148`, `0x01271870`) with `LDR S0` of a literal `3FAAAAAB` (4/3) planted in zero padding after a nearby `ret`. Played and checked.

Layouts (children mode: RootPane untouched because the game overwrites its scale; each direct child of RootPane gets ScaleY and TransY x0.75; panes the code rescales by name, `CODE_SCALE_PANES`, take the factor on their children):

| Area | Rule (curated.py) | Status |
| --- | --- | --- |
| Edge shifts, fills, Title art and glow, loading screens, PauseMenuBG bands | rounds 1-3 | played and checked |
| D-pad icon list edge masks | `CAPTURE_APPLY_INVARIANT`, `SRC_H_SCALE` | played and checked |
| Menu cursor corners | `CURSOR_ROOT_KEEP` (Cursor_00 stock) | played and checked |
| System message pill end caps | `FORCE_SHIFT` MessageSp_00, `SHIFT_FOLLOW` | played and checked |
| HUD at 16:9 size | `HUD_SCALE`, `HUD_PANES` | played and checked |
| Adventure Log page | `NO_SCALE_SUBTREES` N_InOutQuest_02 stock; `PART_SQUASH_Y` (PaPauseQuest_00 panel and tabs, PaPageChallenge5_00 row slots) | played and checked (quest list, description, Memories past row 5); long-list scroll, CLEAR stamp, Memories pictures not yet |
| Sheikah map terrain | `SIZEH_RETARGET` AppMap_00 incl. capture sources N_Capture_00-04 (`MAP_CAPTURE_PAIRS`) | played and checked (grid square, names on terrain) |
| Map player locator | `PART_GROW_H` PaMapPlayer_00 N_PosSize_00 590 -> 830 | played and checked |
| Stamina wheel | `PART_SY` (squash inside the part), `HOST_SY_FACTOR` | played and checked (combined build) |
| Speaker name plate | `FORCE_SHIFT` Message_00 N_NameS_00 + N_Capture_00 | played and checked (combined build) |

The combined build (all rows above, the v1.0.0 mod folder) was played and checked on 2026-11-10: stamina wheel, name plate, Adventure Log and map.

Not yet played: shrine/Divine Beast maps (`AppMapDungeon_00` has the same capture-source/use pattern as the world map and may show the same terrain stretch), tool screen, end credits, a missing menu arrow noted in an early round (cause unknown).

verify.py checks: 0 (no unchanged or stray archive in the output), 1-2 (structure, every changed byte logged), 4-10 (rules re-derived from the originals), 11 (capture use sizes), 12 (Cursor_00 byte-identical), 13-17 (rounds 2-5), 18-19 (pause page containers, Adventure Log subtree stock), 20 (HUD enlargement vs `BOTW_HUD_BASE`), 21 (stamina wheel), 22 (Adventure Log squash).

## Gotchas

- **The game overwrites RootPane scale** (and the scale of panes named in `CODE_SCALE_PANES`), so a root-scale mod is lost at run time. That is why children mode exists.
- **Code reads some pane sizes and scales by name.** The Adventure Log list breaks if its containers (`N_InOutQuest_02`, `Pa_Quest_00`, `N_Cut_00`) are scaled; the map locator clamps to `N_PosSize_00`'s size; the stamina wheel hosts get their ScaleX/ScaleY overwritten by code. Squash below such panes, or grow the box, instead of scaling them.
- **Map captures: keep each source the same size as its use.** Stock keeps them equal in every pose (720 full map, 192 mini-map). With only the uses at 960 the terrain was 1.33x too tall and drifted against names and icons; matching the sources fixed it in game. The guide's capture model (a plain source copies its local size) does not by itself explain this pair; the equal-size rule is what was tested.
- **Bootup.pack is the whole pack** (fonts and other data with it); LayeredFS replaces whole files, which the game-files policy allows for changed archives. Never ship an archive the build did not change (verify check 0).
- **Eden locks layout files while a game runs**, and code patches load only at boot: close the game before syncing. Eden tracks add-ons by folder name, so after a rename tick the new folder and untick old ones.
- The optional map-view exefs patch (`map_view_960`, 720 -> 960 view height at `0x1AFE4`) from round 3 was never enabled or needed; it is not shipped.
