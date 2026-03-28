#!/usr/bin/env python3
"""
Browser Daemon — Persistent Playwright HTTP server.
Provides sub-200ms browser commands via localhost API.

Usage: python browser-daemon.py [--port 9222] [--headless]
"""

import argparse
import json
import os
import signal
import sys
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


TOKEN = str(uuid.uuid4())
TOKEN_FILE = "/tmp/ag-browser-token"
IDLE_TIMEOUT = 1800  # 30 minutes
last_activity = time.time()

playwright_instance = None
browser = None
page = None
refs = {}
ref_counter = 0


def build_refs():
    global refs, ref_counter
    refs = {}
    ref_counter = 0

    try:
        snapshot = page.accessibility.snapshot()
    except Exception:
        return refs

    if not snapshot:
        return refs

    interactive_roles = {
        "button", "link", "textbox", "checkbox", "radio",
        "combobox", "listbox", "option", "slider", "spinbutton",
        "switch", "tab", "menuitem", "searchbox", "textarea"
    }

    def walk(node, depth=0):
        global ref_counter
        role = node.get("role", "")
        name = node.get("name", "")

        if role in interactive_roles and name:
            ref_counter += 1
            ref_id = f"@e{ref_counter}"
            refs[ref_id] = {
                "role": role,
                "name": name,
            }

        for child in node.get("children", []):
            walk(child, depth + 1)

    walk(snapshot)
    return refs


def get_locator(ref_or_selector):
    if ref_or_selector.startswith("@e"):
        if ref_or_selector not in refs:
            raise ValueError(f"Unknown ref: {ref_or_selector}. Run 'refs' to see current mapping.")
        info = refs[ref_or_selector]
        return page.get_by_role(info["role"], name=info["name"])
    return page.locator(ref_or_selector)


class BrowserHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _check_auth(self):
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {TOKEN}":
            self._respond(401, {"error": "Unauthorized"})
            return False
        global last_activity
        last_activity = time.time()
        return True

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if not self._check_auth():
            return

        if self.path == "/refs":
            ref_list = {k: f'{v["role"]} "{v["name"]}"' for k, v in refs.items()}
            self._respond(200, {"refs": ref_list})

        elif self.path == "/status":
            try:
                url = page.url if page else ""
                title = page.title() if page else ""
            except Exception:
                url, title = "", ""
            self._respond(200, {
                "url": url,
                "title": title,
                "refs_count": len(refs)
            })
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        if not self._check_auth():
            return

        body = self._read_body()

        try:
            if self.path == "/navigate":
                url = body["url"]
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                build_refs()
                self._respond(200, {"title": page.title(), "url": page.url, "refs_count": len(refs)})

            elif self.path == "/click":
                target = body.get("ref") or body.get("selector", "")
                locator = get_locator(target)
                locator.click(timeout=5000)
                page.wait_for_load_state("domcontentloaded", timeout=5000)
                build_refs()
                self._respond(200, {"ok": True})

            elif self.path == "/type":
                target = body.get("ref") or body.get("selector", "")
                text = body["text"]
                locator = get_locator(target)
                locator.fill(text, timeout=5000)
                self._respond(200, {"ok": True})

            elif self.path == "/screenshot":
                full_page = body.get("full_page", False)
                screenshot_bytes = page.screenshot(full_page=full_page)
                import base64
                b64 = base64.b64encode(screenshot_bytes).decode()
                self._respond(200, {"image": b64, "size": len(screenshot_bytes)})

            elif self.path == "/evaluate":
                script = body["script"]
                result = page.evaluate(script)
                self._respond(200, {"result": result})

            elif self.path == "/wait":
                target = body.get("ref") or body.get("selector", "")
                timeout = body.get("timeout", 5000)
                locator = get_locator(target)
                locator.wait_for(timeout=timeout)
                self._respond(200, {"ok": True})

            elif self.path == "/stop":
                self._respond(200, {"ok": True, "message": "Shutting down"})
                threading.Thread(target=shutdown).start()

            else:
                self._respond(404, {"error": f"Unknown endpoint: {self.path}"})

        except Exception as e:
            self._respond(500, {"error": str(e)})


def shutdown():
    time.sleep(0.5)
    if browser:
        browser.close()
    if playwright_instance:
        playwright_instance.stop()
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    os._exit(0)


def idle_watchdog():
    while True:
        time.sleep(60)
        if time.time() - last_activity > IDLE_TIMEOUT:
            print(f"Idle for {IDLE_TIMEOUT}s, shutting down.")
            shutdown()


def main():
    global playwright_instance, browser, page

    parser = argparse.ArgumentParser(description="Browser Daemon")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--headless", action="store_true", default=False)
    args = parser.parse_args()

    with open(TOKEN_FILE, "w") as f:
        f.write(TOKEN)
    os.chmod(TOKEN_FILE, 0o600)

    pw = sync_playwright().start()
    playwright_instance = pw
    browser = pw.chromium.launch(headless=args.headless)
    page = browser.new_page()

    watchdog = threading.Thread(target=idle_watchdog, daemon=True)
    watchdog.start()

    signal.signal(signal.SIGTERM, lambda *_: shutdown())
    signal.signal(signal.SIGINT, lambda *_: shutdown())

    server = HTTPServer(("127.0.0.1", args.port), BrowserHandler)
    print(f"Browser daemon running on http://127.0.0.1:{args.port}")
    print(f"Token: {TOKEN}")
    print(f"Token file: {TOKEN_FILE}")
    print(f"Idle timeout: {IDLE_TIMEOUT}s")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
