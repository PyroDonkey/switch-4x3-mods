# Switch Aspect Ratio Modding — Technical Reference

Last updated 2026-10-29. Worked examples: [Super Mario Bros. Wonder](../super-mario-bros-wonder/) (in this repo) and The Legend of Zelda: Breath of the Wild.

## Overview

A native-looking aspect-ratio mod for a Nintendo Switch game has two independent halves, and both must target the exact game build. The **3D render** changes through an exefs code patch, usually a single float holding the game's aspect ratio. The **UI** changes through the game's layout files, which are drawn in a fixed 16:9 coordinate space. This reference covers games whose UI uses Nintendo's nn::ui2d layout system (`.bflyt`/`.bflan` inside SARC archives, the norm for first-party titles), played on yuzu-family emulators (yuzu, citron, Eden, Sudachi) that load `.pchtxt` patches.

| Half | Files | Without it, on a 4:3 screen |
| --- | --- | --- |
| 3D render | `exefs/*.pchtxt` | The world is drawn at 16:9 and squeezed: characters look tall and thin |
| UI layouts | `romfs/…/*.bflyt` in SARC archives | The UI is stretched, or (with only a root scale) sits in a centred 16:9 band with the HUD inset from the edges |

A native result means:

- The 3D view renders at the target ratio.
- HUD and header/footer elements sit at the real screen edges, the same distance from them as in 16:9.
- Central content (menus, dialogs, lists) stays compact and centred.
- Full-screen layers (fades, blurs, wipes, backgrounds) cover the whole screen.
- The emulator displays exactly the target ratio (yuzu-family: Graphics → Aspect Ratio → Force 4:3, or Stretch to Window when the window itself has that shape).

Generators such as AnyAspectRatio produce a quick first pass but have shipped hard-coded values and "centre-only" UI scaling; treat their output as a starting point and check it against the original files.

Examples marked **SMBW reference** come from a 4:3 mod of Super Mario Bros. Wonder built with this method (see the reference example at the end). Treat their names, addresses and values as illustrations; other games use their own.

## Step 1: identify the exact game build

Start by confirming the player's game version, because a code patch only applies to one build and fails silently on every other. Each game update produces a new main executable with its own build ID, and a `.pchtxt` applies only when its `@nsobid-<build ID>` line matches. Layout files have no such check, so a mismatched mod shows a telltale split: the UI changes apply but the 3D view stays 16:9, squeezed to look tall and thin.

- **Version:** the emulator's game list (Version column) or the game's Properties.
- **Build ID:** copy it from any existing patch made for that same version. A `.pchtxt` carries it on its `@nsobid-` line, and an `.ips` patch is named after it. Two unrelated patches agreeing on the ID is good confirmation.
- **Several versions:** put one `.pchtxt` per version in the same `exefs` folder. The emulator applies the one whose build ID matches and ignores the rest.
- **Layouts are version-specific too.** Build from the layouts of the version being played. A generator's cached base files may come from an older update; dump the current ones with the emulator's Dump RomFS command. SMBW reference: the first builds used the generator's cached files. Extracting 1.2.1's own layouts later showed 30 of 234 archives differed, so the mod had been replacing those screens with older versions; it is now built from the 1.2.1 files. Ship only the archives the build changes: unchanged ones fall back to the game's own copy (Workflow and tools).

## Step 2: patch the 3D aspect ratio

In many games the 3D view's aspect ratio is one 32-bit float in the main executable, and changing it to the target ratio is the whole 3D fix. A `.pchtxt` for a single value looks like this:

```
@nsobid-<build ID of this game version>

@flag print_values
@flag offset_shift 0x100

// 4:3 aspect ratio
@enabled
<address> ABAAAA3F
@stop
```

The value is the ratio as a little-endian float. Keep the `offset_shift` line that the source of the address used, because the address is only valid with that shift.

| Ratio | Float | Hex to write |
| --- | --- | --- |
| 16:9 (stock) | 1.7778 | `398EE33F` |
| 16:10 | 1.6000 | `CDCCCC3F` |
| 3:2 | 1.5000 | `0000C03F` |
| 4:3 | 1.3333 | `ABAAAA3F` |
| 5:4 | 1.2500 | `0000A03F` |
| 21:9 (2560×1080) | 2.3704 | `26B41740` |
| 3440×1440 | 2.3889 | `8EE31840` |
| 32:9 | 3.5556 | `398E6340` |

**Finding the address.** The practical route is an existing aspect-ratio or ultrawide patch for the same build ID: decode each line's value as a float, and the line holding that patch's ratio (for example 3.5556 in a 32:9 patch) is the constant. Write your own ratio there. Ultrawide patches often carry extra lines that widen culling or field of view; a ratio narrower than 16:9 doesn't need them, so leave them out and keep the game's defaults. If no patch exists for the build, the constant has to be found by reverse engineering the decrypted executable, which is outside this reference.

**Reading the result.** Tall and thin means the patch wasn't applied (wrong build ID, or the emulator doesn't load `.pchtxt`). Short and wide means the wrong value. Always decode a generator's patch value before trusting it.

**Camera framing for narrower ratios.** Changing only the aspect constant keeps the height and trims the sides. In side-scrolling games that can break progress: rooms sized exactly to the 16:9 width hide exits at their edges, and the camera won't scroll because it treats the room as fully visible. Aspect-ratio packs for such games often add a second line that pulls the camera back so the 16:9 width stays on screen. Find it the same way, by comparing an existing pack's narrow-ratio patches with its stock or wide ones. The trade-off is that everything looks slightly smaller and more is visible above and below.

These camera lines are often an `fmov` instruction with an immediate value (`fmov s1, #20.0` = `0190261E`). `fmov` can only encode values of the form n/16 × 2^e (n 16–31, e −3 to 4), so round the ideal value up to the nearest encodable one; rounding down leaves the edges slightly cut.

**Better: fix the camera code itself.** Games often keep hard-coded 16:9 view widths for camera limits, culling and screen walls, and some of those constants are shared with code that must keep the 16:9 value. Changing them blindly can box the camera and the player into rooms. Step 3 covers how to find and patch them safely.

The zoom-out line is a fallback when that width can't be found. The SMBW reference ships none and picks the view height per area instead (Step 3). It also reveals area above and below the frame the levels were designed for, so ship it as separate mods, one per strength; the player enables one in the emulator's Add-Ons list. The share of the 16:9 frame shown scales with zoom ÷ stock zoom. SMBW reference (stock view height 15.5), at 4:3:

| Zoom value | Width shown (share of 16:9) | Height shown (share of 16:9) | Extra area at top and at bottom |
| --- | --- | --- | --- |
| 15.5 (stock) | 75% | 100% | none |
| 17 | 82% | 110% | 4.8% |
| 18 | 87% | 116% | 8.1% |
| 19 | 92% | 123% | 11.3% |
| 20 | 97% | 129% | 14.5% |

## Step 3: fix the 3D camera beyond the aspect constant

