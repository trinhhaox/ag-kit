"""Tests for analytics, the check runner and the parallel conductor."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CONDUCTOR = ROOT / "skills" / "parallel-conductor" / "scripts" / "conductor.py"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(CONDUCTOR.parent))

import analytics  # noqa: E402
import conductor  # noqa: E402


class AnalyticsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "a.db")
        self.env = {**os.environ, "AG_ANALYTICS_DB": self.db}

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, stdin=None):
        return subprocess.run([sys.executable, str(SCRIPTS / "analytics.py"), *args], input=stdin,
                              capture_output=True, text=True, env=self.env)

    def test_hook_logs_tool_and_skill(self):
        payload = {"tool_name": "Read", "tool_input": {"file_path": "/x/.agent/skills/clean-code/SKILL.md"}}
        subprocess.run(["bash", str(SCRIPTS / "analytics-hook.sh")], input=json.dumps(payload),
                       text=True, env=self.env, check=True)
        self.cli("hook", stdin=json.dumps({"tool_name": "Skill", "tool_input": {"skill": "brainstorming"}}))

        top = json.loads(self.cli("top-skills", "--json").stdout)
        self.assertEqual(top["skills"], {"clean-code": 1, "brainstorming": 1})
        tools = json.loads(self.cli("top-tools", "--json").stdout)
        self.assertEqual(tools["tools"], {"Read": 1, "Skill": 1})

    def test_window_includes_events_from_first_day(self):
        # Regression: comparing SQLite 'YYYY-MM-DD HH:MM:SS' against isoformat
        # ('...T...') dropped events on the first day of the window.
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL "
                     "DEFAULT (datetime('now')), event_type TEXT NOT NULL, data_json TEXT, session_id TEXT)")
        conn.execute("INSERT INTO events (timestamp, event_type, data_json) "
                     "VALUES (datetime('now', '-20 hours'), 'tool_used', '{\"tool\":\"Edit\"}')")
        conn.commit()
        conn.close()
        stats = json.loads(self.cli("stats", "--last", "24h", "--json").stdout)
        self.assertEqual(stats["total"], 1)

    def test_invalid_duration(self):
        r = self.cli("stats", "--last", "abc")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid duration", r.stderr)

    def test_events_from_hook_ignores_unrelated_reads(self):
        events = analytics.events_from_hook({"tool_name": "Read", "tool_input": {"file_path": "/x/src/SKILL.md"}})
        self.assertEqual(events, [("tool_used", {"tool": "Read"})])


class CheckRunnerTest(unittest.TestCase):
    def test_checklist_runs_in_parallel_and_reports_json(self):
        with tempfile.TemporaryDirectory() as proj:
            r = subprocess.run([sys.executable, str(SCRIPTS / "checklist.py"), proj, "--json", "-j", "4"],
                               capture_output=True, text=True)
            report = json.loads(r.stdout)
            names = [x["name"] for x in report["results"]]
            self.assertEqual(names[:2], ["Security Scan", "Lint Check"])  # priority order kept
            self.assertNotIn("Lighthouse Audit", names)  # needs --url

    def test_missing_script_is_skipped(self):
        import check_runner
        r = check_runner.run_check(check_runner.Check("X", "skills/nope/x.py"), Path("."), None, 5)
        self.assertTrue(r.skipped)


class ConductorConfigTest(unittest.TestCase):
    def cfg(self, sessions):
        return {"conductor": {"sessions": sessions}}

    def test_rejects_unknown_dependency(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            conductor.validate_config(self.cfg([{"name": "a", "task": "t", "branch": "b", "depends_on": "zzz"}]))

    def test_rejects_cycle(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            conductor.validate_config(self.cfg([
                {"name": "a", "task": "t", "branch": "a", "depends_on": "b"},
                {"name": "b", "task": "t", "branch": "b", "depends_on": ["a"]},
            ]))

    def test_rejects_unsafe_name(self):
        with self.assertRaisesRegex(ValueError, "invalid session name"):
            conductor.validate_config(self.cfg([{"name": "a; rm -rf /", "task": "t", "branch": "b"}]))

    def test_fallback_parser_without_yaml(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(textwrap.dedent("""\
                conductor:
                  base_branch: main
                  max_concurrent: 2
                  sessions:
                    - name: db
                      task: "Create schema"
                      branch: feat/db
                    - name: api
                      task: "Build API"
                      branch: feat/api
                      depends_on: [db]
                """))
        saved = conductor.yaml
        conductor.yaml = None
        try:
            cfg = conductor.load_config(f.name)
        finally:
            conductor.yaml = saved
            os.unlink(f.name)
        c = cfg["conductor"]
        self.assertEqual((c["base_branch"], c["max_concurrent"]), ("main", 2))
        self.assertEqual(c["sessions"][1]["depends_on"], ["db"])


@unittest.skipUnless(subprocess.run(["git", "--version"], capture_output=True).returncode == 0, "git missing")
class ConductorRunTest(unittest.TestCase):
    """End-to-end run with a fake `claude` binary."""

    def test_dependencies_build_on_each_other_and_failures_propagate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            bindir = os.path.join(tmp, "bin")
            os.makedirs(repo)
            os.makedirs(bindir)
            # Fake claude: writes a file named after the task, commits it; "fail" tasks exit 1.
            # Also prints >64KB to prove output can't deadlock the child.
            with open(os.path.join(bindir, "claude"), "w") as f:
                f.write(textwrap.dedent("""\
                    #!/usr/bin/env bash
                    task="$2"
                    head -c 200000 /dev/zero | tr '\\0' 'x'
                    [ "$task" = fail ] && exit 1
                    echo "$task" > "$task.txt" && git add . && git -c user.email=t@t -c user.name=t commit -qm "$task"
                    """))
            os.chmod(os.path.join(bindir, "claude"), 0o755)

            git = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)  # noqa: E731
            git("init", "-q", "-b", "main")
            git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")

            uid = os.urandom(4).hex()
            names = {k: f"{k}-{uid}" for k in ("db", "api", "bad", "after")}
            cfg_path = os.path.join(tmp, "c.yaml")
            with open(cfg_path, "w") as f:
                f.write(textwrap.dedent(f"""\
                    conductor:
                      base_branch: main
                      sessions:
                        - name: {names['db']}
                          task: "db"
                          branch: t/{names['db']}
                        - name: {names['api']}
                          task: "api"
                          branch: t/{names['api']}
                          depends_on: {names['db']}
                        - name: {names['bad']}
                          task: "fail"
                          branch: t/{names['bad']}
                        - name: {names['after']}
                          task: "x"
                          branch: t/{names['after']}
                          depends_on: [{names['bad']}]
                    """))

            status_file = os.path.join(tmp, "status.json")
            env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "AG_CONDUCTOR_STATUS": status_file,
                   "PYTHONPATH": str(CONDUCTOR.parent)}
            script = "import conductor, sys; conductor.POLL_INTERVAL = 0.1; sys.argv[0] = 'c'; conductor.main()"
            try:
                r = subprocess.run([sys.executable, "-c", script, cfg_path], cwd=repo, env=env,
                                   capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)  # one session failed

                with open(status_file) as f:
                    status = {s["name"]: s for s in json.load(f)["sessions"]}
                self.assertEqual(status[names["db"]]["status"], "completed")
                self.assertEqual(status[names["api"]]["status"], "completed")
                self.assertEqual(status[names["bad"]]["status"], "failed")
                self.assertEqual(status[names["after"]]["status"], "skipped")
                # api was started from db's branch, so it contains db's work
                self.assertTrue(os.path.exists(os.path.join(status[names["api"]]["worktree"], "db.txt")))
            finally:
                for name in names.values():
                    subprocess.run(["git", "worktree", "remove", "--force", f"/tmp/ag-wt-{name}"],
                                   cwd=repo, capture_output=True)


if __name__ == "__main__":
    unittest.main()
