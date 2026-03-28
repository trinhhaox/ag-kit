#!/usr/bin/env python3
"""
Browser CLI — Send commands to the browser daemon.

Usage:
  browser-cli.py navigate <url>
  browser-cli.py click <ref|selector>
  browser-cli.py type <ref|selector> <text>
  browser-cli.py screenshot [--full]
  browser-cli.py evaluate <script>
  browser-cli.py wait <ref|selector> [--timeout ms]
  browser-cli.py refs
  browser-cli.py status
  browser-cli.py stop
"""

import json
import os
import sys
import urllib.request

TOKEN_FILE = "/tmp/ag-browser-token"
DEFAULT_PORT = 9222


def get_token():
    if not os.path.exists(TOKEN_FILE):
        print("Error: Browser daemon not running. Start with: python browser-daemon.py &")
        sys.exit(1)
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def request(method, path, body=None, port=DEFAULT_PORT):
    token = get_token()
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"Error: Cannot connect to daemon on port {port}. Is it running?")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "navigate":
        if len(args) < 2:
            print("Usage: browser-cli.py navigate <url>")
            sys.exit(1)
        result = request("POST", "/navigate", {"url": args[1]})
        print(f"Navigated to: {result.get('title', '')} ({result.get('url', '')})")
        print(f"Found {result.get('refs_count', 0)} interactive elements")

    elif cmd == "click":
        if len(args) < 2:
            print("Usage: browser-cli.py click <ref|selector>")
            sys.exit(1)
        request("POST", "/click", {"ref": args[1]})
        print(f"Clicked: {args[1]}")

    elif cmd == "type":
        if len(args) < 3:
            print("Usage: browser-cli.py type <ref|selector> <text>")
            sys.exit(1)
        request("POST", "/type", {"ref": args[1], "text": " ".join(args[2:])})
        print(f"Typed into: {args[1]}")

    elif cmd == "screenshot":
        full = "--full" in args
        result = request("POST", "/screenshot", {"full_page": full})
        import base64
        img_data = base64.b64decode(result["image"])
        path = "/tmp/ag-screenshot.png"
        with open(path, "wb") as f:
            f.write(img_data)
        print(f"Screenshot saved: {path} ({result.get('size', 0)} bytes)")

    elif cmd == "evaluate":
        if len(args) < 2:
            print("Usage: browser-cli.py evaluate <script>")
            sys.exit(1)
        result = request("POST", "/evaluate", {"script": " ".join(args[1:])})
        print(json.dumps(result.get("result"), indent=2))

    elif cmd == "wait":
        if len(args) < 2:
            print("Usage: browser-cli.py wait <ref|selector> [--timeout ms]")
            sys.exit(1)
        timeout = 5000
        if "--timeout" in args:
            idx = args.index("--timeout")
            timeout = int(args[idx + 1])
        request("POST", "/wait", {"ref": args[1], "timeout": timeout})
        print(f"Element ready: {args[1]}")

    elif cmd == "refs":
        result = request("GET", "/refs")
        for ref_id, desc in sorted(result.get("refs", {}).items()):
            print(f"  {ref_id}: {desc}")
        if not result.get("refs"):
            print("  (no interactive elements found)")

    elif cmd == "status":
        result = request("GET", "/status")
        print(f"URL: {result.get('url', 'none')}")
        print(f"Title: {result.get('title', 'none')}")
        print(f"Refs: {result.get('refs_count', 0)} elements")

    elif cmd == "stop":
        request("POST", "/stop")
        print("Daemon stopped.")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