The aspect constant fixes the picture, but camera logic often still assumes a 16:9 screen: rooms don't scroll, doors at the edges stay hidden, or invisible walls stop the player. These fixes need the game's decrypted executable and a decompiler (Workflow and tools covers extraction).

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Camera won't scroll in rooms exactly one 16:9 screen wide | Camera limits use a hard-coded 16:9 width | Patch the width constants that describe the visible area |
| Camera locked and player boxed in short of the doors in small rooms | A shared "screen width" constant also sizes one-screen rooms, so patching it shrank them | Give that one user the original 16:9 value (code cave) |
| An exit or item at the edge of a locked room or shaft stays off-screen | The lock pins the camera to the point that frames the 16:9 view | Let the locked camera pan within lock ± Δ (Fixed and locked cameras, below) |
| Player outruns an autoscroll, or dies when a scripted event snaps the camera back | The fixed-camera target follows the player with no limit | Ride the scroll exactly while it moves; pan within ± Δ only once it has stopped |
| Camera can't reach an area's edges when the area is narrower than the 16:9 view | The original game just centres there | 16:9 reach rule (below) |
| Walls or ceiling of a boss arena cut off | The fight needs the whole 16:9 frame at once | Zoom that room alone, with Δ = 0 (Zooming only one room) |

**Find the hard-coded widths.** Search the read-only data for the view height × 16/9, its half, and their negative copies; compilers store negatives separately for "right − half-width" maths. List every code reference and read each user before patching. Change only users that describe what the screen shows: visible-area rectangles, camera clamps, transition clamps.

**The shared-constant trap.** One constant can mean "screen width" in one place and "standard room width" in another, so patching it for the screen also resizes rooms. The tell: the camera moves only when the clamp's half-width is set below the target ratio's value. Always check the size of the camera area the game actually uses before patching anything else; a wrong area alone produces a frozen camera, a stuck focus and invisible walls. SMBW reference: the level loader gives every camera area authored one screen wide (27.5 units) the screen-width constant as its size, so patching it to 4:3 shrank 241 one-screen rooms and confined the player.

**Fixed and locked cameras.** Side-scrollers hold the camera in two different ways, and each needs its own fix. Before patching, find which script nodes write each field the camera reads. An autoscroll moves a fixed camera point every frame. Keep stock behaviour while that point moves, so the player cannot outrun the scroll. Once it has been still for about 2 s (a stopped or vertical scroll), let the target ease towards the camera focus within fixed point ± Δ. A screen lock pins the camera to the point that frames a room or shaft in 16:9. There, X = lock X + clamp(normal camera X − lock X, ± Δ), so the 4:3 view pans inside the frame the lock was designed for. Rooms that must show their whole frame at once (boss arenas) use Δ = 0 and a zoom instead. On a room change or a large jump, restart from the game's own position. SMBW reference: only the `SetAutoScrollPos` node writes the fixed point at `subject+0x194` and its flag at `subject+0x1B4` (cave G, hook `006C6FD0`). `StopScroll` locks set `controller+0x29`, and the final camera write then takes X from `controller+0x1A0` (cave H, hook `006C7BEC`). An earlier fix let the fixed-camera target follow the player without a limit, and Mario outran the airship autoscroll. The Wonder Flower then snapped the camera back to the scroll and he died off-screen.

**Narrow areas: the 16:9 reach rule.** Where a camera area is narrower than the 16:9 view, the original camera centres and shows centre ± half the 16:9 width. Give the 4:3 camera at least centre ± Δ of travel, Δ = (16:9 width − 4:3 width) ÷ 2, applied right after the game computes its limits: lower = min(lower, centre − Δ), upper = max(upper, centre + Δ). Δ depends on the view height, so store it per area next to the height (SMBW reference: 3.44 at the stock 15.5, 3.28 at 15.75, 0 in zoomed boss rooms). Have the generator assert Δ ≤ max(0, (16:9 width − 4:3 width at that height) ÷ 2); a leftover Δ in a zoomed room pans the view off its walls.

**Code caves.** When a fix needs more instructions than fit in place, use the unused bytes between the end of `.text` and the next page boundary (SMBW reference: 0x9B0 bytes in 1.2.1, now used from `02138780` to `02138F24`). They are mapped executable, and yuzu-family emulators apply `.pchtxt` lines there. Replace one instruction with a branch to the cave, run the original instruction plus the new code, and branch back. Check three things first: no condition flags are clobbered before a following conditional select, every scratch register is dead at that exact point, and constants come from PC-relative literals in the cave, because `fmov` immediates are limited. Check registers per hook, not per function. SMBW reference: in the camera controller only s31 is unused throughout, and s16 is live at one of the hooks. Have a second reviewer check every encoding, branch target and register claim before shipping. In SMBW that review also caught a wrong assumption about which code path a locked room used.

**Finding which code owns the camera.** When a patch changes nothing, stop guessing and build diagnostic probes: give each candidate code path a deliberate, distinct effect (camera far left and down, far right, far up) and test a normal level as a control before the problem room. Then aim the camera straight at the player's position to test its inputs, and force its limits wide open to test the clamp. Write probe bytes from the encoder's output, never by hand. Once something works, remove the workarounds one at a time and keep only what's needed.

**Zooming only one room.** A fixed room whose whole 16:9 frame must stay visible (a boss arena) needs more than a panning camera, so zoom that room alone and key it by the area's hash. Each map-unit file stores a `RootAreaHash`, and the game's record for the loaded area carries the same number (SMBW reference: at `record+0x90`, reached through the area-record table that the camera controller indexes with a signed byte at `controller+0x10A`). Two caves share one mailbox word in an unused, zeroed tail of `.bss`. One cave in the camera controller looks up the current area's hash in a table and writes that room's view height, or the per-area base elsewhere. The other sits where the game multiplies its zoom field by the stock base height and takes `max(base, mailbox)`. The 4:3 height that restores the 16:9 width is the 16:9 width ÷ (4/3) (SMBW reference: 27.56 ÷ 1.333 = 20.67; 21.0 shipped for the first arena). Give that room Δ = 0, so a lock-panning cave keeps the camera exactly on the lock. If the room also has its own zoom actor, the two multiply: the actor stores zoomBlockCount ÷ 15.5, and the view uses that factor × max(15.5, base). SMBW reference: Course152\_Sub4's actor (17.5) with base 20.67 reproduces its stock 31.1-wide frame at 4:3; a base of 23.33 would have overshot.

**Data-only zoom edits can silently do nothing.** A level's own zoom actor can be edited in its map-unit file, but check that the game applies it in the situation you care about. SMBW reference: the Bowser Jr. arena's `zoomBlockCount` (view height in blocks, stock 15.5) was loaded with the edited value, confirmed by reading it back from memory, yet it does not frame the normal fight. Measure the real view height from a screenshot before and after any edit (blocks = screen height ÷ tile height).

**Screen-anchored actors drift when a room is zoomed.** Some actors place and scale themselves from the camera's visible box, normalised by the box size, instead of from world coordinates. SMBW reference: the Bowser Jr. arena's ceiling pipes use an AI node that reads the world-space box of the camera view, measures their offset as a fraction of its width and height, and scales by box height ÷ 15.5. In 16:9 the box is the 27.56×15.5 frame the script was authored for, so the pipes sit on the ceiling. With the room zoomed to 28×21 they landed about 2 blocks low and at the wrong scale after the phase 2 script ran. Fix it by handing the script its authored box: in the zoomed room, scale the box's vertical extent back about its centre. Hook every path that fills the box. The per-frame update alone was not enough, because a separate initialiser measured the starting rates once and still saw the oversized box. The tell is an actor that behaves at the start of a fight and goes wrong only after a scripted event. Shrinking the engine's cached visible rectangle did nothing, because this node reads the camera's own projection.

