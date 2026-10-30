# Agent instructions: switch-4x3-mods

Native 4:3 aspect-ratio mods for Nintendo Switch games, one folder per game. "Native" means the 3D view renders at 4:3 and the UI is re-laid out for the 4:3 screen (HUD at the real edges, full-screen layers covering it), not stretched or letterboxed.

The method is documented in [`docs/aspect-ratio-guide.md`](docs/aspect-ratio-guide.md). Read its Overview and the section for the task at hand (code patch, camera, layouts, verification) before changing a mod. When a fix teaches something that applies beyond one game, add it to the guide (Common bugs table or the relevant rule) and keep game-specific details in that game's folder.

## Repo layout

```
docs/aspect-ratio-guide.md     General method (exefs patches, camera fixes, nn::ui2d layouts, verification)
docs/game-files-policy.md      What may be committed, how it's enforced, what to do if something leaks
scripts/release.py             Release checks, packaging and publishing (all games)
scripts/check_repo.py          Blocks game data, keys and decompiler dumps (pre-commit hook, release, CI)
.githooks/pre-commit           Runs check_repo.py on staged files (enable: git config core.hooksPath .githooks)
.claude/settings.json          Claude Code hooks: enable the git hook, deny commands that bypass it
.github/workflows/validate.yml Reports check_repo.py failures after a push (a tripwire, not protection)
.github/release-games.json     One entry per game: tag prefix, folders, game version, build ID, layout count
.github/workflows/release.yml  Publishes a GitHub release when a <prefix>-v<version> tag is pushed
<game-folder>/                 One per game, kebab-case English title (e.g. super-mario-bros-wonder)
  README.md                    Player-facing: Download link, install steps, what it changes, known limits
  CHANGELOG.md                 "## v<version>" sections; each becomes that release's notes
  AGENTS.md                    Agent-facing: current state (source of truth), build/verify commands, addresses, gotchas
  CLAUDE.md                    Just "@AGENTS.md"
  mod/<Mod Name>/              The installable mod folder exactly as players get it (exefs/, romfs/, README.txt)
  tools/                       Scripts that generate and check the mod
  docs/DEVELOPMENT.md          Dated log of how the mod got here
```

Games: [`super-mario-bros-wonder/`](super-mario-bros-wonder/) (1.2.1).

## Rules

- **Game files: follow [`docs/game-files-policy.md`](docs/game-files-policy.md).** In short: commit only archives the build changed, never dumps, keys, executables, extracted trees, Ghidra projects or unchanged game files. Never copy files from a workspace into the repo except a tool's build output into `<game>/mod/`.
- **Never bypass the pre-commit check** (`--no-verify`, `git commit -n`, `git add -f`, changing `core.hooksPath`). If it blocks something, fix the cause. In a fresh clone, run `git config core.hooksPath .githooks` first.
- **Quote, don't dump:** never put key contents, whole decompiled functions, disassembly listings or data dumps into docs, commit messages, PR text or changelogs. Cite addresses and a few lines. Tool outputs holding original values (`build_report.json`, decompiler output) stay outside the repo.
- Sending excerpts of game code to outside AI services for review is the maintainer's call; never send game files or whole binaries.
- **No machine-specific paths** in scripts or docs. Scripts take paths as arguments or environment variables (e.g. `SMBW_MAIN_BIN`); docs use `%APPDATA%`, `<repo>` or placeholders.
- **The mod folder is generated output.** Change the generator (`tools/`), rebuild, run the verifiers, then commit tools and output together. Files that cannot be generated go in `tools/hand-edited/` and are copied over the build.
- **Each mod targets exact game builds.** A `.pchtxt` applies only when its `@nsobid` matches; say in the game's README which versions are supported.
- **Report test status honestly.** Separate "confirmed in game" from "built, not yet played" in READMEs, AGENTS.md and commit messages.
- Keep each game's `AGENTS.md` current-state section up to date in the same commit as the change; put the narrative in `docs/DEVELOPMENT.md`.

