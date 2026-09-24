#!/usr/bin/env python3
"""
Lightweight Analytics - Antigravity Kit
========================================
Track tool/skill/command usage with local SQLite storage.
No external dependencies required.

Usage:
    python3 analytics.py hook < hook_payload.json   # used by analytics-hook.sh
    python3 analytics.py log --event "tool_used" --data '{"tool":"Edit"}'
    python3 analytics.py stats --last 7d
    python3 analytics.py stats --last 24h
    python3 analytics.py top-tools --last 7d
    python3 analytics.py top-skills --last 30d
    python3 analytics.py stats --last 7d --json
    python3 analytics.py prune --older-than 90d
"""

import os
import re
import sys
import json
import sqlite3
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("AG_ANALYTICS_DB", Path(__file__).parent.parent / ".data" / "analytics.db"))
SCHEMA_VERSION = 1
# SQLite's datetime('now') format - comparisons must use the same format,
# otherwise ' ' < 'T' silently drops events from the first day of the window.
SQL_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
SKILL_PATH = re.compile(r"(?:^|/)skills/([^/]+)/SKILL\.md$")


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.execute("PRAGMA busy_timeout = 5000")
    # Schema setup only once per database, not on every hook call.
    if conn.execute("PRAGMA user_version").fetchone()[0] >= SCHEMA_VERSION:
        return conn
    conn.execute("PRAGMA journal_mode = WAL")  # concurrent hooks don't block readers
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            event_type TEXT NOT NULL,
            data_json TEXT,
            session_id TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)
    """)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
    return conn


def log_event(event_type: str, data: str = "{}", session_id: str = ""):
    conn = get_db()
    conn.execute(
        "INSERT INTO events (event_type, data_json, session_id) VALUES (?, ?, ?)",
        (event_type, data, session_id),
    )
    conn.commit()
    conn.close()


def events_from_hook(payload: dict) -> list:
    """Turn a hook payload into analytics events (tool usage + skill usage)."""
    tool = payload.get("tool_name") or "unknown"
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    events = [("tool_used", {"tool": tool})]

    skill = None
    if tool == "Skill":
        skill = tool_input.get("skill") or tool_input.get("name")
    else:
        path = str(tool_input.get("file_path") or tool_input.get("path") or "").replace("\\", "/")
        m = SKILL_PATH.search(path)
        if m and tool in ("Read", "read_file"):
            skill = m.group(1)
    if skill:
        events.append(("skill_used", {"skill": str(skill)}))
    return events


def log_hook(stream=sys.stdin):
    try:
        payload = json.load(stream)
    except ValueError:
        return
    session = payload.get("session_id") or os.environ.get("CLAUDE_SESSION_ID", "")
    conn = get_db()
    conn.executemany(
        "INSERT INTO events (event_type, data_json, session_id) VALUES (?, ?, ?)",
        [(event, json.dumps(data), session) for event, data in events_from_hook(payload)],
    )
    conn.commit()
    conn.close()


def parse_duration(duration_str: str) -> timedelta:
    m = re.fullmatch(r"\s*(\d+)\s*([hdwm]?)\s*", duration_str or "")
    if not m:
        raise argparse.ArgumentTypeError(f"invalid duration '{duration_str}' (use e.g. 24h, 7d, 4w)")
    value, unit = int(m.group(1)), m.group(2) or "d"
    return {
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
        "w": timedelta(weeks=value),
        "m": timedelta(days=30 * value),
    }[unit]


def since_timestamp(last: str) -> str:
    return (datetime.now(timezone.utc) - parse_duration(last)).strftime(SQL_TIME_FORMAT)


def show_stats(last: str = "7d", as_json: bool = False):
    conn = get_db()
    since = since_timestamp(last)

    # Total events
    total = conn.execute(
        "SELECT COUNT(*) FROM events WHERE timestamp >= ?", (since,)
    ).fetchone()[0]

    # Events by type
    by_type = conn.execute(
        "SELECT event_type, COUNT(*) as cnt FROM events WHERE timestamp >= ? GROUP BY event_type ORDER BY cnt DESC",
        (since,),
    ).fetchall()

    # Daily breakdown
    daily = conn.execute(
        "SELECT date(timestamp) as day, COUNT(*) as cnt FROM events WHERE timestamp >= ? GROUP BY day ORDER BY day",
        (since,),
    ).fetchall()

    conn.close()

    if as_json:
        print(json.dumps({
            "window": last,
            "total": total,
            "by_type": dict(by_type),
            "daily": dict(daily),
        }, indent=2))
        return

    print(f"\n📊 Analytics - Last {last}")
    print(f"{'='*40}")
    print(f"Total events: {total}\n")

    if by_type:
        print("By type:")
        for event_type, count in by_type:
            print(f"  {event_type:<25} {count:>5}")

    if daily:
        print("\nDaily breakdown:")
        for day, count in daily:
            bar = "█" * min(count, 50)
            print(f"  {day}  {bar} {count}")

    print()


def show_top(category: str, last: str = "7d", as_json: bool = False, limit: int = 20):
    conn = get_db()
    since = since_timestamp(last)
    key = {"tools": "tool", "skills": "skill"}.get(category, category)
    json_path = f"$.{key}"

    results = conn.execute(
        """
        SELECT json_extract(data_json, ?) as name, COUNT(*) as cnt
        FROM events
        WHERE timestamp >= ? AND json_extract(data_json, ?) IS NOT NULL
        GROUP BY name ORDER BY cnt DESC LIMIT ?
        """,
        (json_path, since, json_path, limit),
    ).fetchall()
    conn.close()

    if as_json:
        print(json.dumps({"window": last, category: dict(results)}, indent=2))
        return

    print(f"\n🏆 Top {category} - Last {last}")
    print(f"{'='*40}")
    if results:
        for name, count in results:
            bar = "█" * min(count, 30)
            print(f"  {name:<25} {bar} {count}")
    else:
        print("  No data yet.")
    print()


def prune(older_than: str):
    conn = get_db()
    cur = conn.execute("DELETE FROM events WHERE timestamp < ?", (since_timestamp(older_than),))
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    print(f"🧹 Removed {cur.rowcount} events older than {older_than}")


def main():
    parser = argparse.ArgumentParser(description="Antigravity Analytics")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("hook", help="Log a PostToolUse hook payload read from stdin")

    # log command
    log_parser = subparsers.add_parser("log", help="Log an event")
    log_parser.add_argument("--event", required=True, help="Event type")
    log_parser.add_argument("--data", default="{}", help="JSON data")
    log_parser.add_argument("--session", default="", help="Session ID")

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--last", default="7d", help="Time window (e.g. 24h, 7d, 4w)")
    stats_parser.add_argument("--json", action="store_true", help="Machine-readable output")

    # top-tools / top-skills commands
    for name, help_text in (("top-tools", "Top used tools"), ("top-skills", "Top used skills")):
        top = subparsers.add_parser(name, help=help_text)
        top.add_argument("--last", default="7d", help="Time window")
        top.add_argument("--limit", type=int, default=20, help="Number of rows")
        top.add_argument("--json", action="store_true", help="Machine-readable output")

    prune_parser = subparsers.add_parser("prune", help="Delete old events")
    prune_parser.add_argument("--older-than", default="90d", help="Age threshold (e.g. 30d)")

    args = parser.parse_args()

    for value in (getattr(args, "last", None), getattr(args, "older_than", None)):
        if value is not None:
            try:
                parse_duration(value)
            except argparse.ArgumentTypeError as e:
                parser.error(str(e))

    if args.command == "hook":
        log_hook()
    elif args.command == "log":
        log_event(args.event, args.data, args.session)
    elif args.command == "stats":
        show_stats(args.last, args.json)
    elif args.command == "top-tools":
        show_top("tools", args.last, args.json, args.limit)
    elif args.command == "top-skills":
        show_top("skills", args.last, args.json, args.limit)
    elif args.command == "prune":
        prune(args.older_than)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
