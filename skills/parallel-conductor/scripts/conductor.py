#!/usr/bin/env python3
"""
Parallel Conductor — Multi-session Claude Code orchestrator.

Usage:
  conductor.py <config.yaml>     Start sessions from config
  conductor.py --status          Show session status
  conductor.py --stop            Stop all running sessions
  conductor.py --cleanup         Remove worktrees and branches
"""

import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

STATUS_FILE = os.environ.get("AG_CONDUCTOR_STATUS", "/tmp/ag-conductor-status.json")
WORKTREE_PREFIX = "/tmp/ag-wt-"
LOG_DIR = "/tmp/ag-conductor-logs"
POLL_INTERVAL = 2  # seconds; completion is detected quickly, polling is cheap
DEFAULT_CLAUDE_ARGS = ["--permission-mode", "acceptEdits"]
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def now():
    return datetime.now(timezone.utc).isoformat()


def _as_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(v).strip() for v in value]


def load_config(config_path):
    with open(config_path) as f:
        content = f.read()

    if yaml:
        config = yaml.safe_load(content)
    else:
        config = {"conductor": {"sessions": []}}
        current_session = None

        for line in content.split("\n"):
            line = line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue

            m = re.match(r"\s+base_branch:\s*(.+)", line)
            if m and current_session is None:
                config["conductor"]["base_branch"] = m.group(1).strip().strip("\"'")
                continue

            m = re.match(r"\s+max_concurrent:\s*(\d+)", line)
            if m and current_session is None:
                config["conductor"]["max_concurrent"] = int(m.group(1))
                continue

            m = re.match(r"\s+- name:\s*(.+)", line)
            if m:
                current_session = {"name": m.group(1).strip().strip("\"'")}
                config["conductor"]["sessions"].append(current_session)
                continue

            if current_session is not None:
                for field in ["task", "branch", "depends_on"]:
                    m = re.match(rf"\s+{field}:\s*(.+)", line)
                    if m:
                        value = m.group(1).strip()
                        if value.startswith("[") and value.endswith("]"):
                            value = [v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip()]
                        else:
                            value = value.strip("\"'")
                        current_session[field] = value

    validate_config(config)
    return config


def validate_config(config):
    """Fail fast on configs that would otherwise hang or misbehave at runtime."""
    conductor = (config or {}).get("conductor") or {}
    sessions = conductor.get("sessions") or []
    if not sessions:
        raise ValueError("config has no sessions")

    names = set()
    for s in sessions:
        for key in ("name", "task", "branch"):
            if not s.get(key):
                raise ValueError(f"session {s.get('name', '?')!r} is missing '{key}'")
        if not NAME_RE.match(s["name"]):
            raise ValueError(f"invalid session name {s['name']!r} (use letters, digits, '.', '_', '-')")
        if s["name"] in names:
            raise ValueError(f"duplicate session name {s['name']!r}")
        names.add(s["name"])
        s["depends_on"] = _as_list(s.get("depends_on"))

    for s in sessions:
        unknown = [d for d in s["depends_on"] if d not in names]
        if unknown:
            raise ValueError(f"session {s['name']!r} depends on unknown session(s): {', '.join(unknown)}")

    # Cycle detection (DFS)
    graph = {s["name"]: s["depends_on"] for s in sessions}
    state = {}

    def visit(n, path):
        if state.get(n) == "done":
            return
        if state.get(n) == "visiting":
            raise ValueError(f"dependency cycle: {' -> '.join(path + [n])}")
        state[n] = "visiting"
        for d in graph[n]:
            visit(d, path + [n])
        state[n] = "done"

    for n in graph:
        visit(n, [])


def read_status():
    if not os.path.exists(STATUS_FILE):
        return None
    with open(STATUS_FILE) as f:
        return json.load(f)


def write_status(status):
    tmp = STATUS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(status, f, indent=2, default=str)
    os.replace(tmp, STATUS_FILE)  # atomic: --status never reads a half-written file


def git(*args, cwd=None):
    result = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def create_worktree(name, branch, start_point, merge_branches=()):
    """Create a worktree on a new branch from start_point, merging extra branches."""
    worktree_path = f"{WORKTREE_PREFIX}{name}"

    if os.path.exists(worktree_path):
        print(f"  Worktree already exists: {worktree_path}")
        return worktree_path, None

    code, _, err = git("worktree", "add", worktree_path, "-b", branch, start_point)
    if code != 0:
        return None, f"could not create worktree: {err}"

    for other in merge_branches:
        code, _, err = git("merge", "--no-edit", other, cwd=worktree_path)
        if code != 0:
            git("merge", "--abort", cwd=worktree_path)
            return None, f"could not merge dependency branch {other}: {err}"

    return worktree_path, None


