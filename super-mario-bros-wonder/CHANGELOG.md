# Changelog: Super Mario Bros. Wonder 4:3

Newest first. Each release's section becomes its GitHub release notes.

## v1.2.0

For game v1.2.1.

### Fixed

- Bowser's Rage Stage (`Course290_Main`, [#9](https://github.com/PyroDonkey/switch-4x3-mods/pull/9)): the opening fists and fossil section are zoomed out so the full width is visible, and level events (Goomba spawns and lightning strikes, the rolling obstacles, the dragon, the vertical shaft floor, the Bowser statue enemies) trigger at the same moment as stock. The shaft climb and the singing Piranha Plant section are framed so everything you need is on screen, and the intro cutscene camera no longer jumps when gameplay starts.
- Pole Block Allure (`Course853_Main`, [#10](https://github.com/PyroDonkey/switch-4x3-mods/pull/10)): the autoscroll camera stays down near the poles so the Wonder Flower is on screen, and at the end of the Wonder the cannon now fires its balloon, so the Wonder Seed can be reached.
- World 1 map (`World001`, [#11](https://github.com/PyroDonkey/switch-4x3-mods/pull/11)): the hidden warp pipe in the underground area (to the lost Toad) and Mario beside it are now on screen.
- W2 Outmaway Valley (`Course022_Main`, [#12](https://github.com/PyroDonkey/switch-4x3-mods/pull/12)): the Wonder Seed lands on the knocked-over goal pole again instead of falling out of the course.

### Changed

- The mod now also ships a cutscene file (`romfs/Event/`) for the Bowser's Rage Stage intro, and the camera patch has a zoom helper for that level's opening.

## v1.1.2

For game v1.2.1.

### Added

- Per-area 4:3 camera overrides (`BOSS` table) for W2 Angry Spikes and Sinkin' Pipes Wonder area (`Course008_Sub2`, [#6](https://github.com/PyroDonkey/switch-4x3-mods/pull/6)) and nine Break Time! courses: Wonder Token Tunes (`Course411_Course`), Bouncy Tunes (`Course415_Course`), Trottin' Piranha Plants (`Course417_Course`, [#4](https://github.com/PyroDonkey/switch-4x3-mods/pull/4)), Zip-Go-Round (`Course403_Course`, [#5](https://github.com/PyroDonkey/switch-4x3-mods/pull/5)), Pop Up, Hoppo! (`Course400_Course`, [#7](https://github.com/PyroDonkey/switch-4x3-mods/pull/7)), Kick It, Outmaway! (`Course401`), Unreachable Treasure? (`Course404_Main`), Watery Wonder Tokens (`Course407`), and Floating Wonder Tokens (`Course408`, [#8](https://github.com/PyroDonkey/switch-4x3-mods/pull/8)).
- Guarded pooled-string (`GYAML_EDITS`) support and synthetic unit test suite (`test_build_stage.py`) in `tools/build_stage.py`, plus `tools/scan_autoscroll_ends.py` and the Break Time! QA review checklist (`docs/BREAK-TIME-REVIEW.md`, [#3](https://github.com/PyroDonkey/switch-4x3-mods/pull/3), [#4](https://github.com/PyroDonkey/switch-4x3-mods/pull/4)).

### Changed

- Autoscroll camera handling (`SetAutoScrollPos`, Cave G + `TABLE_ENDS`): check an autoscroll end-stop table (`0x02138EB4`) so stages with intermediate pauses of 2 seconds or longer stay locked until reaching their final rail stop ([#3](https://github.com/PyroDonkey/switch-4x3-mods/pull/3)).

### Fixed

- Keep the autoscroll camera locked during mid-scroll pauses (such as the singing break in Piranha Plants on Parade, `Course002_Main`) instead of drifting toward the player and snapping back when scrolling resumes ([#3](https://github.com/PyroDonkey/switch-4x3-mods/pull/3)).
- Restore full 16:9 room framing and reposition theater proscenium arches, side pillars, and backdrop panels for the taller 4:3 view in Break Time! Wonder Token Tunes (`Course411_Course`), Bouncy Tunes (`Course415_Course`), and Trottin' Piranha Plants (`Course417_Course`, replacing short `A01` side pillars with `A00` so pillar bases extend past the bottom edge) ([#4](https://github.com/PyroDonkey/switch-4x3-mods/pull/4)).
- Restore full-room framing and widen the floor cloud (`ObjectCloudArea`) in Break Time! Zip-Go-Round (`Course403_Course`) to cover the unrendered sky void below the dash floor without stretching art ([#5](https://github.com/PyroDonkey/switch-4x3-mods/pull/5)).
- Zoom out the Wonder area in W2 Angry Spikes and Sinkin' Pipes (`Course008_Sub2`, `G = 20.6667`, `delta = 0`) so its full 16:9 width is visible in 4:3 ([#6](https://github.com/PyroDonkey/switch-4x3-mods/pull/6)).
- Restore full-room camera framing and raise the `EnemyKoropon` and `PopUpTag` spawn elevation by `+5.0` Y in Break Time! Pop Up, Hoppo! (`Course400_Course`) so the Hoppo spawns off-screen above the 4:3 view instead of popping in mid-air ([#7](https://github.com/PyroDonkey/switch-4x3-mods/pull/7)).
- Fix 4:3 camera framing and off-screen actor/background placement in Break Time! Kick It, Outmaway! (`Course401_Course`, ice-block spawns raised `+9.0` Y), Unreachable Treasure? (`Course404_Main`, full-room zoom), Watery Wonder Tokens (`Course407_Course`, full-room zoom and adjusted `DVWaKaiganFarIwaA01` far rock), and Floating Wonder Tokens (`Course408_Course`, horizontal camera lock at `X = 64.0` with `G = 18.5` and Y-shifted `CreateTag` spawns) ([#8](https://github.com/PyroDonkey/switch-4x3-mods/pull/8)).

## v1.1.1

For game v1.2.1.

- Fix the Wonder Seed being off-screen and out of reach after the Wonder autoscroll stops in Piranha Plants on Parade ([#1](https://github.com/PyroDonkey/switch-4x3-mods/issues/1)). Once any autoscroll has stopped, the camera can now pan across the whole original 16:9 frame instead of stopping short of its right edge. This applies to every autoscroll that stops, not only this level.

## v1.1.0

For game v1.2.1. World 4 Bowser Jr. (`Course152_Sub4`) fixes:

- Fix underwater tint and light rays cutting off in 4:3 (scaled the water mix plane in stage data).
- Fix fight camera drifting up and sticking high during swimming (pinned to stock 3.25 height via cave Y).
- Fix Royal Seed and Prince Florian spawning too high to reach after the boss defeat.
- Fix Bowser Jr. getting trapped spinning in the corner (cave K restores stock camera bounds for swim AI navigation).
- Fix unrendered black void boxes in the bottom corners under the walls (extended wall terrain points to y = -10.0 in stage data).

## v1.0.0

First release, for game v1.2.1.

- The game renders at 4:3, with camera fixes: one-screen rooms keep their full 16:9 framing, autoscrolls move like stock, screen-locked rooms and shafts can pan within the original 16:9 frame, and wide levels show slightly more than stock.
- Bowser Jr. arenas are zoomed out so the whole room is visible.
- The UI re-laid out for 4:3 (115 layout archives, built on the game's own v1.2.1 files): HUD, menus, pause screen, title, maps, transitions, course-clear photo and menu pointer.
- Known issues: the death-screen spotlight may look slightly oval; on some Android devices bars may flash briefly when entering a level from the map. Some boss fights and transitions are not yet played; see Known limits in the README.
