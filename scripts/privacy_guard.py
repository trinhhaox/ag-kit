#!/usr/bin/env python3
"""
Privacy Guard - PreToolUse Hook
===============================
Blocks agent access to sensitive files (.env, keys, credentials...) and
enforces the /freeze scope lock for write operations.

Runs as a single short-lived process (no per-pattern subprocesses), so it adds
only a few milliseconds to every tool call.

Hook protocol (Claude Code / Gemini CLI):
    stdin : JSON {"tool_name": ..., "tool_input": {...}, "cwd": ...}
    exit 0: allow
    exit 2: block - the reason on stderr is shown to the agent
"""

import json
import os
import re
import sys

# Allowed exceptions are checked first (templates are safe to read).
ALLOWED = re.compile(
    r"\.env\.(example|sample|template|dist|defaults)$|(^|/)node_modules/",
    re.IGNORECASE,
)

# Sensitive path patterns, matched case-insensitively against the full path.
SENSITIVE = [
    (r"(^|/)\.env$", ".env"),
    (r"(^|/)\.env\.[^/]+$", ".env.*"),
    (r"\.(pem|key|p12|pfx|jks|keystore)$", "private key / certificate"),
    (r"(^|/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$", "SSH key"),
    (r"(^|/)\.ssh/", "SSH directory"),
    (r"(^|/)\.aws/credentials$", "AWS credentials"),
    (r"(^|/)\.(netrc|pgpass|npmrc|pypirc)$", "auth rc file"),
    (r"(^|/)\.docker/config\.json$", "Docker auth config"),
    (r"(^|/)\.cloudflared/", "cloudflared credentials"),
    # credentials.json, secrets.yaml, client_secret.json, ... (data files only,
    # so source files like `SecretsPanel.tsx` or `credentials.ts` stay editable)
    (
        r"(^|/)[^/]*(credential|secret)s?[^/]*\.(json|ya?ml|toml|ini|txt|xml|properties|conf|cfg|env)$",
        "credentials / secrets file",
    ),
    (r"(^|/)\.?secrets/", "secrets directory"),
]
SENSITIVE = [(re.compile(p, re.IGNORECASE), label) for p, label in SENSITIVE]

# Commands that print or copy file content.
_READERS = (
    r"cat|tac|less|more|head|tail|bat|nl|od|xxd|hexdump|strings|base64|"
    r"source|\.|scp|curl|awk|sed|grep|rg|Get-Content"
)
_SENSITIVE_ARG = (
    r"(\.env(\.[\w.-]+)?|\.pem|\.key|\.p12|\.pfx|id_(rsa|dsa|ecdsa|ed25519)|"
    r"\.aws/credentials|\.netrc|\.pgpass|\.cloudflared/|"
    r"[\w.-]*(credential|secret)s?[\w-]*\.(json|ya?ml|toml|ini|txt))"
)
_SECRET_VAR = r"\$\{?\w*(SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|PRIVATE_?KEY|DATABASE_URL)\w*\}?"

BASH_PATTERNS = [
    (
        re.compile(
            rf"(^|[\s;&|(`$])(?:{_READERS})\s[^;&|]*?{_SENSITIVE_ARG}(?![\w.-])",
            re.IGNORECASE,
        ),
        "reads a sensitive file",
    ),
    (re.compile(rf"<\s*\S*{_SENSITIVE_ARG}(?![\w.-])", re.IGNORECASE), "redirects a sensitive file"),
    (re.compile(rf"\b(echo|printf)\b[^;&|]*{_SECRET_VAR}", re.IGNORECASE), "prints a secret variable"),
    (
        re.compile(
            r"\bprintenv\s+\w*(SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|PRIVATE_?KEY|DATABASE_URL)",
            re.IGNORECASE,
        ),
        "prints a secret variable",
    ),
]

# Commands that are fine even though they mention a sensitive name.
BASH_ALLOWED = re.compile(r"\.env\.(example|sample|template|dist|defaults)\b", re.IGNORECASE)

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "write_file", "replace"}
READ_TOOLS = {"Read", "read_file", "read_many_files"}
SEARCH_TOOLS = {"Glob", "Grep", "glob", "search_file_content"}
SHELL_TOOLS = {"Bash", "run_shell_command"}


def block(reason: str) -> None:
    sys.stderr.write(f"Privacy Guard: {reason}\n")
    sys.exit(2)


def normalize(path: str) -> str:
    return path.replace("\\", "/")


def sensitive_reason(path: str):
    path = normalize(path)
    if not path or ALLOWED.search(path):
        return None
    for pattern, label in SENSITIVE:
        if pattern.search(path):
            return label
    return None


def check_path(path: str) -> None:
    label = sensitive_reason(path)
    if label:
        block(f"blocked access to sensitive file ({label}): {path}")


def check_command(cmd: str) -> None:
    stripped = BASH_ALLOWED.sub("", cmd)
    for pattern, label in BASH_PATTERNS:
        if pattern.search(stripped):
            block(f"blocked command that {label}. Command: {cmd[:200]}")


def find_scope_file(start: str):
    """Walk up from `start` looking for .agent/.freeze-scope."""
    d = os.path.abspath(start)
    while True:
        candidate = os.path.join(d, ".agent", ".freeze-scope")
        if os.path.isfile(candidate):
            return d, candidate
        parent = os.path.dirname(d)
        if parent == d:
            return None, None
        d = parent


def check_freeze_scope(path: str, cwd: str) -> None:
    root, scope_file = find_scope_file(cwd)
    if not scope_file:
        return

    target = os.path.normpath(os.path.join(cwd, path))
    try:
        with open(scope_file, encoding="utf-8") as f:
            scopes = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except OSError:
        return

    for scope in scopes:
        abs_scope = os.path.normpath(os.path.join(root, scope))
        # Exact file match, or anything inside the scoped directory.
        if target == abs_scope or target.startswith(abs_scope.rstrip(os.sep) + os.sep):
            return

    block(
        f"Scope Lock: '{path}' is outside the frozen scope ({', '.join(scopes)}). "
        "Run /unfreeze to remove the restriction."
    )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)  # never break the agent on malformed input

    tool = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        sys.exit(0)
    cwd = data.get("cwd") or os.getcwd()

    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or ""

    if tool in READ_TOOLS:
        check_path(file_path)
        for p in tool_input.get("paths") or []:
            check_path(str(p))
    elif tool in WRITE_TOOLS:
        if file_path:
            check_path(file_path)
            check_freeze_scope(file_path, cwd)
    elif tool in SHELL_TOOLS:
        cmd = tool_input.get("command") or ""
        if cmd:
            check_command(cmd)
    elif tool in SEARCH_TOOLS:
        for key in ("pattern", "path", "glob"):
            value = tool_input.get(key)
            # Grep's `pattern` is a regex over content, not a path.
            if value and not (tool in ("Grep", "search_file_content") and key == "pattern"):
                check_path(str(value))

    sys.exit(0)


if __name__ == "__main__":
    main()
