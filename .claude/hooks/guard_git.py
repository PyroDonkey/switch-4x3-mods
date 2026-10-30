"""PreToolUse hook: deny shell commands that would skip or disable the repo's pre-commit check.

The pre-commit hook (.githooks/pre-commit -> scripts/check_repo.py) keeps game files and keys out of git;
see docs/game-files-policy.md. Reads the tool call as JSON on stdin.
"""
import json, re, sys

BLOCKED = [
    (re.compile(r'--no-verify\b'), 'skips the pre-commit check'),
    (re.compile(r'\bgit\b[^\n;&|]*\bcommit\b[^\n;&|]*\s-[a-zA-Z]*n[a-zA-Z]*\b'), '`git commit -n` skips the pre-commit check'),
    (re.compile(r'\bgit\b[^\n;&|]*\badd\b[^\n;&|]*\s(?:-[a-zA-Z]*f[a-zA-Z]*|--force)\b'), '`git add -f` adds ignored files (where game files live)'),
    (re.compile(r'-c\s+core\.hooksPath'), 'overrides the hooks path for one command'),
    (re.compile(r'core\.hooksPath\s+(?!\.githooks\b)\S'), 'points git at a different hooks folder'),
    (re.compile(r'--unset\s+core\.hooksPath'), 'turns the pre-commit check off'),
]

command = (json.load(sys.stdin).get('tool_input') or {}).get('command') or ''
for pattern, why in BLOCKED:
    if pattern.search(command):
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': f'Blocked: this {why}. The check keeps game files and keys out of the repo '
                                        '(docs/game-files-policy.md). Fix what it reports instead of bypassing it.',
        }}))
        break
