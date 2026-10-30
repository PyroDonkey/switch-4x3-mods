# Switch 4:3 Mods

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/pyrodonkey)

Native 4:3 aspect-ratio mods for Nintendo Switch games. "Native" means the game renders at 4:3 and its UI is re-laid out for the 4:3 screen, instead of a 16:9 picture stretched or letterboxed by the emulator: the 3D view is patched to 4:3, the camera still frames each room correctly, and HUD, menus and transitions fit the taller screen.

## Mods

| Game | Needs game version | Download | Install steps |
| --- | --- | --- | --- |
| Super Mario Bros. Wonder | 1.2.1 | <!-- download:smbw -->Coming soon<!-- /download:smbw --> | [Install](super-mario-bros-wonder/README.md#install) |

Tested on Switch emulators on Windows and Android (Retroid Pocket Nova). Each mod only works with the game version listed, so update your game first. Each game's page has the full install steps, known limits and troubleshooting.

## How the mods are made

[`docs/aspect-ratio-guide.md`](docs/aspect-ratio-guide.md) is a technical reference for building native aspect-ratio mods for Switch games: finding and patching the aspect constant, fixing camera logic, transforming nn::ui2d layouts (BFLYT/BFLAN), and verifying the result. It uses Super Mario Bros. Wonder and Breath of the Wild as worked examples, and the method applies to other ratios too.

This repo contains only modified files and the tools that produce them. It contains no game files or keys; you need your own dumped copy of the game to rebuild a mod.

## Thanks

- [Fayaz Shaikh (fayaz12g)](https://github.com/fayaz12g): [AnyAspectRatio](https://github.com/fayaz12g/won-aar) for Super Mario Bros. Wonder, the starting point for this project.
- [KillswitchR6](https://gamebanana.com/members/5605015): the [v1.2.1 port of the 32:9 Super Ultrawide mod](https://gamebanana.com/mods/690034), source of the 1.2.1 aspect-ratio address and build ID.
- [Stevens](https://gamebanana.com/members/2745830), [KeatonTheBot](https://gamebanana.com/members/2739690) and [Fl4sh_#9174](https://gamebanana.com/members/3083977): the original 32:9 mod and the [Aspect Ratio Mods](https://gamebanana.com/mods/474766) for Super Mario Bros. Wonder, whose camera approach for narrow ratios informed this one.

## License

The tools, documentation and code patches written for this repo are under the [MIT License](LICENSE). Game assets are not: the modified layout files are derived from Nintendo's game data and remain Nintendo's property. Nintendo Switch and Super Mario Bros. Wonder are trademarks of Nintendo; this project is not affiliated with or endorsed by Nintendo.
