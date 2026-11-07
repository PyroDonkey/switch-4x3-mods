# Changelog: Super Mario Bros. Wonder 4:3

Newest first. Each release's section becomes its GitHub release notes.

## v1.1.2

For game v1.2.1.

- Keep the autoscroll camera locked during mid-scroll pauses (such as the singing break in Piranha Plants on Parade). In v1.1.1, pauses longer than 2 seconds allowed the camera to ease towards the player mid-scroll and snap back when scrolling resumed. The camera now stays locked during intermediate pauses and only unlocks to follow the player when arriving at the autoscroll's final end stop.

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