**Debugging against the live emulator.** On a PC emulator a script can read and write the running game's memory. Find the code image by searching for a distinctive 48-byte function prologue from the decompressed executable and keeping the page-aligned hit. Do not assume a fixed guest base address; it changed between launches, so work in image-relative offsets. Data (read-only constants, heap) can be changed live, which is a fast way to test a numeric hypothesis. Code cannot: the JIT keeps its own translated copy and ignores a host-side write, so every code patch needs a game restart. Prove that a hook ran by having the cave store a value in a spare zeroed word and reading it back. Loaded AI graphs (AINB files) can be found in heap by their magic, and their strings show what an actor's script queries. A custom node's class can be traced from its name string, through the relocation entries, to its vtable and code. Take screenshots of the emulator window by title rather than a fixed screen rectangle. Eden can keep stale copies of the image in its backing memory, so use the copy whose .bss is live and whose heap pointers resolve. Find the guest base by scoring candidate bases against the entries of a known vtable. Have a cave store the pointers a probe needs in spare words (SMBW reference: the camera controller and subject). In PowerShell, write hex constants of 0x80000000 and above with an L suffix, or they become negative 32-bit numbers.

**Raising the base view height.** To show more of the 16:9 width, raise the base view height G in the same hook that carries the per-room override. Three companions go with it. The camera controller computes its own view half-extents as zoom × base height and zoom × the shared width constant, so give it the same G and scale the width by G ÷ stock base. The reach-rule Δ shrinks to (16:9 width − 4:3 width at G) ÷ 2. Per-room overrides keep working through `max()`. The object-activation rectangle needs no change where, as in SMBW, it derives its zoom from the real view height. Treat clamps that ignore zoom (hard-coded ±10.33 / ±7.75 half-extents) as cosmetic risks and check them in play: level ends and pits for void, one-screen rooms, Wonder zooms and pipe warps, and enemy pop-in at the edges. SMBW reference: a single global G = 17 was tried and reverted (next paragraph).

**Choose the base per area, and keep it small.** A higher base also grows the view vertically, which exposes space outside backdrops painted for the stock frame. SMBW reference: with G = 17 everywhere, a power-up hut showed sky above its ceiling art, and a wide level showed bare sky above its backdrop. Decide per area. Read the loaded area's bounds (SMBW reference: min x at `record+0x94`, max x at `record+0xA0`). Keep the stock height for narrow areas (SMBW reference: bounds narrower than 60 gives 15.5, which covers Poplin houses, shops and one-screen sub-rooms). For wide scrolling areas, raise the base one step at a time and check the worst backdrop after each. SMBW reference: 17 showed sky, 16.25 a thin strip and 16.0 a sliver; 15.75 stayed in frame and shipped, 76% of the 16:9 width. Values like 15.75 are not `fmov` immediates, so keep them as literals in the cave. A table keyed by area hash overrides both for special rooms (boss arenas, Δ = 0). Everything that depends on the base (view height, the controller's half-extents, the reach-rule Δ and any display-box scripts) reads one per-area mailbox word, so the cave that chooses it must run first each frame. Write the measured width, the chosen base and Δ to spare words so you can read them from memory in each kind of room. Not yet tried: lowering the camera so all the extra height falls at the bottom, which might allow a larger base.

## Layout file formats

