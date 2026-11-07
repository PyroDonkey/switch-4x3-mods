# Changelog: Super Mario Bros. Wonder 4:3

Newest first. Each release's section becomes its GitHub release notes.

## v1.1.8

For game v1.2.1. Development build; not released. Visual framing approved on Windows on 2026-11-05; full gameplay checks remain open.

- Restore full 16:9 room width at 4:3 in Break Time! — Zip-Go-Round (`Course403_Course`) using per-area camera zoom G = 20.6667, delta = 0.
- Widen the floor cloud (`ObjectCloudArea` Hash 3184768010431751081: Scale X 6.0 -> 28.0, Translate Y 0.0 -> -0.4) so its decorative puff lobes cover the unrendered black sky void below the red dash floor and seal the bottom corners and scalloped edge gaps off-screen, while keeping the top flush against the platform. All 9 base clouds remain stock; 0 flicker and 0 art stretch. User-approved in Eden; token collection, completion and retry checks remain open.

## v1.1.7

For game v1.2.1. Development build; not released. Visual framing approved on Windows on 2026-11-04; full gameplay checks remain open.

- Replace the two visibly short A01 side pillars in Break Time! — Trottin' Piranha Plants with the existing A00 variant used in Wonder Token Tunes and Bouncy Tunes, at its proven alignment. The maintainer approved the bottom coverage and flush upper joints without stretching artwork. The full enemy sequence, edge movement/activation, completion, retry and current Wonder Token Tunes regression are not yet confirmed.

## v1.1.6

For game v1.2.1. Artwork development trial; not released. A preview showed the A01 pillar bases ending above the screen bottom; superseded by v1.1.7.

- Fit Break Time! — Trottin' Piranha Plants (`Course417_Course`) to the original room width and reposition its arch, A01 side pillars and backdrop panels for the taller 4:3 view without stretching artwork. Final coverage, enemy movement/activation, completion and retry still need checks.

## v1.1.5

For game v1.2.1. Camera-only development trial; not released.

- Full-room camera candidate for Break Time! — Trottin' Piranha Plants (`Course417_Course`). Repositioned artwork is required: the original arch and upper wall overlap the upper screen, and a gap is exposed at the bottom.

## v1.1.4

For game v1.2.1. Development build; not released. Visual framing approved on Windows on 2026-11-04; full gameplay checks remain open.

- Fit Break Time! — Bouncy Tunes (`Course415_Course`) to the original room width, matching the full-arena framing of Wonder Token Tunes without stretching art. Arch y 18.545, side pillars y 14.45, upper wall y 14.05, lower wall y 6.05. Visual framing confirmed by the maintainer in Eden; moving-token sequence, completion, retry and current Wonder Token Tunes regression are not yet confirmed.

## v1.1.3

For game v1.2.1. Camera-only development trial; not released. Superseded by v1.1.4.

- Trial full-room camera for Break Time! — Bouncy Tunes (`Course415_Course`). Exposed the expected top gap and ceiling valance overlap; resolved with artwork translation in v1.1.4.

## v1.1.2

For game v1.2.1. Internal test build; not released.

- Keep the autoscroll camera locked during mid-scroll pauses (such as the singing break in Piranha Plants on Parade). In v1.1.1, pauses longer than 2 seconds allowed the camera to ease towards the player mid-scroll and snap back when scrolling resumed. The camera now stays locked during intermediate pauses and only unlocks to follow the player when arriving at the autoscroll's final end stop.
- Fix Break Time! — Wonder Token Tunes (`Course411_Course`): zoomed out to fit the full 16:9 room width in 4:3 so all wonder tokens and note blocks are visible at once as originally intended.
- Stage framing adjustments in Wonder Token Tunes: shifted the proscenium arch and side pillars together to crown the top of the 4:3 screen with flush corner joints, and adjusted the backdrop panels to extend the natural wood slats across the bottom of the screen, eliminating the out-of-bounds void without stretching artwork.

## v1.1.1

For game v1.2.1. Camera-only development trial; not released.

- Full-room camera for Break Time! — Wonder Token Tunes (`Course411_Course`). Left an artwork gap at the top and exposed a void below the lower wall; resolved with artwork translation in v1.1.2.

## v1.1.0

For game v1.2.1.

- Rebuild all 115 UI archives from original 1.2.1 layouts, restoring 1.2.1 menus, HUD, pause, maps, cursor and amiibo screen.
- Extend W4 Bowser Jr. corridor and arena terrain walls (Unit 1 Walls 0, 1 and 2) down to y = -10.0, eliminating the bottom-left and bottom-right corner void boxes.
- Bowser Jr. swim AI navigation bounds clamped to stock Y range in `GetCameraBoundBox2f` so he stays above the floor.

## v1.0.0

Initial native 4:3 release for Super Mario Bros. Wonder 1.2.1.
