"""PreToolUse hook: deny shell commands that would skip or disable the repo's pre-commit check.

The pre-commit hook (.githooks/pre-commit -> scripts/check_repo.py) keeps game files and keys out of git;
see docs/game-files-policy.md. Reads the tool call as JSON on stdin. Commands are split into git invocations and
read as tokens, so text inside a commit message never triggers it.
"""
import json, re, shlex, sys

# git commit options that take a value as the next token (so that value is never read as a flag)
COMMIT_VALUE_OPTS = {'-m', '--message', '-F', '--file', '-C', '--reuse-message', '-c', '--reedit-message',
                     '--author', '--date', '-t', '--template', '--fixup', '--squash', '--cleanup', '-S'}


def tokens(segment):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def problem(command):
    if '--no-verify' in command:
        return 'skips the pre-commit check'
    if re.search(r'core\.hooks[Pp]ath', command):
        if re.search(r'--unset(?:-all)?\s+core\.hooks[Pp]ath', command):
            return 'turns the pre-commit check off'
        if re.search(r'-c\s*core\.hooks[Pp]ath', command):
            return 'overrides the hooks path for one command'
        for value in re.findall(r'core\.hooks[Pp]ath[\s=]+(\S+)', command):
            if value.strip('"\'') != '.githooks':
                return 'points git at a different hooks folder'
    for segment in re.split(r'&&|\|\||[;|\n]', command):
        t = tokens(segment)
        if 'git' not in t:
            continue
        t = t[t.index('git') + 1:]
        sub = next((x for x in t if not x.startswith('-')), None)
        if sub not in ('commit', 'add'):
            continue
        args, skip = t[t.index(sub) + 1:], False
        for a in args:
            if skip:
                skip = False
                continue
            if a == '--':
                break
            if sub == 'commit':
                if a in COMMIT_VALUE_OPTS:
                    skip = True
                elif re.fullmatch(r'-[a-zA-Z]+', a):
                    flags = a[1:]
                    for i, ch in enumerate(flags):
                        if ch in 'mFCct':        # value follows (attached or next token)
                            skip = i == len(flags) - 1
                            break
                        if ch == 'n':
                            return '`git commit -n` skips the pre-commit check'
            elif a == '--force' or re.fullmatch(r'-[a-zA-Z]*f[a-zA-Z]*', a):
                return '`git add -f` adds ignored files (where game files live)'
    return None


command = (json.load(sys.stdin).get('tool_input') or {}).get('command') or ''
why = problem(command)
if why:
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': f'Blocked: this {why}. The check keeps game files and keys out of the repo '
                                    '(docs/game-files-policy.md). Fix what it reports instead of bypassing it.',
    }}))
