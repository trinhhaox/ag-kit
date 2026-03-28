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
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

STATUS_FILE = "/tmp/ag-conductor-status.json"
WORKTREE_PREFIX = "/tmp/ag-wt-"
POLL_INTERVAL = 60


def load_config(config_path):
    with open(config_path) as f:
        content = f.read()

    if yaml:
        return yaml.safe_load(content)

    import re
    config = {"conductor": {"sessions": []}}
    current_session = None

    for line in content.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        m = re.match(r"\s+base_branch:\s*(.+)", line)
        if m:
            config["conductor"]["base_branch"] = m.group(1).strip()
            continue

        m = re.match(r"\s+max_concurrent:\s*(\d+)", line)
        if m:
            config["conductor"]["max_concurrent"] = int(m.group(1))
            continue

        if re.match(r"\s+- name:\s*(.+)", line):
            m = re.match(r"\s+- name:\s*(.+)", line)
            current_session = {"name": m.group(1).strip()}
            config["conductor"]["sessions"].append(current_session)
            continue

        if current_session:
            for field in ["task", "branch", "depends_on"]:
                m = re.match(rf'\s+{field}:\s*"?([^"]+)"?', line)
                if m:
                    current_session[field] = m.group(1).strip()

    return config


def read_status():
    if not os.path.exists(STATUS_FILE):
        return None
    with open(STATUS_FILE) as f:
        return json.load(f)


def write_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2, default=str)


def run_command(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def create_worktree(name, branch, base_branch):
    worktree_path = f"{WORKTREE_PREFIX}{name}"

    if os.path.exists(worktree_path):
        print(f"  Worktree already exists: {worktree_path}")
        return worktree_path

    code, out, err = run_command(f"git worktree add {worktree_path} -b {branch} {base_branch}")
    if code != 0:
        print(f"  Error creating worktree for {name}: {err}")
        return None

    return worktree_path


def spawn_session(session, worktree_path):
    task = session["task"]
    cmd = f'claude -p "{task}" --cwd {worktree_path}'

    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return process


def start(config_path):
    config = load_config(config_path)
    conductor = config["conductor"]
    base_branch = conductor.get("base_branch", "main")
    max_concurrent = conductor.get("max_concurrent", 5)
    sessions = conductor["sessions"]

    print(f"Conductor: {len(sessions)} sessions, base: {base_branch}, max concurrent: {max_concurrent}")

    status = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "config": config_path,
        "base_branch": base_branch,
        "sessions": []
    }

    processes = {}
    completed = set()
    pending = {s["name"]: s for s in sessions}

    while pending or processes:
        for name in list(processes.keys()):
            proc, sess_status = processes[name]
            if proc.poll() is not None:
                sess_status["status"] = "completed" if proc.returncode == 0 else "failed"
                sess_status["completed_at"] = datetime.now(timezone.utc).isoformat()
                sess_status["exit_code"] = proc.returncode
                completed.add(name)
                del processes[name]
                print(f"  [{name}] {'Completed' if proc.returncode == 0 else 'FAILED'}")
                write_status(status)

        for name, session in list(pending.items()):
            if len(processes) >= max_concurrent:
                break

            depends = session.get("depends_on")
            if depends and depends not in completed:
                continue

            print(f"  [{name}] Starting: {session['task'][:60]}...")
            worktree = create_worktree(name, session["branch"], base_branch)
            if not worktree:
                sess_status = {
                    "name": name,
                    "status": "failed",
                    "error": "Could not create worktree"
                }
                status["sessions"].append(sess_status)
                completed.add(name)
                del pending[name]
                continue

            proc = spawn_session(session, worktree)
            sess_status = {
                "name": name,
                "status": "running",
                "branch": session["branch"],
                "worktree": worktree,
                "pid": proc.pid,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "task": session["task"][:100]
            }
            status["sessions"].append(sess_status)
            processes[name] = (proc, sess_status)
            del pending[name]
            write_status(status)

        if processes:
            time.sleep(POLL_INTERVAL)

    print("\n=== CONDUCTOR SUMMARY ===")
    for s in status["sessions"]:
        icon = "OK" if s.get("status") == "completed" else "FAIL"
        print(f"  [{icon}] {s['name']}: {s.get('branch', 'n/a')}")

    write_status(status)
    print(f"\nStatus: {STATUS_FILE}")
    print("Next: Review changes per branch, then merge.")


def show_status():
    status = read_status()
    if not status:
        print("No conductor session found.")
        return

    print(f"Started: {status.get('started_at', 'unknown')}")
    print(f"Config: {status.get('config', 'unknown')}")
    print(f"Sessions:")
    for s in status.get("sessions", []):
        print(f"  [{s.get('status', '?').upper():9}] {s['name']}: {s.get('branch', 'n/a')}")
        if s.get("pid"):
            try:
                os.kill(s["pid"], 0)
                print(f"             PID {s['pid']} running")
            except ProcessLookupError:
                print(f"             PID {s['pid']} finished")


def stop_all():
    status = read_status()
    if not status:
        print("No conductor session found.")
        return

    for s in status.get("sessions", []):
        if s.get("status") == "running" and s.get("pid"):
            try:
                os.kill(s["pid"], signal.SIGTERM)
                print(f"  Stopped: {s['name']} (PID {s['pid']})")
                s["status"] = "stopped"
            except ProcessLookupError:
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
            run_command(f"git worktree remove {wt} --force")
            print(f"  Removed worktree: {wt}")

        branch = s.get("branch", "")
        if branch:
            run_command(f"git branch -D {branch}")
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
