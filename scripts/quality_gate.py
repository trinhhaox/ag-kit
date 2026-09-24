#!/usr/bin/env python3
"""
Quality Gate - PostToolUse Hook
===============================
Validates a file right after the agent edits it and feeds problems back to the
agent so it can fix them immediately.

Checks by extension:
    .ts/.tsx/.mts/.cts  TypeScript (local tsc, incremental, errors for this file only)
    .json               JSON syntax (tsconfig/jsconfig/.vscode allow comments)
    .yml/.yaml          YAML syntax (when PyYAML is installed)
    .py                 Python syntax (in-process compile)
    .sh/.bash           bash -n
    .prisma             prisma validate (local binary only)

Hook protocol:
    stdin : JSON {"tool_name": ..., "tool_input": {...}, "cwd": ...}
    exit 0: nothing to report
    exit 2: problems found - stderr is shown to the agent (the edit is kept)

Set AG_QUALITY_GATE=warn to only print warnings (always exit 0), or
AG_QUALITY_GATE=off to disable the gate.
"""

import json
import os
import re
import subprocess
import sys

SKIP_DIRS = {"node_modules", ".next", "dist", "build", ".git", "__pycache__", ".turbo", "coverage", ".venv", "venv"}
SKIP_FILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
JSONC_NAMES = re.compile(r"^(tsconfig|jsconfig)(\..*)?\.json$|\.jsonc$")
TSC_TIMEOUT = 25
MAX_LINES = 8


def find_up(start: str, *names: str):
    d = start
    while True:
        for name in names:
            if os.path.exists(os.path.join(d, name)):
                return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def run(cmd, cwd, timeout=TSC_TIMEOUT):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 0, ""  # a slow check must never block the agent
    except OSError:
        return 0, ""


def strip_json_comments(text: str) -> str:
    """Remove // and /* */ comments and trailing commas, respecting strings."""
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def check_typescript(path: str):
    root = find_up(os.path.dirname(path), "tsconfig.json")
    if not root:
        return None
    tsc = os.path.join(root, "node_modules", ".bin", "tsc")
    if not os.path.exists(tsc):
        pkg_root = find_up(root, "node_modules")
        tsc = os.path.join(pkg_root, "node_modules", ".bin", "tsc") if pkg_root else ""
    if not tsc or not os.path.exists(tsc):
        return None  # never `npx tsc`: without a local install it fetches the wrong package

    cache_dir = os.path.join(root, "node_modules", ".cache", "ag-kit")
    os.makedirs(cache_dir, exist_ok=True)
    cmd = [
        tsc, "--noEmit", "--pretty", "false",
        "--incremental", "--tsBuildInfoFile", os.path.join(cache_dir, "quality-gate.tsbuildinfo"),
    ]
    code, output = run(cmd, root)
    if code == 0:
        return None

    rel = os.path.relpath(path, root).replace(os.sep, "/")
    errors = [line for line in output.splitlines() if line.replace("\\", "/").startswith(rel + "(")]
    if not errors:
        return None
    extra = f"\n... and {len(errors) - MAX_LINES} more" if len(errors) > MAX_LINES else ""
    return f"TypeScript errors in {rel}:\n" + "\n".join(errors[:MAX_LINES]) + extra


def check_json(path: str):
    name = os.path.basename(path)
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    if JSONC_NAMES.search(name) or "/.vscode/" in path.replace("\\", "/"):
        text = strip_json_comments(text)
    try:
        json.loads(text)
    except ValueError as e:
        return f"Invalid JSON in {name}: {e}"
    return None


def check_yaml(path: str):
    try:
        import yaml
    except ImportError:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            list(yaml.safe_load_all(f))
    except yaml.YAMLError as e:
        return f"Invalid YAML in {os.path.basename(path)}:\n{e}"
    return None


def check_python(path: str):
    with open(path, "rb") as f:
        source = f.read()
    try:
        compile(source, path, "exec", dont_inherit=True)
    except SyntaxError as e:
        return f"Python syntax error in {os.path.basename(path)}:{e.lineno}: {e.msg}"
    except ValueError as e:
        return f"Python source error in {os.path.basename(path)}: {e}"
    return None


def check_shell(path: str):
    code, output = run(["bash", "-n", path], os.path.dirname(path), timeout=10)
    if code != 0:
        return f"Shell syntax error in {os.path.basename(path)}:\n{output.strip()}"
    return None


def check_prisma(path: str):
    root = find_up(os.path.dirname(path), "package.json")
    prisma = os.path.join(root, "node_modules", ".bin", "prisma") if root else ""
    if not prisma or not os.path.exists(prisma):
        return None
    code, output = run([prisma, "validate", "--schema", path], root)
    if code != 0:
        return f"Prisma validation error:\n{output.strip()[-1500:]}"
    return None


CHECKS = {
    "ts": check_typescript, "tsx": check_typescript, "mts": check_typescript, "cts": check_typescript,
    "json": check_json, "jsonc": check_json,
    "yml": check_yaml, "yaml": check_yaml,
    "py": check_python,
    "sh": check_shell, "bash": check_shell,
    "prisma": check_prisma,
}


def target_path(data: dict):
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path:
        return None
    path = os.path.abspath(os.path.join(data.get("cwd") or os.getcwd(), path))
    if not os.path.isfile(path):
        return None
    parts = set(path.replace("\\", "/").split("/"))
    if parts & SKIP_DIRS or os.path.basename(path) in SKIP_FILES:
        return None
    return path


def evaluate(path: str):
    ext = path.rsplit(".", 1)[-1].lower() if "." in os.path.basename(path) else ""
    check = CHECKS.get(ext)
    if not check:
        return None
    try:
        return check(path)
    except (OSError, UnicodeDecodeError):
        return None


def main() -> None:
    mode = os.environ.get("AG_QUALITY_GATE", "block").lower()
    if mode == "off":
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)

    path = target_path(data)
    problem = evaluate(path) if path else None
    if not problem:
        sys.exit(0)

    sys.stderr.write(f"Quality Gate: {problem}\n")
    sys.exit(0 if mode == "warn" else 2)


if __name__ == "__main__":
    main()
