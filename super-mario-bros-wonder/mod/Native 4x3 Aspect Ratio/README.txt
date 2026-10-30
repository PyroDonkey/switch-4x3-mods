Native 4x3 Aspect Ratio
Super Mario Bros. Wonder (Title ID 010015100B514000), game version 1.2.1 only

Plays the game natively at 4:3 instead of stretching or letterboxing it. The
camera, level framing and the whole UI are adjusted so nothing is squashed.

Full install steps, updates and troubleshooting:
https://github.com/PyroDonkey/switch-4x3-mods/tree/main/super-mario-bros-wonder#install

INSTALL
Windows:
1. Right-click the game > Configure Game > Add-Ons > Import Mod from ZIP, and
   pick the downloaded zip. (No such button? Right-click the game > Open Mod
   Data Location, and drag this "Native 4x3 Aspect Ratio" folder in there.)
2. Make sure "Native 4x3 Aspect Ratio" is ticked in Add-Ons.
3. In the same window: Graphics > Aspect Ratio > Force 4:3. Start the game.
Android:
1. Extract the zip. Long-press the game > Add-ons > Install, and select this
   "Native 4x3 Aspect Ratio" folder itself (the one containing exefs and romfs).
2. Set this game's aspect ratio to 4:3. Start the game.
Updating on Android: uninstall the old version in Add-ons first.
The patch is keyed to the 1.2.1 build ID; other game versions are not supported
and show a squashed 3D picture.

WHAT IT CHANGES
- exefs/1.2.1.pchtxt  Aspect ratio 16:9 -> 4:3, plus camera fixes:
    * one-screen rooms keep their full 16:9 framing
    * autoscrolls move exactly like stock (you can't outrun them); once a
      scroll stops, the camera can pan inside the original 16:9 frame
    * screen-locked rooms and shafts let the camera pan inside the original
      16:9 frame, so items at their edges stay reachable
    * per-area view height: houses, shops and small rooms use the stock height;
      wide levels are shown slightly wider than stock (base height 15.75)
    * Bowser Jr. arenas (Courses 150-153) are zoomed out so the whole room is
      visible, with Pipe-Rock Plateau Palace's ceiling pipes kept in place
- romfs/Layout/*      115 re-laid-out UI archives (HUD, menus, pause screen,
                      title, map, wipes/transitions), including the pause/menu
                      background and course-entry iris fixes, a 4:3 course-clear
                      photo (and a centred "View photo"), the menu pointer on
                      the right spot, and round badges behind the Badge
                      Challenge restart wipe

KNOWN LIMITS
- Tested on Switch emulators on Windows and Android (Retroid Pocket Nova).
- Tested: Pipe-Rock Plateau Palace boss, badge houses, W2 Outmaway Valley, the
  W2 airship autoscroll and its Wonder Flower, Up 'n' Down with Puffy Lifts,
  the world and kingdom maps, course list, pause menu and level transitions,
  the in-level HUD, button glyphs (X/L/R/+), Poplin shop, user select and
  player count menus, main-menu pointer, course-clear photo and View photo,
  Badge Challenge restart wipe. UI proportions were checked against the
  unmodded 16:9 game.
- Photos taken before installing the mod are 16:9 and will look squeezed in
  the 4:3 photo frame until a new course is cleared.
- Not yet played: the other Bowser Jr. rooms (Courses 151-153, zoomed but
  untested), the airship boss rooms and the final boss.
- Wide levels show a little more than stock (about 76% of the 16:9 width vs 75%);
  a bigger zoom reveals empty space above art painted for the stock view, so it
  is kept small.
- Some levels (pits, level edges, Wonder zooms) were not checked at the final
  zoom. Please report anything that looks cut off.

CREDITS
- Aspect-ratio address from the 32:9 Super Ultrawide mod (original by Stevens,
  KeatonTheBot and Fl4sh_#9174; v1.2.1 port by KillswitchR6).
- Camera fixes, zoom hooks and UI layouts by PyroDonkey, found by analysing
  the 1.2.1 executable and layouts.
