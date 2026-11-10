# Super Mario Bros. Wonder: Native 4:3

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/pyrodonkey)

Plays Super Mario Bros. Wonder natively at 4:3 instead of stretching or letterboxing it. The camera, level framing and the whole UI are adjusted so nothing is squashed.

<!-- download:smbw -->**[Download v1.1.2 (for game v1.2.1)](https://github.com/PyroDonkey/switch-4x3-mods/releases/download/smbw-v1.1.2/SMBW-4x3-Native-v1.1.2-for-game-1.2.1.zip)** · [All releases](https://github.com/PyroDonkey/switch-4x3-mods/releases)<!-- /download:smbw -->

Requires **game version 1.2.1**. Tested on Switch emulators on Windows and Android (Retroid Pocket Nova). Other versions of the game are not supported.

## Install

This is the install guide for this mod; the release page, the `README.txt` in the zip and the main page all link here. The menu names below are the ones used by the emulators this was tested on; other emulators may label them differently.

### Before you start

1. **Check your game version.** The game must be updated to **v1.2.1**. Your emulator shows the installed update in the game list (often an Add-ons or Version column) or in the game's properties. Other versions get a squashed 3D picture.
2. **Turn off other aspect-ratio mods** for this game (for example a 32:9 / ultrawide mod or an AnyAspectRatio mod). Two of them at once conflict.
3. **Remove older versions of this mod**, including test builds named "Nova Aspect Ratio 4x3 Native". A different folder name counts as a separate mod, and old files left behind can override new ones.
4. **Close the game** before installing; mod files are only read when the game starts.
5. On the release page, download the `.zip` under **Assets**, not "Source code" (that's the whole repo).

### Windows

1. Right-click Super Mario Bros. Wonder > **Configure Game** > **Add-Ons** > **Import Mod from ZIP**, pick the downloaded zip and confirm.
2. Make sure **Native 4x3 Aspect Ratio** is ticked in the Add-Ons list.
3. In the same Configure Game window, go to **Graphics** > Aspect Ratio and choose **Force 4:3**. This changes only this game.
4. Start the game.

- **No "Import Mod from ZIP" button?** Right-click the game > **Open Mod Data Location**, open the zip, and drag the **Native 4x3 Aspect Ratio** folder into that window.
- **Updating:** remove the old version from Add-Ons first, then import the new zip.

### Android (e.g. Retroid Pocket Nova)

1. Extract the zip with your file manager.
2. Long-press Super Mario Bros. Wonder > **Add-ons** > **Install**. Open the extracted files and select the **Native 4x3 Aspect Ratio** folder itself (the one with `exefs` and `romfs` inside), then tap **Use this folder** and **Allow**.
3. Make sure the add-on is ticked.
4. In this game's own settings, set the aspect ratio to **4:3**.
5. Start the game.

- **Updating:** uninstall the old version in Add-ons first, then install the new folder.

### Troubleshooting

| What you see | Fix |
| --- | --- |
| 3D looks tall and thin, UI looks fine | Wrong game version: update the game to v1.2.1 |
| Nothing changed | The add-on is unticked, the wrong folder was picked (Android: pick the folder that contains `exefs` and `romfs`), or the game was running during install |
| Everything is still stretched, or black bars at the sides | The game's aspect ratio isn't set to 4:3 |
| Parts of the screen look wrong in a way that changes with another mod on | Another aspect-ratio mod is still enabled: turn it off |

Still stuck? [Open an issue](https://github.com/PyroDonkey/switch-4x3-mods/issues/new/choose) with your game version, device and a screenshot.

## What it changes

**`exefs/1.2.1.pchtxt`**: aspect ratio 16:9 to 4:3, plus camera fixes.

- One-screen rooms keep their full 16:9 framing.
- Autoscrolls move exactly like stock, so you can't outrun them. The camera stays locked during mid-scroll pauses (such as musical breaks); once a scroll reaches its final stop, the camera can pan inside the original 16:9 frame to reach items at the edge.
- Screen-locked rooms and shafts let the camera pan inside the original 16:9 frame, so items at their edges stay reachable.
- View height per area: houses, shops and small rooms use the stock height; wide levels are shown slightly wider than stock (base height 15.75).
- Bowser Jr. fights, the W2 Angry Spikes and Sinkin' Pipes Wonder area (`Course008_Sub2`), and fixed-room Break Time! courses — Pop Up, Hoppo! (`Course400`), Kick It, Outmaway! (`Course401`), Zip-Go-Round (`Course403`), Unreachable Treasure? (`Course404`), Watery Wonder Tokens (`Course407`), Floating Wonder Tokens (`Course408`), Wonder Token Tunes (`Course411`), Bouncy Tunes (`Course415`), and Trottin' Piranha Plants (`Course417`) — are framed so the full room width stays visible, with Pipe-Rock Plateau Palace's ceiling pipes kept in place.

**`romfs/Layout/*` and `romfs/BancMapUnit/*`**: the 115 UI archives the mod changes (HUD, menus, pause screen, title, map, wipes and transitions) plus 9 stage data files (`Course152_Sub4`, `Course400_Course`, `Course401_Course`, `Course403_Course`, `Course407_Course`, `Course408_Course`, `Course411_Course`, `Course415_Course`, `Course417_Course`) that adjust World 4 Bowser Jr.'s water tint plane and arena walls, reposition theater arches/pillars/backdrops in Wonder Token Tunes, Bouncy Tunes and Trottin' Piranha Plants, widen the floor cloud in Zip-Go-Round, adjust far-rock backdrop coverage in Watery Wonder Tokens, and move off-screen spawns in Pop Up, Hoppo!, Kick It, Outmaway! and Floating Wonder Tokens; the rest of the game uses its own files.

## Known limits

- Played and checked: Pipe-Rock Plateau Palace boss, badge houses, W2 Outmaway Valley (including the Wonder Seed landing on the knocked-over goal pole at the end of the Wonder), the W2 airship autoscroll and its Wonder Flower, Piranha Plants on Parade (Wonder Seed at autoscroll end, plus camera lock during mid-scroll singing pause), Up 'n' Down with Puffy Lifts, World 4 Bowser Jr. (underwater tint, fight camera, Royal Seed after the boss, Bowser Jr. swim AI, corner voids under the walls), Break Time! — Wonder Token Tunes, Kick It, Outmaway!, Unreachable Treasure?, Watery Wonder Tokens, and Floating Wonder Tokens, plus visual framing in Pop Up, Hoppo!, Zip-Go-Round, Bouncy Tunes, and Trottin' Piranha Plants; world and kingdom maps, course list, pause menu, level transitions, in-level HUD, button glyphs, Poplin shop, user select and player count menus, main-menu pointer, course-clear photo, Badge Challenge restart wipe, and the v1.2.1 rebuild of those UI screens (menus, HUD, pause, maps, transitions, course clear, cursor, amiibo).
- Break Time! follow-up checks still open: full gameplay/completion/retry checks in Pop Up, Hoppo! (Hoppo spawn drop and rebound sequence), Zip-Go-Round (token collection and moving rail sequence), Bouncy Tunes (moving-token sequence), and Trottin' Piranha Plants (enemy sequence and edge activation), plus completion/retry confirmation on Kick It, Outmaway!, Unreachable Treasure?, Watery Wonder Tokens, and Floating Wonder Tokens, and a current-build regression check on Wonder Token Tunes. W2 Angry Spikes and Sinkin' Pipes (`Course008_Sub2`) Wonder area zoom is built and verified, not yet play-tested.
- Not yet played: the other Bowser Jr. fights (zoomed but untested), the airship boss fights, the final boss, multiplayer, and some screen transitions (warp and slide wipes).
- The death-screen spotlight may look slightly oval.
- On some Android devices, bars may flash briefly when entering a level from the map; not seen on PC.
- Wide levels show a little more than stock (about 76% of the 16:9 width vs 75%). A bigger zoom reveals empty space above backdrops painted for the stock view, so it is kept small.
- Photos taken before installing the mod are 16:9 and look squeezed in the 4:3 photo frame until a new course is cleared.
- Some levels (pits, level edges, Wonder zooms) were not checked at the final zoom. Please open an issue if something looks cut off.

## Credits

- Aspect-ratio address from the [32:9 Super Ultrawide mod](https://gamebanana.com/mods/690034): original by Stevens, KeatonTheBot and Fl4sh_#9174, v1.2.1 port by KillswitchR6.
- Starting layouts from [won-aar](https://github.com/fayaz12g/won-aar) (AnyAspectRatio).
- Camera fixes, zoom hooks and UI layouts by PyroDonkey, from analysis of the 1.2.1 executable and layouts.

## For developers

| | |
| --- | --- |
| Title ID | `010015100B514000` |
| Build ID (1.2.1) | `FF773E90972D544EB79406EAA65396D53C43EFB9` |
| Mod folder | [`mod/Native 4x3 Aspect Ratio/`](mod/Native%204x3%20Aspect%20Ratio/) |
| Changelog | [`CHANGELOG.md`](CHANGELOG.md) |

The mod folder is generated by the scripts in [`tools/`](tools/) from the original layouts and the game executable, which you must dump from your own copy of the game. See [`AGENTS.md`](AGENTS.md) for build, verify and release commands, the current state and the addresses used, and [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for how each fix was found.
