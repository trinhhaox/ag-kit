#!/usr/bin/env python3
"""
Auto Preview - Antigravity Kit
==============================
Manages (start/stop/status) the local development server for previewing the application.

Usage:
    python .agent/scripts/auto_preview.py start [port]
    python .agent/scripts/auto_preview.py stop
    python .agent/scripts/auto_preview.py status
"""

import os
import sys
import time
import json
import signal
import argparse
import subprocess
import urllib.request
from pathlib import Path

AGENT_DIR = Path(".agent")
PID_FILE = AGENT_DIR / "preview.pid"
STATE_FILE = AGENT_DIR / "preview.json"
LOG_FILE = AGENT_DIR / "preview.log"
IS_WINDOWS = sys.platform == "win32"

def get_project_root():
    return Path(".").resolve()

def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def detect_package_manager(root):
    for lockfile, pm in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
                         ("bun.lockb", "bun"), ("bun.lock", "bun")):
        if (root / lockfile).exists():
            return pm
    return "npm"


def get_start_command(root):
    pkg_file = root / "package.json"
    if not pkg_file.exists():
        return None

    with open(pkg_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    scripts = data.get("scripts", {})
    pm = detect_package_manager(root)
    for script in ("dev", "start"):
        if script in scripts:
            return [pm, "run", script]
    return None


def read_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        pass
    # Backward compatibility with the old plain PID file
    try:
        return {"pid": int(PID_FILE.read_text().strip()), "port": 3000}
    except (OSError, ValueError):
        return None


def clear_state():
    for f in (STATE_FILE, PID_FILE):
        if f.exists():
            f.unlink()


def health_check(url, timeout=2.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False

def start_server(port=3000, wait=0):
    state = read_state()
    if state and is_running(state["pid"]):
        print(f"⚠️  Preview already running (PID: {state['pid']}, http://localhost:{state.get('port', port)})")
        return

    root = get_project_root()
    cmd = get_start_command(root)
    
    if not cmd:
        print("❌ No 'dev' or 'start' script found in package.json")
        sys.exit(1)
    
    # Add port env var if needed (simple heuristic)
    env = os.environ.copy()
    env["PORT"] = str(port)
    
    print(f"🚀 Starting preview on port {port}: {' '.join(cmd)}")

    AGENT_DIR.mkdir(exist_ok=True)
    popen_kwargs = {}
    if IS_WINDOWS:
        # npm is a .cmd shim on Windows and needs the shell
        popen_kwargs["shell"] = True
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        cmd = subprocess.list2cmdline(cmd)
    else:
        # Own process group so `stop` also kills the dev server's children
        popen_kwargs["start_new_session"] = True

    with open(LOG_FILE, "w") as log:
        process = subprocess.Popen(
            cmd,
            cwd=str(root),
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            **popen_kwargs,
        )

    url = f"http://localhost:{port}"
    PID_FILE.write_text(str(process.pid))
    STATE_FILE.write_text(json.dumps({"pid": process.pid, "port": port, "url": url,
                                      "started_at": time.time()}))
    print(f"✅ Preview started! (PID: {process.pid})")
    print(f"   Logs: {LOG_FILE}")
    print(f"   URL: {url}")

    if wait:
        deadline = time.time() + wait
        while time.time() < deadline:
            if process.poll() is not None:
                print(f"❌ Server exited early (code {process.returncode}). See {LOG_FILE}")
                clear_state()
                sys.exit(1)
            if health_check(url):
                print("💚 Server is responding")
                return
            time.sleep(0.5)
        print(f"⚠️  Server not responding after {wait}s (still starting?)")

def stop_server():
    state = read_state()
    if not state:
        print("ℹ️  No preview server found.")
        return

    pid = state["pid"]
    try:
        if not is_running(pid):
            print("ℹ️  Process was not running.")
        elif IS_WINDOWS:
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])
            print(f"🛑 Preview stopped (PID: {pid})")
        else:
            # Gentle stop of the whole process group, then force after 5s
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if not is_running(pid):
                    break
                time.sleep(0.1)
            else:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass
            print(f"🛑 Preview stopped (PID: {pid})")
    except Exception as e:
        print(f"❌ Error stopping server: {e}")
    finally:
        clear_state()

def status_server(as_json=False):
    state = read_state()
    running = bool(state) and is_running(state["pid"])
    url = state.get("url") or f"http://localhost:{state.get('port', 3000)}" if state else None
    healthy = health_check(url) if running else False

    if as_json:
        print(json.dumps({"running": running, "pid": state["pid"] if running else None,
                          "url": url if running else None, "healthy": healthy,
                          "log": str(LOG_FILE)}))
        return

    print("\n=== Preview Status ===")
    if running:
        print(f"✅ Status: Running")
        print(f"🔢 PID: {state['pid']}")
        print(f"🌐 URL: {url}")
        print(f"{'💚' if healthy else '🟡'} Health: {'OK' if healthy else 'Not responding'}")
        print(f"📝 Logs: {LOG_FILE}")
    else:
        print("⚪ Status: Stopped")
    print("===================\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("port", nargs="?", type=int, default=3000)
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="After start, wait until the server responds")
    parser.add_argument("--json", action="store_true", help="JSON output for status")

    args = parser.parse_args()

    if args.action == "start":
        start_server(args.port, args.wait)
    elif args.action == "stop":
        stop_server()
    elif args.action == "status":
        status_server(args.json)

if __name__ == "__main__":
    main()
