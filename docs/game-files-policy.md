# Game files policy

This repo and its releases must never become a way to get Nintendo's game data. This page says what may go in, how it's enforced, and what to do if something slips. It applies to every game in the repo.

## The rules

1. **Ship only the archives a mod must override.** The emulator replaces whole files (LayeredFS), so a changed archive carries its unchanged contents with it; that is unavoidable. An archive the build didn't change must never be shipped or committed: the emulator uses the game's own copy.
2. **Nothing else from the game, ever:** dumps (NSP/XCI/NCA), keys, tickets, executables (`main`, NSO, NPDM, flat `.bin` images), extracted romfs/exefs trees, Ghidra projects, bulk dumps of game code or data.
3. **Quote, don't dump.** Docs, commit messages, PR text and changelogs (which become release notes) may cite addresses, single instructions, field names and values. Never paste whole decompiled functions, disassembly listings or data dumps.
4. **Game data lives in a workspace outside the repo.** Tools take its paths as arguments or environment variables. Keys stay in `%USERPROFILE%\.switch\`.

| May be committed | Never committed |
| --- | --- |
| Scripts, docs, configs, `.pchtxt` patches | Dumps, keys, tickets, certs, save files |
| Archives the build changed (`<game>/mod/*/romfs/`) | Unchanged game archives, even recompressed |
| Hand-edited archives (`<game>/tools/hand-edited/`) | Executables and flat images |
| Short excerpts in docs | Extracted trees, Ghidra projects, decompiler output, data dumps |
| Small comparison screenshots in `docs/` | Build reports holding original values (`build_report.json`) |

## How it's enforced

| Layer | What it does | Can it be skipped? |
| --- | --- | --- |
| `.gitignore` | Hides common game file types from `git add` | Yes (`git add -f`) |
| Build | `build.py` writes only archives it changed; `verify.py` fails if an output equals its original | Only by editing the tools |
| `scripts/check_repo.py` via `.githooks/pre-commit` | Blocks binaries outside mod folders, game file types, key-like lines, files over 50 MB, and decompiler dumps | Per clone: enable with `git config core.hooksPath .githooks` |
| `.claude/settings.json` | Claude Code sessions in this repo enable the hook automatically and are denied `--no-verify`, `git commit -n`, `git add -f` and hooks-path changes | Only by editing the settings |
| `release.py check` | Runs the same checker plus the zip allowlist before every release | No |
| `.github/workflows/validate.yml` | Reports problems within a minute of a push | It only reports; a pushed file is already on GitHub |

In a fresh clone, run `git config core.hooksPath .githooks` before the first commit (Claude Code sessions do this for you).

## Before the repo goes public

Check that history holds only allowed content (`git rev-list --objects --all`). If it doesn't, and the repo has no forks or releases yet, replace history with a single fresh commit of the clean tree and force-push.

A force-push is not enough on its own: GitHub keeps replaced commits reachable by their hash. **This repo's history was replaced on 2026-10-30 and the old commits (holding unchanged game files) are still reachable that way.** So, on the day the repo goes public:

1. Make sure the local clone is up to date and `python scripts/check_repo.py` passes.
2. Delete the GitHub repo (`gh auth refresh -s delete_repo`, then `gh repo delete PyroDonkey/switch-4x3-mods`).
3. Create it again with the same name, description and topics, push `main`, and re-add the topics and settings (wiki and Projects off).
4. Make it public, then publish the first release.

## If something leaks

- **Not pushed:** amend or reset the commit.
- **Pushed, repo still private and small:** rebuild history as a single fresh commit and force-push. Otherwise use `git filter-repo --sensitive-data-removal --invert-paths --path <every past path of the file>` (filter-repo 2.47+), rewrite affected tags, force-push, and delete affected release assets and Actions runs.
- **Repo public or release published:** assume it was copied. Do the cleanup above; for a small repo, deleting and recreating it is often simpler. Pull-request refs and forks can only be removed by GitHub Support, which may decline for non-secret data. Keys can't be revoked.
- Reference: GitHub Docs, "Removing sensitive data from a repository".

## New game checklist

1. Create a workspace folder outside the repo (`<workspace>/<game-folder>/{dumps,extracted,originals,ghidra,scratch}`) and list it in the game's AGENTS.md "Local inputs" table.
2. Extract the originals for the exact game version you target; build against them, not a third party's cached copies.
3. Make the build write only changed archives and the verifier fail on unchanged output.
4. Make sure `check_repo.py` passes before the first commit (the hook enforces it).
