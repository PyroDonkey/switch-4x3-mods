# Break Time course review checklist

Developer QA checklist for **Super Mario Bros. Wonder 1.2.1**. Created 2026-11-04 after the read-only course census; no additional courses have been play-tested by that audit.

**Current: Group 2 Course403 camera and floor cloud framing fix (v1.1.8).** At the maintainer's request, its full-room zoom was built before a baseline play-test. Initial play-test feedback found framing "looks fairly good already", but the rendered background was dark at the bottom due to the background dome's nadir pole at Y = -2.08. The floor cloud (Hash 3184768010431751081) was widened to Scale X = 28.0 and shifted to Translate Y = -0.4, fully covering the void and scalloped edge gaps off-screen with 0 flicker. Visual framing approved in Eden on 2026-11-05. Course403, Course415 and Course417 retain visual framing approval only; their sequence, edge activation, completion/retry checks and current-build Course411 regression remain open. Course411 is their previously confirmed reference, not another pending fix. Grouping means shared investigation and regression coverage, not that every member needs the same patch.

## Scope and baseline

- All **19** Break Time courses are listed below: **15 pending play-test**, **Course403, Course415 and Course417 visually approved; awaiting remaining gameplay checks**, plus Course411 confirmed fixed on the `smbw-course411-framing` PR. This does not assert that the PR has been merged or released.
- Static-review baseline: mod commit `6bfcf0d`, game 1.2.1. A baseline is not a tested-build claim; record the actual mod commit when a human tests each course.
- Census coverage: all 151 `Stage/CourseInfo` records and 451 `Stage/StageParam` records; the 19 `CourseKind = Mini` courses match the Break Time labels and existing world-map entries. Recursive stage references resolve to 24 map-unit files, including two container roots and five linked subareas.
- No other Break Time courses were found outside Course400–418. Course450–453 are `SecretSquare`; Course460 is `Bonus`, not Break Time.
- The 1.2.1 release shipped with no Break Time overrides in `BOSS` (all ran under the narrow-area defaults, base 15.5 / delta 3.4444).
- Confirmed baseline camera bug (PR): Course411 (Break Time! Wonder Token Tunes) cropped the outer note blocks. Fix: G = 20.6667, delta = 0 in `tools/gen_zoom_v2.py`, plus stage adjustments in `tools/build_stage.py`.
- Confirmed baseline camera bug (2026-11-04): Course415 (Break Time! Bouncy Tunes) cropped both side note blocks and outer token arcs. Fix: full-width camera (G = 20.6667, delta = 0) plus stage edits matching Course411's heights; visual framing approved in Eden, gameplay sequence open.
- Confirmed baseline camera bug (2026-11-04): Course417 (Break Time! Trottin' Piranha Plants) cropped outer enemies and note blocks. Fix: full-width camera (G = 20.6667, delta = 0), matching arch/wall heights, and guarded replacement of short A01 side pillars with the existing A00 variant at y = 14.45; visual framing approved in Eden, gameplay sequence open.
- Remaining courses are candidates for review, not confirmed bugs: do not apply fixes to them without a recorded play-test report or specific maintainer direction.

## How to test

1. Launch Wonder 1.2.1 in Eden with **Force 4:3** enabled.
2. Enter the level from the world map or via the `CourseList` menu (CourseList shows internal stage names when debug is on, or match by world number and level title).
3. Check:
   - Are the outer walls, rails, note blocks and goal items visible?
   - Does any interactive element get cut off before the camera reacts?
   - In autoscrolls or fixed rooms, does the player or Wonder Token leave the screen?
   - Are there untextured voids, cut-off backdrop panels, or visible gaps above/below the room?
4. For candidate fixes, also verify completion (Wonder Seed collection, course-clear photo, return to map) and retry (miss/restart does not break the camera).
5. For Group 1 fixes, run the Course411 regression check (PR reference) to confirm shared theater assets still align.

The current narrow-area default shows about **20.67 blocks** horizontally versus 16:9's 27.56 blocks (or ~22.67 blocks when panning reach is fully active). Any room authored with action outside x ≈ 3.7 to 24.3 (relative to a 28-block room) is at risk of cropping.

Replace `Not tested` with the **mod commit, test date, platform and a short result**. Link any issue/PR in that cell. Check a row only for one of the two completed statuses; never complete both members of a group from a test of just one. Keep historical findings in [DEVELOPMENT.md](DEVELOPMENT.md). If a later camera change invalidates a result, reopen that row and retain the previous test reference.

## Group 1 — Shared musical theater framing

**Review order: 415, then 417; use 411 as the regression reference.** These three use the Mokkin theater asset family. Courses415 and417 each have an authored 27.5 × 15.5 camera area and reuse the arch and upper/lower wall family involved in Course411's fix. Course415 uses A00 side pillars; Course417 originally uses A01. After the A01 artwork trial left the bases above the screen bottom, the current Course417 candidate selects A00 for those two pillars.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course415` — Bouncy Tunes | W5 — Fungi Mines | Visual framing approved; gameplay pending | Visual framing approved in Windows/Eden on 2026-11-04 (v1.1.4 candidate over `6bfcf0d`, uncommitted; patch SHA-256 `862f90a7e131`, stage SHA-256 `8bcfee1751a6`). Full moving-token sequence, completion, retry and Course411 regression remain open. |
| [ ] | `Course417` — Trottin' Piranha Plants | W6 — Deep Magma Bog | Visual framing approved; gameplay pending | Visual framing approved in Windows/Eden on 2026-11-04 (v1.1.7 candidate over `6bfcf0d`, uncommitted; patch SHA-256 `0e7b9b513ec2`, stage SHA-256 `aaea4bd8d675`). Full enemy sequence, edge movement/activation, completion, retry and Course411 regression remain open. |
| [x] | `Course411` — Wonder Token Tunes | W1 — Pipe-Rock Plateau | Confirmed fixed (reference) | Confirmed fixed on PR `smbw-course411-framing` (v1.1.2). Reference course for theater framing; re-check on the current development build. |

**Common mechanics:** all three feature moving Wonder Tokens or enemies that traverse the full width of the room. A full-width zoom (G = 20.6667, delta = 0) is established as visually necessary for 415 and 417, with theater asset alignment mirroring Course411's method.

**Implementation references, not prescribed edits:** `Course415_Course` RootAreaHash `3684305666`; `Course417_Course` `2579434623`; `Course411_Course` `1607468536`. All three use G = 20.6667 and delta = 0 in [gen_zoom_v2.py](../tools/gen_zoom_v2.py), with per-course artwork edits in [build_stage.py](../tools/build_stage.py). All target arch y = 18.545 and walls y = 14.05 / 6.05. Course417's arch shifts +1.295; its current candidate selects A00 pillars at the approved y = 14.45 alignment used by Course411/415, instead of stretching A01. Original actor variants and wall heights differ; do not copy displacements blindly.

**Next Group 1 follow-up (Course417, gameplay):** Does the full enemy sequence remain visible across the room, without enemies activating late or disappearing at the edges?

Both courses have separate visual framing approval, not full gameplay confirmation. Completion/retry in Course417, the full moving-token sequence and completion/retry in Course415, and current-build Course411 regression remain follow-up checks. Neither Course415 nor Course417 is complete.

## Group 2 — Wide puzzle arenas (no Mokkin framing)

**Review order: 403, 408, 401, then 400.** These are fixed-room or phase-based candidates, not evidence for a blanket zoom. They do not have Course411's placed Mokkin frame assets.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course403` — Zip-Go-Round | W2 — Fluff-Puff Peaks | Visual framing approved; gameplay pending | Visual framing approved in Windows/Eden on 2026-11-05 (v1.1.8 candidate over `68af3fd`; patch SHA-256 `08ebeeb79a45`, stage SHA-256 `d71bef2fab7e`). Full-room camera (G = 20.6667, delta = 0) and floor cloud expansion (Hash 3184768010431751081: Scale X 28.0, Translate Y -0.4) cover bottom void. Completion and retry remain open. See DEVELOPMENT.md §31-33. |
| [ ] | `Course408` — Floating Wonder Tokens | W4 — Sunbaked Desert | Pending play-test | Not tested |
| [ ] | `Course401` — Kick It, Outmaway | W2 — Fluff-Puff Peaks | Pending play-test | Not tested |
| [ ] | `Course400` — Pop Up, Hoppo! | W1 — Pipe-Rock Plateau | Pending play-test | Not tested |

- **403:** opposing rails at X = 1.5 and 26.5 cannot both fit in the default narrow view. Check moving tokens and the entire rail puzzle together.
- **408:** outer token centers span 21 blocks, slightly more than the default 20.67-block view. Check all-token readability and incoming enemy cues.
- **401:** starting players and incoming blocks occupy opposite sides. Review both the normal camera and the upper signal-camera phase, including the transition.
- **400:** check launch, rebound and exit-state readability together. Main mechanism centers span only 18.5 blocks, so full-width zoom is not established as necessary.

**Course403 candidate:** `Course403_Course` RootAreaHash `177084102`, G = 20.6667 and delta = 0 in [gen_zoom_v2.py](../tools/gen_zoom_v2.py), restoring about 27.56 blocks of width. Its original `CameraArea` is at `[14.0, 0.5, 0.0]`, scale `[27.5, 15.5, 1.0]`. Floor cloud Hash `3184768010431751081` widened in [build_stage.py](../tools/build_stage.py) to cover the unrendered sky void below the red platform. All other 9 clouds remain stock.

**Next testing question (Course403, gameplay):** Do token collection, moving rail sequence, course completion and retry work cleanly with no camera hitching?

## Group 3 — Scripted vertical autoscroll

**Check early, independently of the full-room zoom candidates.**

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course407` — Lights Out | W3 — Shining Falls | Pending play-test | Not tested |

- **407:** authored vertical autoscroll in a 15.5-wide shaft. Check player headroom and downward visibility during scroll, plus lantern readability.

## Group 4 — Linear / standard Break Time rooms

**Test after Groups 1–3.** These are traditional short challenges where narrow-area scrolling is expected to be sufficient unless a specific hazard or token arc is cropped.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course402` — Revver's Roll | W2 — Fluff-Puff Peaks | Pending play-test | Not tested |
| [ ] | `Course404` — Hurry, Hurry | W3 — Shining Falls | Pending play-test | Not tested |
| [ ] | `Course405` — Timer Switches | W3 — Shining Falls | Pending play-test | Not tested |
| [ ] | `Course406` — Water Dash | W3 — Shining Falls | Pending play-test | Not tested |
| [ ] | `Course409` — Break, Break, Break | W4 — Sunbaked Desert | Pending play-test | Not tested |
| [ ] | `Course410` — Treasure Vault | W4 — Sunbaked Desert | Pending play-test | Not released |
| [ ] | `Course412` — Hot, Hot, Hot | W6 — Deep Magma Bog | Pending play-test | Not tested |
| [ ] | `Course413` — Charge! | W5 — Fungi Mines | Pending play-test | Not tested |
| [ ] | `Course414` — Tumble House | W5 — Fungi Mines | Pending play-test | Not tested |
| [ ] | `Course416` — High-Jump Mystery | W5 — Fungi Mines | Pending play-test | Not tested |
| [ ] | `Course418` — Expert Badge 1 | Special World | Pending play-test | Not tested |

## Audit notes (read-only census)

- Level geometry extracted from 1.2.1 `Stage/StageParam/*.bgyml` and `BancMapUnit/*.bcett.byml.zs`.
- Break Time stages contain no Mokkin frame assets outside Courses 411, 415 and 417.
- Static-analysis figures are references for testing, not proof of bug absence. Always verify in Eden.