Edit layouts in place: decompress the archive, overwrite existing floats, recompress. No float is added or removed, so offsets, SARC tables and sizes stay identical and no repacker is needed. The exception is a layout that needs a new pane (SMBW reference: the kingdom map's band filler). Keep that file hand-edited, have the build copy it over its generated output, and have the checker skip it.

**Archives.** Layouts ship in SARC archives, zstd-compressed (`.zs`) in newer titles and Yaz0 (`.szs`) in older ones. Python 3.14's built-in `compression.zstd` handles zstd in both directions; round-trip every output file.

| SARC field | Location |
| --- | --- |
| Header length (u16) / byte order mark | +0x04 / +0x06 (FF FE = little endian) |
| Data start (u32) | +0x0C |
| SFAT node (16 bytes each) | name hash, attributes (low 16 bits = name offset ÷ 4), data start, data end |
| SFNT | null-terminated names after an 8-byte header |

**BFLYT.** After the header (byte order mark at +4, header size at +6, section count at +0x10), `lyt1` holds the layout's width and height (floats at +12), `pas1`/`pae1` open and close a child list, and the pane sections are `pan1 pic1 txt1 wnd1 bnd1 prt1 scr1 ali1`. Every pane shares this base layout:

| Pane field | Offset from section start |
| --- | --- |
| Origin byte | +9 |
| Name (24 bytes) | +12 |
| Translate X / Y | +44 / +48 |
| Rotate X, Y, Z | +56 |
| Scale X / Y | +68 / +72 |
| Size width / height | +76 / +80 |
| pic1 material index (u16) | +100 |

The origin byte packs four 2-bit fields: bits 0–1 horizontal origin (0 centre, 1 left, 2 right), bits 2–3 vertical origin (0 centre, 1 top, 2 bottom), bits 4–5 and 6–7 attachment to the parent's left/right and top/bottom edge. So `08` is a bottom origin, and `88` is a bottom origin attached to the parent's bottom edge.

**Materials.** In BFLYT version 9, each `mat1` material is a 28-byte name, a u32 flags word at +0x1C (texture-map count = flags & 3), then 4-byte texture-map entries from +0x2C (u16 index into the `txl1` name list, wrap S, wrap T). The layout differs between BFLYT versions, so confirm offsets by checking that decoded texture names make sense. A placeholder texture (in Nintendo's titles often named like `CmnDummy`) marks a pane that displays a runtime screen capture.

**BFLAN.** Animations live in `pai1`: entry count at +14, offset to the entry-offset table at +16. Each entry is a 28-byte pane name, a tag count (u8, +28), an is-material flag (u8, +29) and tag offsets from +32. Pane transforms use `FLPA` tags; skip other tag types, whose layouts differ. An FLPA tag entry holds the target, curve type (2 = Hermite) and key count, and points to 12-byte keys: frame, value, slope. FLPA targets: 0 TransX, 1 TransY, 6 ScaleX, 7 ScaleY, 8 SizeW, 9 SizeH. Check a pane's animations before changing it: an animated property overrides the static value at runtime.

**Parts vs top-level layouts.** A layout named inside some other layout's `prt1` section is a part (a reusable sub-layout). The `prt1` pane stands in for the part's RootPane, so only top-level layouts' root scale matters. Leave parts' roots at their original (1, 1).

## Coordinate model

The emulator stretches the 16:9 layout space to fill the screen, so scaling the RootPane against that stretch makes layout units square again and reveals extra room at the edges. For a target narrower than 16:9 the extra room is vertical; for a wider one it is horizontal. Root-local units are coordinates inside RootPane, before its own scale; all distances in this reference use them.

```
            1920 wide (x stays 1:1)
  y = +720  +------------------------------+  <- real 4:3 top edge
            |   new band (180)             |     HUD/header shifted up by 180
  y = +540  +------------------------------+  <- old 16:9 top edge
            |                              |
            |   original 16:9 composition  |  central content stays put
            |   (root scale Y 0.75)        |
            |                              |
  y = -540  +------------------------------+  <- old 16:9 bottom edge
            |   new band (180)             |     footer shifted down by 180
  y = -720  +------------------------------+  <- real 4:3 bottom edge
  Full-screen layers (fades, blurs, wipes) grow 1080 -> 1440 to cover both bands.
```

At 4:3 the visible height becomes ±720 while the original composition fills ±540. An element 130 from the old top edge (y 410) moves +180 to y 590, keeping 130 to the real edge.

**Narrower than 16:9** (ratio r, layout height H, usually 1080):

- Root scale Y = r ÷ (16/9); root scale X stays 1.
- Visible half-height = (H/2) ÷ root scale Y.
- Edge shift = visible half-height − H/2.
- Fill factor = 1 ÷ root scale Y.
- A pane's local offset = edge shift ÷ (product of its ancestors' scale Y below RootPane).

**Wider than 16:9**: the same logic on the X axis. Root scale X = (16/9) ÷ r, visible half-width = (W/2) ÷ root scale X, edge elements shift along X, and full-screen layers grow in width.

| Target | Axis | Root scale | Visible half-extent | Edge shift | Fill factor |
| --- | --- | --- | --- | --- | --- |
| 16:10 | Y | 0.9000 | 600 | 60 | × 1.111 |
| 3:2 | Y | 0.8438 | 640 | 100 | × 1.185 |
| 4:3 | Y | 0.7500 | 720 | 180 | × 1.333 |
| 5:4 | Y | 0.7031 | 768 | 228 | × 1.422 |
| 21:9 (2560×1080) | X | 0.7500 | 1280 | 320 | × 1.333 |
| 32:9 | X | 0.5000 | 1920 | 960 | × 2.000 |

Values assume a 1920×1080 layout; scale them for layouts authored at 1280×720.

For 1280×720 layouts at 4:3 (BOTW): root scale 0.75, visible half-height 480, edge shift 120, fill factor × 1.333.

**When the game rewrites the root scale.** Some titles overwrite RootPane's scale at runtime, which silently discards a root-scale mod. Find out from the code, or from a test build where the root scale changes nothing in-game. BOTW does this. The fallback that worked: leave RootPane alone, multiply the Y scale and Y translation of each direct child of RootPane by the root scale, and for panes whose scale the game sets itself (list them by name) change their size instead and push the factor down to their children. Apply every later rule with that per-child factor in place of the root scale. Keep the root-scale mode as an option and verify both.

## Layout transformation rules

Apply these rules in order, to the original layout files, for every top-level layout. Numbers are for a narrower-than-16:9 target with 1080-tall layouts, with relative values in brackets; for a wider target, swap Y for X. The thresholds come from the SMBW reference build and are starting points, not constants.

1. **Root scale.** Set RootPane scale Y to the root scale from the table. Leave parts layouts at (1, 1).
2. **Edge anchoring.** Walk down from RootPane through containers (`pan1 scr1 ali1`) whose translate Y is 0, scale Y is 1 and rotation is 0. The first pane in each chain with a non-zero translate Y is a *positioning pane*. Treat it as edge-anchored when its height is under 864 \[0.8 H\] and any of these holds:
   - its centre is at |y| ≥ 380 \[0.7 × H/2\];
   - its origin point (for top- or bottom-origin panes) is at |y| ≥ 380;
   - it is at most 400 tall \[0.37 H\] and its outer edge reaches |y| ≥ 380.

   Null panes at their nominal placeholder size (30×40 in Nintendo's editor) count as height 0. Move each edge-anchored pane outward by the edge shift, converted to local units, and add the same offset to every TransY key of that pane in every animation file of the archive (slopes unchanged). Shifting additively keeps the distance to the edge, and parent slide animations stay consistent because they add to it.
3. **Pivot splitting.** Don't move a `pan1` container whole if one of its children is not edge-anchored and counter-translates back towards the centre by 300 or more \[0.28 H\]. Judge each child separately instead. Corner pivots used for scale animations (a container at a screen corner whose child cancels the offset) are the usual case.
4. **Full-screen fill.** A pane qualifies when its absolute height is between 0.95 H and the visible height and its centre is within 10 of 0. Eligible panes: `pic1 wnd1 scr1`, and full-size `pan1` containers whose children attach to their top or bottom edge. A full-width pane with a TransY animation also qualifies.
   - Grow its **size** height by the fill factor, not its scale, so children don't stretch and window borders keep their thickness. Move top- or bottom-origin panes by half the growth so their centre stays put.
   - Artwork and patterns spanning the full width: also grow the width (uniform zoom, sides cropped). Screen captures, untextured fades and window frames: height only, so captured screens stay mapped 1:1. Any capture texture in a material means height only.
   - If the pane's TransY is animated (screen-slide wipes), multiply static Y and key values and slopes by the fill factor so the slide stays proportional.
   - **Capture sources keep their 16:9 size.** A capture source is the pane that marks the screen area copied for a blurred or frozen background; a separate use pane draws the copy. Some games read the source's local size directly as framebuffer pixels and ignore the root scale. There, leave the source at 1920×1080, which already copies the whole frame, and fill only the use pane. The tell for a wrongly filled source: the background shows as a 16:9 band with streaky lines above and below. Exception: when another element follows the capture's size, such as an iris wipe whose circle is only round with a filled capture, keep that capture filled and crop the use pane's V coordinates to 0.5 ± 0.5 × root scale (0.125–0.875 at 4:3), the rows that hold the real frame. SMBW reference: sources are `pan1` panes such as `N_Cap` with `CaptureOn` or `DynamicCaptureOn` user data, and the course-entry wipe `WipeCourseIn` needed the exception.
5. **Edge strips.** A strip inside a block that stays put, whose outer edge sat on the 16:9 edge (typically a scroll-list mask), grows outward by the edge shift: height + shift, centre moved by half.
6. **Title and art screens.** Zoom background art uniformly. Move art-tied decorations (sparkles, dust, shadows) to absolute position × fill factor, computed in screen space and converted back to local space, and grow their size by the same factor; size is safer than scale, which is often animated. Edge-anchor version text and "press start" prompts, and leave logos in place.

**Small capture-use panes.** Rule 4 covers full-screen captures. Smaller ones, such as a magnified view inside a window, a mask that redraws the background at the end of a list, or a cut-in, draw a capture from a source pane of the same size, and the game copies the source's local size as pixels, so the capture maps 1:1 to the screen. Under a scaled root such a use pane can be drawn squashed; the fix is to multiply its local height by the fill factor (1.333 at 4:3) and leave the source alone. Apply it one pane at a time, never as a blanket rule (see the SMBW result at the end of this rule). Round shapes (an iris or circle window with a uniform scale) are already round under the root scale: compensating them stretches them, so change only the panes that display a capture 1:1. To find candidates, list every `pic1` whose material uses the capture placeholder texture and whose height is under 0.95 H, then test them in-game one at a time; the right fix differs by screen (a source that must stay filled needs the V-crop in rule 4 instead). SMBW reference: the shop's list-end masks and its 320×320 world view needed the taller use pane, while its closing circle needed no change. SMBW result when the fill factor was applied to all 42 small use panes at once: the in-level HUD icons, the course-list header icons, the controller-button glyphs (X, L, R, +) and the profile card's icon row all came out about 1.3 to 1.4 times too tall. Measure each candidate against a screenshot of the unmodified game (same screen, compare the width-to-height ratio of round or square icons after allowing for the different window width) before compensating it, and keep an allow-list of layouts instead of a name pattern. Icon, number and glyph rows drawn through a capture are the usual failures; only the shop's world view and list-end masks needed the taller pane.

**Capture geometry, in general.** The rule behind every capture case above: the on-screen height of the pane that draws a capture must equal the height of the region its source copies. Work it out per pair instead of applying one policy. In BOTW 1.6.0 (disassembled), a plain source copies a rectangle equal to its own local width and height, centred on its global position. Parent and own scale multiply that rectangle only for sources flagged `CaptureApplyScale`, and only while a global engine flag is on. The use pane draws the whole texture (UV 0 to 1), so the two heights have to match. Sources flagged `CaptureBGColor` differ: they render their own subtree offscreen with an identity transform, so ancestors and their own transform are ignored.

A source nested under panes you scaled shrinks on screen with them, but its copy size does not, so it needs the same compensation as a use pane. When you cannot tell how an engine flag is set, write values that are correct in both states: source local height = stock height × the scale applied to its ancestors, and own scale = stock scale ÷ that factor. The copy is then the same size whether or not the engine multiplies it. This fixed the small squares at the ends of BOTW's D-pad icon list.

**Text.** A text pane outside every scaled ancestor is still stretched by the display. Multiply its font height and line spacing by the compensation factor, or loading-screen tips and captions look vertically stretched.

**Full-screen art that is letterboxed.** A picture authored for 16:9 (SMBW reference: the kingdom map, 1920×1080) cannot cover a 4:3 screen undistorted. Left at its true size it leaves bands above and below. First check what is drawn beneath the band. SMBW reference: the course-list layer under the map (header, buttons, cards) is hidden by the opaque art in 16:9 but showed through the bands at 4:3, and in the world-travel view the bands were plain black. Fill the bands with one pane placed first inside the art's offset node: full root size, behind the art, flagged to follow its parent's alpha so it fades with the screen. Use a texture from that layout's own archive. In all 234 SMBW layouts every material uses only its own archive's textures, and copying another layout's texture needs texture-container name, hash and relocation edits. Tiling scale on these materials works in texture-pixel units (the game's own tiling materials use scale (1,1)), so a scale of 40 aliased to a flat colour and a scale of 1/3 gave the intended 48-unit stripes. Cropping the art (about 12.5% lost on each side) or mirroring its edge rows are the alternatives, and a pane in the game's own background colours looked most natural. A solid backdrop also makes the bands deterministic on emulators whose drivers leave unpainted buffer areas undefined.

**Screen-projected patterns.** A material can map a tiling pattern through a texture projection instead of the pane's own UVs (texture-coordinate generator source 3, orthographic projection). That projection follows the 16:9 screen, not the scaled root, so at 4:3 the pattern comes out 0.75 as wide as tall while the pane's shape stays correct. Fix it in the material: multiply that texture's TexSRT scale X by the root scale (0.75 at 4:3), which restores the stock tile size. Check that no animation writes the same scale; a scrolling pattern usually animates only the translation. SMBW reference: the Badge Challenge restart wipe (`WipeBadgeChallenge`) drew its badge emblems at about 0.76 wide/tall around a correctly round flower-shaped hole; scale X 0.75 on materials `W_WipeC` and `W_WipeLT` made them round. Material names can carry trailing spaces, so strip them before matching.

**Photos captured by code.** Some screens show a snapshot of the 3D view that the game captures itself and hands to a picture pane at runtime (a placeholder texture marks the pane). With the aspect patch the snapshot holds a 4:3 view, so a frame authored at 16:9 draws it about 1.33 times too wide. Narrow the photo pane and everything sized to it by 0.25 × the photo width, keep the frame border, and move corner decorations by half that amount. Cropping the snapshot's V coordinates to 0.125–0.875 instead keeps the 16:9 frame but loses the top and bottom. Photos taken before the mod are true 16:9 and will look squeezed in the narrower frame. SMBW reference: the course-clear photo (`CourseOut` and the main menu's photo, `P_Screenshot`); bricks measured 35.5×27 px before and 26.5×26.7 px after.

