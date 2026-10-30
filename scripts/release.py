"""Check, package and release a game's mod. Stdlib only (runs on the CI runner's Python 3.12 too).

usage:
  python scripts/release.py check   <game> <version>     checks only (game = tag prefix, e.g. smbw)
  python scripts/release.py package <game> <version>     checks + dist/<zip> + dist/notes.md, built from HEAD
  python scripts/release.py publish <game> <version>     tag HEAD and push it, wait for the workflow's release,
                                                         then commit and push the README Download links
  python scripts/release.py links   <game> <version>     only the last step (if publish stopped waiting)
  python scripts/release.py ci <tag>                     used by .github/workflows/release.yml

The Download links change only after the release and its zip exist, so a failed workflow never leaves a dead link.
A version with a suffix (1.1.0-rc.1) is a pre-release: the links are left alone.
"""
import io, json, os, re, shutil, subprocess, sys, tarfile, time, zipfile

import check_repo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(ROOT, '.github', 'release-games.json'), encoding='utf-8'))
REPO = CONFIG['repo']
SEMVER = re.compile(r'^(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.-]+)?$')
DIST = os.path.join(ROOT, 'dist')


class ReleaseError(Exception):
    pass


def git(*args, check=True):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    if check and r.returncode:
        raise ReleaseError(f"git {' '.join(args)} failed: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout


def game_cfg(game):
    if game not in CONFIG['games']:
        raise ReleaseError(f"unknown game '{game}'; known: {', '.join(CONFIG['games'])}")
    return CONFIG['games'][game]


def names(game, version):
    g = game_cfg(game)
    tag = f'{game}-v{version}'
    zip_name = f"{g['zip_stem']}-v{version}-for-game-{g['game_version']}.zip"
    url = f'https://github.com/{REPO}/releases/download/{tag}/{zip_name}'
    title = f"{g['name']} 4:3 v{version} (for game v{g['game_version']})"
    return tag, zip_name, url, title


def is_prerelease(version):
    return SEMVER.match(version).group(4) is not None


def changelog_section(game, version):
    """Notes for v<version>; a pre-release may use its base version's section."""
    g = game_cfg(game)
    path = os.path.join(ROOT, g['folder'], 'CHANGELOG.md')
    text = git('show', f"HEAD:{g['folder']}/CHANGELOG.md", check=False).decode('utf-8') or \
        (open(path, encoding='utf-8').read() if os.path.exists(path) else '')
    base = version.split('-')[0]
    for v in ([version, base] if is_prerelease(version) else [version]):
        m = re.search(rf'^## v{re.escape(v)}\b.*?\n(.*?)(?=^## |\Z)', text, re.M | re.S)
        if m:
            return m.group(1).strip()
    raise ReleaseError(f"{g['folder']}/CHANGELOG.md has no '## v{version}' section")


def mod_files(game):
    """{path inside the mod folder: bytes} for the mod folder as committed at HEAD."""
    g = game_cfg(game)
    prefix = f"{g['folder']}/mod/{g['mod_folder']}/"
    raw = git('archive', '--format=tar', 'HEAD', prefix)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as t:
        for m in t.getmembers():
            if m.isfile():
                files[m.name[len(prefix):]] = t.extractfile(m).read()
    if not files:
        raise ReleaseError(f'nothing committed under {prefix}')
    return files


def check(game, version):
    g = game_cfg(game)
    if not SEMVER.match(version):
        raise ReleaseError(f"version '{version}' is not SemVer (e.g. 1.0.0 or 1.1.0-rc.1), no leading v")
    changelog_section(game, version)
    files = mod_files(game)
    problems = []
    for p in files:
        if not (re.fullmatch(r'exefs/[^/]+\.pchtxt', p) or p.startswith('romfs/') or p == 'README.txt'):
            problems.append(f'not allowed in a release: {p}')
    romfs = [p for p in files if p.startswith('romfs/')]
    if len(romfs) != g['layout_count']:
        problems.append(f"romfs has {len(romfs)} files, expected {g['layout_count']}")
    patches = [p for p in files if p.startswith('exefs/')]
    if not patches:
        problems.append('no exefs/*.pchtxt')
    for p in patches:
        first = files[p].decode('utf-8', errors='replace').lstrip('﻿').splitlines()[0].strip()
        if first.upper() != f"@NSOBID-{g['build_id']}".upper():
            problems.append(f"{p}: first line is '{first}', expected @nsobid-{g['build_id']}")
    readme = files.get('README.txt', b'').decode('utf-8', errors='replace')
    if not readme:
        problems.append('README.txt missing')
    elif g['game_version'] not in readme:
        problems.append(f"README.txt doesn't mention game version {g['game_version']}")
    problems += check_repo.problems()
    if problems:
        raise ReleaseError('checks failed:\n  ' + '\n  '.join(problems))
    return files


def render_notes(game, version):
    g = game_cfg(game)
    tag, zip_name, url, title = names(game, version)
    readme = f"https://github.com/{REPO}/blob/{tag}/{g['folder']}/README.md#install"
    return f"""## Download

Download **[{zip_name}]({url})** from the Assets list below. (Not "Source code": that's the whole repo, not the mod.)

## Install

Requires game version **{g['game_version']}**. Turn off any other aspect-ratio mod for this game and remove older versions of this one first. Then follow the [install steps]({readme}) for Windows or Android: import the zip (Windows) or install the extracted **{g['mod_folder']}** folder (Android), make sure the add-on is ticked, and set this game's aspect ratio to 4:3.

## What's new

{changelog_section(game, version)}

---
If you like this mod, you can support it on [Ko-fi](https://ko-fi.com/pyrodonkey).
"""


def package(game, version, out=DIST):
    g = game_cfg(game)
    if git('status', '--porcelain').strip():
        print('warning: uncommitted changes; the zip is built from HEAD and does not include them')
    files = check(game, version)
    tag, zip_name, url, title = names(game, version)
    os.makedirs(out, exist_ok=True)
    stamp = int(git('log', '-1', '--format=%ct', 'HEAD').decode().strip())
    date_time = time.gmtime(stamp)[:6]
    path = os.path.join(out, zip_name)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(files):
            info = zipfile.ZipInfo(f"{g['mod_folder']}/{p}", date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, files[p])
    with open(os.path.join(out, 'notes.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(render_notes(game, version))
    with open(os.path.join(out, 'title.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(title)
    print(f'packaged {path} ({os.path.getsize(path) / 1e6:.1f} MB, {len(files)} files)')
    return path


def update_links(game, version):
    """Rewrite the one-line <!-- download:<game> --> markers in the root and game READMEs."""
    g = game_cfg(game)
    tag, zip_name, url, title = names(game, version)
    releases = f'https://github.com/{REPO}/releases'
    content = {
        'README.md': f'[Download v{version}]({url})',
        f"{g['folder']}/README.md": f"**[Download v{version} (for game v{g['game_version']})]({url})** · [All releases]({releases})",
    }
    for rel, text in content.items():
        path = os.path.join(ROOT, rel)
        src = open(path, encoding='utf-8').read()
        pat = re.compile(rf'(<!-- download:{re.escape(game)} -->).*?(<!-- /download:{re.escape(game)} -->)')
        if not pat.search(src):
            raise ReleaseError(f'{rel}: no <!-- download:{game} --> marker')
        new = pat.sub(lambda m: m.group(1) + text + m.group(2), src)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new)
    return list(content)


def require_clean_main():
    if git('status', '--porcelain').strip():
        raise ReleaseError('working tree has uncommitted changes; commit or stash them first')
    branch = git('rev-parse', '--abbrev-ref', 'HEAD').decode().strip()
    if branch != 'main':
        raise ReleaseError(f"releases are made from main (you're on {branch})")
    git('fetch', 'origin', 'main', '--tags')
    if git('rev-list', '--count', 'HEAD..origin/main').decode().strip() != '0':
        raise ReleaseError('main is behind origin/main; pull first')


def gh():
    for exe in (shutil.which('gh'), r'C:\Program Files\GitHub CLI\gh.exe'):
        if exe and os.path.exists(exe):
            return exe
    raise ReleaseError('GitHub CLI (gh) not found; install it and run `gh auth login`')


def wait_for_release(tag, zip_name, timeout=1200):
    """Poll GitHub until the workflow has published <tag> with <zip_name> attached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run([gh(), 'release', 'view', tag, '--repo', REPO, '--json', 'assets,isDraft'],
                           capture_output=True, text=True)
        if r.returncode == 0:
            info = json.loads(r.stdout)
            if not info['isDraft'] and any(a['name'] == zip_name for a in info['assets']):
                return
        time.sleep(15)
    raise ReleaseError(f'no published release {tag} with {zip_name} after {timeout // 60} min. Check the Actions tab; '
                       f'once the release exists, run: python scripts/release.py links {tag.split("-v")[0]} '
                       f'{tag.split("-v", 1)[1]}')


def links(game, version):
    """Point the README Download links at a published release, commit and push."""
    tag, zip_name, url, title = names(game, version)
    require_clean_main()
    changed = update_links(game, version)
    if not git('status', '--porcelain').strip():
        print('Download links already point at this release')
        return
    git('add', *changed)
    git('commit', '-m', f'Point Download links at {game} v{version}')
    git('push', 'origin', 'main')
    print(f'Download links updated: {url}')


def publish(game, version):
    tag, zip_name, url, title = names(game, version)
    require_clean_main()
    if git('tag', '--list', tag).strip() or git('ls-remote', '--tags', 'origin', f'refs/tags/{tag}').strip():
        raise ReleaseError(f'tag {tag} already exists')
    package(game, version)
    git('tag', '-a', tag, '-m', title)
    git('push', '--atomic', 'origin', 'main', tag)
    print(f'pushed {tag}; waiting for GitHub Actions to publish https://github.com/{REPO}/releases/tag/{tag}')
    wait_for_release(tag, zip_name)
    print('release published')
    if not is_prerelease(version):
        links(game, version)


def ci(tag, out=DIST):
    m = re.fullmatch(r'([a-z0-9]+)-v(.+)', tag)
    if not m:
        raise ReleaseError(f"tag '{tag}' is not <game>-v<version>")
    game, version = m.groups()
    package(game, version, out)
    if is_prerelease(version):
        open(os.path.join(out, 'prerelease'), 'w').close()


def main(argv):
    if len(argv) < 2 or argv[0] not in ('check', 'package', 'publish', 'links', 'ci'):
        sys.exit(__doc__)
    cmd = argv[0]
    try:
        if cmd == 'ci':
            ci(argv[1])
        elif len(argv) != 3:
            sys.exit(__doc__)
        elif cmd == 'check':
            check(argv[1], argv[2])
            print('checks passed')
        elif cmd == 'package':
            package(argv[1], argv[2])
        elif cmd == 'links':
            links(argv[1], argv[2])
        else:
            publish(argv[1], argv[2])
    except ReleaseError as e:
        sys.exit(f'error: {e}')


if __name__ == '__main__':
    main(sys.argv[1:])
