#!/usr/bin/env python3
"""
Lightweight Analytics - Antigravity Kit
========================================
Track tool/skill/command usage with local SQLite storage.
No external dependencies required.

Usage:
    python3 analytics.py log --event "tool_used" --data '{"tool":"Edit"}'
    python3 analytics.py stats --last 7d
    python3 analytics.py stats --last 24h
    python3 analytics.py top-tools --last 7d
    python3 analytics.py top-skills --last 30d
"""

import sys
import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / ".data" / "analytics.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
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


def parse_duration(duration_str: str) -> timedelta:
    value = int(duration_str[:-1])
    unit = duration_str[-1]
    if unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    else:
        return timedelta(days=value)


def show_stats(last: str = "7d"):
    conn = get_db()
    delta = parse_duration(last)
    since = (datetime.utcnow() - delta).isoformat()

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


def show_top(category: str, last: str = "7d"):
    conn = get_db()
    delta = parse_duration(last)
    since = (datetime.utcnow() - delta).isoformat()

    if category == "tools":
        key = "tool"
    elif category == "skills":
        key = "skill"
    else:
        key = category

    results = conn.execute(
        f"""
        SELECT json_extract(data_json, '$.{key}') as name, COUNT(*) as cnt
        FROM events
        WHERE timestamp >= ? AND json_extract(data_json, '$.{key}') IS NOT NULL
        GROUP BY name ORDER BY cnt DESC LIMIT 20
        """,
        (since,),
    ).fetchall()
    conn.close()

    print(f"\n🏆 Top {category} - Last {last}")
    print(f"{'='*40}")
    if results:
        for name, count in results:
            bar = "█" * min(count, 30)
            print(f"  {name:<25} {bar} {count}")
    else:
        print("  No data yet.")
    print()


def main():
    parser = argparse.ArgumentParser(description="Antigravity Analytics")
    subparsers = parser.add_subparsers(dest="command")

    # log command
    log_parser = subparsers.add_parser("log", help="Log an event")
    log_parser.add_argument("--event", required=True, help="Event type")
    log_parser.add_argument("--data", default="{}", help="JSON data")
    log_parser.add_argument("--session", default="", help="Session ID")

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--last", default="7d", help="Time window (e.g. 24h, 7d, 4w)")

    # top-tools command
    top_tools = subparsers.add_parser("top-tools", help="Top used tools")
    top_tools.add_argument("--last", default="7d", help="Time window")

    # top-skills command
    top_skills = subparsers.add_parser("top-skills", help="Top used skills")
    top_skills.add_argument("--last", default="7d", help="Time window")

    args = parser.parse_args()

    if args.command == "log":
        log_event(args.event, args.data, args.session)
    elif args.command == "stats":
        show_stats(args.last)
    elif args.command == "top-tools":
        show_top("tools", args.last)
    elif args.command == "top-skills":
        show_top("skills", args.last)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