## Patterns that need a manual decision

Automatic rules handle most panes, but a handful of recurring structures break them. Read each top-level layout's pane tree looking for these before trusting a build.

| Pattern | How to recognise it | What to do |
| --- | --- | --- |
| Corner pivot | Container at a corner, e.g. (−960, −540), whose child cancels it (960, 540); often has scale animations | Split: judge children separately (rule 3) |
| Mixed wrapper | One in/out wrapper at an edge holds both a title near the edge and content near the centre | Split: move only the edge children |
| Cohesive edge block | A window plus its text hanging below an anchor; a clip window with text inside; a photo with its button | Move the whole block; don't split |
| Stacked column | Several boxes touching vertically, the top one near an edge | Keep the column in place as one block; moving its ends opens gaps |
| Edge cluster under the threshold | An element just under the threshold that belongs with an edge element (an item row under a counter) | Force-shift it with the cluster |
| Scroll list with masks | Strip panes over a list's top and bottom that draw captured background to hide scrolled items | Keep the list and masks together; extend the outer strip to the new edge (rule 5) |
| Edge-attached children | Origin bits 6–7 set (`4x`, `8x`), attached to a full-size parent | Grow the parent with the fill rule so the child follows the new edge |
| Off-centre full-screen pane | Top or bottom origin (`04`, `08`) on a 1080-tall pane | Grow it and move it by half the growth |
| Content placed on art | Labels or frames positioned over a map or illustration | Don't fill or shift that screen; letterboxing beats misaligned labels |
| Animated paths | Cut-ins or fly-ins whose positions are mostly in animation keys | Don't shift; fill their full-screen glow layers only |
| Code-positioned elements | Markers or name tags at (0, 0) in the layout, placed by the game at runtime | Nothing to do in layouts; they keep 16:9 coordinates |
| Cursor or selector | Positioned and sized by code at runtime, often with a capture | Leave its root at stock scale. Scaling it moved its corner markers off the item; restoring it fixed that. To keep the art's shape, put the root scale on the unrotated node that holds the art, never on a pane under a rotation (SMBW: Cursor root 1, LCursor N\_RB scale Y 0.75) |
| Capture source under scaled panes | Its copy size no longer matches what the use pane draws | Compensate the source's local size and own scale (Capture geometry) |

## Common bugs and their fixes

Each of these was a real defect, either in generator output or in an early version of a careful build. Most show up only in-game unless the verification checks below are in place.

