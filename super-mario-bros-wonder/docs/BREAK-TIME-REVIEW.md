# Break Time! 4:3 framing review

Developer QA checklist for **Super Mario Bros. Wonder 1.2.1**. Created 2026-11-04 after the read-only course census; no additional courses have been play-tested by that audit.

**Current: finish Group 1 gameplay checks after Course415/417 visual framing approval.** Next check Course417's full enemy sequence and edge movement/activation, then completion/retry. Course415's full moving-token sequence and completion/retry also remain open. Course411 is their previously confirmed reference, not another pending fix; current-build regression is not yet reported. Grouping means shared investigation and regression coverage, not that every member needs the same patch.

## Scope and baseline

- All **19** Break Time courses are listed below: **16 pending play-test**, **Course415 and Course417 visually approved; awaiting remaining gameplay checks**, plus Course411 confirmed fixed on the `smbw-course411-framing` PR. This does not assert that the PR has been merged or released.
- Static-review baseline: mod commit `6bfcf0d`, game 1.2.1. A baseline is not a tested-build claim; record the actual mod commit when a human tests each course.
- Census coverage: all 151 `Stage/CourseInfo` records and 451 `Stage/StageParam` records; the 19 `CourseKind = Mini` courses match the Break Time labels and existing world-map entries. Recursive stage references resolve to 24 map-unit files, including two container roots and five linked subareas.
- No other Break Time courses were found outside Course400–418. Course450–453 are `SecretSquare`; Course460 is `Bonus`, not Break Time.
- IDs, world membership, geometry and area links come from the local 1.2.1 originals. English titles were matched against [public course references](https://www.mariowiki.com/Break_Time!), not a local 1.2.1 English message archive. Every title in the tables has the prefix **Break Time!**.

The current narrow-area default shows about **20.67 blocks** horizontally versus the stock **27.56**. Panning can restore access to the edges without showing a whole puzzle at once. Conversely, scrolling courses do not need their entire length on screen. Static concerns below are **review hypotheses, not confirmed defects**.

## Updating this checklist

| Status | Meaning | Done? |
| --- | --- | --- |
| Pending play-test | Static inspection only; no course-specific human result recorded | No |
| Problem reproduced | A human observed a concrete visibility, camera or artwork problem | No |
| Built; awaiting play-test | A candidate fix passed the applicable build/verifier checks but is not human-confirmed | No |
| Visual framing approved; gameplay pending | A human approved the artwork, but sequence/activation, completion, retry or regression checks remain open | No |
| Confirmed fixed | A human checked the affected behavior with the fix | Yes |
| Checked; no change needed | A human checked the concern and the existing behavior is acceptable | Yes |

Replace `Not tested` with the **mod commit, test date, platform and a short result**. Link any issue/PR in that cell. Check a row only for one of the two completed statuses; never complete both members of a group from a test of just one. Keep historical findings in [DEVELOPMENT.md](DEVELOPMENT.md). If a later camera change invalidates a result, reopen that row and retain the previous test reference.

## Group 1 — Shared musical theater framing: start here

**Review order: 415, then 417; use 411 as the regression reference.** These three use the Mokkin theater asset family. Courses415 and417 each have an authored 27.5 × 15.5 camera area and reuse the arch and upper/lower wall family involved in Course411's fix. Course415 uses A00 side pillars; Course417 originally uses A01. After the A01 artwork trial left the bases above the screen bottom, the current Course417 candidate selects A00 for those two pillars.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course415` — Bouncy Tunes | W4 — Sunbaked Desert | Visual framing approved; gameplay pending | 2026-11-04, Windows/Eden: maintainer approved v1.1.4 artwork framing over `6bfcf0d` (uncommitted; tested patch SHA-256 prefix `862f90a7e131`, stage `8bcfee1751a6`). Full moving-token sequence, completion, retry and Course411 regression not reported; row remains open. Earlier camera-only gaps and the fix are recorded in DEVELOPMENT.md §§25–27. |
| [ ] | `Course417` — Trottin' Piranha Plants | W5 — Fungi Mines | Visual framing approved; gameplay pending | 2026-11-04, Windows/Eden: maintainer approved v1.1.7 visual framing ("Looks good") after the pillar bottom-coverage/flush-upper-joints question. Tested over `6bfcf0d` (uncommitted; unchanged patch SHA-256 prefix `0e7b9b513ec2`, stage `aaea4bd8d675`). Full enemy sequence, edge movement/activation, completion, retry and current Course411 regression not reported; row remains open. Earlier A01 bases and the A00 fix are recorded in DEVELOPMENT.md §§27–30. |
| [x] | `Course411` — Wonder Token Tunes | W1 — Pipe-Rock Plateau | Confirmed fixed | User-confirmed 2026-11-03 in Eden on the Course411 PR; exact tested commit not recorded. Fix commit: `6bfcf0d`; see DEVELOPMENT.md §23. |

**Review together:**

- **415:** check whether the active Wonder Tokens and relevant Marimba Blocks remain visible together. Its 52 xylophone actors span X = 1.5–26.5; token movement is rail-controlled, so initial placements alone do not establish their live bounds.
- **417:** check the musical sequence and five enemies across the room, including movement at the edges. Check whether narrower framing affects enemy activation or disappearance; that behavior is not yet verified.
- **If a zoom is needed:** inspect top arch/pillar joints, upper/lower wall overlap, bottom coverage and artwork proportions in each course separately. More vertical view can reveal void or backdrop gaps even after width is correct.
- **Regression:** retain Course411's full-width puzzle visibility and clean framing. Complete each candidate course and check retry behavior before closing its row.

**Implementation references, not prescribed edits:** `Course415_Course` RootAreaHash `3684305666`; `Course417_Course` `2579434623`; `Course411_Course` `1607468536`. All three use G = 20.6667 and delta = 0 in [gen_zoom_v2.py](../tools/gen_zoom_v2.py), with per-course artwork edits in [build_stage.py](../tools/build_stage.py). All target arch y = 18.545 and walls y = 14.05 / 6.05. Course417's arch shifts +1.295; its current candidate selects A00 pillars at the approved y = 14.45 alignment used by Course411/415, instead of stretching A01. Original actor variants and wall heights differ; do not copy displacements blindly.

**Next testing question (Course417, gameplay):** Does the full enemy sequence remain visible across the room, without enemies activating late or disappearing at the edges?

Both courses have separate visual framing approval, not full gameplay confirmation. Completion/retry in Course417, the full moving-token sequence and completion/retry in Course415, and current-build Course411 regression remain follow-up checks. Neither Course415 nor Course417 is complete.

## Group 2 — Full-room puzzle and threat visibility

**Review order: 403, 408, 401, then 400.** These are fixed-room or phase-based candidates, not evidence for a blanket zoom. They do not have Course411's placed Mokkin frame assets.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course403` — Zip-Go-Round | W2 — Fluff-Puff Peaks | Pending play-test | Not tested |
| [ ] | `Course408` — Floating Wonder Tokens | W4 — Sunbaked Desert | Pending play-test | Not tested |
| [ ] | `Course401` — Kick It, Outmaway | W2 — Fluff-Puff Peaks | Pending play-test | Not tested |
| [ ] | `Course400` — Pop Up, Hoppo! | W1 — Pipe-Rock Plateau | Pending play-test | Not tested |

- **403:** opposing rails at X = 1.5 and 26.5 cannot both fit in the default narrow view. Check moving tokens and the entire rail puzzle together.
- **408:** outer token centers span 21 blocks, slightly more than the default 20.67-block view. Check all-token readability and incoming enemy cues.
- **401:** starting players and incoming blocks occupy opposite sides. Review both the normal camera and the upper signal-camera phase, including the transition.
- **400:** check launch, rebound and exit-state readability together. Main mechanism centers span only 18.5 blocks, so full-width zoom is not established as necessary.

## Group 3 — Scripted vertical autoscroll

**Check early, independently of the full-room zoom candidates.**

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course407` — Watery Wonder Tokens | W3 — Shining Falls | Pending play-test | Not tested |

- Check lateral token visibility/reach during descent, the end of the autoscroll and the reward observation camera.
- The autoscroll rail moves vertically with constant X. Cave G's X-still behavior deserves checking during the descent; this is not a reproduced bug or a reason to apply Course411's fixed-room solution.

## Group 4 — Linked foreground/background scenes

Review foreground readability and background alignment as one scene. The root `Course` files are containers, not separate playable rooms.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course404` — Unreachable Treasure? | W3 — Shining Falls | Pending play-test | Not tested |
| [ ] | `Course409` — Raise the Stage | W4 — Sunbaked Desert | Pending play-test | Not tested |

- **404:** inspect `Course404_Main` with background `Course404_Sub1`: clue/action visibility, alignment during panning and reward access.
- **409:** inspect `Course409_Main` with background performer units `Course409_Sub1` and `Course409_Sub2`: rhythm cues and stage composition. These use different wall artwork from Course411. Sub2's loading/activation is established, but its precise background-locator relationship remains unresolved.
- Do not independently add camera overrides to background-unit hashes merely because those units have camera actors.

## Group 5 — Vertical traversal and platform visibility

These courses already span more than one screen vertically. Review the next action and lateral context, rather than trying to display the whole course at once.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course405` — Timer-Switch Climb | W3 — Shining Falls | Pending play-test | Not tested |
| [ ] | `Course402` — Cloud Cover | W2 — Fluff-Puff Peaks | Pending play-test | Not tested |
| [ ] | `Course412` — Lights Out | W4 — Sunbaked Desert | Pending play-test | Not tested |
| [ ] | `Course416` — Hot-Hot Rocks | W6 — Deep Magma Bog | Pending play-test | Not tested |

- **405:** check the next timed switch/platform during the climb and lateral changes of direction.
- **402:** check cloud/pole visibility, lateral travel to the starting block, vertical following and reward framing.
- **412:** check silhouette geometry, lateral context and access to the block/reward under the timer.
- **416:** check vertically distributed hot-stone platforms, the observation camera's return and backdrop edges. Its bubble movement limits are not evidence of a camera lock.

## Group 6 — Rotating-room visibility

A separate camera case; do not treat it as another static one-screen theater.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course414` — Tumble House | W5 — Fungi Mines | Pending play-test | Not tested |

- Check token visibility, camera following, backdrop coverage and pipe positions in every orientation and during rotations.
- The room rotates in 90-degree steps and already exceeds one stock screen vertically. Some token positions reach beyond the default horizontal half-width; actual visibility still needs play-testing.

## Group 7 — Horizontal traversal, lookahead and limits

These are scrolling courses. Check anticipation and camera transitions, not simultaneous visibility of their entire lengths.

| Done | Course / level | World | Status | Tested commit / result |
| --- | --- | --- | --- | --- |
| [ ] | `Course418` — Hurry, Hurry | W1 — Pipe-Rock Plateau | Pending play-test | Not tested |
| [ ] | `Course410` — Revver Run | W4 — Sunbaked Desert | Pending play-test | Not tested |
| [ ] | `Course406` — Timer-Switch Dash | W3 — Shining Falls | Pending play-test | Not tested |
| [ ] | `Course413` — Treasure Vault | W4 — Sunbaked Desert | Pending play-test | Not tested |

- **418:** check forward sight distance across timed blocks and the final reward approach.
- **410:** check fast-target pursuit, obstacle anticipation and the return route.
- **406:** check timed-platform transitions, running lookahead, restart framing and the final reward.
- **413:** check its conditional horizontal scroll limit, treasure approach and return route. Its limit behavior differs from the timed/fast courses above.

## From review to a fix

1. Reproduce and describe a specific problem before choosing a patch. Create an issue for the reproduced problem or coherent shared cause, not one speculative issue per course.
2. Keep fixes small. Edit the generator, rebuild and run the applicable verifiers from [AGENTS.md](../AGENTS.md); never hand-edit generated mod output. Update this checklist, AGENTS.md and DEVELOPMENT.md with the actual state.
3. Test each affected course separately, plus the relevant group reference(s). A built/verified candidate stays open until human confirmation; a shared asset family does not prove shared coordinates or behavior.
