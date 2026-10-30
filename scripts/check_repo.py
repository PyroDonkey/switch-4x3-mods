"""Block original game data, keys and decompiler dumps from the repo. Stdlib only.

usage:
  python scripts/check_repo.py            check every tracked file (CI, release.py)
  python scripts/check_repo.py --staged   check what is staged for commit (.githooks/pre-commit)

Policy: see docs/game-files-policy.md. Binary files are allowed only where a mod ships them.
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY_OK = re.compile(r'^([^/]+/mod/[^/]+/romfs/'          # archives a mod overrides
                       r'|[^/]+/tools/hand-edited/'           # hand-edited archives the build copies in
                       r'|(?:[^/]+/)?docs/.+\.(?:png|jpe?g|webp)$)')
FORBIDDEN_EXT = ('.nsp', '.xci', '.nsz', '.xcz', '.nca', '.ncz', '.tik', '.cert', '.keys', '.nso', '.nro',
                 '.npdm', '.bin', '.sav', '.gpr', '.rep')
FORBIDDEN_NAME = {'main', 'rtld', 'sdk', 'prod.keys', 'title.keys', 'dev.keys'}
KEY_LINE = re.compile(rb'^\s*[A-Za-z0-9_]+\s*=\s*[0-9A-Fa-f]{32,}\s*$', re.M)
DECOMPILED = re.compile(rb'\b(?:[ui]Var\d+|undefined[1248]?\b|DAT_[0-9a-f]{6,}|FUN_[0-9a-f]{6,}\s*\()')
MAX_BYTES = 50 * 1024 * 1024
MAX_DECOMPILED_LINES = 20


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def files(staged):
    """(path, bytes) pairs to check."""
    if staged:
        for p in git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').decode().split('\0'):
            if p:
                yield p, git('show', f':{p}')
    else:
        for p in git('ls-files', '-z').decode().split('\0'):
            if p and os.path.isfile(os.path.join(ROOT, p)):
                yield p, open(os.path.join(ROOT, p), 'rb').read()


def is_binary(data):
    if b'\0' in data[:8192]:
        return True
    try:
        data.decode('utf-8')
        return False
    except UnicodeDecodeError:
        return True


def problems(staged=False):
    out = []
    for path, data in files(staged):
        name = os.path.basename(path).lower()
        if name in FORBIDDEN_NAME or name.endswith(FORBIDDEN_EXT) or '.rep/' in path.lower():
            out.append(f'{path}: game file, executable or key file type')
        elif len(data) > MAX_BYTES:
            out.append(f'{path}: {len(data) / 1e6:.0f} MB, over the 50 MB limit')
        elif is_binary(data):
            if not BINARY_OK.match(path):
                out.append(f'{path}: binary file outside a mod folder, tools/hand-edited or docs images')
        else:
            if KEY_LINE.search(data):
                out.append(f'{path}: contains a line that looks like a console key (name = long hex)')
            hits = sum(1 for line in data.splitlines() if DECOMPILED.search(line))
            if hits > MAX_DECOMPILED_LINES:
                out.append(f'{path}: {hits} lines of decompiler output; quote a few lines, not whole functions')
    return out


def main(argv):
    found = problems(staged='--staged' in argv)
    if found:
        print('Blocked: this would put game data, keys or decompiler dumps in the repo.')
        print('  ' + '\n  '.join(found))
        print('See docs/game-files-policy.md. Unstage the files (git restore --staged <path>) and keep them in your workspace.')
        sys.exit(1)
    print('check_repo: OK')


if __name__ == '__main__':
    main(sys.argv[1:])