| Symptom | Cause | Fix |
| --- | --- | --- |
| 3D world tall and thin, UI fine | Code patch targets a different build ID, so it is skipped | Patch for the build being played; ship one `.pchtxt` per version |
| 3D at the wrong ratio whatever the settings | Generator wrote a hard-coded value instead of the chosen ratio | Decode the value; write the ratio float |
| HUD inset from the top and bottom edges | Only the root was scaled ("centre" mode) | Edge anchoring (rule 2) |
| Element moves, then snaps back when animated | Static position changed, animation keys not | Add the same offset to every TransY key |
| Fades and blurs leave unfilled strips | 16:9 full-screen panes under a scaled root | Full-screen fill (rule 4) |
| Screen captures distorted, or art squashed | Fill mode chosen from misread textures, or from the first texture slot only | Confirm material offsets by decoding names; check every slot; any capture texture means height only |
| Background shifted off-centre | Top- or bottom-origin pane grown without moving it | Move it by half the growth |
| HUD inside a full-screen clip window never moves | Traversal skipped panes picked for fill | Descend into fill containers |
| Top-origin banner left behind | Edge test looked only at pane centres | Also test the origin point |
| Gap opens inside a panel or column | Only one end of a stacked block moved | Keep the block in place as a unit |
| Blur layer overshoots the screen | Fill applied in a layout whose root stayed unscaled | Give every top-level layout the same root scale |
| Decorations look small on zoomed art | Only their positions were scaled | Grow their size by the fill factor |
| Centred menu dragged towards an edge | A corner pivot or mixed wrapper moved whole | Pivot splitting, limited to real counter-translation so cohesive blocks stay whole |
| Ground strip or bar stops short of the edge | Child attached to a parent's edge; parent never grown, attachment not modelled | Grow edge-attached parents; model attachment in position maths |
| List items show in the new band | Scroll mask ends at the old 16:9 edge | Extend the mask strip to the new edge |
| Captured backgrounds (pause blur, menu backdrops) drawn as a 16:9 band with streaky lines above and below | Capture source pane filled to the visible height; the game copies its local size as pixels, reads past the frame edges and smears the edge rows | Leave capture sources at 1080; fill only the panes that draw the capture (rule 4) |
| Iris wipe circle turns oval once captures are fixed, or its snapshot jumps when the wipe starts | The wipe's circle follows the capture pane's size, so one value controls both the circle and the snapshot | Keep that capture filled and crop its use pane's V coordinates to 0.125–0.875 |
| Exit at a room edge is cut off; the camera won't scroll | Narrower aspect crops the sides while the camera still frames rooms for the 16:9 width | Patch the hard-coded view widths and keep the 16:9 width for one-screen rooms (Step 3); a zoom-out line is only a fallback |
| Camera locked and player boxed in short of the doors in one-screen rooms | A patched width constant is shared with the level loader, which sizes one-screen rooms from it | Give that user the original 16:9 value through a code cave (Step 3) |
| A patch line has no effect, or the wrong effect | Hand-typed bytes differ from the encoder's output | Write patch lines from the encoder and disassemble every enabled line before shipping |
| A captured view inside a small window or mask looks squashed | The use pane maps a same-size capture 1:1, but the root scale shrinks its height | Multiply the use pane's local height by the fill factor, only for panes measured against the unmodded game; leave the capture source alone |
| A circle or iris turns taller than wide after it was "corrected" | A uniform-scale round window was already round under the root scale; compensating it over-stretched it | Revert; compensate only the panes that show a 1:1 capture |
| Small squares or smeared edges at the ends of a masked list | The mask's capture source copies a taller region than the mask draws, because it sits under a scaled parent | Set source height and own scale so the copy equals the drawn height in both engine-flag states |
| Menu cursor corners offset from the item | Cursor layout was scaled although code positions it | Leave the cursor layout stock |
| Character or world stretched in menus and weapon-select windows | A full-frame capture source was shrunk along with its parent | Keep full-frame sources full-frame; fill only the use pane |
| Title art or glow does not fill the screen | Art panes grown in size only; their TransY keys still hold 16:9 values | Grow size and scale the TransY keys by the fill factor |
| A grow step changes nothing on some panes | The helper silently skips panes that have TransY keys | Write static value and keys together, and have the checker confirm every pane |
| Dark side bars at the screen edge are too short | A bar anchored at both edges was grown by one edge shift | Grow by twice the edge shift, since both edges move |
| Loading-screen tips look vertically stretched | Text pane sits outside any scaled ancestor | Multiply font height and line spacing by the compensation factor |
| Map does not reach the screen edge | Map scissor and capture panes sized for 16:9; a code constant can also be involved | Resize those panes; ship any code change as a separate optional patch, disabled by default |
| A scrolling list shows one row drawn on top of another, only at the new ratio | A page container, or the part it holds, that the game's list code reads carries the root-child scale | Leave that subtree at stock scale, position and size; find it by reverting layouts to stock in halves |
| HUD and menus look about three-quarters the size they have at 16:9 | The layout width is kept and the height is squeezed by the ratio factor | Scale HUD groups by 1/factor about their screen corner, keys included; skip panes whose scale the code writes |
| Round gauges and icons are stretched taller than wide with only the aspect patch | The code patch changes the 3D view; the layouts are still authored for 16:9 | Ship the layout changes with the patch, not the patch alone |
| Player dies off-screen when a scripted event (a Wonder Flower) starts during an autoscroll | The fixed-camera target followed the player with no limit, so he outran the scroll; the event snapped the camera back | Ride the scroll exactly while it moves; pan within ± Δ only after it stops (Step 3) |
| A goal or item in a locked shaft or room stays just off-screen | The screen lock pins the camera to its 16:9 framing point | Let the locked camera pan within lock ± Δ (Step 3) |
| A zoomed boss arena slides off its walls | A leftover Δ lets the lock-panning rule move a camera that already shows the whole frame | Δ = 0 in zoomed rooms; have the generator assert it |
| Sky or empty space shows above a backdrop or ceiling | Base view height raised past what the backdrop was painted for | Stock height in small rooms; raise wide areas one small step at a time (Step 3) |
| A scrolling or tiled background pattern is squeezed (tall ovals) while the shapes over it are round | The pattern is mapped by a screen projection that ignores the root scale | Multiply that texture's TexSRT scale X by the root scale (Screen-projected patterns) |
| A captured photo of the level looks too wide (square blocks wider than tall) | The game captures the 4:3 view, but the frame that shows it is authored at 16:9 | Narrow the photo pane and its frame by 0.25 × the photo width (Photos captured by code) |
| A zoom-to-centre animation ends off-centre | The edge shift added its offset to every TransY key, including the key that should stay at the centre | Shift only keys at the edge rest position; list the exceptions by layout, pane, animation and frame |
| Menu pointer sits nearer the screen's middle than its item and covers labels next to it | Code places the pointer in screen coordinates, and the cursor layout's root scale shrinks that position again | Stock root scale for the cursor layout; apply the scale to the unrotated node holding the arrow art |
| An icon comes out narrower and taller after a compensating scale | The scale was set on a pane under a rotated parent, so it squashed along the rotated axis | Apply screen-axis scale fixes above any rotation in the pane chain |

## Verification

Verify every build against the original files with a script separate from the builder, and prove each check catches the bug it targets by running it against a known-bad build first. These checks need no game or emulator; in-game testing is still the final step.

| Check | What it catches |
| --- | --- |
| SARC tables and file sizes identical to the original | Structural damage, accidental resizing |
| Every changed byte lies inside a logged write, and every logged write is present | Stray or lost edits |
| Re-parse every layout and animation file | Corrupted sections |
| Parts layouts keep root (1, 1) | Accidental edits to sub-layouts |
| No visible element that was on-screen in 16:9 now extends past the visible half-extent | Over-shifted elements |
| Every fill pane covers the visible area and is centred (animated slides exempt) | Fill gaps, off-centre growth |
| No moved group contains a visible element whose original centre was near the middle (±250 at 1080) | Pivots and wrappers dragging central content |
| Every full-width element that touched the 16:9 edge now touches the new edge | Elements left short of the edge |
| No animation targets RootPane; no fill pane has a size animation on the grown axis | Runtime overrides of the core changes |

Model origins and parent-relative attachment in the position maths. A checker that shares the builder's blind spots passes the builder's bugs. List groups that move as one unit on purpose as reviewed exceptions, so new warnings stay visible.

**Model the engine, not only the file.** For every capture pair, compute what the engine will copy and what the use pane will project with all ancestor scales applied, and require them to match; run it once per engine-flag state you cannot rule out. Run each new check against the previous build first and confirm it fails there. Keep the previous output as a dated backup before every install.

## Workflow and tools

1. Find the game version being played and its build ID (Step 1).
2. Get that version's original layouts: Dump RomFS in the emulator, or a generator's cached base files if they match the version.
3. If an existing mod is involved, diff it against the originals to learn exactly what it changes.
4. Write the 3D patch for that build ID (Step 2) and decode every value.
5. Separate parts from top-level layouts.
6. Work out the constants for the target ratio (Coordinate model).
7. Read each top-level layout's tree and animations; note the manual-decision patterns.
8. Build in place, logging every write, then run the verification checks. Write only the archives the build changed; an unchanged archive is pure game data the emulator already has (see `docs/game-files-policy.md`).
9. Test in-game with the emulator set to exactly the target ratio; fix anything reported, rebuild and re-verify.

The reference tools, written for the SMBW mod, are in [`super-mario-bros-wonder/tools`](../super-mario-bros-wonder/tools/). Most take the tools folder as their first argument.

