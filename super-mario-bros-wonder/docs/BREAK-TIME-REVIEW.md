# Break Time! 4:3 framing review

Developer QA checklist for **Super Mario Bros. Wonder 1.2.1**. Created 2026-11-04 after the read-only course census; updated 2026-11-07 to reflect musical theater framing fixes (PR #4), Zip-Go-Round camera and floor cloud framing (PR #5), Course400/Course401 spawn fixes, and the Course401/404/407/408 play-test approvals.

**Current status:**
- **Group 1 (Musical theater framing, [PR #4](https://github.com/PyroDonkey/switch-4x3-mods/pull/4)):** Course411 confirmed fixed (reference). Course415 and Course417 visual framing approved in Eden on 2026-11-04; gameplay sequence, completion/retry, and regression checks remain open.
- **Group 2 (Wide puzzle arenas, [PR #5](https://github.com/PyroDonkey/switch-4x3-mods/pull/5)):** Course403 visual framing approved in Eden on 2026-11-05 (full-room camera zoom $G = 20.6667$, $\text{delta} = 0$ plus widened floor cloud to cover the background dome void without flicker); token collection, moving rail sequence, completion, and retry checks remain open. Course400 visual framing approved in Eden on 2026-11-06; Hoppo spawn raised off-screen ($Y = 12.0 \to 17.0$, `PopUpTag` $16.5 \to 21.5$) to eliminate visible mid-air pop-in. Course401 ice-block spawns are raised off-screen ($Y = 18.0 \to 27.0$ and $19.0 \to 28.0$) and approved in Eden on 2026-11-07. Course408 keeps the stock CameraArea height and Y centre, locks X at 64.0, and moves only `CreateTag` Y positions (top-right $+6.0$, bottom pair $-1.5$); all four Balloon Killers spawn with no visible pop-in, approved in Eden on 2026-11-07.
- **Group 4 (Linked foreground/background scenes, 2026-11-07):** Course404's full-room camera is approved in Eden on 2026-11-07. Course409 is reverted to stock and remains on the TODO list for a later play-test.
- **Remaining 13 courses:** Course400, Course403, Course415 and Course417 still have gameplay checks open; Course409 is stock and remains on the TODO list; 8 others remain pending play-test. Course414 was checked; no change needed.

## Scope and baseline

- All **19** Break Time courses are listed below: **13 not complete**, including Course400 (visual framing approved; Hoppo spawn fix awaiting retry), Course403/Course415/Course417 (visually approved; remaining gameplay checks), Course409 (stock; TODO), and 8 pending play-tests; **Course401, Course404, Course407 and Course408 are approved in Eden on 2026-11-07**, and **Course411 is confirmed fixed** on PR #4 (`smbw-course411-framing`).
- Static-review baseline: mod commit `6bfcf0d`, game 1.2.1. A baseline is not a tested-build claim; record the actual mod commit when a human tests each course.
- Census coverage: all 151 `Stage/CourseInfo` records and 451 `Stage/StageParam` records; the 19 `CourseKind = Mini` courses match the Break Time labels and existing world-map entries. Recursive stage references resolve to 24 map-unit files, including two container roots and five linked subareas.
- No other Break Time courses exist outside Course400–418. Course450–453 are `SecretSquare`; Course460 is `Bonus`, not Break Time.
- IDs, world membership, geometry, and area links come directly from local 1.2.1 originals (`Stage/WorldMapInfo/World*.bgyml` and `Stage/StageParam/*.bgyml`). English titles match official release titles. Every title in the tables carries the prefix **Break Time!**.
- The 1.2.1 release shipped with no Break Time overrides in `BOSS` (all ran under the narrow-area defaults, base 15.5 / delta 3.4444).
- The default narrow-area view shows about **20.67 blocks** horizontally versus the stock **27.56 blocks** (or ~22.67 blocks when panning reach is fully active). Any room authored with action outside $X \approx 3.7$ to $24.3$ (relative to a 28-block room) is at risk of cropping.

## Updating this checklist

| Status | Meaning | Done? |
| --- | --- | --- |
| Pending play-test | Static inspection only; no course-specific human result recorded | No |
| Problem reproduced | A human observed a concrete visibility, camera, or artwork problem | No |
| Built; awaiting play-test | A candidate fix passed the applicable build/verifier checks but is not human-confirmed | No |
| Visual framing approved; gameplay pending | A human approved the artwork/framing, but sequence/activation, completion, retry, or regression checks remain open | No |
| Confirmed fixed | A human checked all affected behavior and gameplay with the fix | Yes |
| Checked; no change needed | A human checked the concern and the existing behavior is acceptable | Yes |

Replace `Not tested` with the **mod commit, test date, platform, and a short result**. Link any issue/PR in that cell. Check a row only for one of the two completed statuses; never complete both members of a group from a test of just one. Keep historical findings in [DEVELOPMENT.md](DEVELOPMENT.md).

## How to test

1. Launch Wonder 1.2.1 in Eden with **Force 4:3** enabled.
2. Enter the level from the world map or via the `CourseList` menu (CourseList shows internal stage names when debug is on, or match by world number and level title).
3. Check:
   - Are the outer walls, rails, note blocks, and goal items visible?
   - Does any interactive element get cut off before the camera reacts?
   - In autoscrolls or fixed rooms, does the player or Wonder Token leave the screen?
   - Are there untextured voids, cut-off backdrop panels, or visible gaps above/below the room?
4. For candidate fixes, also verify completion (Wonder Seed collection, course-clear photo, return to map) and retry (miss/restart does not break the camera).
5. For Group 1 fixes, run the Course411 regression check (PR reference) to confirm shared theater assets still align.

---

## Group 1 — Shared musical theater framing ([PR #4](https://github.com/PyroDonkey/switch-4x3-mods/pull/4))

**Review order: 415, then 417; use 411 as the regression reference.** These three use the Mokkin theater asset family. Courses 415 and 417 each have an authored $27.5 \times 15.5$ camera area and reuse the arch and upper/lower wall family involved in Course411's fix. Course415 uses A00 side pillars; Course417 originally uses short A01 pillars, replaced with A00 in `build_stage.py` to prevent exposed bases below the taller screen.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course415` — Bouncy Tunes | W4 — Sunbaked Desert | Visual framing approved; gameplay pending | 2026-11-04, Windows/Eden: maintainer approved v1.1.4 artwork framing over `6bfcf0d` ([PR #4](https://github.com/PyroDonkey/switch-4x3-mods/pull/4), commit `68af3fd`; tested patch SHA-256 `862f90a7e131`, stage `8bcfee1751a6`). Full moving-token sequence, completion, retry, and Course411 regression remain open. See DEVELOPMENT.md §§25–27. |
| [ ] | `Course417` — Trottin' Piranha Plants | W5 — Fungi Mines | Visual framing approved; gameplay pending | 2026-11-04, Windows/Eden: maintainer approved v1.1.7 visual framing ("Looks good") with A00 replacement side pillars at $Y = 14.45$ ([PR #4](https://github.com/PyroDonkey/switch-4x3-mods/pull/4), commit `68af3fd`; tested patch SHA-256 `0e7b9b513ec2`, stage `aaea4bd8d675`). Full enemy sequence, edge movement/activation, completion, retry, and Course411 regression remain open. See DEVELOPMENT.md §§27–30. |
| [x] | `Course411` — Wonder Token Tunes | W1 — Pipe-Rock Plateau | Confirmed fixed (reference) | User-confirmed 2026-11-03 in Eden on [PR #4](https://github.com/PyroDonkey/switch-4x3-mods/pull/4) (commit `6bfcf0d`, v1.1.2). Reference course for theater framing; see DEVELOPMENT.md §23. |

**Common mechanics:** all three feature moving Wonder Tokens or enemies that traverse the full width of the room. A full-width zoom ($G = 20.6667$, $\text{delta} = 0$) is visually necessary, with theater asset alignment mirroring Course411's method.
- **Implementation references:** `Course415_Course` RootAreaHash `3684305666`; `Course417_Course` `2579434623`; `Course411_Course` `1607468536`. All target arch $Y = 18.545$ and walls $Y = 14.05 / 6.05$. Course417 selects A00 pillars at $Y = 14.45$.
- **Next Group 1 follow-up (Course417, gameplay):** Does the full enemy sequence remain visible across the room, without enemies activating late or disappearing at the edges?

---

## Group 2 — Full-room puzzle and threat visibility ([PR #5](https://github.com/PyroDonkey/switch-4x3-mods/pull/5))

**Review order: 403, 408, 401, then 400.** These are fixed-room or phase-based candidates, not evidence for a blanket zoom. They do not have Course411's placed Mokkin frame assets.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course403` — Zip-Go-Round | W2 — Fluff-Puff Peaks | Visual framing approved; gameplay pending | 2026-11-05, Windows/Eden: maintainer approved v1.1.8 Candidate C28 framing ("Yes that's good") on [PR #5](https://github.com/PyroDonkey/switch-4x3-mods/pull/5) (commit `0192150`; patch SHA-256 `08ebeeb79a45`, stage SHA-256 `d71bef2fab7e`). Full-room camera ($G = 20.6667$, $\text{delta} = 0$) and floor cloud expansion (Hash `3184768010431751081`: Scale X 28.0, Translate Y -0.4) cover bottom void and seal corner/edge gaps with 0 flicker and 0 art stretch. Token collection, moving rail sequence, completion, and retry remain open. See DEVELOPMENT.md §§31–33. |
| [x] | `Course408` — Floating Wonder Tokens | W4 — Sunbaked Desert | Approved in Eden | 2026-11-07, Windows/Eden: maintainer approved the final build. `CameraArea` Hash `892663682` keeps Translate Y = 0.5 and Scale Y = 15.5, locking X at 64.0 with Scale X = 24.6667. All four `EnemyBalloonKiller` actors and tag `2621681372` are stock; only `CreateTag` Y moves: `2021327989` 13.5 -> 19.5 (+6.0), `1522517719` and `1001471908` -1.5 -> -3.0 (-1.5). All four spawn with no visible pop-in and unchanged paths. Completion/retry not separately reported. See DEVELOPMENT.md §§42–43. |
| [x] | `Course401` — Kick It, Outmaway | W2 — Fluff-Puff Peaks | Approved in Eden | 2026-11-07, Windows/Eden: maintainer approved the play-test. BOSS table entry at G = 20.6667, delta = 0.0; 14 ice-block actors raised +9.0 in Y keep their spawns above the 4:3 view. Completion/retry not separately reported. See DEVELOPMENT.md §43. |
| [ ] | `Course400` — Pop Up, Hoppo! | W1 — Pipe-Rock Plateau | Visual framing approved; gameplay pending | 2026-11-06, Windows/Eden: maintainer approved full-room camera framing ("Okay, looks good"). In 4:3 with $G = 20.6667$, stock Hoppo spawn at $Y = 12.0$ was exposed on-screen. Added stage edit in `build_stage.py` shifting `EnemyKoropon` $Y = 12.0 \to 17.0$ and `PopUpTag` $16.5 \to 21.5$ (patch SHA-256 `ca091bb6d71f`, stage SHA-256 `c51dc7836e74`). Off-screen spawn drop, rebound sequence, completion, and retry remain open. See DEVELOPMENT.md §§35–36. |

- **403:** opposing rails at $X = 1.5$ and $26.5$ cannot both fit in the default narrow view. Full-room camera ($G = 20.6667$, $\text{delta} = 0$) approved. Unrendered floor void covered by widened floor cloud; all other 9 clouds remain stock.
- **408:** the locked camera centres the 24.6667-block-wide room at X = 64.0 while keeping the stock Y centre and height. Approved after play-test in Eden. Observed in Eden, cause unknown: changing a `CreateTag` X stopped the Balloon Killers spawning; Y-only moves kept them spawning. Stock Course408 tags have `onAppearSensor` false.
- **401:** starting players and incoming blocks occupy opposite sides. Review both the normal camera and the upper signal-camera phase, including the transition.
- **400:** check launch, rebound, and exit-state readability together. Main mechanism centers span only 18.5 blocks, so full-width zoom is not established as necessary.

---

## Group 3 — Scripted vertical autoscroll

**Check early, independently of the full-room zoom candidates.**

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [x] | `Course407` — Watery Wonder Tokens | W3 — Shining Falls | Approved in Eden | 2026-11-07, Windows/Eden: maintainer approved the play-test. BOSS table entry for RootAreaHash `2395215932` at G = 20.6667, delta = 0.0; `DVWaKaiganFarIwaA02` stock, carved `DVWaKaiganFarIwaA01` Y 48.0 -> 49.5 and Scale 0.7 -> 0.82. Completion/retry not separately reported. See DEVELOPMENT.md §43. |

- Check lateral token visibility/reach during descent, the end of the autoscroll, and the reward observation camera.
- The autoscroll rail moves vertically with constant X. Cave G's X-still behavior deserves checking during the descent; this is not a reproduced bug or a reason to apply Course411's fixed-room solution.

---

## Group 4 — Linked foreground/background scenes

Review foreground readability and background alignment as one scene. The root `Course` files are containers, not separate playable rooms.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [x] | `Course404` — Unreachable Treasure? | W3 — Shining Falls | Approved in Eden | 2026-11-07, Windows/Eden: maintainer approved the play-test. `Course404_Main` BOSS table entry at G = 20.6667, delta = 0.0; no stage edits. Completion/retry not separately reported. See DEVELOPMENT.md §43. |
| [ ] | `Course409` — Raise the Stage | W4 — Sunbaked Desert | Stock; TODO | Reverted to stock; leave on the TODO list for a later play-test and investigation. |

- **404:** inspect `Course404_Main` with background `Course404_Sub1`: clue/action visibility, alignment during panning, and reward access.
- **409:** inspect `Course409_Main` with background performer units `Course409_Sub1` and `Course409_Sub2`: rhythm cues and stage composition. These use different wall artwork from Course411. Sub2's loading/activation is established, but its precise background-locator relationship remains unresolved.
- Do not independently add camera overrides to background-unit hashes merely because those units have camera actors.

---

## Group 5 — Vertical traversal and platform visibility

These courses already span more than one screen vertically. Review the next action and lateral context, rather than trying to display the whole course at once.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course405` — Timer-Switch Climb | W3 — Shining Falls | Pending play-test | Not tested |
| [ ] | `Course402` — Cloud Cover | W2 — Fluff-Puff Peaks | Pending play-test | Not tested |
| [ ] | `Course412` — Lights Out | W4 — Sunbaked Desert | Pending play-test | Not tested |
| [ ] | `Course416` — Hot-Hot Rocks | W6 — Deep Magma Bog | Pending play-test | Not tested |

- **405:** check the next timed switch/platform during the climb and lateral changes of direction.
- **402:** check cloud/pole visibility, lateral travel to the starting block, vertical following, and reward framing. Note: uses 56 `ObjectCloudArea` actors as climbable poles/clouds, unlike Course403's decorative border vignette.
- **412:** check silhouette geometry, lateral context, and access to the block/reward under the timer.
- **416:** check vertically distributed hot-stone platforms, the observation camera's return, and backdrop edges.

---

## Group 6 — Rotating-room visibility

A separate camera case; do not treat it as another static one-screen theater.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [x] | Course414 — Tumble House | W5 — Fungi Mines | Checked; no change needed | 2026-11-06, Windows/Eden: maintainer confirmed room does not fit within 1 screen; normal camera tracking is acceptable. |

- Check token visibility, camera following, backdrop coverage, and pipe positions in every orientation and during rotations.
- The room rotates in 90-degree steps and already exceeds one stock screen vertically. Some token positions reach beyond the default horizontal half-width; actual visibility still needs play-testing.

---

## Group 7 — Horizontal traversal, lookahead and limits

These are scrolling courses. Check anticipation and camera transitions, not simultaneous visibility of their entire lengths.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course418` — Hurry, Hurry | W1 — Pipe-Rock Plateau | Pending play-test | Not tested |
| [ ] | `Course410` — Revver Run | W4 — Sunbaked Desert | Pending play-test | Not tested |
| [ ] | `Course406` — Timer-Switch Dash | W3 — Shining Falls | Pending play-test | Not tested |
| [ ] | `Course413` — Treasure Vault | W4 — Sunbaked Desert | Pending play-test | Not tested |

- **418:** check forward sight distance across timed blocks and the final reward approach.
- **410:** check fast-target pursuit, obstacle anticipation, and the return route.
- **406:** check timed-platform transitions, running lookahead, restart framing, and the final reward.
- **413:** check its conditional horizontal scroll limit, treasure approach, and return route.

---

## Audit notes (read-only census)

- Level geometry extracted from 1.2.1 `Stage/StageParam/*.bgyml` and `BancMapUnit/*.bcett.byml.zs`.
- Break Time stages contain no Mokkin frame assets outside Courses 411, 415, and 417.
- `Course403` is the sole Break Time stage (and sole single-screen arena in the game) using decorative `ObjectCloudArea` border framing.
- Static-analysis figures are references for testing, not proof of bug absence. Always verify in Eden.
