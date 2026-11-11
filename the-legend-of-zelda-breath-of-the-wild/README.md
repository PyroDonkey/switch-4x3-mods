# The Legend of Zelda: Breath of the Wild: Native 4:3

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/pyrodonkey)

Plays Breath of the Wild natively at 4:3 instead of stretching or letterboxing it. The 3D view renders at 4:3, and the HUD, menus and Sheikah Slate map are re-laid out for the taller screen so nothing is squashed.

<!-- download:botw --><!-- /download:botw -->

Requires **game version 1.6.0**. Tested on Switch emulators on Windows, with both DLC packs installed. Other versions of the game are not supported.

## Install

This is the install guide for this mod; the release page, the `README.txt` in the zip and the main page all link here. The menu names below are the ones used by the emulators this was tested on; other emulators may label them differently.

### Before you start

1. **Check your game version.** The game must be updated to **v1.6.0**. Your emulator shows the installed update in the game list (often an Add-ons or Version column) or in the game's properties. Other versions get a squashed 3D picture.
2. **Turn off other aspect-ratio mods** for this game (for example an ultrawide or 21:9 mod, or another 4:3 patch). Two of them at once conflict.
3. **Remove older versions of this mod**, including test builds named "Nova Aspect Ratio 4x3 Native" or "Aspect Ratio 4x3 Native". A different folder name counts as a separate mod, and old files left behind can override new ones.
4. **Close the game** before installing; mod files are only read when the game starts.
5. On the release page, download the `.zip` under **Assets**, not "Source code" (that's the whole repo).

### Windows

1. Right-click The Legend of Zelda: Breath of the Wild > **Configure Game** > **Add-Ons** > **Import Mod from ZIP**, pick the downloaded zip and confirm.
2. Make sure **Native 4x3 Aspect Ratio** is ticked in the Add-Ons list.
3. In the same Configure Game window, go to **Graphics** > Aspect Ratio and choose **Force 4:3**. This changes only this game.
4. Start the game.

- **No "Import Mod from ZIP" button?** Right-click the game > **Open Mod Data Location**, open the zip, and drag the **Native 4x3 Aspect Ratio** folder into that window.
- **Updating:** remove the old version from Add-Ons first, then import the new zip.

### Android

1. Extract the zip with your file manager.
2. Long-press The Legend of Zelda: Breath of the Wild > **Add-ons** > **Install**. Open the extracted files and select the **Native 4x3 Aspect Ratio** folder itself (the one with `exefs` and `romfs` inside), then tap **Use this folder** and **Allow**.
3. Make sure the add-on is ticked.
4. In this game's own settings, set the aspect ratio to **4:3**.
5. Start the game.

- **Updating:** uninstall the old version in Add-ons first, then install the new folder.

### Troubleshooting

| What you see | Fix |
| --- | --- |
| 3D looks tall and thin, UI looks fine | Wrong game version: update the game to v1.6.0 |
| Nothing changed | The add-on is unticked, the wrong folder was picked (Android: pick the folder that contains `exefs` and `romfs`), or the game was running during install |
| Everything is still stretched, or black bars at the sides | The game's aspect ratio isn't set to 4:3 |
| Parts of the screen look wrong in a way that changes with another mod on | Another aspect-ratio mod is still enabled: turn it off |

Still stuck? [Open an issue](https://github.com/PyroDonkey/switch-4x3-mods/issues/new/choose) with your game version, device and a screenshot.

## What it changes

**`exefs/1.6.0.pchtxt`**: the 3D aspect ratio, 16:9 to exactly 4:3.

**`romfs/Pack/Bootup.pack`, `romfs/Pack/Title.pack`, `romfs/Layout/BootUp.sblarc`, `romfs/Layout/Horse.sblarc`**: the game's UI layouts, re-laid out for 4:3. These archives hold many screens each, so the whole archive is replaced; everything else comes from the game.

- HUD and menu elements sit at the real 4:3 screen edges, and full-screen layers (backgrounds, fades, the Sheikah Slate frame) cover the taller screen.
- Gameplay HUD pieces are shown at their 16:9 size: hearts, Divine Beast gauges, weapon and shield icons, sensor, noise meter, temperature and clock. The stamina wheel stays round.
- Adventure Log: quest text, the quest list and Memories have the correct shape.
- Sheikah Slate map: the terrain, place names and icons line up, and the marker pointing to Link appears only when he is off screen.
- Dialog boxes: the speaker's name plate sits on the box.

## Known limits

- Played and checked: D-pad weapon windows, menu cursors, Link in the inventory, pause-menu bars, loading screens, title screen art, the HUD at 16:9 size, the stamina wheel, the speaker's name plate on dialog boxes, Adventure Log (quest list, full quest descriptions, Memories list past the fifth row), and the Sheikah Slate map (terrain, place names, icons and the marker pointing to Link).
- Not yet played: scrolling far down a long quest list, a completed quest's CLEAR stamp, Memories preview pictures, shrine and Divine Beast maps, and the end credits.
- Some HUD pieces are drawn by the game's code rather than its layouts and keep their stock 4:3 size, for example the minimap circle.
- Please open an issue if something looks stretched, squashed or cut off.

## Credits

- Aspect-ratio instruction addresses from the community 1.6.0 aspect-ratio patch.
- Exact 4:3 code patch and UI layouts by PyroDonkey, from analysis of the 1.6.0 executable and layouts.

## For developers

| | |
| --- | --- |
| Title ID | `01007EF00011E000` |
| Build ID (1.6.0) | `8E9978D50BDD20B4C8395A106C27FFDE` |
| Mod folder | [`mod/Native 4x3 Aspect Ratio/`](mod/Native%204x3%20Aspect%20Ratio/) |
| Changelog | [`CHANGELOG.md`](CHANGELOG.md) |

The mod folder is generated by the scripts in [`tools/`](tools/) from the original layouts, which you must dump from your own copy of the game. See [`AGENTS.md`](AGENTS.md) for build and verify commands, the current state and the gotchas, and [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for how each fix was found.