| Script | Purpose |
| --- | --- |
| `lyt.py` | SARC, BFLYT and BFLAN reader that records byte offsets for in-place patching |
| `find_toplevel.py` | Splits parts from top-level layouts and writes `toplevel.txt` |
| `dump.py` / `analyze.py` | Print every pane, or the positioning panes with their animations |
| `build.py` | Applies the rules and curated decisions, copies hand-edited layouts over the generated ones, and writes the mod and `build_report.json` |
| `verify.py` | Compares the output with the originals and runs the checks (hand-edited layouts are skipped) |
| `nso_to_bin.py` | Unpacks an extracted exefs main (LZ4) into a flat memory image; pchtxt addresses with `offset_shift 0x100` are image offsets |
| `xref.py` | Finds every float value in the data sections and the code (ADRP + load) that reads a given address |
| `ghidra/DecompileAt.java` | Headless Ghidra script that decompiles just the functions containing given addresses, without a full analysis |
| `byml.py` | Reads BYML/BGYML level and stage data (zstd `.zs` too); `--grep` searches the dump |
| `bymlpatch.py` | Edits one BYML value in place at the same size and recompresses the file |
| `gen_zoom_v2.py` | Generates the camera patch: per-area base and Δ, the boss-room table and caves A to H; asserts the Δ limit |
| `verify_pchtxt.py` | Disassembles every enabled line of a `.pchtxt` |

To adapt them to another game: change the archive file pattern in `lyt.py` (`*.blarc.zs`), set `ROOT_SY` in `build.py` to the new root scale, empty its curated tables, and rerun `find_toplevel.py`. `build.py` implements the narrower-than-16:9 (Y axis) case; a wider target needs the X-axis mirror of the shift and fill steps.

**Working from bug reports.** Turn each reported symptom into a mechanism before changing anything (the Common bugs table is the index), investigate the areas in parallel, write the plan to a file and have a second model audit it, then implement, run both checkers and install. Keep one mod folder, with optional variants in a separate extras folder, and leave the shipped code patch untouched unless a layout cannot solve the problem. Say which fixes are confirmed in-game and which are not. Disassembling the executable settles questions the layout files cannot, such as how a capture rectangle is sized; decompile only the functions you need.

**Extracting the executable and game data.** Use nstool with the console's `prod.keys`. Extract the update `.nsp`, then extract partition 0 of its program NCA with `--tik <update ticket>` to get `exefs/main`. For RomFS (layouts, level data, event scripts), add `--basenca <base program NCA>` and extract partition 1, for example `-x /1/Stage <out>`. nstool reads title keys from `%USERPROFILE%\.switch\title.keys`; a base game's key can be added from its ticket (encrypted title key at offset 0x180, rights ID at 0x2A0). Run Ghidra headless (Java 21) with `ghidra/DecompileAt.java` to decompile only the functions you need, after importing the flat image as raw AArch64 at base 0. SMBW reference: stage labels in `Stage/StageParam/*.bgyml` name each course, and `BancMapUnit/*.bcett.byml.zs` holds each room's actors, including `CameraArea` sizes.

## Reference example: Super Mario Bros. Wonder at 4:3

Everything in this section is specific to one game and serves as a reference for applying the method to others. This method produced a 4:3 mod for Super Mario Bros. Wonder (title ID 010015100B514000) that was confirmed working in-game on Eden. The starting point was an AnyAspectRatio (won-aar) mod whose only layout change was root scale Y = 0.75. Its code patch was hard-coded to 2.3889 (3440×1440) and targeted only 1.0.1.

| Version | Build ID | Aspect constant | 4:3 line |
| --- | --- | --- | --- |
| 1.0.1 | `F91868B88F60D3D59009DB3389FDE314A6A32FCD` | `029B5108` | `029B5108 ABAAAA3F` |
| 1.2.1 | `FF773E90972D544EB79406EAA65396D53C43EFB9` | `02AEEDB4` | `02AEEDB4 ABAAAA3F` |

The current 1.2.1 patch (`exefs/1.2.1.pchtxt`, 266 lines, `offset_shift 0x100`, generated by `gen_zoom_v2.py`) contains:

- the aspect constant at `02AEEDB4`;
- the four hard-coded width constants set to 4:3: `02AEE9E8` (27.5556 → 20.6667), its half `02AEE968` and the negative copies `02AEE834` and `02AEEBD8`;
- the level-loader exception: hook `00136A80` → cave `02138780`, which keeps 27.5556 for camera areas authored one screen wide;
- cave A at `02138800`, hooked from the reach-rule site `006C66DC`: picks the area's base view height and Δ (boss table at `02138E00` first, then area width: under 60 → 15.5 and 3.4444, otherwise 15.75 and 3.2778), writes them to the mailbox words `037D1F00` and `037D1F18`, and applies the 16:9 reach rule;
- cave B at `02138900`, hooked from the zoom instruction `002E2B30`: the stock `fmov s1, #15.5`, then `fmax` with the mailbox base;
- the camera-controller clamp: `006C6358` and `006C6364` → caves at `02138D00` and `02138D20`, which use the same base and scale the width constant by base ÷ 15.5;
- the boss-room table, all with Δ = 0: Course150\_Sub4 at 21.0; Course151\_Sub2, Course152\_Sub4 and Course153\_Sub3 at 20.6667;
- the arena pipes' display box held at its authored size in zoomed rooms: caves `02138B00` (hook `00833B00`, the per-frame update) and `02138C00` (hook `005E428C`, the initialiser);
- autoscrolls and other fixed-position cameras: hook `006C6FD0` → cave G at `02138A00`;
- `StopScroll` screen locks: hook `006C7BEC` → cave H at `02138F00`.

Optional lines stay commented out after `@stop`: a camera zone-lock disable and fixed zoom-outs from 17 to 20 at `002E2B30`. Neither is needed. The mod supports 1.2.1 only; the 1.0.1 patch was dropped because its camera code was never analysed. Confirmed in-game on Eden: the Pipe-Rock Plateau badge house (Course500, one 27.5-wide `CameraArea` with doors at x ±13.5), the palace arena, the 15.75 base in Outmaway Valley, the airship autoscroll and its Wonder Flower (Course101), and the Puffy Lifts Wonder seed (Course021). Workarounds that turned out unnecessary once the one-screen-room fix was in (a camera hold flag, the focus target, the demo-camera override, fixed half-widths) were removed.

- 235 layout archives in 1.2.1 (`romfs/Layout/*.Nin_NX_NVN.blarc.zs`): 115 top-level, 120 parts. The build changes 115 of them (638 float writes, 46 fill panes, every check passing) and ships only those.
- Manual decisions: 4 force-shifts (item stock, race timer, a top-right button, an intro badge), 5 subtrees left in place (pause-menu right column, controls page, options list, collection list, a screenshot flash), 5 whole layouts not shifted (animated or art-bound screens, including the grand map), 2 pivots split (shop, course list).
- The game version mismatch (player on 1.2.1, patch for 1.0.1) produced exactly the tall-and-thin 3D symptom described in Step 1. Note that captured backgrounds, such as the pause-menu blur, show the same distortion while the 3D patch isn't applied, because they are pictures of the 3D view.
- Filling the capture panes made the pause and menu backgrounds show the world as a squeezed 16:9 band with streaks above and below. Leaving the 16 capture sources at 1080 fixed it. The world-map course-entry iris (`WipeCourseIn`) then came out taller than wide, and squashing the circle by 0.75 overshot to wider than tall. That one capture stays filled, with its use pane cropped to V 0.125–0.875. Several transitions use different wipe layouts (`Wipe`, `WipeCourseIn`, `WipeMiss`, `WipeWonder`), so confirm which one a report means first. The kept-fill capture still copies 180 rows past each frame edge. It is the remaining suspect for intermittent flashing bars reported on an Android emulator; the PC build has not shown them.

