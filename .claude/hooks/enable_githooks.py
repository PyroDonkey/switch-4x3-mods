"""SessionStart: point this repo's git at .githooks (pre-commit -> check_repo.py)."""
import os
import subprocess
from pathlib import Path


def repo_root():
    if os.environ.get('CLAUDE_PROJECT_DIR'):
        return Path(os.environ['CLAUDE_PROJECT_DIR'])
    p = Path.cwd().resolve()
    for _ in range(8):
        if (p / '.githooks' / 'pre-commit').is_file():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None


root = repo_root()
if root is not None:
    subprocess.run(['git', '-C', str(root), 'config', 'core.hooksPath', '.githooks'], check=False)