def spawn_session(session, worktree_path, claude_args):
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"{session['name']}.log")
    log = open(log_path, "w")
    # Output goes to a file: an unread PIPE fills up (~64KB) and hangs the child.
    process = subprocess.Popen(
        ["claude", "-p", session["task"], *claude_args],
        cwd=worktree_path,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.close()
    return process, log_path


def start(config_path):
    try:
        config = load_config(config_path)
    except (ValueError, OSError) as e:
        print(f"Invalid config: {e}")
        sys.exit(1)

    conductor = config["conductor"]
    base_branch = conductor.get("base_branch", "main")
    max_concurrent = int(conductor.get("max_concurrent", 5))
    claude_args = conductor.get("claude_args")
    claude_args = shlex.split(claude_args) if isinstance(claude_args, str) else (claude_args or DEFAULT_CLAUDE_ARGS)
    sessions = conductor["sessions"]
    branch_of = {s["name"]: s["branch"] for s in sessions}

    print(f"Conductor: {len(sessions)} sessions, base: {base_branch}, max concurrent: {max_concurrent}")

    status = {
        "started_at": now(),
        "config": os.path.abspath(config_path),
        "base_branch": base_branch,
        "sessions": [],
    }

    processes = {}
    succeeded, failed = set(), set()
    pending = {s["name"]: s for s in sessions}

    def finish(name, sess_status, state, error=None):
        sess_status["status"] = state
        sess_status["completed_at"] = now()
        if error:
            sess_status["error"] = error
        (succeeded if state == "completed" else failed).add(name)

    while pending or processes:
        for name in list(processes.keys()):
            proc, sess_status = processes[name]
            if proc.poll() is not None:
                sess_status["exit_code"] = proc.returncode
                finish(name, sess_status, "completed" if proc.returncode == 0 else "failed")
                del processes[name]
                print(f"  [{name}] {'Completed' if proc.returncode == 0 else 'FAILED'} "
                      f"(log: {sess_status['log']})")
                write_status(status)

        for name, session in list(pending.items()):
            deps = session["depends_on"]

            # A failed dependency means this session can never run correctly.
            blocked_by = [d for d in deps if d in failed]
            if blocked_by:
                sess_status = {"name": name, "branch": session["branch"], "task": session["task"][:100]}
                finish(name, sess_status, "skipped", f"dependency failed: {', '.join(blocked_by)}")
                status["sessions"].append(sess_status)
                del pending[name]
                print(f"  [{name}] SKIPPED (dependency failed: {', '.join(blocked_by)})")
                write_status(status)
                continue

            if len(processes) >= max_concurrent or any(d not in succeeded for d in deps):
                continue

            # Build on top of dependencies so their changes are visible.
            start_point = branch_of[deps[0]] if deps else base_branch
            merge_branches = [branch_of[d] for d in deps[1:]]

            print(f"  [{name}] Starting from {start_point}: {session['task'][:60]}...")
            worktree, error = create_worktree(name, session["branch"], start_point, merge_branches)
            if not worktree:
                sess_status = {"name": name, "branch": session["branch"], "task": session["task"][:100]}
                finish(name, sess_status, "failed", error)
                status["sessions"].append(sess_status)
                del pending[name]
                print(f"  [{name}] FAILED: {error}")
                write_status(status)
                continue

            try:
                proc, log_path = spawn_session(session, worktree, claude_args)
            except OSError as e:
                sess_status = {"name": name, "branch": session["branch"], "worktree": worktree}
                finish(name, sess_status, "failed", f"could not start claude: {e}")
                status["sessions"].append(sess_status)
                del pending[name]
                print(f"  [{name}] FAILED: could not start claude: {e}")
                write_status(status)
                continue

            sess_status = {
                "name": name,
                "status": "running",
                "branch": session["branch"],
                "base": start_point,
                "worktree": worktree,
                "pid": proc.pid,
                "log": log_path,
                "started_at": now(),
                "task": session["task"][:100],
            }
            status["sessions"].append(sess_status)
            processes[name] = (proc, sess_status)
            del pending[name]
            write_status(status)

        if processes:
            time.sleep(POLL_INTERVAL)

    status["finished_at"] = now()
    print("\n=== CONDUCTOR SUMMARY ===")
    for s in status["sessions"]:
        icon = {"completed": "OK", "skipped": "SKIP"}.get(s.get("status"), "FAIL")
        extra = f" — {s['error']}" if s.get("error") else ""
        print(f"  [{icon}] {s['name']}: {s.get('branch', 'n/a')}{extra}")

    write_status(status)
    print(f"\nStatus: {STATUS_FILE}")
    print(f"Logs:   {LOG_DIR}/")
    print("Next: Review changes per branch, then merge.")
    sys.exit(1 if failed else 0)


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def show_status():
    status = read_status()
    if not status:
        print("No conductor session found.")
        return

    print(f"Started: {status.get('started_at', 'unknown')}")
    print(f"Config: {status.get('config', 'unknown')}")
    print("Sessions:")
    for s in status.get("sessions", []):
        print(f"  [{s.get('status', '?').upper():9}] {s['name']}: {s.get('branch', 'n/a')}")
        if s.get("status") == "running" and s.get("pid"):
            state = "running" if _alive(s["pid"]) else "finished"
            print(f"             PID {s['pid']} {state}")
        if s.get("log"):
            print(f"             log: {s['log']}")
        if s.get("error"):
            print(f"             error: {s['error']}")


def stop_all():
    status = read_status()
    if not status:
        print("No conductor session found.")
        return

    for s in status.get("sessions", []):
        if s.get("status") == "running" and s.get("pid"):
            try:
                # Sessions run in their own process group: stop claude and its children.
                os.killpg(s["pid"], signal.SIGTERM)
                print(f"  Stopped: {s['name']} (PID {s['pid']})")
                s["status"] = "stopped"
            except (ProcessLookupError, PermissionError):
                s["status"] = "finished"

    write_status(status)
    print("All sessions stopped.")


def cleanup():
    status = read_status()
    if not status:
        print("No conductor session found.")
        return

    for s in status.get("sessions", []):
        wt = s.get("worktree", "")
        if wt and os.path.exists(wt):
            git("worktree", "remove", wt, "--force")
            print(f"  Removed worktree: {wt}")

        branch = s.get("branch", "")
        if branch:
            git("branch", "-D", branch)
            print(f"  Deleted branch: {branch}")

    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)
    print("Cleanup complete.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    arg = sys.argv[1]

    if arg == "--status":
        show_status()
    elif arg == "--stop":
        stop_all()
    elif arg == "--cleanup":
        cleanup()
    elif os.path.exists(arg):
        start(arg)
    else:
        print(f"Error: Config file not found: {arg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