**Bowser Jr. rooms.** A scan of every map unit for boss actors finds four Bowser Jr. rooms, all in the zoom table with Δ = 0. The base is the 16:9 frame width ÷ 4/3; a room's own zoom actor multiplies it (Zooming only one room). Only the first row has been played.

| Room | Area hash | Camera lock | Stock frame | Base in patch | Status |
| --- | --- | --- | --- | --- | --- |
| Course150\_Sub4 (World 1 palace) | 607466214 | stop-scroll, side and vertical; area 70×25 | 27.56×15.5 | 21.0 | tested; also needs the pipe box hooks; recheck since Δ became 0 |
| Course151\_Sub2 | 101336182 | stop-scroll, side only; area 37.5 wide | 27.56×15.5 | 20.67 | in patch, untested; no pop-up pipes placed |
| Course152\_Sub4 | 1778226157 | stop-scroll, side only; area 31.1×17.5; zoom actor 17.5 | 31.1×17.5 | 20.67 (× 17.5/15.5 from its actor) | in patch, untested |
| Course153\_Sub3 | 1019598315 | stop-scroll, side only; area 34.5 wide | 27.56×15.5 | 20.67 | in patch, untested |

Still to check in the three new rooms: about 2.6 to 2.9 extra blocks show above and below, and an alternate zoom path (taken when `subject+0x1BE` is set) bypasses the base hooks. The last boss (Course290\_Main) and the airship boss rooms (Course100\_Sub4, Course101, Course102\_Sub2) use scrolling or scripted cameras and were not assessed beyond the autoscroll fix. Before adding a room, check whether its actors use screen-anchored scripts like the pipes above.

**Autoscroll and screen-lock coverage.** A scan of all map units finds autoscrolls in 22 courses and side-only screen locks in 22. Both fixes live in code, so they apply to all of them. Two were played: the World 2 airship (Course101, the Wonder Flower during the autoscroll) and Up 'n' Down with Puffy Lifts (Course021, a Wonder seed just outside the 4:3 view of a locked shaft). Course file numbers do not match in-game world numbers, so identify a level by its stage label.

## Second reference: The Legend of Zelda: Breath of the Wild at 4:3

BOTW 1.6.0 (title ID 01007EF00011E000) on an Eden-family emulator at 4:3, built with the same method over several rounds of in-game feedback. Its layouts are 1280×720 and the game overwrites the root scale, so the build scales the children of RootPane instead (see the root-scale note under Coordinate model). Confirmed in-game by the player: D-pad weapon windows including their edge masks, cursor corners, Link in menus, pause-menu bars, loading screens, title art and glow, and the Sheikah map edge. Left alone: the 3D code patch (the existing 1.6.0 aspect patch was kept as the stock option; an exact-4/3 variant was added later, see below), the dungeon map, tool screen and credits (they share the shrunk-capture-source pattern but nothing was reported), and a missing menu arrow whose cause is unexplained. HUD pieces placed by code at runtime cannot be fixed from layouts.

**Exact 4/3 patch.** The stock 1.6.0 patch writes `fmov s0, #1.3125` at three sites (1.56% under 4/3); another community patch writes `#1.375` (3.125% over). `fmov` cannot encode 4/3, so the exact variant replaces each instruction with an `LDR S0` of a literal `ABAAAA3F` (1.3333334) planted in zero padding after a nearby `ret`, and was confirmed running in the emulator. Both patches rewrite the same three addresses, so only one can be active in a mod.

**An aspect patch alone is not a 4:3 mod.** With only the code patch, the 3D view is correct but the HUD is laid out for 1280×720 and stretched: the minimap measured about 152 px wide by 202 px tall at the same window height where 16:9 gives a 204 px circle. The layout work is what restores round gauges, undistorted icons and the menu fixes above.

**Game code reads scale on list containers.** In the pause menu, the Adventure Log → Memories list drew row 6 on top of row 5 at 4:3 only. The cause was the 0.75 root-child scale on one container (and the part it holds) whose scale the list code reads. Moving the 0.75 onto its child, or into the part's own layout, did not help; leaving that subtree at stock scale, position and size did. Page containers that the code rewrites still take the factor on their children, but a pane the list code reads has to stay stock, at the cost of that page not being squeezed. A check that the pane stays at stock guards it.

**Find in-game bugs by reverting layouts in halves.** When the cause is unknown, ship test mods that contain only the changed archive, with every layout in a group left at stock, and let the player test one at a time: all pause layouts stock, then half, then single layouts, then single panes. Each answer halves the search; this one took eight rounds. Keep the code patch fixed while testing, and give each test its own throwaway folder in the emulator's load directory, deleted afterwards.

**Rule out the emulator before blaming the mod.** Read the status bar of every screenshot before comparing: resolution scale, post-processing, and the list's scroll position all differed between runs that looked like a clean/broken split. Here scale, FX and the shader cache were not the cause; an earlier "clean" result had been taken with a different state than the broken one.

**Matching 16:9 pixel size.** Keeping the 1280-unit width and squeezing height by 0.75 makes every UI element 75% of its 16:9 pixel size at the same window height, which is small on a handheld. To restore it, scale HUD groups by 1/0.75 about their screen corner: new position = anchor + 1.333 × (position − anchor), scale × 1.333, and the same on every TransX, TransY and scale animation key (slopes × 1.333). Run it after the edge shift and the root-child pass; for edge-anchored panes the result lands back on the stock 16:9 values. Skip panes whose scale or translation the game code writes, and leave screen-capture panes alone. Measured in-game, the hearts went from about 55 px to about 70 px wide against 73 px on 16:9, with the same corner margin.

**Verify a derived pass against a baseline.** The enlargement pass is checked against a build of the same sources with it switched off, not against the stock layout, because earlier passes already moved those panes.

**Emulator add-on housekeeping.** The emulator tracks enabled mods by folder name and rewrites its config on launch and exit, so edits made while it runs are lost. Renaming a mod to a name that was disabled earlier can leave it disabled; have the player tick the add-on after any rename, and confirm which folder is actually active before testing. Eden also locks the mod's layout files while a game runs, so close it before copying a new build; code patches load only at game boot.

## Sources (SMBW reference)

- [fayaz12g/won-aar](https://github.com/fayaz12g/won-aar), the AnyAspectRatio generator for Super Mario Bros. Wonder (source of the hard-coded patch value and the "centre" UI mode).
- [32:9 Super Ultrawide (For v1.2.1)](https://gamebanana.com/mods/690034) on GameBanana: original 32:9 mod by Stevens, KeatonTheBot and Fl4sh_#9174, v1.2.1 port by KillswitchR6 (1.2.1 build ID and aspect-constant address).
- [Switch-Emulator-Ultrawide-FPS-Mods issue #233](https://github.com/Fl4sh9174/Switch-Emulator-Ultrawide-FPS-Mods/issues/233) (the 1.2.1 Stabilize FPS patch posted there confirms the same build ID).
- [Aspect Ratio Mods](https://gamebanana.com/mods/474766) on GameBanana by Stevens with KeatonTheBot and Fl4sh_#9174 (4:3 to 48:9 patches for 1.0.0 and 1.0.1, including the camera zoom-out fix for narrow ratios).