- **Player-facing text names no emulators** and never links to emulator downloads: say "Switch emulators on Windows and Android". Developer docs (AGENTS.md, DEVELOPMENT.md, the guide) may name the emulator used for testing.

## Checks

Run before committing a mod change and before every release:

```
python scripts/check_repo.py                       # game data / keys / dumps (also the pre-commit hook)
python scripts/release.py check <prefix> <version> # release rules: changelog, build ID, allowlist, archive count
# plus the game's own verifiers, listed in its AGENTS.md (SMBW: tools/verify.py and tools/verify_pchtxt.py)
```

`scripts/` needs only Python 3.8+ (CI uses the runner's 3.12). Game tools may need more (SMBW: Python 3.14 plus `capstone` and `lz4`).

## Releasing

Players get mods only through GitHub Releases: one zip per game version, linked from the READMEs. `gh` must be installed and signed in.

1. Make the player docs true for this build: the game README's Known limits ("played and checked" vs "not yet played") and the `## v<version>` section of `<game-folder>/CHANGELOG.md` (it becomes the release notes). Commit everything and push.
2. `python scripts/release.py package <prefix> <version>` builds `dist/<zip>` and `dist/notes.md` from HEAD. The tester installs that zip, following only the README's Install section, before any mod change is released.
3. `python scripts/release.py publish <prefix> <version>`: re-checks, tags HEAD `<prefix>-v<version>`, pushes, waits until the workflow has published the release with its zip (`--latest=false`, since "Latest" is repo-wide), then rewrites the `<!-- download:<prefix> -->` links in the root and game READMEs, commits and pushes them. The links never point at a zip that doesn't exist.
4. A suffixed version (`1.1.0-rc.1`) is a pre-release: the links are left alone.

If `publish` stops waiting (20 min): check the Actions tab.
- **Transient failure** (runner, network): re-run the job; then `python scripts/release.py links <prefix> <version>`.
- **Code or content failure**: a re-run uses the tagged commit's code, so it can't pick up a fix. No release exists yet, so delete the tag (`git push origin :refs/tags/<tag>` and `git tag -d <tag>`), fix on `main`, and publish again.

Never link to `releases/latest`. Bump the version for any change to the mod folder; never move or delete a tag that has a published release. The install steps exist in full only in the game README's `#install` section; `README.txt` (in the zip) and the release notes (`render_notes` in `scripts/release.py`) carry a short version and link to it, so update all three together.

## Testing loop

Only the human tester can play (the emulator is bound to a physical controller). Build and verify here, then sync the mod folder into the emulator's load directory with the game closed (layout files are locked while it runs; code patches load only at boot). Use a mirror copy (`robocopy <src> <dst> /MIR`) so archives the build no longer ships are deleted. For the Android handheld, give the tester the `release.py package` zip to install through the Add-ons menu. Ask the tester one clear question per round. Take screenshots of their screen only when they ask for one.

## Adding a game

1. Create `<game-folder>/` with the layout above; copy the README (with its `<!-- download:<prefix> -->` marker), CHANGELOG and AGENTS.md structure from Super Mario Bros. Wonder. Use a generic mod folder name (players see it in the emulator's add-on list; renaming after a release leaves them with two copies).
2. Set up its workspace outside the repo and extract the originals for the exact game version (never a third party's cached copies); list both in its AGENTS.md "Local inputs". See the checklist in `docs/game-files-policy.md`.
3. Follow the guide's Workflow and tools section: build ID, 3D patch, camera, layouts, verification. The build must write only changed archives and the verifier must fail on unchanged output.
4. Register it in `.github/release-games.json` under a short tag prefix (e.g. `botw`). The workflow needs no change.
5. Generalise shared tools only when a second game actually needs them; until then each game keeps its own `tools/`.
6. Add a row with its own download marker to the table in the root `README.md`, and add it to the list above.
