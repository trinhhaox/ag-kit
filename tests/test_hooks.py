"""Tests for the PreToolUse / PostToolUse hook scripts."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def run_hook(script, payload, env=None):
    proc = subprocess.run(
        ["bash", str(SCRIPTS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return proc.returncode, proc.stderr


class PrivacyGuardTest(unittest.TestCase):
    def assertBlocked(self, tool, tool_input, cwd=None):
        code, err = run_hook("privacy-guard.sh", {"tool_name": tool, "tool_input": tool_input, "cwd": cwd})
        self.assertEqual(code, 2, f"expected block for {tool} {tool_input}")
        self.assertIn("Privacy Guard", err)

    def assertAllowed(self, tool, tool_input, cwd=None):
        code, err = run_hook("privacy-guard.sh", {"tool_name": tool, "tool_input": tool_input, "cwd": cwd})
        self.assertEqual(code, 0, f"unexpected block for {tool} {tool_input}: {err}")

    def test_blocks_sensitive_reads(self):
        for path in [
            "/p/.env", "/p/.env.local", "/p/certs/server.pem", "/p/tls.key", "/home/u/.ssh/id_ed25519",
            "/home/u/.aws/credentials", "/p/config/credentials.json", "/p/secrets.yaml",
            "/p/client_secret.json", "/home/u/.cloudflared/abc.json", "/p/.secrets/token",
        ]:
            self.assertBlocked("Read", {"file_path": path})

    def test_allows_normal_and_template_files(self):
        for path in [
            "/p/.env.example", "/p/.env.sample", "/p/src/app.ts", "/p/src/SecretsPanel.tsx",
            "/p/src/auth/credentials.ts", "/p/node_modules/pkg/.env", "/p/src/environment.ts",
            "/p/docs/keyboard.md",
        ]:
            self.assertAllowed("Read", {"file_path": path})

    def test_bash_commands(self):
        for cmd in [
            "cat .env", "less config/.env.production", "head -n 5 ~/.ssh/id_rsa", "source .env",
            "grep TOKEN .env", "echo $API_KEY", "echo ${GITHUB_TOKEN}", "printenv DATABASE_URL",
            "cd app && cat secrets.json", "tail -f x.log; cat server.pem", "node x.js < .env",
        ]:
            self.assertBlocked("Bash", {"command": cmd})
        for cmd in [
            "ls -la", "cat .env.example", "cp .env.example .env", "npm run build", "cat package.json",
            "echo 'set API_KEY in your env'", "git add src/env.ts", "cat src/keys.ts",
            "grep -r API_KEY src/",
        ]:
            self.assertAllowed("Bash", {"command": cmd})

    def test_grep_pattern_is_not_a_path(self):
        self.assertAllowed("Grep", {"pattern": "\\.env", "path": "/p/src"})
        self.assertBlocked("Grep", {"pattern": "x", "path": "/p/.env"})

    def test_malformed_input_never_blocks(self):
        proc = subprocess.run(["bash", str(SCRIPTS / "privacy-guard.sh")], input="not json",
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)

    def test_freeze_scope(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".agent"))
            os.makedirs(os.path.join(root, "src", "auth"))
            with open(os.path.join(root, ".agent", ".freeze-scope"), "w") as f:
                f.write("src/auth/\nsrc/lib/api.ts\n")

            self.assertAllowed("Edit", {"file_path": f"{root}/src/auth/login.ts"}, cwd=root)
            self.assertAllowed("Write", {"file_path": f"{root}/src/lib/api.ts"}, cwd=root)
            self.assertAllowed("Edit", {"file_path": "src/auth/x.ts"}, cwd=root)  # relative path
            self.assertAllowed("Edit", {"file_path": "auth/x.ts"}, cwd=os.path.join(root, "src"))
            self.assertBlocked("Edit", {"file_path": f"{root}/src/app.ts"}, cwd=root)
            self.assertBlocked("Edit", {"file_path": f"{root}/src/authz/x.ts"}, cwd=root)  # prefix only
            self.assertBlocked("Write", {"file_path": f"{root}/src/lib/api.ts.bak"}, cwd=root)
            # reads are never scope-locked
            self.assertAllowed("Read", {"file_path": f"{root}/src/app.ts"}, cwd=root)


class QualityGateTest(unittest.TestCase):
    def gate(self, filename, content, env=None):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return run_hook("quality-gate.sh", {"tool_name": "Write", "tool_input": {"file_path": path}}, env)

    def test_valid_files_pass(self):
        self.assertEqual(self.gate("a.py", "x = 1\n")[0], 0)
        self.assertEqual(self.gate("a.json", '{"a": 1}')[0], 0)
        self.assertEqual(self.gate("a.sh", "echo ok\n")[0], 0)
        self.assertEqual(self.gate("README.md", "# hi")[0], 0)

    def test_tsconfig_comments_are_allowed(self):
        self.assertEqual(self.gate("tsconfig.json", '{\n // c\n "a": "http://x", /* b */ "c": [1,],\n}')[0], 0)

    def test_errors_are_reported_to_agent(self):
        code, err = self.gate("a.py", "def f(:\n")
        self.assertEqual(code, 2)
        self.assertIn("Python syntax error", err)
        code, err = self.gate("a.json", "{bad}")
        self.assertEqual(code, 2)
        self.assertIn("Invalid JSON", err)
        code, err = self.gate("a.sh", "if then fi (\n")
        self.assertEqual(code, 2)

    def test_quote_in_path_is_safe(self):
        code, err = self.gate("it's.py", "x = 1\n")
        self.assertEqual(code, 0, err)

    def test_warn_and_off_modes(self):
        code, err = self.gate("a.py", "def f(:\n", {"AG_QUALITY_GATE": "warn"})
        self.assertEqual(code, 0)
        self.assertIn("Python syntax error", err)
        code, err = self.gate("a.py", "def f(:\n", {"AG_QUALITY_GATE": "off"})
        self.assertEqual((code, err), (0, ""))

    def test_skip_dirs_match_whole_segments(self):
        # "dist" must not skip "distance/", but must skip "dist/"
        self.assertEqual(self.gate("distance/a.py", "def f(:\n")[0], 2)
        self.assertEqual(self.gate("dist/a.py", "def f(:\n")[0], 0)


if __name__ == "__main__":
    unittest.main()
